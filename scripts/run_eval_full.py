"""Evaluación completa D1+D2 sobre el eval set.

Ejecuta el orquestador check_novelty() sobre cada teorema del eval set
(paper/eval_set.csv) y guarda resultados incrementales en CSV.

El pipeline es:
  1. D2 (trivialidad) — lake env lean, ~30-40s primer teorema, ~5-10s siguientes
  2. D1 C_F (Mathlib/Leandex) — ~1-2s por consulta
  3. D1 C_I (Semantic Scholar + LLM judge) — solo si no hay match en C_F
     (~5-10s SS + ~10-15s LLM por candidato)

Tiempo total estimado: ~30-60 minutos para el eval set completo.

Checkpointing: cada resultado se guarda en results/eval_full_TIMESTAMP.csv
inmediatamente después de computarse. Si el script se interrumpe, los
resultados ya guardados no se pierden.

Uso:
  python scripts/run_eval_full.py [--lean-project PATH] [--limit N] [--resume CSV]
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Asegurar que el repo raíz está en sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.novelty_v2.orchestrator import check_novelty
from src.novelty_v2.types import Verdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Timestamp para esta corrida
RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")


def load_eval_set(csv_path: Optional[Path] = None) -> List[Dict[str, str]]:
    """Carga el eval set desde paper/eval_set.csv.

    Columnas: id, par_id, enunciado_informal, categoria, ...
    Filtra entradas TBD (slots vacíos) y pares duplicados (solo type-level).
    """
    if csv_path is None:
        csv_path = _REPO_ROOT / "paper" / "eval_set.csv"

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = (row.get("id") or "").strip()
            # Skip TBD slots
            if not tid or tid.startswith("TBD"):
                continue
            # Skip sub-items of D3 pairs (T07b, T08b, T09b) — same type as T07a/T08a/T09a
            # D2 tests the type, not the proof
            if tid.endswith("b") and tid[:-1] + "a" in [r["id"] for r in rows]:
                continue
            row["theorem_id"] = tid  # alias
            rows.append(row)
    logger.info("Loaded %d theorems from %s", len(rows), csv_path.name)
    return rows


def load_lean_statements(md_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """Carga enunciados Lean desde paper/eval_set_lean_statements.md.

    El archivo tiene secciones:
      ## T01 — Title
      ```lean
      theorem T01 : <type> := sorry
      ```

    Y a veces un bloque de Imports: `import Mathlib...`

    Devuelve {theorem_id: {"lean_type": "Irrational (Real.sqrt 2)", "lean_imports": "..."}}.
    """
    if md_path is None:
        md_path = _REPO_ROOT / "paper" / "eval_set_lean_statements.md"

    statements = {}
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    # Parse sections
    import re
    # Match: ## TXX — ... followed by ```lean ... ```
    sections = re.split(r"\n##\s+", content)

    for section in sections:
        # Extract theorem ID
        tid_match = re.match(r"(T\d+)\b", section)
        if not tid_match:
            continue
        tid = tid_match.group(1)

        # Extract type from `theorem TXX : <type> := sorry` (may span multiple lines)
        type_match = re.search(
            rf"theorem\s+{tid}\s*:\s*(.+?)\s*:=\s*sorry",
            section,
            re.DOTALL,
        )
        if not type_match:
            logger.debug("%s: no theorem type found in section", tid)
            continue

        lean_type = type_match.group(1).strip()
        # Collapse multiline: replace newlines and multiple spaces with single space
        lean_type = re.sub(r"\s+", " ", lean_type)

        # Extract imports if present
        imports = "import Mathlib.Tactic"
        imp_match = re.search(
            r"(?:Imports?|imports?)[:\s]*\n?((?:import\s+[^\n]+\n?)+)",
            section,
            re.IGNORECASE,
        )
        if imp_match:
            imports = imp_match.group(1).strip().replace("\n", "\\n")

        statements[tid] = {
            "lean_statement": lean_type,
            "lean_imports": imports,
        }

    logger.info("Loaded %d Lean statements from %s", len(statements), md_path.name)
    return statements


def run_single(
    row: Dict[str, str],
    lean_stmt_info: Dict[str, str],
    lean_project_dir: Optional[Path],
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Ejecuta check_novelty() sobre un teorema del eval set.

    Args:
        row: fila del eval_set.csv
        lean_stmt_info: {"lean_statement": str, "lean_imports": str}
        lean_project_dir: ruta al lean_project/
        use_cache: usar cache de src/novelty/

    Returns:
        dict con resultado completo para guardar en CSV.
    """
    tid = row["theorem_id"]
    title = row.get("title") or row.get("enunciado_informal", "")[:80]
    stmt_latex = (
        row.get("statement_latex")
        or row.get("content_latex")
        or row.get("enunciado_informal", "")
    )

    lean_stmt = lean_stmt_info.get("lean_statement", "")
    lean_imports = lean_stmt_info.get("lean_imports", "import Mathlib")

    if not lean_stmt:
        logger.warning("%s: sin enunciado Lean — skipping", tid)
        return {"theorem_id": tid, "error": "no lean statement"}

    logger.info("%s: running check_novelty...", tid)
    t0 = time.monotonic()

    try:
        result = check_novelty(
            block={"title": title, "content_latex": stmt_latex},
            lean_statement=lean_stmt,
            lean_project_dir=lean_project_dir,
            lean_imports=lean_imports,
            use_cache=use_cache,
        )
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.error("%s: FAILED after %.1fs: %s", tid, elapsed, exc)
        return {
            "theorem_id": tid,
            "error": str(exc)[:200],
            "elapsed_s": round(elapsed, 1),
        }

    elapsed = time.monotonic() - t0
    logger.info(
        "%s: %s (stage=%d, D2=%s, C_F=%s, C_I=%s) in %.1fs",
        tid,
        result.veredicto.value,
        result.stage_detenido,
        "T" if result.d2.trivial else "F",
        "T" if result.d1.existe_en_C_F else "F",
        "T" if result.d1.existe_en_C_I else "F",
        elapsed,
    )

    return {
        "theorem_id": tid,
        "title": title[:120],
        "category": row.get("category", ""),
        "veredicto": result.veredicto.value,
        "stage_detenido": result.stage_detenido,
        "d2_trivial": result.d2.trivial,
        "d2_tactica": result.d2.tactica or "",
        "d2_tiempo_s": round(result.d2.tiempo_segundos, 1) if result.d2.tiempo_segundos else "",
        "d1_existe_en_C_F": result.d1.existe_en_C_F,
        "d1_match_C_F": (result.d1.match_C_F or {}).get("lean_name", ""),
        "d1_C_F_similarity": round((result.d1.match_C_F or {}).get("similarity", 0), 2),
        "d1_existe_en_C_I": result.d1.existe_en_C_I,
        "d1_match_C_I_title": (result.d1.match_C_I or {}).get("title", "")[:120],
        "d1_llm_judge_verdict": result.d1.llm_judge_verdict or "",
        "d1_traduccion_incierta": result.d1.traduccion_incierta,
        "d3_activa": result.d3.activa,
        "revision_humana": result.revision_humana,
        "razonamiento": result.razonamiento[:300],
        "elapsed_s": round(elapsed, 1),
        "error": "",
    }


def write_csv_row(
    csv_path: Path,
    fieldnames: List[str],
    row: Dict[str, Any],
    write_header: bool = False,
):
    """Escribe una fila al CSV (append, no sobreescribe)."""
    mode = "w" if write_header else "a"
    with open(csv_path, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    logger.debug("Wrote row for %s to %s", row.get("theorem_id"), csv_path.name)


def main():
    parser = argparse.ArgumentParser(description="Evaluación D1+D2 sobre eval set")
    parser.add_argument(
        "--lean-project",
        default=None,
        help="Ruta al lean_project/ con Mathlib compilado",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limitar a N teoremas (0 = todos)",
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Reanudar desde CSV previo (saltea IDs ya computados)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="No usar cache de src/novelty/",
    )
    parser.add_argument(
        "--prewarm",
        action="store_true",
        default=True,
        help="Ejecutar D2 de precalentamiento (default: True)",
    )
    parser.add_argument(
        "--no-prewarm",
        action="store_false",
        dest="prewarm",
        help="No ejecutar precalentamiento D2",
    )
    args = parser.parse_args()

    lean_project_dir = Path(args.lean_project) if args.lean_project else None
    use_cache = not args.no_cache

    # Cargar eval set y enunciados Lean
    rows = load_eval_set()
    lean_stmts = load_lean_statements()

    # Filtrar por resume
    done_ids = set()
    if args.resume:
        resume_path = Path(args.resume)
        if resume_path.exists():
            with open(resume_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    tid = row.get("theorem_id", "")
                    err = row.get("error", "")
                    if tid and not err:
                        done_ids.add(tid)
            logger.info("Resume: %d theorems already done", len(done_ids))

    # Limitar
    if args.limit > 0:
        rows = rows[: args.limit]

    # Prewarm D2 (carga Mathlib oleans en OS cache)
    if args.prewarm and lean_project_dir:
        logger.info("Prewarming D2 with simple statement...")
        from src.novelty_v2.dimensions.d2_triviality import check_triviality
        try:
            check_triviality(
                "True",
                lean_project_dir=lean_project_dir,
                lean_imports="import Mathlib.Tactic",
            )
            logger.info("Prewarm complete")
        except Exception as exc:
            logger.warning("Prewarm failed (non-fatal): %s", exc)

    # Preparar CSV de salida
    results_dir = _REPO_ROOT / "scripts" / "eval"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_csv = results_dir / f"eval_full_{RUN_TS}.csv"

    fieldnames = [
        "theorem_id", "title", "category",
        "veredicto", "stage_detenido",
        "d2_trivial", "d2_tactica", "d2_tiempo_s",
        "d1_existe_en_C_F", "d1_match_C_F", "d1_C_F_similarity",
        "d1_existe_en_C_I", "d1_match_C_I_title", "d1_llm_judge_verdict",
        "d1_traduccion_incierta",
        "d3_activa",
        "revision_humana", "razonamiento",
        "elapsed_s", "error",
    ]

    write_header = True
    total = len(rows)
    done = 0
    errores = 0

    for i, row in enumerate(rows):
        tid = row["theorem_id"]
        if tid in done_ids:
            logger.info("%s: already done (resume), skipping", tid)
            continue

        # Buscar enunciado Lean
        stmt_info = lean_stmts.get(tid, {})
        if not stmt_info:
            # Fallback: strip 'a'/'b' suffix for D3 pair items (T07a → T07)
            if len(tid) > 1 and tid[-1] in ('a', 'b'):
                base_tid = tid[:-1]
                stmt_info = lean_stmts.get(base_tid, {})
        if not stmt_info:
            # Intentar cargar de la fila CSV directamente
            lean_stmt = row.get("lean_statement", "")
            lean_imports = row.get("lean_imports", "import Mathlib")
            if lean_stmt:
                stmt_info = {
                    "lean_statement": lean_stmt.strip().strip("`"),
                    "lean_imports": lean_imports.strip().strip("`"),
                }
            else:
                logger.warning("%s: no Lean statement found, skipping", tid)
                continue

        logger.info("─" * 50)
        logger.info("[%d/%d] %s", i + 1, total, tid)

        result = run_single(row, stmt_info, lean_project_dir, use_cache)
        write_csv_row(output_csv, fieldnames, result, write_header=write_header)
        write_header = False

        if result.get("error"):
            errores += 1
        else:
            done += 1

    # Resumen
    logger.info("=" * 50)
    logger.info("Complete! %d theorems, %d errors", done, errores)
    logger.info("Results saved to: %s", output_csv)

    # Imprimir tabla resumen
    if output_csv.exists():
        print("\n" + "=" * 64)
        print("SUMMARY")
        print("=" * 64)
        verdicts = {}
        stages = {}
        with open(output_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                v = row.get("veredicto", "ERROR")
                s = row.get("stage_detenido", "?")
                verdicts[v] = verdicts.get(v, 0) + 1
                stages[s] = stages.get(s, 0) + 1

        print(f"\nVeredictos ({len(verdicts)} types):")
        for v, c in sorted(verdicts.items(), key=lambda x: -x[1]):
            print(f"  {v:40s} {c:3d}")

        print(f"\nStages:")
        for s, c in sorted(stages.items()):
            print(f"  Stage {s}: {c} theorems")

        print(f"\nFull results: {output_csv}")


if __name__ == "__main__":
    main()
