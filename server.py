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
LANDING_HTML = Path(os.environ.get(
    "LANDING_HTML",
    "D:/Mis documentos/Documentos/avid-journal.github.io/AViD Journal - Landing.html",
))

# ═══════════════════════════════════════════════════════════════════════════
# FastAPI app
# ═══════════════════════════════════════════════════════════════════════════

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

    # Inject Google Client ID and API base URL into the page
    html = html.replace(
        "</head>",
        f"""<script>
          window.AVID_GOOGLE_CLIENT_ID = "{GOOGLE_CLIENT_ID}";
          window.AVID_API_BASE = "";
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
# Analysis endpoint (delegates to app.py pipeline)
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/analyze")
async def api_analyze(request: Request):
    """Run the full novelty pipeline on an uploaded .tex file.

    Requires authentication. Tracks the action in the activity log.
    """
    # Auth check
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    session = get_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    # Read uploaded file
    form = await request.form()
    uploaded = form.get("file")
    if uploaded is None:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Save to temp file and process
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as tmp:
        tmp.write(await uploaded.read())
        tex_path = tmp.name

    try:
        # Import here to avoid circular deps
        from app import process_tex
        # process_tex expects a Gradio file-like object — wrap the path
        class FakeFile:
            name = tex_path
        summary, results, pub_html = process_tex(FakeFile())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Log the action
    log_action(session.user.google_id, "analyze", {
        "filename": uploaded.filename,
        "n_blocks": summary.get("n_blocks", 0),
        "n_errors": summary.get("n_errors", 0),
    })

    return JSONResponse({
        "summary": summary,
        "results": results,
        "publication_html": pub_html,
    })


# ═══════════════════════════════════════════════════════════════════════════
# Mount Gradio UI at /app (for direct browser use)
# ═══════════════════════════════════════════════════════════════════════════

from app import demo
app = gr.mount_gradio_app(app, demo, path="/app")
