# src — Pipeline modules

The Python side of AViD, in pipeline order plus the web/infra support modules.

## Pipeline

| Module | Role | Docs |
|---|---|---|
| [`parser/`](parser/README.md) | LaTeX `.tex` → ordered blocks + dependency graph. | ✓ |
| [`formalization/`](formalization/README.md) | Turns each block into type-checked Lean 4 with an LLM agent looping against the compiler. | ✓ + [ARCHITECTURE.md](formalization/ARCHITECTURE.md) |
| [`novelty/`](novelty/README.md) | The D1/D2/D3 novelty metric and its orchestrator (seven verdicts). | ✓ |
| [`lean_repl/`](lean_repl/README.md) | Resident Mathlib REPL pool shared by all Lean work. | ✓ |

## Web app & infra

| Module | Role |
|---|---|
| `auth/` | Verifies Google sign-in JWTs (against Google's tokeninfo endpoint) and mints in-memory sessions. The JWT is never persisted. |
| `users/` | SQLite user store (`users.db`): profile + activity log. Gitignored; created at runtime. |
| `publication/` | Writes accepted submissions to the publication store. |
| `notifications/` | Outbound notifications for pipeline events. |

The web layer that ties these together is [`server.py`](../server.py) (FastAPI: queue,
SSE progress, auth) driving [`app.py`](../app.py) (the pipeline entry point).
