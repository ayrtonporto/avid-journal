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
    import asyncio, threading

    progress_queue = asyncio.Queue()

    async def stream():
        loop = asyncio.get_running_loop()  # capture in main async context

        def on_progress_cb(step, msg, pct):
            # Called from thread — use captured loop
            loop.call_soon_threadsafe(
                progress_queue.put_nowait,
                {"type": "progress", "step": step, "msg": msg, "pct": pct},
            )

        yield _json.dumps({"type": "progress", "step": "start", "msg": f"Starting pipeline for {uploaded.filename}...", "pct": 0}) + "\n"

        # Run process_tex in a thread (it's synchronous and blocks)
        result_holder = {"summary": None, "results": None, "lean_path": None, "pub_html": None, "error": None}

        def run_pipeline():
            try:
                class FakeFile:
                    name = tex_path
                summary, results, lean_path, pub_html = process_tex(FakeFile(), on_progress=on_progress_cb)
                result_holder["summary"] = summary
                result_holder["results"] = results
                result_holder["lean_path"] = lean_path
                result_holder["pub_html"] = pub_html
            except Exception as e:
                result_holder["error"] = str(e)

        thread = threading.Thread(target=run_pipeline)
        thread.start()

        # Stream progress events while the thread is running
        while thread.is_alive():
            try:
                msg = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                yield _json.dumps(msg) + "\n"
            except asyncio.TimeoutError:
                pass

        # Drain any remaining messages
        while not progress_queue.empty():
            msg = progress_queue.get_nowait()
            yield _json.dumps(msg) + "\n"

        thread.join()

        if result_holder["error"]:
            yield _json.dumps({"type": "error", "msg": result_holder["error"]}) + "\n"
        else:
            yield _json.dumps({"type": "done", "msg": "Analysis complete"}) + "\n"
            yield _json.dumps({
                "type": "result",
                "summary": result_holder["summary"],
                "results": result_holder["results"],
                "lean_path": result_holder["lean_path"],
                "publication_html": result_holder["pub_html"],
            }) + "\n"

    # Log the action (fire and forget — don't block the stream)
    if DEV_MODE:
        from src.users import upsert_user as _upsert
        _upsert("dev-user", "dev@localhost", "Dev Mode")
    log_action(google_id, "analyze", {
        "filename": uploaded.filename,
    })

    from fastapi.responses import StreamingResponse
    return StreamingResponse(stream(), media_type="application/x-ndjson")


# ═══════════════════════════════════════════════════════════════════════════
# Publication endpoint
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/publish")
async def api_publish(request: Request):
    """Handle paper publication submission from the landing page."""
    from src.publication import submit as pub_submit
    from src.users import increment_papers

    body = await request.json()
    author = (body.get("author") or "").strip()
    email = (body.get("email") or "").strip()
    llm = (body.get("llm") or "").strip()
    filename = (body.get("filename") or "unknown.tex")

    if not author:
        return JSONResponse({"status": "error", "detail": "Author name is required"}, status_code=400)
    if not llm:
        return JSONResponse({"status": "error", "detail": "LLM model is required"}, status_code=400)

    try:
        record = pub_submit(
            tex_path=filename,
            title=f"Submission by {author}",
            authors=author,
            email=email,
            llm_model=llm,
        )
        # Update user stats if logged in
        if not DEV_MODE:
            increment_papers(request.headers.get("Authorization", "").replace("Bearer ", ""))

        return JSONResponse({"status": "ok", "id": record["id"]})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════
# Mount Gradio UI at /app (for direct browser use)
# ═══════════════════════════════════════════════════════════════════════════

from app import demo
app = gr.mount_gradio_app(app, demo, path="/app")
