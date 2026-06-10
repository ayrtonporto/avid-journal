"""Re-corrida de T14, T18, T23, T26 con `import Mathlib` completo.

Los 4 teoremas fallaron en la corrida principal por "object file" error
al usar imports específicos de Mathlib (_IMP_PARITY, _IMP_FINSET,
_IMP_SGRAPH, _IMP_PARITY_FINSET).  Este script los re-corre con
`import Mathlib` — único entry-point confiable en Mathlib v4.29.0
compilado monolíticamente (ver L11 en limitations.md).

Salida: scripts/d2/results/rerun_import_errors_<YYYYMMDD_HHMMSS>.csv

Uso:
    python scripts/d2/rerun_import_errors.py
    python scripts/d2/rerun_import_errors.py --lean-project "D:/ruta/al/lean_project"
    python scripts/d2/rerun_import_errors.py --verbose
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.novelty_v2.dimensions.d2_triviality import check_triviality

_WIN_DEFAULT = Path("D:/Mis documentos/Documentos/AViD Journal/lean_project")
_RELATIVE_DEFAULT = Path(__file__).resolve().parents[2] / "lean_project"
DEFAULT_LEAN_PROJECT = _WIN_DEFAULT if _WIN_DEFAULT.exists() else _RELATIVE_DEFAULT

_IMP_MATHLIB = "import Mathlib"

# ---------------------------------------------------------------------------
# Los 4 teoremas que fallaron por import error en la corrida principal
# ---------------------------------------------------------------------------

RERUN_CASES = [
    {
        "id": "T14",
        "categoria": "trivial",
        "desc": "La suma de cuatro enteros pares es par",
        "lean_statement": (
            "∀ (a b c d : Int), "
            "Even a → Even b → Even c → Even d → Even (a + b + c + d)"
        ),
        "lean_imports": _IMP_MATHLIB,
        "expected_trivial": True,
        "notas": "Re-corrida con import Mathlib (fallé con _IMP_PARITY). Día 4: aesop 215s.",
    },
    {
        "id": "T18",
        "categoria": "trivial",
        "desc": "Σ primeros n impares = n² — TRAMPA DE CONTROL",
        "lean_statement": (
            "∀ (n : Nat), "
            "(Finset.range n).sum (fun k => 2 * k + 1) = n ^ 2"
        ),
        "lean_imports": _IMP_MATHLIB,
        "expected_trivial": False,
        "notas": (
            "Re-corrida con import Mathlib (falló con _IMP_FINSET). "
            "CONTROL: inducción necesaria, ninguna táctica debe cerrar."
        ),
    },
    {
        "id": "T23",
        "categoria": "caso_falla",
        "desc": "Grafo conexo + acíclico → árbol — FALSO POSITIVO esperado",
        "lean_statement": (
            "∀ (V : Type) [Fintype V] [DecidableEq V] (G : SimpleGraph V), "
            "G.Connected → G.IsAcyclic → G.IsTree"
        ),
        "lean_imports": _IMP_MATHLIB,
        "expected_trivial": "probable (falso positivo esperado)",
        "notas": (
            "Re-corrida con import Mathlib (falló con _IMP_SGRAPH). "
            "Día 4: tauto cerró en 146s. FP esperado: IsTree = Connected ∧ IsAcyclic."
        ),
    },
    {
        "id": "T26",
        "categoria": "enunciados_cercanos_distintos",
        "desc": "Suma de n enteros pares es par — generalización de T14",
        "lean_statement": (
            "∀ (n : ℕ) (f : Fin n → ℤ), (∀ i, Even (f i)) → Even (∑ i, f i)"
        ),
        "lean_imports": _IMP_MATHLIB,
        "expected_trivial": False,
        "notas": (
            "Re-corrida con import Mathlib (falló con _IMP_PARITY_FINSET). "
            "Generalización de T14. aesop podría intentarlo."
        ),
    },
]

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Re-corre T14/T18/T23/T26 con import Mathlib")
    parser.add_argument("--lean-project", default=str(DEFAULT_LEAN_PROJECT))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    lean_project = Path(args.lean_project)
    if not lean_project.exists():
        print(f"ERROR: lean_project no encontrado en {lean_project}", file=sys.stderr)
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / f"rerun_import_errors_{ts}.csv"

    fieldnames = [
        "id", "categoria", "desc",
        "d2_trivial", "tactica_ganadora", "tiempo_tactica_s", "tiempo_total_s",
        "expected_trivial", "correct",
        "import_group", "error_typecheck", "first_error_snippet", "notas",
    ]

    print(f"\n{'='*60}")
    print(f"Re-corrida import Mathlib — {len(RERUN_CASES)} teoremas")
    print(f"lean_project: {lean_project}")
    print(f"Salida CSV: {csv_path}")
    print(f"{'='*60}\n")

    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        csv_file.flush()

        for i, tc in enumerate(RERUN_CASES, 1):
            tid = tc["id"]
            print(f"[{i}/{len(RERUN_CASES)}] {tid} — {tc['desc']}")
            print(f"  import: {_IMP_MATHLIB}")
            print(f"  enunciado: {tc['lean_statement'][:80]}...")

            t0 = time.monotonic()
            result = check_triviality(
                lean_statement=tc["lean_statement"],
                lean_project_dir=lean_project,
                lean_imports=tc["lean_imports"],
            )
            elapsed_total = time.monotonic() - t0

            # Extraer error typecheck del primer intento si lo hubo
            error_typecheck = False
            first_error_snippet = ""
            for _, success, _, out in result.all_attempts:
                if out and ("error" in out.lower() or "Error" in out):
                    error_typecheck = True
                    first_error_snippet = out[:100].replace("\n", " ")
                    break

            expected = tc["expected_trivial"]
            if isinstance(expected, bool):
                correct = result.trivial == expected
            else:
                correct = None  # expected_trivial es string (caso especial T23)

            row = {
                "id": tid,
                "categoria": tc["categoria"],
                "desc": tc["desc"],
                "d2_trivial": result.trivial,
                "tactica_ganadora": result.tactica or "",
                "tiempo_tactica_s": f"{result.tiempo_segundos:.2f}" if result.tiempo_segundos else "",
                "tiempo_total_s": f"{elapsed_total:.2f}",
                "expected_trivial": str(expected),
                "correct": str(correct),
                "import_group": _IMP_MATHLIB,
                "error_typecheck": error_typecheck,
                "first_error_snippet": first_error_snippet,
                "notas": tc["notas"],
            }
            writer.writerow(row)
            csv_file.flush()

            status = "✓ trivial" if result.trivial else "✗ no-trivial"
            tact = f"→ {result.tactica} ({result.tiempo_segundos:.1f}s)" if result.trivial else ""
            print(f"  {status} {tact}  [total: {elapsed_total:.1f}s]")

            if args.verbose:
                for tname, success, elapsed, out in result.all_attempts:
                    mark = "✓" if success else "✗"
                    print(f"    {mark} {tname}: {elapsed:.1f}s")

            print()

    print(f"\n{'='*60}")
    print(f"Resultados guardados: {csv_path}")
    print(f"{'='*60}\n")

    # Resumen rápido
    print("Resumen:")
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        print(f"  {row['id']}: trivial={row['d2_trivial']}, tactica={row['tactica_ganadora']}, "
              f"tiempo={row['tiempo_total_s']}s, correct={row['correct']}")


if __name__ == "__main__":
    main()
