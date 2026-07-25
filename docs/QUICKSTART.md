# Quick Start

First ten minutes after cloning. For the full setup walkthrough, see [GUIA_INSTALACION_Y_USO.md](GUIA_INSTALACION_Y_USO.md).

---

## 1. Python environment

From the repo root:

```bash
python -m venv .venv
```

Activate the venv:

- **macOS / Linux**: `source .venv/bin/activate`
- **Windows (PowerShell)**: `.venv\Scripts\Activate.ps1`

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy the env template and fill in keys:

```bash
cp .env.example .env
# then edit .env and set OPENCODE_GO_API_KEY (and optionally SEMANTIC_SCHOLAR_API_KEY)
```

On Windows PowerShell, use `Copy-Item .env.example .env`.

---

## 2. Lean 4 and Mathlib (optional but recommended)

The formalization pipeline needs a Lean toolchain. Install **elan** following the official instructions: <https://leanprover-community.github.io/get_started.html>.

Then pre-compile Mathlib once so per-block verification is fast afterwards:

```bash
cd lean_project
lake update
lake build
cd ..
```

The first build is slow (downloads + compiles Mathlib). Subsequent runs read the cached oleans.

---

## 3. Sanity-check the parser

```bash
python src/parser/parse_tex.py examples/tiny_even_numbers/paper.tex --stats
```

Should print three extracted blocks (one definition, one lemma, one theorem).

---

## 4. Orchestrator dry-run (no Claude credits)

```bash
python tests/test_orchestrator.py
```

This exercises the parser, complexity classifier, topological sort, and per-block project setup without launching Claude. Append `--real` only if you have the Claude CLI installed and the Mathlib build is cached — that runs the full end-to-end pipeline.

---

## 5. Run the offline test suite

```bash
pytest -m "not live"
```

`-m "not live"` skips tests that hit Leandex, arXiv, TheoremSearch, or Anthropic. Drop the flag to run them.

---

## 6. Next steps

- [CONTEXT.md](CONTEXT.md) — design decisions and the "why" behind PAPER_INDEX.md, axiom policy, search order
- [ARCHITECTURE.md](ARCHITECTURE.md) — module-level design and data flow
- [GUIA_INSTALACION_Y_USO.md](GUIA_INSTALACION_Y_USO.md) — full setup walkthrough in Spanish
- [examples/README.md](../examples/README.md) — reproduce the worked Lean output for both example papers
