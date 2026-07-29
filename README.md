# AViD Journal

**Automated Verification in Demonstrations** — an automated pipeline that reads a
mathematics paper, formalizes its proofs in Lean 4, and judges whether the results
are *new* to the mathematical record.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Lean 4](https://img.shields.io/badge/Lean-4.29-orange.svg)](https://leanprover.github.io/)

---

## What it does

You give it a `.tex` file with theorems, lemmas and definitions. AViD:

1. **Parses** the LaTeX into blocks and a dependency graph.
2. **Formalizes** each block into **Lean 4** with an LLM agent, iterating against the
   Lean compiler until it type-checks (or is marked for human review).
3. **Checks novelty** across three dimensions and emits one of seven verdicts.
4. **Publishes** the result if it clears the bar.

It ships as a **web app** (Google sign-in, a submission queue, live progress) and as a
set of **Python modules** you can drive from the command line.

---

## The novelty metric (three dimensions, seven verdicts)

Evaluated cheapest-first: **D2 → D1 → D3**.

| Dim | Question | How |
|---|---|---|
| **D1** | Does it already exist? | Mathlib search (Leandex + `exact?`) for the formal corpus C_F; arXiv + an LLM judge for the informal corpus C_I. |
| **D2** | Is it trivial? | Standard tactics (`decide`, `norm_num`, `simp`, `omega`, `tauto`, `aesop`) with budgets. If one closes the goal, it's trivial. |
| **D3** | Is the *proof* structurally new? | Jaccard distance over the premise sets of the candidate proof vs. the matched Mathlib theorem. |

**Verdicts:** `NOVEDAD_ENUNCIADO`, `NOVEDAD_DEMOSTRACION`, `CONOCIDO_LITERATURA`,
`NO_NOVEDOSO_redundante`, `NO_NOVEDOSO_trivial`, `ZONA_GRIS`, `INCONCLUSIVE`.

See [`src/novelty/README.md`](src/novelty/README.md) for the decision tree.

---

## Architecture

```
 .tex ─► src/parser ─► src/formalization ─► src/novelty ─► verdict ─► src/publication
             │            (Lean 4 + LLM)     (D2 ► D1 ► D3)
             │                   │                  │
             └───────────────────┴──────────────────┘
                    all Lean work shares one resident
                    Mathlib process  ──►  src/lean_repl
```

Mathlib is heavy (thousands of `.olean` files, ~2 min to load cold). Instead of
re-loading it for every compile, AViD keeps a **resident REPL pool**
([`src/lean_repl/`](src/lean_repl/README.md)) with Mathlib loaded once and shared by
formalization, D2 and D3. This is what makes a full run take ~2 min instead of ~15.

---

## Running it

### Option A — Web app via Docker (recommended)

This is how a fresh machine should run it. Everything (Lean, Mathlib, Python) lives
inside the image.

```bash
git clone https://github.com/ayrtonporto/avid-journal.git
cd avid-journal
cp .env.example .env      # fill in your keys — see Configuration below
docker compose up -d --build
docker compose logs -f    # wait for "REPL pool started" / "Analysis queue ready"
```

Then open `http://SERVER_IP:7860` (or your Cloudflare tunnel domain).

> The first build is slow (~30–60 min: it downloads Mathlib and compiles). Requirements,
> RAM/disk sizing and operations are documented separately in the **deploy guide**
> (shared out-of-band — ask Ayrton). Deploy internals also live in
> [`deploy/`](deploy/README.md).

### Option B — Local Python / CLI (development)

For hacking on the modules directly. Needs Lean 4 installed via
[elan](https://leanprover-community.github.io/get_started.html) and Mathlib built once
under [`lean_project/`](lean_project/README.md).

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Parse a paper into blocks
python -m src.parser.parse_tex tests/fixtures/sample_paper.tex --stats

# Run the full pipeline on a paper
python app.py tests/fixtures/sample_paper.tex
```

The [Spanish install-and-use walkthrough](docs/GUIA_INSTALACION_Y_USO.md) covers the
local setup end to end (elan, Lake/Mathlib, Python, LLM keys).

---

## Configuration

All secrets go in `.env` (gitignored). Copy [`.env.example`](.env.example) and fill in:

| Variable | Needed for | Notes |
|---|---|---|
| `OPENCODE_GO_API_KEY` | Formalization + LLM judge | Must have credit. |
| `GOOGLE_CLIENT_ID` | Web sign-in | OAuth Client ID (public, safe in the frontend). |
| `AVID_DEV_MODE` | Local testing | `1` disables login. **Set to `0` in production.** |
| `AVID_REPL_POOL_SIZE` / `AVID_ANALYSIS_WORKERS` | Concurrency | One unit ≈ 2.5 GB RAM. Keep them equal. |

Never commit real keys. The full variable list is in `.env.example` and the deploy guide.

---

## Repository layout

```
avid-journal/
├── app.py                  # Pipeline entry point (parse → formalize → novelty)
├── server.py               # FastAPI web server: queue, SSE progress, auth
├── docker-compose.yaml     # Web app + Cloudflare tunnel
│
├── src/
│   ├── parser/             # LaTeX → blocks + dependency graph
│   ├── formalization/      # LLM + Lean 4 formalization loop
│   ├── novelty/            # D1/D2/D3 novelty metric + orchestrator
│   ├── lean_repl/          # Resident Mathlib REPL pool
│   ├── auth/               # Google sign-in verification
│   ├── users/              # SQLite user store
│   ├── publication/        # Publishing accepted submissions
│   └── notifications/      # Outbound notifications
│
├── lean_project/           # Shared Lean 4 project (Mathlib built once)
│   └── Papers/             # One sub-module per formalized paper
├── prompts/                # LLM agent prompts (SIMPLE/MEDIUM/HARD + agent docs)
├── deploy/                 # Dockerfile, landing page, deploy notes
├── tests/                  # Test suite + fixtures
├── docs/                   # Architecture + install/usage guides
└── paper/                  # The manuscript (LaTeX)
```

Each folder has its own `README.md` with the details.

---

## Testing

```bash
pytest tests/                # full suite
pytest -m "not live"         # skip tests that hit Leandex / arXiv / the LLM
```

---

## Documentation

- [docs/QUICKSTART.md](docs/QUICKSTART.md) — first steps after cloning
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — module-level design and data flow
- [docs/GUIA_INSTALACION_Y_USO.md](docs/GUIA_INSTALACION_Y_USO.md) — full Spanish setup walkthrough

---

## License & credits

MIT — see [LICENSE](LICENSE).

Built on **Lean 4** + **Mathlib**, **Leandex** (Mathlib semantic search), and a
Numina-Lean-Agent–derived formalization runner. The paper is *Beyond Correctness —
Toward Automated Novelty Verification with Lean 4*.

**Author:** Ayrton Porto · <https://ayrtonporto.github.io/>

> Research software, under active development. Not production-hardened.
