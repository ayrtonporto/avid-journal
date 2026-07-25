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
# Default to the copy vendored into the repo (deploy/landing.html) so the app
# is self-contained (Docker, Linux, CI). Override with LANDING_HTML to point at
# an external source (e.g. the avid-journal.github.io working copy).
LANDING_HTML = Path(os.environ.get(
    "LANDING_HTML",
    str(REPO_ROOT / "deploy" / "landing.html"),
))

# ═══════════════════════════════════════════════════════════════════════════
# FastAPI app
# ═══════════════════════════════════════════════════════════════════════════

from collections import defaultdict
import time as time_module

app = FastAPI(title="AViD Journal", version="1.0")

# CORS. The spec forbids wildcard origins together with credentials, and
# browsers reject such responses. Auth here uses a Bearer token in the
# Authorization header (not cookies), so credentials aren't required for the
# default public config. Set AVID_ALLOWED_ORIGINS (comma-separated) to lock
# down origins; doing so re-enables credentialed requests.
_origins_env = os.environ.get("AVID_ALLOWED_ORIGINS", "").strip()
if _origins_env:
    _allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
    _allow_credentials = True
else:
    _allowed_origins = ["*"]
    _allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# Static assets (images referenced by the landing page)
# ═══════════════════════════════════════════════════════════════════════════
STATIC_DIR = REPO_ROOT / "deploy" / "assets"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ═══════════════════════════════════════════════════════════════════════════
# Pre-warm Mathlib olean cache on startup
# ═══════════════════════════════════════════════════════════════════════════
# The first `lake`/`lean` invocation after boot must deserialize ~2 GB of
# Mathlib oleans from disk (the "cold load", several minutes). We pay that ONCE
# in a background thread at startup so the first client's analysis is fast.
# Disable with AVID_PREWARM=0.

def _prewarm_mathlib() -> None:
    import shutil
    import subprocess
    import time as _t
    import uuid

    import app as _appmod

    lean_dir = _appmod.LEAN_PROJECT_DIR
    if not lean_dir or not Path(lean_dir).exists():
        logger.info("[prewarm] skipped — LEAN_PROJECT_DIR not found")
        return
    lake = shutil.which("lake")
    if not lake:
        logger.info("[prewarm] skipped — lake not on PATH")
        return

    probe = Path(lean_dir) / f"_prewarm_{uuid.uuid4().hex}.lean"
    try:
        probe.write_text("import Mathlib\n", encoding="utf-8")
        t0 = _t.time()
        logger.info("[prewarm] loading Mathlib oleans (first time can take minutes)…")
        subprocess.run(
            [lake, "env", "lean", str(probe)],
            cwd=str(lean_dir),
            capture_output=True, text=True, timeout=1800,
        )
        logger.info(f"[prewarm] Mathlib cache warm in {_t.time() - t0:.0f}s")
    except Exception as e:
        logger.warning(f"[prewarm] failed: {e}")
    finally:
        try:
            probe.unlink()
        except OSError:
            pass


def _warm_minilm() -> None:
    """Load the MiniLM model once at boot so the first novelty check (D1 stage A)
    doesn't pay the lazy cold-load (torch init, tens of seconds) mid-request."""
    try:
        from src.novelty.block_comparator import get_model
        get_model()
        logger.info("[prewarm] MiniLM model loaded")
    except Exception as e:
        logger.warning("[prewarm] MiniLM preload failed: %s", e)


def _warm_startup() -> None:
    """Warm Lean on boot. If the resident REPL pool is enabled, starting it
    imports Mathlib into every worker (which also warms the OS disk cache), so
    it subsumes the cold prewarm. Otherwise fall back to the cold prewarm."""
    from src.lean_repl import pool_enabled, warm_pool
    import app as _appmod

    # MiniLM powers the D1 novelty coarse filter; load it up front too.
    _warm_minilm()

    if pool_enabled():
        logger.info("[prewarm] starting resident REPL pool…")
        pool = warm_pool(_appmod.LEAN_PROJECT_DIR)
        if pool is not None:
            logger.info("[prewarm] REPL pool warm and ready")
            return
        logger.warning("[prewarm] REPL pool unavailable — using cold prewarm")
    _prewarm_mathlib()


@app.on_event("startup")
async def _on_startup() -> None:
    if os.environ.get("AVID_PREWARM", "1") == "1":
        import threading
        threading.Thread(target=_warm_startup, daemon=True).start()
        logger.info("[prewarm] background warm-up started")


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    from src.lean_repl import shutdown_pool
    shutdown_pool()

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
    # Cleanup: drop only IPs whose window has fully expired, so we never reset
    # the limit for currently-active clients.
    if len(_rate_buckets) > 10000:
        for stale_ip in [k for k, v in _rate_buckets.items()
                         if not v or v[-1] <= window]:
            del _rate_buckets[stale_ip]
    return True


# ═══════════════════════════════════════════════════════════════════════════
# Auth helper
# ═══════════════════════════════════════════════════════════════════════════

def _require_user(request: Request) -> str:
    """Return the authenticated user's google_id, or raise 401.

    In dev mode (AVID_DEV_MODE=1) auth is disabled and a synthetic dev user is
    returned. Otherwise a valid Bearer session token is required.
    """
    if DEV_MODE:
        return "dev-user"
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    session = get_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session.user.google_id


# ═══════════════════════════════════════════════════════════════════════════
# Analysis endpoint (delegates to app.py pipeline)
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/analyze")
async def api_analyze(request: Request):
    """Run the full novelty pipeline on an uploaded .tex file.
    Streams progress as JSON Lines, ending with the final result.
    """
    google_id = _require_user(request)

    # Rate limit
    ip = request.client.host if request.client else "unknown"
    if not _check_rate(ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Read uploaded file + optional client model choice.
    form = await request.form()
    uploaded = form.get("file")
    if uploaded is None:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Client's own provider + key (transient — used for this request only,
    # never stored or logged). Empty => server default (DeepSeek V4 Pro).
    client_provider = (form.get("provider") or "").strip()
    client_model = (form.get("model") or "").strip()
    client_api_key = (form.get("api_key") or "").strip()

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

        yield f"data: {_json.dumps({'type': 'progress', 'step': 'start', 'msg': f'Starting pipeline for {uploaded.filename}...', 'pct': 0})}\n\n"

        # Run process_tex in a thread (it's synchronous and blocks)
        result_holder = {"summary": None, "results": None, "lean_path": None, "pub_html": None, "error": None}

        def run_pipeline():
            try:
                class FakeFile:
                    name = tex_path
                summary, results, lean_path, pub_html = process_tex(
                    FakeFile(),
                    api_key_input=client_api_key,
                    provider_name=client_provider,
                    model_name=client_model,
                    on_progress=on_progress_cb,
                )
                result_holder["summary"] = summary
                result_holder["results"] = results
                result_holder["lean_path"] = lean_path
                result_holder["pub_html"] = pub_html
            except Exception as e:
                result_holder["error"] = str(e)

        thread = threading.Thread(target=run_pipeline)
        thread.start()

        # Stream progress events while the thread runs. If a step goes quiet
        # for a while (cold Mathlib load, a slow proof), emit a heartbeat with
        # the elapsed time so the page never looks frozen.
        _start = time_module.time()
        _last_activity = _start
        _last_msg = "working…"
        _HEARTBEAT_S = 10
        while thread.is_alive():
            try:
                msg = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                _last_activity = time_module.time()
                _last_msg = msg.get("msg", _last_msg)
                yield f"data: {_json.dumps(msg)}\n\n"
            except asyncio.TimeoutError:
                now = time_module.time()
                if now - _last_activity >= _HEARTBEAT_S:
                    _last_activity = now
                    elapsed = int(now - _start)
                    hb = {
                        "type": "progress", "step": "heartbeat",
                        "msg": f"{_last_msg} · still working ({elapsed}s)",
                    }
                    yield f"data: {_json.dumps(hb)}\n\n"

        # Drain any remaining messages
        while not progress_queue.empty():
            msg = progress_queue.get_nowait()
            yield f"data: {_json.dumps(msg)}\n\n"

        thread.join()

        if result_holder["error"]:
            yield f"data: {_json.dumps({'type': 'error', 'msg': result_holder['error']})}\n\n"
        else:
            yield f"data: {_json.dumps({'type': 'done', 'msg': 'Analysis complete'})}\n\n"
            yield f"data: {_json.dumps({'type': 'result', 'summary': result_holder['summary'], 'results': result_holder['results'], 'lean_path': result_holder['lean_path'], 'publication_html': result_holder['pub_html']})}\n\n"

    # Log the action (fire and forget — don't block the stream)
    if DEV_MODE:
        from src.users import upsert_user as _upsert
        _upsert("dev-user", "dev@localhost", "Dev Mode")
    log_action(google_id, "analyze", {
        "filename": uploaded.filename,
    })

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Publication endpoint
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/publish")
async def api_publish(request: Request):
    """Handle paper publication submission from the landing page."""
    from src.publication import submit as pub_submit
    from src.users import increment_papers

    google_id = _require_user(request)

    body = await request.json()
    author = (body.get("author") or "").strip()
    email = (body.get("email") or "").strip()
    llm = (body.get("llm") or "").strip()
    filename = (body.get("filename") or "unknown.tex")
    submission_id = (body.get("submission_id") or "").strip() or None

    if not author:
        return JSONResponse({"status": "error", "detail": "Author name is required"}, status_code=400)
    if not llm:
        return JSONResponse({"status": "error", "detail": "LLM model is required"}, status_code=400)

    try:
        # If the analysis auto-recorded a novel run, enrich THAT row (by id)
        # with the author's data instead of creating a duplicate.
        record = pub_submit(
            tex_path=filename,
            title=f"Submission by {author}",
            authors=author,
            email=email,
            llm_model=llm,
            submission_id=submission_id,
        )
        # Attribute the submission to the authenticated user.
        if not DEV_MODE:
            increment_papers(google_id)

        return JSONResponse({"status": "ok", "id": record["id"]})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════
# Mount Gradio UI at /app (for direct browser use)
# ═══════════════════════════════════════════════════════════════════════════

from app import demo
app = gr.mount_gradio_app(app, demo, path="/app")
