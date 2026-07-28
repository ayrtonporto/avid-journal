"""Resident Lean REPL pool + a drop-in compile-check facade.

Public entry point is `compile_check(code, context_lean, fallback_target,
project_dir)`, which returns the SAME 4-tuple as
`src.formalization.scripts.lean_checker.check_lean_file`:

    (has_error: bool, has_sorry: bool, stdout: str, stderr: str)

so it is a behavioural drop-in for the cold checker.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("avid-repl")

# Lines that must be neutralised before sending code to a resident REPL: env 0
# already has `import Mathlib`, and Lean rejects any `import` inside a command
# that runs against an existing environment ("invalid 'import' command"). We
# replace each import line with a bare comment so line numbers stay aligned
# with the cold path's `full_code` (all of Mathlib is already loaded, so a
# narrower `import Mathlib.X` was redundant anyway).
_IMPORT_LINE_RE = re.compile(r"^[ \t]*import\b.*$", re.MULTILINE)


def _neutralize_imports(text: str) -> str:
    return _IMPORT_LINE_RE.sub("--", text or "")

# ── Tunables (env-overridable) ───────────────────────────────────────────────
IMPORT_TIMEOUT = float(os.environ.get("AVID_REPL_IMPORT_TIMEOUT", "300"))
CHECK_TIMEOUT = float(os.environ.get("AVID_REPL_CHECK_TIMEOUT", "120"))
ACQUIRE_TIMEOUT = float(os.environ.get("AVID_REPL_ACQUIRE_TIMEOUT", "180"))
# Recycle a worker after this many checks to bound the memory growth from the
# REPL storing a new environment per command. Restart re-imports Mathlib once.
RECYCLE_AFTER = int(os.environ.get("AVID_REPL_RECYCLE_AFTER", "150"))

# A no-op first line so REPL-reported line numbers line up with the cold path's
# `full_code`, which begins with `import Mathlib`. Same line count => the
# error_parser gets correct line numbers without any offset arithmetic.
_PRELUDE = "-- (Mathlib preloaded in env 0)"


# ═════════════════════════════════════════════════════════════════════════════
# Response parsing
# ═════════════════════════════════════════════════════════════════════════════
def _resp_to_tuple(resp: dict) -> Tuple[bool, bool, str, str]:
    """Convert a REPL JSON response into (has_error, has_sorry, stdout, stderr).

    `stdout` is synthesised in the standard Lean CLI diagnostic format
    (`file.lean:LINE:COL: severity: message`) so the existing
    `error_parser.parse_lean_errors` consumes it unchanged.
    """
    messages = resp.get("messages") or []
    sorries = resp.get("sorries") or []

    has_error = any(m.get("severity") == "error" for m in messages)
    has_sorry = bool(sorries) or any(
        "sorry" in (m.get("data", "") or "").lower() for m in messages
    )

    lines: List[str] = []
    for m in messages:
        pos = m.get("pos") or {}
        ln = pos.get("line", 1)
        col = pos.get("column", 0)
        sev = m.get("severity", "error")
        data = (m.get("data", "") or "").replace("\r", " ").replace("\n", " ")
        lines.append(f"repl.lean:{ln}:{col}: {sev}: {data}")
    for s in sorries:
        pos = s.get("pos") or {}
        ln = pos.get("line", 1)
        col = pos.get("column", 0)
        lines.append(f"repl.lean:{ln}:{col}: warning: declaration uses 'sorry'")

    return has_error, has_sorry, "\n".join(lines), ""


# ═════════════════════════════════════════════════════════════════════════════
# Worker: one resident REPL process
# ═════════════════════════════════════════════════════════════════════════════
class ReplWorker:
    """A single resident `lake env <repl>` process with Mathlib in env 0.

    Not thread-safe on its own — the pool guarantees one caller at a time by
    only handing an idle worker to a single check.
    """

    def __init__(self, project_dir: str | Path, repl_bin: str | Path, wid: int):
        self.project_dir = str(project_dir)
        self.repl_bin = str(repl_bin)
        self.wid = wid
        self.proc: Optional[subprocess.Popen] = None
        self.env0: Optional[int] = None
        self.out_q: "queue.Queue[Optional[str]]" = queue.Queue()
        self.n_checks = 0

    # ── process lifecycle ────────────────────────────────────────────────────
    def _spawn(self) -> None:
        # encoding="utf-8" is mandatory: the REPL emits UTF-8 (goal states use
        # ⊢, ∀, …). Without it, Windows would decode as cp1252 and mangle the
        # diagnostics fed back to the model.
        self.proc = subprocess.Popen(
            ["lake", "env", self.repl_bin],
            cwd=self.project_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self.out_q = queue.Queue()
        reader = threading.Thread(target=self._read_loop, daemon=True)
        reader.start()

    def _read_loop(self) -> None:
        assert self.proc and self.proc.stdout
        try:
            for line in self.proc.stdout:
                self.out_q.put(line)
        except Exception:  # pragma: no cover - defensive
            pass
        finally:
            self.out_q.put(None)  # EOF sentinel

    def _read_response(self, timeout: float) -> dict:
        """Read one JSON object, terminated by a blank line, with a deadline."""
        deadline = time.time() + timeout
        buf: List[str] = []
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError(f"worker {self.wid}: response timeout")
            try:
                line = self.out_q.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError(f"worker {self.wid}: response timeout")
            if line is None:
                raise EOFError(f"worker {self.wid}: process ended")
            if line.strip() == "":
                if buf:  # blank line after content => end of response
                    break
                continue  # skip leading blank lines
            buf.append(line)
        return json.loads("".join(buf))

    def start(self) -> None:
        """Spawn the process and import Mathlib into env 0 (the one-time cost)."""
        self._spawn()
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(json.dumps({"cmd": "import Mathlib"}) + "\n\n")
        self.proc.stdin.flush()
        resp = self._read_response(IMPORT_TIMEOUT)
        self.env0 = resp.get("env")
        if self.env0 is None:
            raise RuntimeError(
                f"worker {self.wid}: `import Mathlib` returned no env: {str(resp)[:200]}"
            )
        self.n_checks = 0
        logger.info("REPL worker %s ready (env0=%s)", self.wid, self.env0)

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def kill(self) -> None:
        try:
            if self.proc:
                self.proc.kill()
        except Exception:  # pragma: no cover - defensive
            pass

    # ── the actual check ─────────────────────────────────────────────────────
    def check(
        self, code: str, context_lean: str = "", timeout: float = CHECK_TIMEOUT
    ) -> Tuple[bool, bool, str, str]:
        assert self.proc and self.proc.stdin and self.env0 is not None
        # env 0 already imported Mathlib; strip any `import` lines from the
        # model's code (and context) or the REPL rejects the whole command.
        cmd = f"{_PRELUDE}\n\n{_neutralize_imports(context_lean)}\n\n{_neutralize_imports(code)}"
        self.proc.stdin.write(json.dumps({"cmd": cmd, "env": self.env0}) + "\n\n")
        self.proc.stdin.flush()
        resp = self._read_response(timeout)
        return _resp_to_tuple(resp)

    # ── raw command (for env chaining / metaprograms) ────────────────────────
    def run_raw(self, cmd: str, env: Optional[int], timeout: float = CHECK_TIMEOUT) -> dict:
        """Send one raw command against `env` and return the full REPL response
        dict (includes the resulting `env` id and `messages`). Used by callers
        that need the environment id (env chaining) or the raw message data
        (metaprograms), not the compile-check tuple."""
        assert self.proc and self.proc.stdin
        payload: dict = {"cmd": cmd}
        if env is not None:
            payload["env"] = env
        self.proc.stdin.write(json.dumps(payload) + "\n\n")
        self.proc.stdin.flush()
        return self._read_response(timeout)


# ═════════════════════════════════════════════════════════════════════════════
# Pool: N workers behind an idle queue
# ═════════════════════════════════════════════════════════════════════════════
class ReplPool:
    def __init__(self, size: int, project_dir: str | Path, repl_bin: str | Path):
        self.size = max(1, size)
        self.project_dir = project_dir
        self.repl_bin = repl_bin
        self.idle: "queue.Queue[ReplWorker]" = queue.Queue()
        self.workers: List[ReplWorker] = []
        self._start_lock = threading.Lock()
        self._started = False

    def start(self) -> int:
        """Spawn all workers in parallel (each import ~25s). Returns the number
        of workers that became ready."""
        with self._start_lock:
            if self._started:
                return self.idle.qsize()
            threads = []
            for i in range(self.size):
                w = ReplWorker(self.project_dir, self.repl_bin, i)
                self.workers.append(w)
                t = threading.Thread(target=self._start_one, args=(w,), daemon=True)
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
            self._started = True
            ready = self.idle.qsize()
            logger.info("REPL pool started: %d/%d workers ready", ready, self.size)
            return ready

    def _start_one(self, w: ReplWorker) -> None:
        try:
            w.start()
            self.idle.put(w)
        except Exception as e:
            logger.error("REPL worker %s failed to start: %s", w.wid, e)
            w.kill()

    def check(
        self,
        code: str,
        context_lean: str = "",
        timeout: float = CHECK_TIMEOUT,
        acquire_timeout: float = ACQUIRE_TIMEOUT,
    ) -> Tuple[bool, bool, str, str]:
        """Run one check on an idle worker. Blocks up to `acquire_timeout` for a
        free worker (natural back-pressure when all are busy). Raises on
        timeout/EOF/protocol errors after restarting the worker — the caller
        (compile_check) then falls back to the cold path."""
        try:
            w = self.idle.get(timeout=acquire_timeout)
        except queue.Empty:
            raise TimeoutError("no idle REPL worker available")

        try:
            if not w.alive():
                w.start()
            result = w.check(code, context_lean, timeout)
            w.n_checks += 1
            if w.n_checks >= RECYCLE_AFTER:
                logger.info("Recycling REPL worker %s after %d checks", w.wid, w.n_checks)
                w.kill()
                w.start()
            return result
        except (TimeoutError, EOFError, OSError, ValueError, json.JSONDecodeError) as e:
            # ValueError covers json.JSONDecodeError on some Python versions.
            logger.warning("REPL worker %s check failed (%s); restarting", w.wid, e)
            w.kill()
            try:
                w.start()
            except Exception as e2:
                logger.error("REPL worker %s restart failed: %s", w.wid, e2)
            raise
        finally:
            self.idle.put(w)

    def run_env_chain(
        self,
        cmd1: str,
        cmd2: str,
        timeout: float = CHECK_TIMEOUT,
        acquire_timeout: float = ACQUIRE_TIMEOUT,
    ) -> str:
        """Elaborate `cmd1` on top of env 0 (Mathlib), then run `cmd2` against the
        resulting environment, and return the concatenated `data` of cmd2's REPL
        messages. `cmd1`'s imports are neutralised (env 0 already has Mathlib).

        This lets a metaprogram (`cmd2`) inspect declarations introduced by
        `cmd1` — e.g. query the used constants of a freshly-elaborated candidate
        proof — reusing the resident Mathlib environment (sub-second)."""
        w = self.idle.get(timeout=acquire_timeout)
        try:
            if not w.alive():
                w.start()
            r1 = w.run_raw(_neutralize_imports(cmd1), w.env0, timeout)
            env1 = r1.get("env")
            if env1 is None:
                env1 = w.env0
            r2 = w.run_raw(cmd2, env1, timeout)
            w.n_checks += 1
            if w.n_checks >= RECYCLE_AFTER:
                logger.info("Recycling REPL worker %s after %d checks", w.wid, w.n_checks)
                w.kill()
                w.start()
            messages = r2.get("messages") or []
            return "\n".join((m.get("data", "") or "") for m in messages)
        except (TimeoutError, EOFError, OSError, ValueError, json.JSONDecodeError) as e:
            logger.warning("REPL worker %s env-chain failed (%s); restarting", w.wid, e)
            w.kill()
            try:
                w.start()
            except Exception as e2:
                logger.error("REPL worker %s restart failed: %s", w.wid, e2)
            raise
        finally:
            self.idle.put(w)

    def shutdown(self) -> None:
        for w in self.workers:
            w.kill()


# ═════════════════════════════════════════════════════════════════════════════
# Module-level singleton + facade
# ═════════════════════════════════════════════════════════════════════════════
_pool: Optional[ReplPool] = None
_pool_lock = threading.Lock()


def _repl_bin() -> str:
    return os.environ.get("AVID_REPL_BIN", "").strip()


def pool_enabled() -> bool:
    """True only if the pool is switched on AND the REPL binary actually exists.
    Any other case silently uses the cold path."""
    if os.environ.get("AVID_REPL_POOL", "0") != "1":
        return False
    binp = _repl_bin()
    return bool(binp) and Path(binp).exists()


def get_pool(project_dir: str | Path) -> Optional[ReplPool]:
    """Return the started pool, or None if disabled / unable to start."""
    global _pool
    if not pool_enabled():
        return None
    with _pool_lock:
        if _pool is None:
            size = int(os.environ.get("AVID_REPL_POOL_SIZE", "2"))
            p = ReplPool(size, project_dir, _repl_bin())
            try:
                ready = p.start()
            except Exception as e:
                logger.error("REPL pool init failed: %s", e)
                return None
            if ready <= 0:
                logger.error("REPL pool started but no workers ready; using cold path")
                p.shutdown()
                return None
            _pool = p
        return _pool


def warm_pool(project_dir: str | Path) -> Optional[ReplPool]:
    """Eagerly start the pool (call at server startup so the first client is
    already fast). No-op + None if disabled."""
    return get_pool(project_dir)


def shutdown_pool() -> None:
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.shutdown()
            _pool = None


def query_env_chain(
    cmd1: str,
    cmd2: str,
    project_dir: str | Path,
) -> Optional[str]:
    """Run `cmd1` then `cmd2` (against cmd1's env) on a resident worker and return
    cmd2's message data. Returns None if the pool is disabled/unavailable or the
    query fails — callers fall back to their cold path."""
    pool = get_pool(project_dir)
    if pool is None:
        return None
    try:
        return pool.run_env_chain(cmd1, cmd2)
    except Exception as e:
        logger.warning("query_env_chain failed: %s", e)
        return None


def compile_check(
    code: str,
    context_lean: str,
    fallback_target: str | Path,
    project_dir: str | Path,
) -> Tuple[bool, bool, str, str]:
    """Drop-in replacement for check_lean_file, warm when possible.

    Uses a resident REPL worker (env 0 = Mathlib) when the pool is enabled and
    healthy; otherwise writes `full_code` to `fallback_target` and calls the
    original cold `check_lean_file`. Always returns
    (has_error, has_sorry, stdout, stderr).
    """
    pool = get_pool(project_dir)
    if pool is not None:
        try:
            return pool.check(code, context_lean)
        except Exception as e:
            logger.warning("REPL pool unavailable, falling back to cold check: %s", e)

    # Cold fallback — identical to the historical behaviour.
    from src.formalization.scripts.lean_checker import check_lean_file

    full_code = f"import Mathlib\n\n{context_lean}\n\n{code}\n"
    Path(fallback_target).write_text(full_code, encoding="utf-8")
    return check_lean_file(Path(fallback_target))
