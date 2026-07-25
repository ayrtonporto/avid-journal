"""
AViD Journal — persistent Lean REPL pool.

Motivation
----------
The web pipeline used to compile every candidate with a fresh `lake env lean`
process, each of which re-imports Mathlib (~27s of olean deserialization) on
*every* round of *every* block. Benchmarked on the reference machine:

    cold  `lake env lean` per check : ~27s   (warm disk cache)
    warm  resident REPL, env 0 reuse: ~0.02s per trivial check
    one-time `import Mathlib`        : ~25s, paid ONCE per worker lifetime

This module keeps a small pool of resident REPL processes, each with Mathlib
imported once into `env 0`. Each compile check runs against `env 0`, so the
import cost is amortised away.

Concurrency
-----------
A REPL is a *serial* stdin/stdout conversation: two requests must never share
one worker at the same time. The pool holds N workers behind an idle queue —
each incoming check checks out an idle worker, uses it under its own lock, and
returns it. With N=2 (default) two analyses run warm in parallel; a third waits
in the queue. Every check runs against the pristine `env 0`, so no state leaks
between clients.

Safety
------
`compile_check()` degrades gracefully: if the pool is disabled, fails to start,
or a check errors/times out, it falls back to the original cold
`check_lean_file()` path, so the pipeline never breaks because of the REPL.

Enable with (see .env.example):
    AVID_REPL_POOL=1
    AVID_REPL_BIN=/path/to/repl            (the built REPL executable)
    AVID_REPL_POOL_SIZE=2                   (workers; ~4-6 GB RAM each)
"""

from .pool import (
    compile_check,
    get_pool,
    warm_pool,
    shutdown_pool,
    pool_enabled,
    ReplPool,
    ReplWorker,
)

__all__ = [
    "compile_check",
    "get_pool",
    "warm_pool",
    "shutdown_pool",
    "pool_enabled",
    "ReplPool",
    "ReplWorker",
]
