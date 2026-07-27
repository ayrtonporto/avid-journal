"""Orquestador de la métrica de novedad v2.

Ejecuta el árbol de decisión D2 → D1 → D3 siguiendo la spec
(paper/metric_spec.md §6) y devuelve NoveltyVerdict con los 8 veredictos.

Árbol completo:
  1. D2 (trivialidad):
     Si trivial → NO_NOVEDOSO_trivial, FIN.
  2. D1 C_F (Mathlib via Leandex):
     Si match → evaluar D3:
       - D3 no disponible → MATCH_ENCONTRADO_PENDIENTE_D3
       - D3 disponible ∧ jaccard > θ → NOVEDAD_DEMOSTRACION
       - D3 disponible ∧ jaccard ≤ θ → NO_NOVEDOSO_redundante
       - D3 disponible ∧ jaccard is None → INCONCLUSIVE (conjuntos vacíos)
  3. D1 C_I (Semantic Scholar + LLM judge), solo si C_F no dio match:
     - equivalent → CONOCIDO_LITERATURA
     - generalization / specialization → ZONA_GRIS
     - different / vacío → NOVEDAD_ENUNCIADO

D3 (distancia de premisas) integrado vía compute_d3 desde 2026-07-03.
Cuando d3_premises_a y d3_premises_b se proveen, D3 corre en vivo.
Cuando no, se emite MATCH_ENCONTRADO_PENDIENTE_D3 (análisis offline).

Uso:
  from src.novelty.orchestrator import check_novelty

  result = check_novelty(
      block={"title": "...", "content_latex": "..."},
      lean_statement="Irrational (Real.sqrt 2)",
      lean_imports="import Mathlib.Tactic",
  )
  print(result.veredicto.value)  # e.g. NOVEDAD_ENUNCIADO
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.novelty.dimensions.d1_existence import (
    _check_cf,
    _run_ci_stage_a,
    _run_ci_stage_b,
    CI_SIMILARITY_THRESHOLD_A,
)
from src.novelty.dimensions.d2_triviality import check_triviality, _run_tactic, LEAN_STARTUP_OVERHEAD_S
from src.novelty.dimensions.d3_premises import compute_d3
from src.novelty.types import (
    D1Result,
    D2Result,
    D3Result,
    NoveltyVerdict,
    Verdict,
)

logger = logging.getLogger(__name__)


def check_novelty(
    block: Dict[str, Any],
    lean_statement: str,
    lean_project_dir: Optional[str | Path] = None,
    lean_imports: str = "import Mathlib",
    use_cache: bool = True,
    ci_top_k: int = 3,
    ci_threshold: float = CI_SIMILARITY_THRESHOLD_A,
    d3_star_pairs: Optional[Dict[str, str]] = None,
    d3_premises_a: Optional[List[dict]] = None,
    d3_premises_b: Optional[List[dict]] = None,
    d3_statement_lines_a: Optional[Tuple[int, int]] = None,
    d3_statement_lines_b: Optional[Tuple[int, int]] = None,
    on_progress: Any = None,
) -> NoveltyVerdict:
    """Evalúa la novedad de un teorema usando el árbol D2 → D1 → D3.

    Args:
        block: dict con "title" y "content_latex" (enunciado informal).
        lean_statement: enunciado Lean 4 del teorema (para D2).
        lean_project_dir: ruta al lean_project/ con Mathlib compilado.
        lean_imports: imports para el archivo Lean de D2.
        use_cache: compartido con los módulos de src/novelty/.
        ci_top_k: candidatos Semantic Scholar que pasan a llm_judge.
        ci_threshold: umbral de similitud MiniLM para C_I etapa A.
        d3_star_pairs: pares de teoremas para evaluación D3 manual.
            Formato: {"lean_name_nuevo": "lean_name_existente", ...}
            Si se provee, D3 se ejecuta sobre estos pares en vez de
            sobre el match de C_F. Útil para evaluación offline.
        d3_premises_a: lista de dicts PremiseTrace para la prueba candidata.
            Si se provee junto con d3_premises_b, D3 corre en vivo.
        d3_premises_b: lista de dicts PremiseTrace para la prueba existente.
        d3_statement_lines_a: (start, end) del enunciado de A (para Filtro 2).
        d3_statement_lines_b: (start, end) del enunciado de B (para Filtro 2).

    Returns:
        NoveltyVerdict con veredicto, razonamiento y resultados de las 3 dimensiones.
    """
    d2 = D2Result()
    d1 = D1Result()
    d3 = D3Result()

    # ── Paso 1: D2 (trivialidad) ────────────────────────────────────────────
    label = block.get("title") or block.get("label") or "?"
    if on_progress: on_progress("d2", f"D2: checking triviality for '{label}'...", -1)
    d2 = check_triviality(
        lean_statement,
        lean_project_dir=lean_project_dir,
        lean_imports=lean_imports,
    )

    if d2.trivial:
        return NoveltyVerdict(
            veredicto=Verdict.NO_NOVEDOSO_trivial,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=False,
            razonamiento=(
                f"D2: tactic '{d2.tactica}' closed the statement "
                f"in {d2.tiempo_segundos:.1f}s. No mathematical idea required."
            ),
            stage_detenido=2,
        )

    # ── Paso 2: D1 C_F (Mathlib/Leandex) ────────────────────────────────────
    if on_progress: on_progress("d1", f"D1: searching Mathlib for '{label}'...", -1)
    d1 = _check_cf(block, use_cache)

    if d1.existe_en_C_F:
        # ── Paso 2a: D3 (distancia de premisas) ──────────────────────────
        lean_name_existente = (d1.match_C_F or {}).get("lean_name", "?")
        if on_progress: on_progress("d3", f"D3: computing proof distance vs '{lean_name_existente}'...", -1)
        d3 = _run_d3_if_possible(
            lean_statement=lean_statement,
            lean_name_existente=lean_name_existente,
            lean_project_dir=lean_project_dir,
            d3_star_pairs=d3_star_pairs,
            d3_premises_a=d3_premises_a,
            d3_premises_b=d3_premises_b,
            d3_statement_lines_a=d3_statement_lines_a,
            d3_statement_lines_b=d3_statement_lines_b,
        )

        # Case: D3 ran but sets were empty → INCONCLUSIVE
        if d3.activa and d3.jaccard is None:
            return NoveltyVerdict(
                veredicto=Verdict.INCONCLUSIVE,
                d1=d1,
                d2=d2,
                d3=d3,
                revision_humana=True,
                razonamiento=(
                    f"D1 C_F: found in Mathlib — '{lean_name_existente}'. "
                    f"D3: could not compute proof distance — requires human review."
                ),
                stage_detenido=3,
            )

        if d3.pruebas_distantes is True:
            return NoveltyVerdict(
                veredicto=Verdict.NOVEDAD_DEMOSTRACION,
                d1=d1,
                d2=d2,
                d3=d3,
                revision_humana=True,
                razonamiento=(
                    f"D1 C_F: found in Mathlib — '{lean_name_existente}'. "
                    f"D3: possible proof novelty — requires human review."
                ),
                stage_detenido=3,
            )

        if d3.pruebas_distantes is False:
            return NoveltyVerdict(
                veredicto=Verdict.NO_NOVEDOSO_redundante,
                d1=d1,
                d2=d2,
                d3=d3,
                revision_humana=True,
                razonamiento=(
                    f"D1 C_F: found in Mathlib — '{lean_name_existente}'. "
                    f"D3: proof appears similar to known result — requires human review."
                ),
                stage_detenido=3,
            )

        # D3 no disponible → veredicto provisional
        sim = (d1.match_C_F or {}).get("similarity") or 0.0
        return NoveltyVerdict(
            veredicto=Verdict.MATCH_ENCONTRADO_PENDIENTE_D3,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=True,
            razonamiento=(
                f"D1 C_F: found in Mathlib — '{lean_name_existente}' "
                f"(sim={sim:.2f}). Proof novelty pending (D3 offline). "
                f"Requires human review."
            ),
            stage_detenido=1,
        )

    # ── Fallback C_F: exact? (si Leandex no encontró match) ─────────────
    # exact? busca en el entorno Lean cargado. Si encuentra un teorema
    # existente, lo tratamos como match en C_F. Esto captura teoremas que
    # Leandex podría no encontrar por diferencia de idioma o formato.
    if lean_project_dir and lean_statement:
        try:
            success, elapsed, output = _run_tactic(
                lean_statement,
                "exact?",
                lean_project_dir,
                budget_seconds=15,
                lean_imports=lean_imports,
            )
            if success and output:
                # Extraer el nombre del lema que exact? sugirió
                import re
                exact_match = re.search(r"Try this:\s*([^\s]+)", output)
                if not exact_match:
                    exact_match = re.search(r"exact\s+([^\s]+)", output)
                lean_name = exact_match.group(1) if exact_match else "exact?_match"
                d1.existe_en_C_F = True
                d1.match_C_F = {
                    "lean_name": lean_name,
                    "statement": f"exact? closed in {elapsed:.1f}s",
                    "similarity": 0.95,  # exact match, slightly below 1.0 to distinguish from Leandex
                    "url": "",
                }
                # Emitir MATCH_ENCONTRADO_PENDIENTE_D3 igual que si Leandex lo hubiera encontrado
                return NoveltyVerdict(
                    veredicto=Verdict.MATCH_ENCONTRADO_PENDIENTE_D3,
                    d1=d1,
                    d2=d2,
                    d3=d3,
                    revision_humana=True,
                    razonamiento=(
                        f"D1 C_F (exact?): '{lean_name}' closed the statement "
                        f"in {elapsed:.1f}s. Found in Mathlib (via exact?). "
                        f"Proof novelty pending — requires human review."
                    ),
                    stage_detenido=1,
                )
        except Exception as exc:
            logger.debug("exact? fallback failed: %s", exc)

    # ── Paso 3: D1 C_I (solo si C_F no dio match) ───────────────────────────
    if on_progress: on_progress("d1", f"D1: searching arXiv/Semantic Scholar for '{label}'...", -1)
    ci_candidates = _run_ci_stage_a(block, use_cache, ci_top_k, ci_threshold)
    if ci_candidates:
        ci_result = _run_ci_stage_b(block, ci_candidates, use_cache)
        d1.existe_en_C_I = ci_result.existe_en_C_I
        d1.match_C_I = ci_result.match_C_I
        d1.llm_judge_verdict = ci_result.llm_judge_verdict
        if ci_result.traduccion_incierta:
            d1.traduccion_incierta = True

    llm_v = d1.llm_judge_verdict or "different"

    if llm_v in ("generalization", "specialization"):
        return NoveltyVerdict(
            veredicto=Verdict.ZONA_GRIS,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=True,
            razonamiento=(
                f"D1 C_I: LLM judge returned '{llm_v}' for candidate "
                f"'{(d1.match_C_I or {}).get('title', '?')}'. "
                f"Related but not identical — requires human review."
            ),
            stage_detenido=1,
        )

    if d1.existe_en_C_I:
        return NoveltyVerdict(
            veredicto=Verdict.CONOCIDO_LITERATURA,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=d1.traduccion_incierta,
            razonamiento=(
                f"D1 C_I: found in informal literature — "
                f"'{(d1.match_C_I or {}).get('title', '?')}'. "
                f"No match in Mathlib. Formalization may be an engineering "
                f"contribution."
            ),
            stage_detenido=1,
        )

    # ── No match in C_F or C_I → genuinely new statement ──────────────────
    return NoveltyVerdict(
        veredicto=Verdict.NOVEDAD_ENUNCIADO,
        d1=d1,
        d2=d2,
        d3=d3,
        revision_humana=d1.traduccion_incierta,
        razonamiento=(
            "D1: no match in C_F (Mathlib) or C_I (arXiv/Semantic Scholar). "
            "Genuinely new statement."
            + (" [uncertain translation — review]" if d1.traduccion_incierta else "")
        ),
        stage_detenido=1,
    )


# ---------------------------------------------------------------------------
# D3 — Distancia de premisas (stub + integración futura)
# ---------------------------------------------------------------------------

def _run_d3_if_possible(
    lean_statement: str,
    lean_name_existente: str,
    lean_project_dir: Optional[str | Path] = None,
    d3_star_pairs: Optional[Dict[str, str]] = None,
    d3_premises_a: Optional[List[dict]] = None,
    d3_premises_b: Optional[List[dict]] = None,
    d3_statement_lines_a: Optional[Tuple[int, int]] = None,
    d3_statement_lines_b: Optional[Tuple[int, int]] = None,
) -> D3Result:
    """Ejecuta D3 si hay premisas disponibles. Si no, devuelve activa=False.

    Cuando d3_premises_a y d3_premises_b se proveen, llama a compute_d3.
    Si solo d3_premises_a está presente, intenta auto-localizar el lado B
    (Mathlib) usando locate_mathlib_source con lean_name_existente.
    """
    # ── Both sides available → run D3 ──────────────────────────────────
    if d3_premises_a is not None and d3_premises_b is not None:
        logger.info(
            "D3: ejecutando compute_d3 con %d y %d premisas",
            len(d3_premises_a), len(d3_premises_b),
        )
        return compute_d3(
            premises_a=d3_premises_a,
            premises_b=d3_premises_b,
            statement_lines_a=d3_statement_lines_a,
            statement_lines_b=d3_statement_lines_b,
        )

    # ── Side A only → try auto-locate Side B ──────────────────────────
    if d3_premises_a is not None and lean_project_dir is not None:
        logger.info(
            "D3: auto-locating Side B for '%s'", lean_name_existente,
        )
        try:
            from src.novelty.premise_autolocation import (
                locate_mathlib_source,
            )
            from src.novelty.premise_extraction import (
                extract_premises_for_theorem,
            )

            proj = Path(lean_project_dir)
            mathlib_root = proj / ".lake" / "packages" / "mathlib"

            loc_b = locate_mathlib_source(lean_name_existente, mathlib_root)
            if loc_b is not None:
                file_b, start_b, end_b = loc_b
                prems_b = extract_premises_for_theorem(
                    file_b, proj,
                    theorem_line_start=start_b,
                    theorem_line_end=end_b,
                )
                if prems_b is not None:
                    logger.info(
                        "D3: Side B auto-located: %s → %d premises",
                        lean_name_existente, len(prems_b),
                    )
                    return compute_d3(
                        premises_a=d3_premises_a,
                        premises_b=prems_b,
                        statement_lines_a=d3_statement_lines_a,
                        statement_lines_b=(start_b, start_b),
                    )
                else:
                    logger.warning(
                        "D3: Side B located but extraction failed for '%s'",
                        lean_name_existente,
                    )
            else:
                logger.info(
                    "D3: Side B not found in Mathlib for '%s'",
                    lean_name_existente,
                )
        except Exception as exc:
            logger.warning(
                "D3: Side B auto-location error for '%s': %s",
                lean_name_existente, exc,
            )

    # Fallback: sin premisas → D3 no disponible
    logger.info(
        "D3: sin premisas para '%s'. D3 requiere análisis offline.",
        lean_name_existente,
    )
    return D3Result(activa=False)


# ---------------------------------------------------------------------------
# Demo mínima
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

    def _demo(label: str, block: dict, lean_stmt: str, imports: str = "import Mathlib.Tactic"):
        print(f"\n{'='*64}")
        print(f"Demo: {label}")
        print("=" * 64)
        v = check_novelty(
            block=block,
            lean_statement=lean_stmt,
            lean_imports=imports,
        )
        print(f"Veredicto:       {v.veredicto.value}")
        print(f"Stage detenido:  {v.stage_detenido}")
        print(f"Revisión humana: {v.revision_humana}")
        print(f"Razonamiento:    {v.razonamiento}")
        print(f"D2 trivial:      {v.d2.trivial}, táctica: {v.d2.tactica}")
        print(f"D1 C_F match:    {v.d1.existe_en_C_F} | C_I match: {v.d1.existe_en_C_I}")
        if v.d1.match_C_F:
            m = v.d1.match_C_F
            print(f"  C_F: {m.get('lean_name')} (sim={m.get('similarity', 0):.2f})")
        if v.d1.match_C_I:
            m = v.d1.match_C_I
            print(f"  C_I: {m.get('title', '?')} (sim={m.get('similarity', 0):.2f})")
        return v

    # Caso 1: trivial
    _demo(
        "T15 — trivial: (2:Nat)+2=4",
        block={"title": "2 + 2 = 4", "content_latex": "2 + 2 = 4"},
        lean_stmt="(2 : Nat) + 2 = 4",
        imports="import Mathlib.Tactic",
    )

    # Caso 2: clásico en Mathlib
    _IMP_REAL = (
        "import Mathlib.Tactic\n"
        "import Mathlib.Analysis.SpecialFunctions.Pow.Real\n"
        "import Mathlib.Data.Real.Irrational"
    )
    _demo(
        "T01 — en Mathlib: Irrational (sqrt 2)",
        block={
            "title": "Irrationality of sqrt(2)",
            "content_latex": r"$\sqrt{2}$ is irrational",
        },
        lean_stmt="Irrational (Real.sqrt 2)",
        imports=_IMP_REAL,
    )

    # Caso 3: potencial novedad
    _IMP_PARITY = (
        "import Mathlib.Tactic\n"
        "import Mathlib.Data.Int.Parity\n"
        "import Mathlib.Algebra.BigOperators.Group.Finset"
    )
    _demo(
        "T26 — suma de n pares es par",
        block={
            "title": "Sum of n even integers is even",
            "content_latex": r"If $f(i)$ is even for all $i$, then $\sum_{i} f(i)$ is even",
        },
        lean_stmt="∀ (n : ℕ) (f : Fin n → ℤ), (∀ i, Even (f i)) → Even (∑ i, f i)",
        imports=_IMP_PARITY,
    )
