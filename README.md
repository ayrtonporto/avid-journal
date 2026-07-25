# AViD Journal

**Automated Verification in Demonstrations** - The first fully automated mathematics journal.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 Vision

AViD Journal accepts `.tex` files, formalizes proofs in Lean 4, verifies correctness, checks novelty against Mathlib + arXiv + TheoremSearch, and auto-publishes if valid.

This is critical infrastructure for AI-driven mathematical research — when AIs discover theorems autonomously, they'll need automated verification and review.

> **Estado (jul 2026):** el veredicto de novedad activo vive en `src/novelty_v2/`
> (árbol D2→D1→D3, 7 veredictos). El **demo web** es `app.py` (backend) + `server.py`
> (FastAPI, sirve `deploy/landing.html`, SSE), acelerado por un **REPL pool Lean
> residente** (`src/lean_repl/`). Fuentes C_I: arXiv + TheoremSearch (Semantic
> Scholar retirado). Ver `CLAUDE.md` para el estado detallado y las decisiones.

---

## 🏗️ Architecture

```
.tex Paper
    │
    ▼
┌─────────────────────────────┐
│ PARSER                      │  → Extract blocks + dependency graph
│ src/parser/                 │     (theorems, lemmas, definitions)
└──────────────┬──────────────┘
               │ blocks in topological order
               ▼
╔═════════════ orchestrator (src/formalization/) ═══════════════╗
║                                                               ║
║   for each block (resume mode skips done):                    ║
║     ┌─────────────────────────────────────────────────────┐   ║
║     │ FORMALIZATION + VERIFICATION (per-block loop)       │   ║
║     │                                                     │   ║
║     │   Claude Code session (Numina-derived runner):      │   ║
║     │     • writes / edits Blocks/<lean_name>.lean        │   ║
║     │     • calls lean_diagnostic_messages                │   ║
║     │     • iterates until clean or max_rounds            │   ║
║     │                                                     │   ║
║     │   then orchestrator:                                │   ║
║     │     • final lean_checker pass                       │   ║
║     │     • appends declaration → Paper.lean              │   ║
║     │     • updates PAPER_INDEX.md / REVIEW.md            │   ║
║     │     • lake build Papers.<ModuleName>.Paper (olean)  │   ║
║     └─────────────────────────────────────────────────────┘   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
               │
               ▼
┌─────────────────────────────┐
│ NOVELTY CHECK (separate pass)│  → Check if new
│ src/novelty/                 │     • Stage 0: Mathlib via Leandex
│                              │     • Stages 1–3: ArXiv + LLM judge
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ DECISION                    │  → Accept / Reject
│ orchestrator + report       │     + Citation report
└─────────────────────────────┘
```

The agent that writes Lean is **Claude Code**, not Numina. AViD vendors Numina-Lean-Agent's runner scripts (`run_claude.py`, `runner.py`, `lean_checker.py`, …) and its coordinator / blueprint / sketch prompt pattern, but the agent loop itself is Claude Code calling `lean_diagnostic_messages` via [lean-lsp-mcp](https://github.com/leanprover-community/lean-lsp-mcp).

---

## 📁 Project Structure

```
avid-journal/
│
├── examples/                       # LaTeX inputs with checked-in Lean output
│   ├── tiny_even_numbers/paper.tex
│   └── thesis_ayrton_porto/paper.tex
│
├── src/
│   ├── parser/                     # LaTeX → blocks + dependency graph
│   │   ├── latex_parser.py
│   │   └── parse_tex.py
│   │
│   ├── novelty/                    # Novelty detection (Stages 0–3)
│   │   ├── mathlib_checker.py      # Stage 0: Leandex search in Mathlib
│   │   ├── arxiv_search.py         # Stage 1: arXiv + TheoremSearch (Semantic Scholar retired)
│   │   ├── paper_extractor.py      # Stage 2: PDF download & text extraction
│   │   ├── block_comparator.py     # Stage 3: block ↔ candidate comparison
│   │   ├── llm_judge.py            # Claude judge for theorem equivalence
│   │   ├── novelty_checker.py      # Orchestrates Stages 0–3
│   │   └── _cache.py               # Disk cache for external API calls
│   │
│   └── formalization/              # Lean 4 formalization pipeline
│       ├── orchestrator.py         # Main loop (topo sort + per-block driver)
│       ├── lean_project.py         # Shared Lean project + per-paper sub-modules
│       ├── complexity.py           # SIMPLE / MEDIUM / HARD / EXTERNAL classifier
│       ├── mathlib_search.py       # Mathlib lookup for external results
│       └── scripts/                # Numina-derived Claude runner + lean_checker
│
├── prompts/                        # Agent prompts driven by complexity mode
│   ├── prompt_avid.txt             # SIMPLE
│   ├── prompt_medium_mode_avid.txt # MEDIUM
│   ├── prompt_hard_mode_avid.txt   # HARD
│   └── docs/prompts/               # coordinator / blueprint / sketch / common
│
├── lean_project/                   # Shared Lean 4 project (Mathlib precompiled)
│   ├── lakefile.toml
│   ├── lean-toolchain
│   └── Papers/<ModuleName>/        # One sub-module per formalized paper
│
├── scripts/
│   └── formalization/              # CLI helpers (diagnose, rebuild, smoke, etc.)
│
├── tests/
│   ├── test_orchestrator.py
│   ├── test_novelty.py
│   └── fixtures/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PROGRESS.md
│   └── GUIA_INSTALACION_Y_USO.md
│
├── .env.example
├── .gitignore
├── requirements.txt
├── setup.sh
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Lean 4 (for formalization)
- Claude API key (for LLM judge)

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/avid-journal.git
cd avid-journal

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

### Usage

**1. Parse a LaTeX paper:**

```bash
python src/parser/parse_tex.py paper.tex --stats
```

**2. Check novelty (ArXiv search):**

```bash
python src/novelty/arxiv_search.py "Boolean algebra isomorphism" --top-k 10
```

**3. Full formalization pipeline:**

```bash
python -X utf8 -m src.formalization.orchestrator paper.tex --title "Paper Title"
```

Resume mode is on by default — blocks already marked `verified`/`axiom` in `PAPER_INDEX.md` are skipped. Use `--blocks-range "1-13"` to formalize a subset, `--dry-run` to validate the pipeline without spending Claude credits.

---

## 📊 Current Status

See [docs/PROGRESS.md](docs/PROGRESS.md) for the up-to-date breakdown of what's done, in progress, and planned.

---

## 🧪 Testing

```bash
# Full test suite
pytest tests/

# Skip tests that hit Leandex / arXiv / TheoremSearch / Anthropic
pytest -m "not live"

# Orchestrator dry-run (no Claude credits spent)
python tests/test_orchestrator.py
```

---

## 📖 Documentation

- [docs/QUICKSTART.md](docs/QUICKSTART.md) — first 10 minutes after cloning
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — module-level design and data flow
- [docs/GUIA_INSTALACION_Y_USO.md](docs/GUIA_INSTALACION_Y_USO.md) — full Spanish setup walkthrough (Lean/elan, Lake/Mathlib, Python, Claude CLI, orchestrator usage)
- [docs/PROGRESS.md](docs/PROGRESS.md) — status of each component
- [examples/README.md](examples/README.md) — worked LaTeX examples and how to reproduce their Lean output
- [scripts/formalization/README.md](scripts/formalization/README.md) — helper CLI index

---

## 🤝 Contributing

This project is currently in early development. Contributions welcome once we reach v0.1.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **Numina-Lean-Agent** - Autoformalization framework
- **LeanDex** - Semantic search over Mathlib
- **Lean Community** - For Mathlib and the Lean ecosystem
- **MerLean** - Inspiration for autoformalization pipeline

---

## 📧 Contact

Ayrton Porto  
Website: https://ayrtonporto.github.io/  
Project: AViD Journal

---

**Note:** This is research software in active development. Not production-ready.
