# AViD Journal — Demo (D1-only)
# Lightweight image: no Lean 4, no Mathlib. Only existence checks.
#
# Build:  docker build -t avid-journal .
# Run:    docker run -p 7860:7860 --env-file .env avid-journal

FROM python:3.11-slim

LABEL org.opencontainers.image.title="AViD Journal Demo"
LABEL org.opencontainers.image.description="Automated novelty assessment for formalized mathematics (D1-only)"
LABEL org.opencontainers.image.authors="Ayrton Porto <ayrporto@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/ayrtonporto/avid-journal"

# System deps for sentence-transformers (BLAS) and general health
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ──────────────────────────────────────────────────────────
COPY requirements_web.txt .
RUN pip install --no-cache-dir -r requirements_web.txt

# ── Warm up: pre-download MiniLM model (120 MB) at build time ────────────
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Source code ──────────────────────────────────────────────────────────
COPY src/ ./src/
COPY config/ ./config/
COPY prompts/ ./prompts/
COPY app.py .

# ── Runtime ──────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV GRADIO_SERVER_NAME=0.0.0.0

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

CMD ["python", "app.py"]
