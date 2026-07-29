# src/lean_repl — Resident Mathlib REPL pool

Loading Mathlib cold takes ~2 min and re-deserializes thousands of `.olean` files. This
module keeps a **pool of long-lived Lean REPL processes** with Mathlib already loaded in
environment 0, so every compile check across the pipeline (formalization, D2, D3) is
sub-second instead of paying that cost each time.

Measured impact: a full pipeline run dropped from **~800 s to ~100 s (≈8×)**.

## API

`pool.py` exposes a small facade:

| Function | Use |
|---|---|
| `compile_check(code, context, target, project_dir)` | Type-check Lean `code` against Mathlib env 0. Drop-in for the old cold checker. |
| `query_env_chain(cmd1, cmd2, project_dir)` | Elaborate `cmd1` on env 0, then run `cmd2` against the resulting env — used for D3 side-A premise extraction. |

Under the hood a `ReplPool` manages N `ReplWorker` processes; workers are recycled after
a configurable number of uses to bound memory.

## Configuration

| Variable | Meaning |
|---|---|
| `AVID_REPL_POOL` | `1` to enable the pool (falls back to a cold checker if off). |
| `AVID_REPL_POOL_SIZE` | Number of resident workers. Each holds its own Mathlib (~2.5 GB RAM). |
| `AVID_REPL_BIN` | Path to the built `repl` binary (baked into the Docker image). |

Keep `AVID_ANALYSIS_WORKERS` (in `server.py`) equal to the pool size — there is no point
running more concurrent analyses than resident Mathlib envs.
