# src/formalization — LaTeX block → Lean 4

Takes one parsed block and produces a **type-checked Lean 4 declaration**. An LLM agent
writes Lean, reads the compiler's diagnostics, and iterates until the code compiles
cleanly or the block is flagged for human review.

For the full design (agent loop, per-block driver, provider abstraction) see
[ARCHITECTURE.md](ARCHITECTURE.md).

## Key files

| File | Role |
|---|---|
| `orchestrator.py` | Main driver: topo-sorts blocks, runs the per-block formalize→verify loop, appends verified declarations to the paper's `Paper.lean`. |
| `complexity.py` | Classifies a block `SIMPLE` / `MEDIUM` / `HARD` / `EXTERNAL` to pick the prompt and budget. |
| `lean_project.py` | Manages the shared Lean project and each paper's sub-module (creates dirs, copies agent prompts, runs `lake build`). |
| `error_parser.py` | Parses Lean compiler diagnostics into structured errors for the agent. |
| `mathlib_search.py` | Looks up existing Mathlib results for `EXTERNAL` blocks. |
| `batch_formalize_informal.py` | Batch-formalizes informal literature matches (writes to `Papers/InformalMatches/`, runtime-only). |
| `providers/` | LLM provider adapters: `claude_code` (default), `anthropic`, `openai_compatible`, behind `base.py`. |
| `scripts/` | Numina-derived runner helpers: `lean_checker`, `verification_loop`, `safe_verify`, `statement_tracker`, … |

## Compile backend

Compilation goes through the resident Mathlib REPL pool
([`src/lean_repl/`](../lean_repl/README.md)) so each round is sub-second instead of
paying the ~2 min cold Mathlib load. Falls back to a cold `lake env lean` if the pool
is disabled.
