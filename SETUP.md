# AViD Journal — Server Setup Guide

Quick setup to run the AViD Journal server on your own machine.

## Prerequisites

- **Python 3.11+**
- **Git**
- **~3 GB free disk** (for Mathlib oleans)
- **OpenCode Go API key** (https://opencode.ai) — powers formalization and the LLM judge

## 1. Clone and install Python deps

```bash
git clone https://github.com/ayrtonporto/avid-journal.git
cd avid-journal
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Get the Lean project

The `lean_project/` directory contains Lean 4 with Mathlib pre-compiled (~2 GB of `.olean` files). It is **not** in git.

**Option A — Copy from Ayrton's machine (recommended):**
Get a zip/tarball of `lean_project/` from Ayrton and extract it into the repo root.

**Option B — Build from scratch (~2–4 hours):**
```bash
cd lean_project
lake update
lake exe cache get    # downloads pre-built Mathlib oleans
lake build
cd ..
```

## 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```ini
OPENCODE_GO_API_KEY=sk-...      # your OpenCode Go key
AVID_DEV_MODE=1                  # 1 = no login required (local), 0 = requires Google OAuth
```

For production with Google sign-in, also set `GOOGLE_CLIENT_ID`.

## 4. Run the server

```bash
.venv/Scripts/python.exe -m uvicorn server:app --host 0.0.0.0 --port 7860
```

Then open **http://localhost:7860** in your browser.

## 5. Test it

Upload `tests/fixtures/sample_paper.tex` through the landing page. The pipeline will:
1. Parse the LaTeX
2. Formalize each block in Lean 4
3. Check triviality (D2) and existence (D1) against Mathlib + arXiv
4. Compute proof distance (D3) if a Mathlib match is found
5. Show a verdict for each theorem

First run takes longer (~5 min) because Mathlib oleans are loaded into memory. Subsequent runs are faster.

## Environment variables reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENCODE_GO_API_KEY` | Yes | — | OpenCode Go API key |
| `AVID_DEV_MODE` | No | `0` | Set to `1` to skip Google sign-in |
| `GOOGLE_CLIENT_ID` | For prod | — | Google OAuth client ID |
| `LEAN_PROJECT_DIR` | No | `./lean_project` | Path to Lean project with Mathlib |
| `AVID_FORMALIZATION_MODEL` | No | `deepseek-v4-pro` | Model for formalization |
| `AVID_JUDGE_MODEL` | No | `deepseek-v4-flash` | Model for D1 LLM judge |
| `AVID_PREWARM` | No | `1` | Pre-load Mathlib on startup |

## Ports

- `7860` — Landing page + API + Gradio UI at `/app`
