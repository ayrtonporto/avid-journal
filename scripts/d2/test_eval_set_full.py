"""Corrida completa de D2 (trivialidad) sobre los 24 teoremas del eval set.

Ejecutar desde la raíz del repo (Windows nativo):

    python scripts/d2/test_eval_set_full.py

    python scripts/d2/test_eval_set_full.py --verbose

    python scripts/d2/test_eval_set_full.py --lean-project "D:/ruta/al/lean_project"

    python scripts/d2/test_eval_set_full.py --no-prewarm   # si hay sesión Lean activa

NOTA: Esta corrida puede tardar 90–130 minutos.
Con imports mínimos, la esperanza es 90–100 min; si los imports no reducen
el overhead de startup significativamente, puede llegar a 120–130 min.
El script imprime resultados en tiempo real e incrementa el CSV en disco
después de cada teorema — si se interrumpe, los resultados parciales se conservan.

Salida: scripts/d2/results/eval_set_full_<YYYYMMDD_HHMMSS>.csv

Deduplicación para D2:
  T07a = T07b (mismo tipo τ — par Euclides/Euler, diferencia aparece en D3)
  T08a = T08b (mismo tipo τ — par paridad/raíz-racional)
  T09a = T09b (mismo tipo τ — par inducción/Gauss)
  → Testeamos T07, T08, T09 una vez (enunciado canónico de T07a, T08a, T09a).
  T20 excluido (mismo enunciado que T01/T08 → D2 redundante; se procesa en D1, Día 6).
  T21 excluido (TBD — requiere caso específico de Kasaura et al., Día 19).

SUPUESTO DOCUMENTADO (results_log.md):
  La identidad de D2 para pares a/b asume formalización canónica de los tipos.
  Este supuesto se sostiene cuando se escriben los enunciados a mano (como en esta corrida).
  Un autoformalizador podría romperlo si formaliza T07a y T07b con tipos Lean distintos
  (p. ej. distintas formulas de ∃). Reportar si sucede en corridas automatizadas futuras.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# UTF-8 en consola Windows para que los enunciados con ∀ ≤ ℝ etc. se impriman.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

# Permite importar src/ desde repo root aunque se llame como script suelto.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.novelty_v2.dimensions.d2_triviality import check_triviality

# ---------------------------------------------------------------------------
# Default lean_project para Windows nativo
# ---------------------------------------------------------------------------

_WIN_DEFAULT = Path("D:/Mis documentos/Documentos/AViD Journal/lean_project")
_RELATIVE_DEFAULT = Path(__file__).resolve().parents[2] / "lean_project"
DEFAULT_LEAN_PROJECT = _WIN_DEFAULT if _WIN_DEFAULT.exists() else _RELATIVE_DEFAULT

# ---------------------------------------------------------------------------
# Grupos de imports mínimos
# ---------------------------------------------------------------------------
# Principio: usar los módulos mínimos que satisfacen el enunciado.
# Beneficio: menor tiempo de carga de oleans + detección temprana de dependencias.
# Riesgo: si el módulo elegido no incluye el término necesario, Lean dará error de
#   tipo; el script lo registra como NO TRIVIAL (con output de error en el CSV).
#   Los módulos marcados con [?] son inciertos y pueden necesitar ajuste.

_IMP_TACTIC = "import Mathlib.Tactic"
# ^ Para tácticas puras sobre ℕ/ℤ básico. Incluye decide, omega, norm_num, simp, aesop, tauto.

_IMP_PARITY = "import Mathlib.Tactic\nimport Mathlib.Data.Int.Parity"
# ^ Para Even sobre ℤ y ℕ (Int.Parity importa Nat.Parity transitivamente). [?]

_IMP_REAL = (
    "import Mathlib.Tactic\n"
    "import Mathlib.Analysis.SpecialFunctions.Pow.Real\n"
    "import Mathlib.Data.Real.Irrational"
)
# ^ Para Irrational, Real.sqrt. [?] Irrational puede estar en topology/order.

_IMP_NAT_PRIME = "import Mathlib.Tactic\nimport Mathlib.Data.Nat.Prime"
# ^ Para Nat.Prime, Nat.Prime.two_le, etc.

_IMP_FINSET = (
    "import Mathlib.Tactic\n"
    "import Mathlib.Algebra.BigOperators.Group.Finset"
)
# ^ Para Finset.range, Finset.sum, Finset.prod, BigOperators notation.

_IMP_FTC = (
    "import Mathlib.Tactic\n"
    "import Mathlib.MeasureTheory.Integral.FundThmCalculus"
)
# ^ Para intervalIntegral, HasDerivAt, IntervalIntegrable. [?] módulo exacto incierto.

_IMP_INNER = (
    "import Mathlib.Tactic\n"
    "import Mathlib.Analysis.InnerProductSpace.PiL2"
)
# ^ Para EuclideanSpace ℝ (Fin n), inner, ‖⋅‖ en espacios euclídeos.

_IMP_RPOW_AMGM = (
    "import Mathlib.Tactic\n"
    "import Mathlib.Analysis.SpecialFunctions.Pow.Real\n"
    "import Mathlib.Algebra.BigOperators.Group.Finset"
)
# ^ Para Real.rpow (via ^), Finset.prod/sum sobre Fin n.

_IMP_SGRAPH = (
    "import Mathlib.Tactic\n"
    "import Mathlib.Combinatorics.SimpleGraph.Connectivity\n"
    "import Mathlib.Combinatorics.SimpleGraph.Acyclicity"
)
# ^ Para SimpleGraph.Connected, IsAcyclic. IsTree puede estar en Acyclicity o Trees. [?]

_IMP_ALGGEOM = (
    "import Mathlib.Tactic\n"
    "import Mathlib.AlgebraicGeometry.Scheme"
)
# ^ Para AlgebraicGeometry.Scheme, IsNoetherianScheme.
# CoherentSheaf y HasFiniteLocallyFreeResolution NO existen → tipo error esperado.

_IMP_PARITY_FINSET = (
    "import Mathlib.Tactic\n"
    "import Mathlib.Data.Int.Parity\n"
    "import Mathlib.Algebra.BigOperators.Group.Finset"
)
# ^ Para Even sobre ℤ con sumas de Finset (T26).

# ---------------------------------------------------------------------------
# Casos de test — 24 teoremas del eval set deduplicados para D2
# ---------------------------------------------------------------------------

TEST_CASES = [

    # ═══════════════════════════════════════════════════════════════════════
    # CATEGORÍA 1: Clásicos en mathlib (D1 → NO_NOVEDOSO_redundante)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "id": "T01",
        "categoria": "clasico_en_mathlib",
        "desc": "La raíz cuadrada de 2 es irracional",
        "lean_statement": "Irrational (Real.sqrt 2)",
        "lean_imports": _IMP_REAL,
        "expected_trivial": False,
        "notas": "Mathlib: irrational_sqrt_two. No automatizable.",
    },
    {
        "id": "T02",
        "categoria": "clasico_en_mathlib",
        "desc": "Existen infinitos números primos",
        "lean_statement": "∀ n : ℕ, ∃ p : ℕ, n ≤ p ∧ Nat.Prime p",
        "lean_imports": _IMP_NAT_PRIME,
        "expected_trivial": False,
        "notas": "Mathlib: Nat.exists_infinite_primes.",
    },
    {
        "id": "T03",
        "categoria": "clasico_en_mathlib",
        "desc": "Teorema fundamental del cálculo",
        "lean_statement": (
            "∀ (f f' : ℝ → ℝ) (a b : ℝ), a ≤ b → "
            "(∀ x ∈ Set.uIcc a b, HasDerivAt f (f' x) x) → "
            "IntervalIntegrable f' MeasureTheory.volume a b → "
            "∫ x in a..b, f' x = f b - f a"
        ),
        "lean_imports": _IMP_FTC,
        "expected_trivial": False,
        "notas": (
            "RIESGO: el enunciado puede no type-check si MeasureTheory.Integral."
            "FundThmCalculus no incluye HasDerivAt o Set.uIcc."
            " Error registrado en CSV si falla."
        ),
    },
    {
        "id": "T04",
        "categoria": "clasico_en_mathlib",
        "desc": "Pequeño teorema de Fermat: p | aᵖ - a",
        "lean_statement": (
            "∀ (p : ℕ) (a : ℤ), Nat.Prime p → (p : ℤ) ∣ a ^ p - a"
        ),
        "lean_imports": _IMP_NAT_PRIME,
        "expected_trivial": False,
        "notas": "Forma de divisibilidad. Mathlib: ZMod.intCast_zmod_eq_zero_iff_dvd.",
    },
    {
        "id": "T05",
        "categoria": "clasico_en_mathlib",
        "desc": "Teorema de Pitágoras",
        "lean_statement": (
            "∀ (x y : EuclideanSpace ℝ (Fin 2)), "
            "⟪x, y⟫_ℝ = 0 → "
            "‖x + y‖ ^ 2 = ‖x‖ ^ 2 + ‖y‖ ^ 2"
        ),
        "lean_imports": _IMP_INNER,
        "expected_trivial": False,
        "notas": (
            "Formulación canónica con EuclideanSpace. "
            "RIESGO menor: ⟪x,y⟫_ℝ puede necesitar 'open scoped InnerProductSpace'."
        ),
    },
    {
        "id": "T06",
        "categoria": "clasico_en_mathlib",
        "desc": "Suma 1+2+…+n = n(n+1)/2",
        "lean_statement": (
            "∀ (n : ℕ), 2 * ∑ i ∈ Finset.range (n + 1), i = n * (n + 1)"
        ),
        "lean_imports": _IMP_FINSET,
        "expected_trivial": False,
        "notas": "Multiplicado por 2 para evitar división entera en ℕ. Mathlib: Finset.sum_range_id.",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # CATEGORÍA 2: Pares con prueba distinta (D3 — misma τ, distinta π)
    # ═══════════════════════════════════════════════════════════════════════
    # NOTA: T07a/T07b, T08a/T08b, T09a/T09b tienen el mismo tipo τ para D2.
    # La diferencia entre a y b aparece en D3 (Días 8-9) cuando se comparen
    # los conjuntos de premisas de las dos pruebas.
    # SUPUESTO: esta identidad de enunciado se sostiene cuando los escribimos a mano.
    # Un autoformalizador podría producir tipos Lean distintos para la misma proposición
    # (p. ej. distintas curried forms o definiciones desplegadas). Registrar en D3.

    {
        "id": "T07",
        "categoria": "par_distinta_prueba",
        "desc": "Infinitos primos (T07a Euclides / T07b Euler — mismo τ para D2)",
        "lean_statement": "∀ n : ℕ, ∃ p : ℕ, n ≤ p ∧ Nat.Prime p",
        "lean_imports": _IMP_NAT_PRIME,
        "expected_trivial": False,
        "notas": "Idéntico a T02. D3 distinguirá Euclides (T07a) de Euler (T07b).",
    },
    {
        "id": "T08",
        "categoria": "par_distinta_prueba",
        "desc": "√2 irracional (T08a paridad / T08b raíz racional — mismo τ para D2)",
        "lean_statement": "Irrational (Real.sqrt 2)",
        "lean_imports": _IMP_REAL,
        "expected_trivial": False,
        "notas": "Idéntico a T01. D3 distinguirá paridad (T08a) de raíz racional (T08b).",
    },
    {
        "id": "T09",
        "categoria": "par_distinta_prueba",
        "desc": "Suma gaussiana (T09a inducción / T09b emparejamiento — mismo τ para D2)",
        "lean_statement": (
            "∀ (n : ℕ), 2 * ∑ i ∈ Finset.range (n + 1), i = n * (n + 1)"
        ),
        "lean_imports": _IMP_FINSET,
        "expected_trivial": False,
        "notas": (
            "Idéntico a T06. D3 distinguirá inducción (T09a) de truco de Gauss (T09b). "
            "POSIBLE COLAPSO: T09b (Gauss) puede no tener traducción natural distinta "
            "en Lean 4 — documentar en D3 si T09a y T09b producen el mismo término de prueba."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════
    # CATEGORÍA 3: Enunciados cercanos distintos (D1 zona gris)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "id": "T10",
        "categoria": "enunciados_cercanos_distintos",
        "desc": "Todo primo mayor que 2 es impar",
        "lean_statement": "∀ (p : ℕ), Nat.Prime p → 2 < p → ¬ 2 ∣ p",
        "lean_imports": _IMP_NAT_PRIME,
        "expected_trivial": False,
        "notas": "omega/decide no conocen Nat.Prime. Mathlib: Nat.Prime.odd_of_ne_two.",
    },
    {
        "id": "T11",
        "categoria": "enunciados_cercanos_distintos",
        "desc": "Todo primo mayor que 2 es ≡ 1 o 3 (mod 4)",
        "lean_statement": (
            "∀ (p : ℕ), Nat.Prime p → 2 < p → p % 4 = 1 ∨ p % 4 = 3"
        ),
        "lean_imports": _IMP_NAT_PRIME,
        "expected_trivial": False,
        "notas": "Requiere teoría de números no trivial. Sin lema directo en Mathlib con esta forma.",
    },
    {
        "id": "T12",
        "categoria": "enunciados_cercanos_distintos",
        "desc": "AM-GM para n=2: √(ab) ≤ (a+b)/2",
        "lean_statement": (
            "∀ (a b : ℝ), 0 ≤ a → 0 ≤ b → Real.sqrt (a * b) ≤ (a + b) / 2"
        ),
        "lean_imports": _IMP_REAL,
        "expected_trivial": False,
        "notas": "Real.sqrt no se maneja con norm_num/nlinarith sin lemas específicos.",
    },
    {
        "id": "T13",
        "categoria": "enunciados_cercanos_distintos",
        "desc": "AM-GM general: (∏f)^(1/n) ≤ (Σf)/n",
        "lean_statement": (
            "∀ (n : ℕ) (hn : 0 < n) (f : Fin n → ℝ), (∀ i, 0 ≤ f i) → "
            "(∏ i : Fin n, f i) ^ ((1 : ℝ) / (n : ℝ)) ≤ (∑ i : Fin n, f i) / (n : ℝ)"
        ),
        "lean_imports": _IMP_RPOW_AMGM,
        "expected_trivial": False,
        "notas": (
            "Usa Real.rpow (via ^ con exponente ℝ). "
            "RIESGO: coerción (n : ℝ) puede necesitar anotación explícita."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════
    # CATEGORÍA 4: Triviales (D2 → NO_NOVEDOSO_trivial)
    # Ya testeados en Día 4 — se re-corren para confirmar consistencia.
    # ═══════════════════════════════════════════════════════════════════════

    {
        "id": "T14",
        "categoria": "trivial",
        "desc": "La suma de cuatro enteros pares es par (YA TESTEADO Día 4)",
        "lean_statement": (
            "∀ (a b c d : Int), "
            "Even a → Even b → Even c → Even d → Even (a + b + c + d)"
        ),
        "lean_imports": _IMP_PARITY,
        "expected_trivial": True,
        "notas": "Confirmado Día 4: aesop, 215 s.",
    },
    {
        "id": "T15",
        "categoria": "trivial",
        "desc": "2 + 2 = 4 (YA TESTEADO Día 4)",
        "lean_statement": "(2 : Nat) + 2 = 4",
        "lean_imports": _IMP_TACTIC,
        "expected_trivial": True,
        "notas": "Confirmado Día 4: decide, 29 s.",
    },
    {
        "id": "T16",
        "categoria": "trivial",
        "desc": "∀ n : ℕ, n + 0 = n (YA TESTEADO Día 4)",
        "lean_statement": "∀ (n : Nat), n + 0 = n",
        "lean_imports": _IMP_TACTIC,
        "expected_trivial": True,
        "notas": "Confirmado Día 4: norm_num, 61 s.",
    },
    {
        "id": "T17",
        "categoria": "trivial",
        "desc": "∀ n : ℕ, n ≤ n + 1 (YA TESTEADO Día 4)",
        "lean_statement": "∀ (n : Nat), n ≤ n + 1",
        "lean_imports": _IMP_TACTIC,
        "expected_trivial": True,
        "notas": "Confirmado Día 4: norm_num, 60 s.",
    },
    {
        "id": "T18",
        "categoria": "trivial",
        "desc": "Σ primeros n impares = n² — TRAMPA DE CONTROL (YA TESTEADO Día 4)",
        "lean_statement": (
            "∀ (n : Nat), "
            "(Finset.range n).sum (fun k => 2 * k + 1) = n ^ 2"
        ),
        "lean_imports": _IMP_FINSET,
        "expected_trivial": False,
        "notas": "CONTROL: inducción necesaria. Confirmado Día 4: ninguna táctica cierra.",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # CATEGORÍA 5: Generados por IA
    # ═══════════════════════════════════════════════════════════════════════

    {
        "id": "T19",
        "categoria": "generado_IA",
        "desc": "LLM sobre pares: Even n → Even (n+2) [AGREGADO Día 5]",
        "lean_statement": "∀ (n : ℕ), Even n → Even (n + 2)",
        "lean_imports": _IMP_TACTIC,
        "expected_trivial": True,
        "notas": (
            "Enunciado representativo de lo que produce un LLM al pedir 'un teorema "
            "original sobre números pares'. Expectativa TRIVIAL confirma modo de falla LLM."
        ),
    },

    # ═══════════════════════════════════════════════════════════════════════
    # CATEGORÍA 6: Casos de falla
    # ═══════════════════════════════════════════════════════════════════════

    {
        "id": "T22",
        "categoria": "caso_falla",
        "desc": "Even n → Even (n+0) — equivalente lógico con sintaxis distinta",
        "lean_statement": "∀ (n : Nat), Even n → Even (n + 0)",
        "lean_imports": _IMP_TACTIC,
        "expected_trivial": True,
        "notas": (
            "D2 lo marca trivial (omega: n+0=n → Even n → Even n). "
            "El interés es D1: ¿detecta equivalencia lógica con 'Even n → Even n'?"
        ),
    },
    {
        "id": "T23",
        "categoria": "caso_falla",
        "desc": "Grafo conexo + acíclico → árbol — FALSO POSITIVO esperado (YA TESTEADO Día 4)",
        "lean_statement": (
            "∀ (V : Type) [Fintype V] [DecidableEq V] (G : SimpleGraph V), "
            "G.Connected → G.IsAcyclic → G.IsTree"
        ),
        "lean_imports": _IMP_SGRAPH,
        "expected_trivial": "probable (falso positivo esperado)",
        "notas": (
            "FALSO POSITIVO D2: IsTree = Connected ∧ IsAcyclic en Mathlib v4.29.0. "
            "Confirmado Día 4: tauto, 146 s. "
            "RIESGO IMPORT: IsTree puede no estar en SimpleGraph.Acyclicity. "
            "Si type-check falla → anotar y re-correr con import Mathlib."
        ),
    },
    {
        "id": "T24",
        "categoria": "caso_falla",
        "desc": "Haz coherente sobre esquema noetheriano — FALLA de formalización esperada",
        "lean_statement": (
            "∀ (X : AlgebraicGeometry.Scheme) "
            "[AlgebraicGeometry.IsNoetherianScheme X] "
            "(F : AlgebraicGeometry.CoherentSheaf X), "
            "∃ (n : ℕ), AlgebraicGeometry.HasFiniteLocallyFreeResolution F n"
        ),
        "lean_imports": _IMP_ALGGEOM,
        "expected_trivial": False,
        "notas": (
            "FALLA ESPERADA: CoherentSheaf y HasFiniteLocallyFreeResolution no existen "
            "en Mathlib v4.29.0. Error de type-check registrado en CSV (campo output). "
            "Dato experimental para Limitations del paper."
        ),
    },
    {
        "id": "T25",
        "categoria": "caso_falla",
        "desc": "Even n ↔ 2 ∣ n — equivalencia definicional (test D1 nivel 1)",
        "lean_statement": "∀ (n : ℕ), Even n ↔ 2 ∣ n",
        "lean_imports": _IMP_TACTIC,
        "expected_trivial": True,
        "notas": (
            "simp con Nat.even_iff_two_dvd debería cerrar. "
            "Si simp no lo encuentra sin argumento → omega tampoco → resultado real."
        ),
    },
    {
        "id": "T26",
        "categoria": "enunciados_cercanos_distintos",
        "desc": "Suma de n enteros pares es par — generalización de T14",
        "lean_statement": (
            "∀ (n : ℕ) (f : Fin n → ℤ), (∀ i, Even (f i)) → Even (∑ i, f i)"
        ),
        "lean_imports": _IMP_PARITY_FINSET,
        "expected_trivial": False,
        "notas": (
            "Generalización de T14 (caso n=4). n cuantificado → omega/decide no aplican. "
            "aesop podría intentarlo; si lo cierra → falso positivo conectado con T14."
        ),
    },
]

# Verificación de conteo en carga del módulo
assert len(TEST_CASES) == 24, f"Esperados 24 casos, encontrados {len(TEST_CASES)}"


# ---------------------------------------------------------------------------
# Pre-calentamiento de oleans
# ---------------------------------------------------------------------------

def _prewarm(lean_project_dir: Path) -> None:
    """Carga oleans de Mathlib en caché de OS antes del cronómetro de tests.

    Usa 'import Mathlib' para calentar el caché completo — beneficia todos los
    grupos de imports, incluso los mínimos (los oleans ya están en RAM/disco-cache).
    """
    src = "import Mathlib\n\nexample : True := trivial\n"
    fd, path = tempfile.mkstemp(suffix=".lean", prefix="avid_prewarm_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(src)
        print("Pre-calentando entorno Lean (carga de oleans en caché de OS)...")
        print("  (usando 'import Mathlib' para calentar todos los grupos de imports)")
        t0 = time.monotonic()
        r = subprocess.run(
            ["lake", "env", "lean", path],
            cwd=lean_project_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
        elapsed = time.monotonic() - t0
        if r.returncode == 0:
            print(f"  ✓ Listo en {elapsed:.1f}s — caché caliente\n")
        else:
            print(f"  ⚠ Prewarm falló (rc={r.returncode}, {elapsed:.1f}s)")
            print(f"  stderr: {r.stderr[:200]}\n")
    except subprocess.TimeoutExpired:
        print("  ⚠ Prewarm timeout (>300s) — tests pueden ser lentos\n")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Formato de salida
# ---------------------------------------------------------------------------

def _fmt_attempts_short(all_attempts) -> str:
    """Muestra táctica ganadora o primer fallo con truncado."""
    for tactic, success, elapsed, out in all_attempts:
        if success:
            return f"✓ {tactic} ({elapsed:.1f}s)"
    # No ganador
    first_tactic, _, elapsed, out = all_attempts[0]
    err_snippet = ((out or "")[:60]).replace("\n", " ")
    return f"✗ [{len(all_attempts)} tácticas, {elapsed:.1f}s/primera] {err_snippet}"


def _fmt_attempts_verbose(all_attempts) -> str:
    lines = []
    for tactic, success, elapsed, out in all_attempts:
        mark = "✓" if success else "✗"
        short = ((out or "")[:80]).replace("\n", " ")
        lines.append(f"    {mark} {tactic:<12} {elapsed:.1f}s  {short}")
        if success:
            break
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Corrida principal
# ---------------------------------------------------------------------------

def run_full_eval(
    lean_project_dir: Path,
    csv_path: Path,
    verbose: bool = False,
) -> list:
    """Ejecuta D2 sobre todos los TEST_CASES, guarda CSV incremental, imprime en tiempo real."""

    total = len(TEST_CASES)
    results = []

    # Abrir CSV incremental — escribir encabezado
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_file = open(csv_path, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=[
        "id", "categoria", "desc",
        "d2_trivial", "tactica_ganadora", "tiempo_tactica_s", "tiempo_total_s",
        "expected_trivial", "correct", "import_group",
        "error_typecheck",  # True si todos los intentos fallaron con error de tipo
        "first_error_snippet",  # fragmento del primer error
        "notas",
    ])
    writer.writeheader()
    csv_file.flush()

    print(f"\n{'='*72}")
    print(f"D2 Trivialidad — eval set completo ({total} teoremas)")
    print(f"lean_project: {lean_project_dir}")
    print(f"CSV: {csv_path}")
    print(f"{'='*72}\n")

    grand_t0 = time.monotonic()

    for i, case in enumerate(TEST_CASES, 1):
        tid = case["id"]
        desc = case["desc"]
        stmt = case["lean_statement"]
        imports = case["lean_imports"]
        expected = case["expected_trivial"]

        # Línea de progress
        import_first_line = imports.split("\n")[0]
        print(f"[{i:02d}/{total}] {tid} — {desc[:55]}")
        print(f"         imports: {import_first_line}{'+…' if chr(10) in imports else ''}")
        print(f"         stmt: {stmt[:72]}{'...' if len(stmt) > 72 else ''}")

        t_start = time.monotonic()
        result = check_triviality(
            stmt,
            lean_project_dir=lean_project_dir,
            lean_imports=imports,
        )
        t_total = time.monotonic() - t_start

        # Determinar si hubo type-check error (todos los intentos fallaron
        # con error que no es "tactic failed")
        all_outputs = [out or "" for _, _, _, out in result.all_attempts]
        is_typecheck_error = (
            not result.trivial
            and len(result.all_attempts) > 0
            and any(
                "unknown identifier" in o or "unknown constant" in o or
                "application type mismatch" in o or "type expected" in o
                for o in all_outputs
            )
        )
        first_error = (all_outputs[0] if all_outputs else "")[:120]

        # Determinar si el resultado es correcto
        if isinstance(expected, bool):
            correct = (result.trivial == expected)
            correct_str = "✓" if correct else "✗"
            expected_str = "trivial" if expected else "no trivial"
        else:
            correct = None  # caso especial (T23 falso positivo esperado)
            correct_str = "ℹ"
            expected_str = str(expected)

        status = "TRIVIAL" if result.trivial else ("FALLA_TIPO" if is_typecheck_error else "NO TRIVIAL")
        winning = (
            f" ← {result.tactica} ({result.tiempo_segundos:.1f}s)"
            if result.trivial else ""
        )
        print(f"         → {status}{winning}  [total {t_total:.1f}s]  {correct_str} (esperado: {expected_str})")

        if verbose:
            print(_fmt_attempts_verbose(result.all_attempts))

        print()

        # Guardar en CSV incrementalmente
        row = {
            "id": tid,
            "categoria": case["categoria"],
            "desc": desc,
            "d2_trivial": result.trivial,
            "tactica_ganadora": result.tactica or "",
            "tiempo_tactica_s": f"{result.tiempo_segundos:.2f}" if result.tiempo_segundos else "",
            "tiempo_total_s": f"{t_total:.2f}",
            "expected_trivial": str(expected),
            "correct": str(correct),
            "import_group": import_first_line,
            "error_typecheck": is_typecheck_error,
            "first_error_snippet": first_error.replace("\n", " "),
            "notas": case["notas"],
        }
        writer.writerow(row)
        csv_file.flush()
        results.append(row)

    csv_file.close()

    grand_total = time.monotonic() - grand_t0
    print(f"\n{'='*72}")
    print(f"Corrida completada en {grand_total:.1f}s ({grand_total/60:.1f} min)")
    print(f"CSV guardado en: {csv_path}")
    print(f"{'='*72}\n")

    return results


# ---------------------------------------------------------------------------
# Tabla resumen por categoría
# ---------------------------------------------------------------------------

def print_summary_table(results: list) -> None:
    """Imprime tabla de resultados agrupada por categoría."""

    # Agrupar
    by_cat: dict = {}
    for row in results:
        cat = row["categoria"]
        by_cat.setdefault(cat, []).append(row)

    cat_order = [
        "clasico_en_mathlib",
        "par_distinta_prueba",
        "enunciados_cercanos_distintos",
        "trivial",
        "generado_IA",
        "caso_falla",
    ]

    print(f"\n{'='*72}")
    print("TABLA RESUMEN — D2 por categoría")
    print(f"{'='*72}")
    print(f"{'ID':<6}  {'D2':<12}  {'Táctica':<12}  {'Tiempo':<8}  {'OK?':<5}  {'Notas (cortas)'}")
    print(f"{'-'*6}  {'-'*12}  {'-'*12}  {'-'*8}  {'-'*5}  {'-'*30}")

    total_correct = 0
    total_bool = 0

    for cat in cat_order:
        cases = by_cat.get(cat, [])
        if not cases:
            continue
        print(f"\n  [{cat.upper()}]")
        for row in cases:
            trivial = row["d2_trivial"]
            tactica = row["tactica_ganadora"] or ("FALLA_TIPO" if row["error_typecheck"] == "True" else "—")
            tiempo = row["tiempo_total_s"]
            correct_str = row["correct"]
            notas_short = row["notas"][:35] + "…" if len(row["notas"]) > 35 else row["notas"]

            status = "TRIVIAL" if trivial == "True" else (
                "FALLA_TIPO" if row["error_typecheck"] == "True" else "NO TRIVIAL"
            )

            if correct_str == "True":
                ok = "✓"
                total_correct += 1
                total_bool += 1
            elif correct_str == "False":
                ok = "✗"
                total_bool += 1
            else:
                ok = "ℹ"  # caso especial

            print(f"  {row['id']:<6}  {status:<12}  {tactica:<12}  {tiempo:>6}s  {ok:<5}  {notas_short}")

    print(f"\n{'-'*72}")
    print(f"Score con expectativa booleana: {total_correct}/{total_bool}")

    # Resumen por categoría
    print(f"\nAciertos por categoría:")
    for cat in cat_order:
        cases = by_cat.get(cat, [])
        n_correct = sum(1 for r in cases if r["correct"] == "True")
        n_bool = sum(1 for r in cases if r["correct"] != "None")
        n_special = sum(1 for r in cases if r["correct"] == "None")
        if n_bool > 0 or n_special > 0:
            print(f"  {cat:<35} {n_correct}/{n_bool} correctos"
                  + (f" + {n_special} casos especiales" if n_special else ""))
    print(f"{'='*72}\n")


# ---------------------------------------------------------------------------
# Tiempos por táctica (estadística)
# ---------------------------------------------------------------------------

def print_tactic_stats(results: list) -> None:
    """Imprime qué tácticas ganaron y en qué tiempos."""
    wins: dict = {}
    for row in results:
        t = row["tactica_ganadora"]
        if t:
            wins[t] = wins.get(t, 0) + 1

    if wins:
        print("Tácticas ganadoras:")
        for tac, count in sorted(wins.items(), key=lambda x: -x[1]):
            print(f"  {tac:<12} {count} casos")
    else:
        print("Ninguna táctica cerró ningún goal.")


# ---------------------------------------------------------------------------
# Estimación de tiempo antes de correr
# ---------------------------------------------------------------------------

def _print_time_estimate() -> None:
    n_expected_trivial = sum(
        1 for c in TEST_CASES if c["expected_trivial"] is True
    )
    n_expected_nontrivial = sum(
        1 for c in TEST_CASES
        if c["expected_trivial"] is False
        or c["expected_trivial"] == "probable (falso positivo esperado)"
    )
    # Triviales: en promedio paran a la táctica 3-5 → ~90-150s
    # No triviales: 7 tácticas × 30s = ~210s
    est_trivial = n_expected_trivial * 100  # segundos promedio
    est_nontrivial = n_expected_nontrivial * 210
    est_prewarm = 30  # si caché caliente; 165 si no
    est_total = est_trivial + est_nontrivial + est_prewarm
    print(f"\n⏱  Estimación de tiempo:")
    print(f"   {n_expected_trivial} casos esperados TRIVIALES × ~100s promedio = ~{est_trivial//60} min")
    print(f"   {n_expected_nontrivial} casos esperados NO TRIVIALES × ~210s = ~{est_nontrivial//60} min")
    print(f"   Prewarm (si caché caliente): ~{est_prewarm}s")
    print(f"   Total estimado: {est_total//60}–{(est_total + 30*len(TEST_CASES))//60} minutos")
    print(f"   Rango real esperado con imports mínimos: 90–130 minutos\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="D2 (trivialidad) sobre el eval set completo — 24 teoremas."
    )
    parser.add_argument(
        "--lean-project",
        type=Path,
        default=DEFAULT_LEAN_PROJECT,
        help=f"Ruta al lean_project/ con Mathlib pre-compilado. Default: {DEFAULT_LEAN_PROJECT}",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar todos los intentos de tácticas, no solo el ganador.",
    )
    parser.add_argument(
        "--no-prewarm",
        action="store_true",
        help="Saltear el pre-calentamiento de oleans (útil si hay sesión Lean reciente).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo imprimir los casos sin correr Lean (verificar lista de 24).",
    )
    args = parser.parse_args()

    if not args.lean_project.exists():
        print(f"ERROR: lean_project no encontrado en {args.lean_project}")
        print("Especificá --lean-project /ruta/ con Mathlib compilado.")
        sys.exit(1)

    # Dry run: solo listar casos
    if args.dry_run:
        print(f"\nDRY RUN — {len(TEST_CASES)} casos registrados:\n")
        for i, c in enumerate(TEST_CASES, 1):
            exp = c["expected_trivial"]
            exp_s = "TRIVIAL" if exp is True else ("NO TRIVIAL" if exp is False else str(exp))
            print(f"  [{i:02d}] {c['id']:<6} [{c['categoria']:<30}]  {exp_s:<12}  {c['desc'][:50]}")
        print()
        return

    # Mostrar estimación antes de correr
    _print_time_estimate()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = (
        Path(__file__).resolve().parent / "results" / f"eval_set_full_{timestamp}.csv"
    )

    if not args.no_prewarm:
        _prewarm(args.lean_project)

    results = run_full_eval(args.lean_project, csv_path, verbose=args.verbose)

    print_summary_table(results)
    print_tactic_stats(results)


if __name__ == "__main__":
    main()
