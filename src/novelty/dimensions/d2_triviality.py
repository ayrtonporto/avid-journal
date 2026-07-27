"""D2 — No-trivialidad.

Para cada táctica en T_auto = {decide, norm_num, simp, omega, tauto, exact?, aesop},
genera `example : τ := by T` y ejecuta `lake env lean` con presupuesto de tiempo b.
Devuelve qué táctica cerró el goal, si alguna.

Spec: paper/metric_spec.md §4.2

Valores de presupuesto (registrados en paper/decisions.md):
  - decide, omega, simp, norm_num, tauto, exact?: 10 s
  - aesop: 30 s  (búsqueda más exhaustiva)

Entorno de ejecución: Windows nativo con Lean 4.29.0 (x86_64-w64-windows-gnu).
`lake env lean` en Windows tarda ~30 s con caché de OS caliente solo en inicialización
de entorno (carga de oleans de Mathlib). El OS timeout incluye un overhead constante
LEAN_STARTUP_OVERHEAD_S para absorber esa latencia.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..types import D2Result

# Orden de ejecución: tácticas baratas y específicas primero, aesop al final.
# NOTA (2026-06-28): exact? se movió a D1 como fuente secundaria de C_F.
# La táctica busca teoremas existentes en el entorno, lo cual es una verificación
# de existencia previa, no de trivialidad. Ver paper/decisions.md.
T_AUTO_ORDER: List[str] = [
    "decide",
    "norm_num",
    "simp",
    "omega",
    "tauto",
    "aesop",
]

# Overhead constante de inicialización de entorno Lean (carga de oleans de Mathlib).
# En Windows nativo con OS cache caliente: ~28-32 s medidos experimentalmente.
# Se usa como margen extra en el OS timeout: timeout_os = budget_s + LEAN_STARTUP_OVERHEAD_S.
LEAN_STARTUP_OVERHEAD_S: int = 45

DEFAULT_BUDGETS: Dict[str, int] = {
    "decide": 10,
    "norm_num": 10,
    "simp": 10,
    "omega": 10,
    "tauto": 10,
    "aesop": 30,
}


# Predicados que norm_num "demuestra" por atajo hardcodeado, no por
# trivialidad genuina. Saltamos norm_num cuando el enunciado los contiene
# para evitar falsos positivos (L10 — paper/decisions.md).
_NORM_NUM_BLACKLIST = ["Irrational"]


def _heartbeats(budget_seconds: int) -> int:
    # ~200_000 heartbeats ≈ 1–2 s en hardware moderno; usamos 400k/s como techo
    # generoso. El OS timeout es el límite duro.
    return budget_seconds * 400_000


def _lean_source(
    statement: str,
    tactic: str,
    heartbeats: int,
    lean_imports: str = "import Mathlib",
) -> str:
    return (
        f"{lean_imports}\n\n"
        f"set_option maxHeartbeats {heartbeats}\n\n"
        f"example : {statement} := by\n"
        f"  {tactic}\n"
    )


def _run_tactic(
    lean_statement: str,
    tactic: str,
    lean_project_dir: Path,
    budget_seconds: int,
    lean_imports: str = "import Mathlib",
) -> Tuple[bool, float, Optional[str]]:
    """Ejecuta un intento con una táctica. Devuelve (success, elapsed_s, output)."""
    source = _lean_source(lean_statement, tactic, _heartbeats(budget_seconds), lean_imports)

    # Warm fast-path: correr la táctica contra el pool de REPLs residentes
    # (Mathlib en env 0), evitando el ~30s de `lake env lean` frío por táctica.
    # `pool.check` neutraliza el `import Mathlib` del source (env 0 ya lo tiene).
    # Si el pool está apagado o falla, cae al path frío de abajo.
    try:
        from src.lean_repl import pool_enabled, get_pool
        if pool_enabled():
            pool = get_pool(lean_project_dir)
            if pool is not None:
                t0 = time.monotonic()
                has_error, _hs, out, _err = pool.check(
                    source, "", timeout=budget_seconds + LEAN_STARTUP_OVERHEAD_S
                )
                return (not has_error), time.monotonic() - t0, (out or None)
    except Exception:
        pass  # fall back to the cold subprocess path

    fd, tmppath = tempfile.mkstemp(suffix=".lean", prefix="avid_d2_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(source)

        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                ["lake", "env", "lean", tmppath],
                cwd=lean_project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=budget_seconds + LEAN_STARTUP_OVERHEAD_S,
            )
            elapsed = time.monotonic() - t0
            success = proc.returncode == 0
            out = (proc.stdout + proc.stderr).strip() or None
            return success, elapsed, out
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - t0
            return False, elapsed, f"timeout after {budget_seconds + LEAN_STARTUP_OVERHEAD_S}s"
        except FileNotFoundError:
            elapsed = time.monotonic() - t0
            return (
                False,
                elapsed,
                "lake no encontrado — asegurate de que lake/lean estén en PATH",
            )
    finally:
        try:
            os.unlink(tmppath)
        except OSError:
            pass


def check_triviality(
    lean_statement: str,
    lean_project_dir: Optional[str | Path] = None,
    budgets: Optional[Dict[str, int]] = None,
    lean_imports: str = "import Mathlib",
) -> D2Result:
    """Intenta cerrar lean_statement con cada táctica en T_auto + exact?.

    Detiene en la primera táctica que cierra el goal (trivial = True).
    Si ninguna lo cierra, devuelve trivial = False con todos los intentos.

    Args:
        lean_statement: Expresión de tipo Lean τ, sin 'example :' ni ':= by'.
            Ej.: '∀ (n : Nat), n + 0 = n'
        lean_project_dir: Ruta al lean_project/ del repo (debe tener Mathlib y
            sus oleans pre-compilados). Por defecto: detectado relativo al módulo
            (parents[3]/lean_project). Pasar explícitamente si el auto-detect falla.
        budgets: Presupuesto en segundos por táctica.
            Valores por defecto: 10 s para todas salvo aesop (30 s).
        lean_imports: Líneas de import para el archivo Lean generado.
            Por defecto 'import Mathlib'. Usar imports mínimos para reducir
            tiempo de carga. Ej.: 'import Mathlib.Tactic\\nimport Mathlib.Data.Nat.Prime'
            NOTA: cambiar este parámetro NO afecta el comportamiento validado de los
            tests del Día 4 (todos usaron el default 'import Mathlib').

    Returns:
        D2Result con trivial flag, táctica ganadora, tiempo, y all_attempts.
    """
    if lean_project_dir is None:
        # parents: [0]=dimensions/ [1]=novelty_v2/ [2]=src/ [3]=repo_root/
        lean_project_dir = Path(__file__).resolve().parents[3] / "lean_project"
    lean_project_dir = Path(lean_project_dir)
    budgets = {**DEFAULT_BUDGETS, **(budgets or {})}

    # Saltar norm_num si el enunciado contiene predicados con atajos
    # hardcodeados (e.g. Irrational — L10).
    tactics_order = list(T_AUTO_ORDER)
    if any(pred in lean_statement for pred in _NORM_NUM_BLACKLIST):
        tactics_order = [t for t in tactics_order if t != "norm_num"]

    all_attempts: List[Tuple[str, bool, float, Optional[str]]] = []

    for tactic in tactics_order:
        budget = budgets.get(tactic, 10)
        success, elapsed, out = _run_tactic(
            lean_statement, tactic, lean_project_dir, budget, lean_imports
        )
        all_attempts.append((tactic, success, elapsed, out))
        if success:
            return D2Result(
                trivial=True,
                tactica=tactic,
                tiempo_segundos=elapsed,
                all_attempts=all_attempts,
            )

    return D2Result(
        trivial=False,
        tactica=None,
        tiempo_segundos=None,
        all_attempts=all_attempts,
    )
