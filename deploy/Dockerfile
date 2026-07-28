# AViD Journal — Full demo (formalization + D2 + D1)
# Includes Lean 4 + Mathlib (~4.5 GB image).
#
# Build:  docker build -t avid-journal .
# Run:    docker run -p 7860:7860 --env-file .env avid-journal

FROM python:3.11-slim

LABEL org.opencontainers.image.title="AViD Journal Demo"
LABEL org.opencontainers.image.description="Automated novelty assessment for formalized mathematics (full pipeline)"
LABEL org.opencontainers.image.authors="Ayrton Porto <ayrporto@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/ayrtonporto/avid-journal"

# ── System deps ───────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential pkg-config libgmp-dev \
    libopenblas0 \
    && rm -rf /var/lib/apt/lists/*

# ── Lean 4 via elan ───────────────────────────────────────────────────────
ENV ELAN_HOME=/opt/elan
ENV PATH="/opt/elan/bin:${PATH}"

RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- --default-toolchain leanprover/lean4:v4.29.0 -y \
    && mv /root/.elan /opt/elan

# ── Python deps ───────────────────────────────────────────────────────────
WORKDIR /app
COPY requirements_web.txt .
RUN pip install --no-cache-dir -r requirements_web.txt

# Pre-download MiniLM model at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Lean project with Mathlib ─────────────────────────────────────────────
# Copy lakefile + toolchain first (caching: only rebuild Mathlib if these change)
COPY lean_project/lakefile.toml lean_project/lean-toolchain /app/lean_project/
WORKDIR /app/lean_project

# Download precompiled Mathlib oleans (~2 GB, cached in Docker layer)
RUN lake exe cache get || echo "Cache download failed — will need to build from source"
RUN lake build || echo "Build failed — D2 will be disabled"

# ── Lean REPL (resident Mathlib pool) ──────────────────────────────────────
# Build leanprover-community/repl on the SAME toolchain as Mathlib (v4.29.0) so
# its oleans are compatible. The pool keeps Mathlib resident in env 0 and drops
# every compile check from ~27s to sub-second. If this build fails the app
# still works — it falls back to the cold `lake env lean` path automatically.
WORKDIR /app/vendor
RUN git clone --depth 1 --branch v4.29.0-rc8 \
      https://github.com/leanprover-community/repl.git repl \
    && echo "leanprover/lean4:v4.29.0" > repl/lean-toolchain \
    && (cd repl && lake build repl) \
    || echo "REPL build failed — pool disabled, cold path will be used"
WORKDIR /app/lean_project

# ── Source code ───────────────────────────────────────────────────────────
WORKDIR /app
COPY src/ ./src/
COPY config/ ./config/
COPY prompts/ ./prompts/
COPY lean_project/ ./lean_project/

# Register the `Papers` module root so D3 premise extraction (ExtractData) can
# resolve the runtime temp files it writes under Papers/_d3_temp/. Compiling one
# small module creates the Papers build dir; without it ExtractData aborts with
# "unknown module prefix 'Papers'" and D3 (candidate side) is unavailable.
RUN cd /app/lean_project && lake build Papers.Paper.Blocks.def_even \
    || echo "Papers build failed — D3 candidate-side premise extraction disabled"

COPY app.py .
COPY server.py .
COPY deploy/landing.html /app/deploy/landing.html
COPY deploy/assets/ /app/deploy/assets/
RUN mkdir -p /app/src/publication/submissions

# ── Runtime ───────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV LEAN_PROJECT_DIR=/app/lean_project
ENV LANDING_HTML=/app/deploy/landing.html
ENV AVID_FORMALIZATION_ENABLED=1
ENV AVID_D2_ENABLED=1

# Resident Lean REPL pool (see .env.example). Enabled by default in the image;
# the app falls back to the cold path if the REPL binary is missing. Tune
# AVID_REPL_POOL_SIZE to the host RAM (each worker holds Mathlib, ~4-6 GB).
ENV AVID_REPL_POOL=1
ENV AVID_REPL_BIN=/app/vendor/repl/.lake/build/bin/repl
ENV AVID_REPL_POOL_SIZE=2

# D1 novelty (C_I) tuning: enable the theorem-level source (replaces Semantic
# Scholar) and hard-cap each DeepSeek judge call so novelty never hangs.
ENV THEOREMSEARCH_ENABLED=1
ENV AVID_JUDGE_TIMEOUT=30

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
