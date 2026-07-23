"""
AViD Journal — Production server.

Serves the landing page + Google OAuth + Gradio demo + API.
Deploy: uvicorn server:app --host 0.0.0.0 --port 7860
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import gradio as gr

# ── Path setup ─────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.auth import verify_google_token, create_session, get_session, delete_session
from src.users import upsert_user, log_action, get_user, stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("avid-server")

# ── Config ─────────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
DEV_MODE = os.environ.get("AVID_DEV_MODE", "0") == "1"
LANDING_HTML = Path(os.environ.get(
    "LANDING_HTML",
    "D:/Mis documentos/Documentos/avid-journal.github.io/AViD Journal - Landing.html",
))

# ═══════════════════════════════════════════════════════════════════════════
# FastAPI app
# ═══════════════════════════════════════════════════════════════════════════

from collections import defaultdict
import time as time_module

app = FastAPI(title="AViD Journal", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════════
# Landing page
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def landing():
    """Serve the landing page with Google Client ID injected."""
    if not LANDING_HTML.exists():
        return HTMLResponse("<h1>Landing page not found</h1>", status_code=404)

    html = LANDING_HTML.read_text(encoding="utf-8")

    # Inject Google Client ID, API base URL, and dev mode flag
    dev_flag = "true" if DEV_MODE else "false"
    html = html.replace(
        "</head>",
        f"""<script>
          window.AVID_GOOGLE_CLIENT_ID = "{GOOGLE_CLIENT_ID}";
          window.AVID_API_BASE = "";
          window.AVID_DEV_MODE = {dev_flag};
        </script>
        </head>""",
    )

    # Replace the static upload mock note with auth-aware UI
    html = html.replace(
        "Visual only — the working upload lives in the demo.",
        "Sign in with Google to analyze your papers.",
    )

    return HTMLResponse(html)


# ═══════════════════════════════════════════════════════════════════════════
# Auth endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/google")
async def google_auth(request: Request):
    """Verify Google credential and create session."""
    body = await request.json()
    credential = body.get("credential", "")

    if not credential:
        raise HTTPException(status_code=400, detail="Missing credential")

    user = verify_google_token(credential)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # Persist user
    db_user = upsert_user(
        google_id=user.google_id,
        email=user.email,
        name=user.name,
        picture=user.picture,
    )

    # Log the login
    log_action(user.google_id, "login", {"email": user.email})

    # Create session
    session = create_session(user)

    return JSONResponse({
        "token": session.token,
        "user": {
            "google_id": user.google_id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "papers_submitted": db_user.get("papers_submitted", 0),
            "api_key_mode": db_user.get("api_key_mode", "server"),
        },
    })


@app.get("/api/auth/me")
async def auth_me(request: Request):
    """Return current user info from session token."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="No token")

    session = get_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    db_user = get_user(session.user.google_id)
    return JSONResponse({
        "user": {
            "google_id": session.user.google_id,
            "email": session.user.email,
            "name": session.user.name,
            "picture": session.user.picture,
            "papers_submitted": db_user.get("papers_submitted", 0) if db_user else 0,
            "api_key_mode": db_user.get("api_key_mode", "server") if db_user else "server",
        },
    })


@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    """Log out and delete session."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        delete_session(token)
    return JSONResponse({"status": "ok"})


@app.get("/api/stats")
async def journal_stats():
    """Public stats about the journal."""
    return JSONResponse(stats())


# ═══════════════════════════════════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "version": "1.0"})


# ═══════════════════════════════════════════════════════════════════════════
# Rate limiter (simple in-memory, per-IP)
# ═══════════════════════════════════════════════════════════════════════════

_rate_window = 60  # seconds
_rate_limit = 5     # max requests per window per IP
_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _check_rate(ip: str) -> bool:
    """Return True if the request is within the rate limit."""
    now = time_module.time()
    window = now - _rate_window
    _rate_buckets[ip] = [t for t in _rate_buckets[ip] if t > window]
    if len(_rate_buckets[ip]) >= _rate_limit:
        return False
    _rate_buckets[ip].append(now)
    # Cleanup old entries periodically
    if len(_rate_buckets) > 10000:
        _rate_buckets.clear()
    return True


# ═══════════════════════════════════════════════════════════════════════════
# Analysis endpoint (delegates to app.py pipeline)
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/analyze")
async def api_analyze(request: Request):
    """Run the full novelty pipeline on an uploaded .tex file.
    Streams progress as JSON Lines, ending with the final result.
    """
    # Auth check (skipped in dev mode — uses anonymous user)
    google_id = "dev-user"
    if not DEV_MODE:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        session = get_session(token)
        if session is None:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        google_id = session.user.google_id

    # Rate limit
    ip = request.client.host if request.client else "unknown"
    if not _check_rate(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Read uploaded file
    form = await request.form()
    uploaded = form.get("file")
    if uploaded is None:
        raise HTTPException(status_code=400, detail="No file uploaded")

    import tempfile, json as _json
    with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as tmp:
        content = await uploaded.read()
        tmp.write(content)
        tex_path = tmp.name

    from app import process_tex

    async def stream():
        progress_msgs = []
        def send(step, msg, pct=0):
            progress_msgs.append({"step": step, "msg": msg, "pct": pct})
            return _json.dumps({"type": "progress", "step": step, "msg": msg, "pct": pct}) + "\n"

        yield send("parse", f"Parsing LaTeX ({uploaded.filename})...", 5)

        try:
            # Run pipeline — process_tex returns (summary, results, lean_path, pub_html)
            # We wrap it to track progress
            class FakeFile:
                name = tex_path

            # Call process_tex — it handles its own progress internally
            # We send pre/post messages
            yield send("pipeline", "Running novelty pipeline (formalization + D2 + D1)...", 10)

            summary, results, lean_path, pub_html = process_tex(FakeFile())

            n = summary.get("total", 0)
            formalized = summary.get("formalized", 0)
            yield send("done", f"Analysis complete: {n} theorems, {formalized} formalized", 100)

            # Return final result
            final = _json.dumps({
                "type": "result",
                "summary": summary,
                "results": results,
                "lean_path": lean_path,
                "publication_html": pub_html,
            }) + "\n"
            yield final

        except Exception as e:
            yield _json.dumps({"type": "error", "msg": str(e)}) + "\n"

    # Log the action
    if DEV_MODE:
        from src.users import upsert_user as _upsert
        _upsert("dev-user", "dev@localhost", "Dev Mode")
    log_action(google_id, "analyze", {
        "filename": uploaded.filename,
    })

    from fastapi.responses import StreamingResponse
    return StreamingResponse(stream(), media_type="application/x-ndjson")

# ═══════════════════════════════════════════════════════════════════════════
# Mount Gradio UI at /app (for direct browser use)
# ═══════════════════════════════════════════════════════════════════════════

from app import demo
app = gr.mount_gradio_app(app, demo, path="/app")
