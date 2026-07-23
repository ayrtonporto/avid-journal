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

# ── Source code ───────────────────────────────────────────────────────────
WORKDIR /app
COPY src/ ./src/
COPY config/ ./config/
COPY prompts/ ./prompts/
COPY lean_project/ ./lean_project/
COPY app.py .

# ── Runtime ───────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV LEAN_PROJECT_DIR=/app/lean_project
ENV AVID_FORMALIZATION_ENABLED=1
ENV AVID_D2_ENABLED=1

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

CMD ["python", "app.py"]
