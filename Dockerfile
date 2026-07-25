# AViD Journal — Hugging Face Docker Space (UID-1000, non-root runtime).
#
# HF Spaces run the container as user id 1000. This Dockerfile creates that user
# and installs Lean/Mathlib/REPL under its home so every runtime-writable path is
# user-owned (root-owned paths would fail at runtime on HF). For the root-based
# VPS/docker-compose build see deploy/Dockerfile — keep the two in sync.
#
# The HF Space YAML lives in README.md (sdk: docker, app_port: 7860).
# Build context = repo root. Image ~4.5 GB (bundles precompiled Mathlib).

FROM python:3.11-slim

LABEL org.opencontainers.image.title="AViD Journal Demo"
LABEL org.opencontainers.image.description="Automated novelty assessment for formalized mathematics (full pipeline)"
LABEL org.opencontainers.image.source="https://github.com/ayrtonporto/avid-journal"

# ── System deps (root, build-time only) ────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential pkg-config libgmp-dev \
    libopenblas0 \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user 1000 (HF requirement) ────────────────────────────────────
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:/home/user/.elan/bin:${PATH}
WORKDIR /home/user/app

# ── Lean 4 via elan (installed into $HOME/.elan, owned by user) ─────────────
ENV ELAN_HOME=/home/user/.elan
RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- --default-toolchain leanprover/lean4:v4.29.0 -y

# ── Python deps (user site) ────────────────────────────────────────────────
COPY --chown=user requirements_web.txt .
RUN pip install --no-cache-dir --user -r requirements_web.txt

# Pre-download MiniLM model at build time (cached under $HOME)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Lean project with Mathlib ─────────────────────────────────────────────
# Copy lakefile + toolchain first so the (slow) Mathlib layer is only rebuilt
# when these change.
COPY --chown=user lean_project/lakefile.toml lean_project/lean-toolchain /home/user/app/lean_project/
WORKDIR /home/user/app/lean_project

# Download precompiled Mathlib oleans (~2 GB, cached in the Docker layer).
RUN lake exe cache get || echo "Cache download failed — will need to build from source"
RUN lake build || echo "Build failed — D2 will be disabled"

# ── Lean REPL (resident Mathlib pool) ──────────────────────────────────────
# Build leanprover-community/repl on the SAME toolchain as Mathlib (v4.29.0) so
# its oleans are compatible. If this build fails the app still works — it falls
# back to the cold `lake env lean` path automatically.
WORKDIR /home/user/app/vendor
RUN git clone --depth 1 --branch v4.29.0-rc8 \
      https://github.com/leanprover-community/repl.git repl \
    && echo "leanprover/lean4:v4.29.0" > repl/lean-toolchain \
    && (cd repl && lake build repl) \
    || echo "REPL build failed — pool disabled, cold path will be used"

# ── Source code ────────────────────────────────────────────────────────────
WORKDIR /home/user/app
COPY --chown=user src/ ./src/
COPY --chown=user config/ ./config/
COPY --chown=user prompts/ ./prompts/
COPY --chown=user lean_project/ ./lean_project/
COPY --chown=user app.py .
COPY --chown=user server.py .
COPY --chown=user deploy/landing.html /home/user/app/deploy/landing.html
COPY --chown=user deploy/assets/ /home/user/app/deploy/assets/
RUN mkdir -p /home/user/app/src/publication/submissions /home/user/app/cache

# ── Runtime ────────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV LEAN_PROJECT_DIR=/home/user/app/lean_project
ENV LANDING_HTML=/home/user/app/deploy/landing.html
ENV AVID_FORMALIZATION_ENABLED=1
ENV AVID_D2_ENABLED=1

# Resident Lean REPL pool. POOL_SIZE=1 keeps RAM within HF free CPU Basic
# (16 GB); each worker holds Mathlib (~4-6 GB). Raise only on bigger hardware.
ENV AVID_REPL_POOL=1
ENV AVID_REPL_BIN=/home/user/app/vendor/repl/.lake/build/bin/repl
ENV AVID_REPL_POOL_SIZE=1

# D1 novelty (C_I): enable the theorem-level source and hard-cap the judge.
ENV THEOREMSEARCH_ENABLED=1
ENV AVID_JUDGE_TIMEOUT=30

EXPOSE 7860

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
