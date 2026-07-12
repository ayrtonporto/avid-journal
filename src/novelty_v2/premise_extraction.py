"""Auto-extracción de premisas vía ExtractData.lean + caché SHA256.

Ejecuta ExtractData en Windows nativo (subprocess + lake), cachea resultados
por hash del archivo .lean, y devuelve List[dict] en formato compute_d3.

Principio rector: DEGRADACIÓN ELEGANTE. Cualquier fallo → None + log.
Nunca excepción hacia arriba.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from src.novelty_v2.dimensions.d3_premises import load_premises_from_ast

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 900  # 15 minutes (3× the measured ~5 min for import Mathlib)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _sha256_hex(file_path: Path) -> str:
    """SHA256 hash of file content (hex string)."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _cache_dir(lean_project_dir: Path) -> Path:
    """Cache directory: <lean_project>/cache/premises/"""
    d = lean_project_dir / "cache" / "premises"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_path(lean_project_dir: Path, file_hash: str) -> Path:
    """Path to cached premises JSON for a given file hash."""
    return _cache_dir(lean_project_dir) / f"{file_hash}.json"


def _read_cache(cache_path: Path) -> Optional[List[dict]]:
    """Read cached premises. Returns None if missing or corrupt."""
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            logger.warning("Cache %s: not a list, ignoring", cache_path.name)
            return None
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cache %s: corrupt (%s), will re-extract",
                       cache_path.name, exc)
        return None


def _write_cache(cache_path: Path, premises: List[dict]) -> None:
    """Write premises to cache as JSON."""
    tmp = cache_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(premises, fh, ensure_ascii=False, indent=2)
    tmp.replace(cache_path)


# ---------------------------------------------------------------------------
# Extraction log
# ---------------------------------------------------------------------------

def _log_dir(lean_project_dir: Path) -> Path:
    """Log directory: <lean_project>/logs/extraction/"""
    d = lean_project_dir / "logs" / "extraction"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_extraction_log(log_path: Path, file_hash: str,
                          stdout: str, stderr: str,
                          elapsed_s: float, success: bool) -> None:
    """Write extraction stdout/stderr to a timestamped log file."""
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"{file_hash[:12]}_{ts}.log"
    with open(log_file, "w", encoding="utf-8") as fh:
        fh.write(f"hash: {file_hash}\n")
        fh.write(f"elapsed_s: {elapsed_s:.1f}\n")
        fh.write(f"success: {success}\n")
        fh.write("=" * 60 + "\n")
        fh.write("STDOUT:\n")
        fh.write(stdout)
        fh.write("\n" + "=" * 60 + "\n")
        fh.write("STDERR:\n")
        fh.write(stderr)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_premises(
    lean_file_path: str | Path,
    lean_project_dir: str | Path,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[List[dict]]:
    """Extrae premisas de un archivo .lean usando ExtractData.

    Pipeline:
      1. SHA256 del archivo → buscar en cache/premises/<hash>.json
      2. Cache hit → devolver (log: "cache hit")
      3. Cache miss → subprocess.run lake env lean --run ExtractData.lean
      4. Leer ast.json generado, extraer TODAS las premisas del archivo
      5. Guardar en caché, devolver

    Args:
        lean_file_path: ruta al archivo .lean (absoluta o relativa a cwd).
        lean_project_dir: ruta al proyecto Lean que contiene ExtractData.lean.
        timeout: segundos máximos para la extracción (default: 900s).

    Returns:
        Lista de dicts PremiseTrace (todos los del archivo), o None si falla.
        Nunca lanza excepción.
    """
    file_path = Path(lean_file_path).resolve()
    project_dir = Path(lean_project_dir).resolve()

    if not file_path.exists():
        logger.error("extract_premises: file not found: %s", file_path)
        return None

    if not (project_dir / "ExtractData.lean").exists():
        logger.error("extract_premises: ExtractData.lean not found in %s",
                     project_dir)
        return None

    # ── 1. Hash & cache check ────────────────────────────────────────────
    try:
        file_hash = _sha256_hex(file_path)
    except OSError as exc:
        logger.error("extract_premises: cannot hash file %s: %s", file_path, exc)
        return None

    cp = _cache_path(project_dir, file_hash)
    cached = _read_cache(cp)
    if cached is not None:
        logger.info("extract_premises: cache hit for %s (%d premises)",
                    file_path.name, len(cached))
        return cached

    # ── 2. Subprocess: lake env lean --run ExtractData.lean <file> ──────
    # Compute path relative to project_dir for the command
    try:
        rel_path = file_path.relative_to(project_dir)
    except ValueError:
        # File is outside project_dir — pass absolute path
        rel_path = file_path

    # Use POSIX-style path for lake (it handles both / and \ on Windows)
    rel_str = str(rel_path).replace("\\", "/")

    cmd = ["lake", "env", "lean", "--run", "ExtractData.lean", rel_str]
    logger.info("extract_premises: running %s in %s", " ".join(cmd), project_dir)

    import time
    t0 = time.monotonic()

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - t0
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - t0
        stdout = exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        _write_extraction_log(
            _log_dir(project_dir), file_hash, stdout, stderr, elapsed, False,
        )
        logger.error(
            "extract_premises: timeout after %ds for %s",
            timeout, file_path.name,
        )
        return None
    except Exception as exc:
        elapsed = time.monotonic() - t0
        _write_extraction_log(
            _log_dir(project_dir), file_hash, "", str(exc), elapsed, False,
        )
        logger.error(
            "extract_premises: subprocess failed for %s: %s",
            file_path.name, exc,
        )
        return None

    # ── 3. Log extraction output ─────────────────────────────────────────
    _write_extraction_log(
        _log_dir(project_dir), file_hash,
        proc.stdout, proc.stderr, elapsed, proc.returncode == 0,
    )

    if proc.returncode != 0:
        logger.error(
            "extract_premises: ExtractData failed (exit=%d) for %s",
            proc.returncode, file_path.name,
        )
        return None

    # ── 4. Locate ast.json ──────────────────────────────────────────────
    from src.novelty_v2.premise_autolocation import resolve_ast_json_path

    ast_json = resolve_ast_json_path(file_path, project_dir)
    if ast_json is None:
        logger.error(
            "extract_premises: ast.json not found for %s", file_path.name,
        )
        return None

    # ── 5. Parse premises ───────────────────────────────────────────────
    try:
        # Load ALL premises in the file (line 1 to 999999)
        premises = load_premises_from_ast(str(ast_json), 1, 999_999)
    except Exception as exc:
        logger.error(
            "extract_premises: failed to parse ast.json for %s: %s",
            file_path.name, exc,
        )
        return None

    # ── 6. Save to cache and return ─────────────────────────────────────
    try:
        _write_cache(cp, premises)
    except OSError as exc:
        logger.warning("extract_premises: cannot write cache: %s", exc)

    logger.info(
        "extract_premises: extracted %d premises from %s in %.1fs",
        len(premises), file_path.name, elapsed,
    )
    return premises


# ---------------------------------------------------------------------------
# Convenience: extract with theorem line filter
# ---------------------------------------------------------------------------

def extract_premises_for_theorem(
    lean_file_path: str | Path,
    lean_project_dir: str | Path,
    theorem_line_start: int,
    theorem_line_end: int,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[List[dict]]:
    """Extrae premisas y filtra por rango de líneas del teorema.

    Internamente llama a extract_premises (con caché) y luego filtra
    por pos.line dentro del rango especificado.

    Args:
        lean_file_path: ruta al archivo .lean.
        lean_project_dir: ruta al proyecto Lean.
        theorem_line_start: primera línea del teorema (inclusivo).
        theorem_line_end: última línea del teorema (inclusivo).
        timeout: segundos máximos para la extracción.

    Returns:
        Lista filtrada de dicts PremiseTrace, o None si falla la extracción.
    """
    all_premises = extract_premises(
        lean_file_path, lean_project_dir, timeout=timeout,
    )
    if all_premises is None:
        return None

    # Filter by line range
    result = []
    for p in all_premises:
        pos = p.get("pos")
        if pos is not None:
            line = pos.get("line", 0)
            if theorem_line_start <= line <= theorem_line_end:
                result.append(p)

    logger.debug(
        "extract_premises_for_theorem: %d/%d premises in lines %d-%d",
        len(result), len(all_premises), theorem_line_start, theorem_line_end,
    )
    return result
