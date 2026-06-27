"""D1 — No-existencia previa.

Verifica si el teorema candidato ya existe en:
  C_F (corpus formal):   Mathlib, vía Leandex (búsqueda semántica sobre declaraciones Lean).
  C_I (corpus informal): arXiv/Semantic Scholar, con filtro grueso MiniLM + juez LLM fino.

Spec: paper/metric_spec.md §4.1
Decisiones de diseño: paper/decisions.md

Interface pública:
  check_d1(block, use_cache=True, ci_top_k=3, ci_threshold=0.40) → D1Result
  check_novelty_verdict_simple(block, lean_statement, lean_project_dir=None) → NoveltyVerdict

NOTA sobre el bloque de entrada:
  block = {"title": str, "content_latex": str}
  donde "content_latex" es el enunciado informal (texto libre / LaTeX).
  La función acepta opcionalmente "lean_statement" como campo extra del dict
  para futuros usos, pero D1 opera sobre el texto informal.

Relación con src/novelty/ (congelado):
  - mathlib_checker.check_in_mathlib → C_F
  - arxiv_search.search_semantic_scholar → C_I etapa A (filtro)
  - block_comparator._cosine_similarity_text → C_I etapa A (similitud)
  - llm_judge.judge_theorem_pair → C_I etapa B (verificación fina)

NOTA TÉCNICA sobre check_novelty_verdict_simple:
  Esta función fue un orchestrador mínimo D2→D1 creado como adelanto del Día 6.
  El orchestrator canónico ahora está en src/novelty_v2/orchestrator.py
  (función check_novelty), que incluye el paso D3 en el árbol de decisión.
  Esta función se mantiene por compatibilidad hacia atrás pero se recomienda
  migrar a check_novelty().
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.novelty.arxiv_search import PaperCandidate, search_semantic_scholar
from src.novelty.llm_judge import judge_theorem_pair
from src.novelty.mathlib_checker import check_in_mathlib
from src.novelty_v2.dimensions.d2_triviality import check_triviality
from src.novelty_v2.types import D1Result, D2Result, D3Result, NoveltyVerdict, Verdict

logger = logging.getLogger(__name__)

# Umbral de similitud para etapa A (filtro grueso MiniLM).
# Más bajo que el umbral de mathlib (0.85) porque arXiv abstracts son más ruidosos
# que declaraciones Lean. Los candidatos que pasan van a etapa B (llm_judge).
CI_SIMILARITY_THRESHOLD_A: float = 0.40


def _block_text(block: Dict[str, Any]) -> str:
    """Texto corto para embeddings MiniLM."""
    title = (block.get("title") or "").strip()
    content = (block.get("content_latex") or "").strip()
    parts = [p for p in (title, content) if p]
    return " ".join(parts)


def _cosine_sim(a: str, b: str) -> float:
    """Similitud coseno entre dos textos vía MiniLM (import lazy)."""
    if not a or not b:
        return 0.0
    try:
        from src.novelty.block_comparator import get_model
        model = get_model()
        embeddings = model.encode([a, b], convert_to_numpy=True, normalize_embeddings=True)
        return float(embeddings[0] @ embeddings[1])
    except Exception as exc:
        logger.warning("MiniLM similarity failed: %s", exc)
        return 0.0


# ---------------------------------------------------------------------------
# C_F — Corpus formal (Mathlib vía Leandex)
# ---------------------------------------------------------------------------

def _check_cf(block: Dict[str, Any], use_cache: bool) -> D1Result:
    """Busca el bloque en Mathlib vía Leandex. Devuelve D1Result parcial (solo C_F)."""
    result = D1Result()
    try:
        mathlib_res = check_in_mathlib(block, use_cache=use_cache)
    except Exception as exc:
        logger.warning("check_in_mathlib failed: %s", exc)
        return result

    result.existe_en_C_F = mathlib_res.found
    if mathlib_res.matches:
        best = mathlib_res.matches[0]
        result.match_C_F = {
            "lean_name": best.lean_name,
            "statement": best.statement,
            "similarity": best.similarity,
            "url": best.url,
        }
    return result


# ---------------------------------------------------------------------------
# C_I — Corpus informal (arXiv/Semantic Scholar + LLM judge)
# ---------------------------------------------------------------------------

def _run_ci_stage_a(
    block: Dict[str, Any],
    use_cache: bool,
    top_k: int,
    similarity_threshold: float,
) -> List[tuple[PaperCandidate, float]]:
    """Etapa A: búsqueda Semantic Scholar + filtro de similitud MiniLM.

    Devuelve lista de (candidato, sim) ordenada por similitud desc,
    limitada a top_k candidatos que superan similarity_threshold.
    """
    query = _block_text(block)
    if not query:
        return []

    try:
        ss_candidates = search_semantic_scholar(query, top_k=20, use_cache=use_cache)
    except Exception as exc:
        logger.warning("Semantic Scholar search failed: %s", exc)
        return []

    block_text = _block_text(block)
    scored: List[tuple[PaperCandidate, float]] = []
    for cand in ss_candidates:
        cand_text = f"{cand.title} {cand.abstract}"
        sim = _cosine_sim(block_text, cand_text)
        if sim >= similarity_threshold:
            scored.append((cand, sim))

    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]


def _run_ci_stage_b(
    block_new: Dict[str, Any],
    candidates: List[tuple[PaperCandidate, float]],
    use_cache: bool,
) -> D1Result:
    """Etapa B: verificación fina con llm_judge sobre candidatos que pasaron etapa A.

    Mapeo de veredictos del juez (decisions.md 2026-05-31):
      "equivalent"     → existe_en_C_I = True
      "generalization" → llm_judge_verdict = "generalization", revision_humana = True (ZONA_GRIS)
      "specialization" → llm_judge_verdict = "specialization", revision_humana = True (ZONA_GRIS)
      "different"      → no match, continuar con siguiente candidato

    Se detiene en el primer match (equivalent) o primer zona gris (gen/spec).
    """
    result = D1Result()
    for cand, sim in candidates:
        block_candidate = {
            "title": cand.title,
            "content_latex": cand.abstract,
        }
        try:
            judge = judge_theorem_pair(block_new, block_candidate, use_cache=use_cache)
        except Exception as exc:
            logger.warning("llm_judge failed for candidate '%s': %s", cand.title, exc)
            result.traduccion_incierta = True
            continue

        result.llm_judge_verdict = judge.verdict

        if judge.verdict == "equivalent":
            result.existe_en_C_I = True
            result.match_C_I = {
                "paper_id": cand.paper_id,
                "title": cand.title,
                "block_title": cand.title,
                "similarity": sim,
                "arxiv_id": cand.arxiv_id,
                "judge_confidence": judge.confidence,
                "judge_reasoning": judge.reasoning,
            }
            return result

        if judge.verdict in ("generalization", "specialization"):
            # Zona gris: tipos relacionados pero no iguales → no forzar etiqueta
            result.match_C_I = {
                "paper_id": cand.paper_id,
                "title": cand.title,
                "block_title": cand.title,
                "similarity": sim,
                "arxiv_id": cand.arxiv_id,
                "judge_confidence": judge.confidence,
                "judge_reasoning": judge.reasoning,
            }
            return result

        # "different" → continuar con el siguiente candidato

    return result


# ---------------------------------------------------------------------------
# API pública: check_d1
# ---------------------------------------------------------------------------

def check_d1(
    block: Dict[str, Any],
    use_cache: bool = True,
    ci_top_k: int = 3,
    ci_threshold: float = CI_SIMILARITY_THRESHOLD_A,
) -> D1Result:
    """Verifica si el bloque ya existe en C_F (Mathlib) y en C_I (arXiv/SS).

    Sigue el orden de la spec (§6):
      1. C_F vía Leandex (barato y rápido).
      2. C_I etapa A: Semantic Scholar + similitud MiniLM.
      3. C_I etapa B: llm_judge sobre top-k candidatos de etapa A.

    Args:
        block: dict con "title" y "content_latex" (descripción informal del teorema).
        use_cache: si usar el cache compartido de src/novelty/_cache.py.
        ci_top_k: máximo de candidatos de etapa A a pasar a etapa B (llm_judge).
        ci_threshold: umbral de similitud MiniLM para etapa A (default 0.40).

    Returns:
        D1Result con existe_en_C_F, existe_en_C_I, match_C_F, match_C_I,
        llm_judge_verdict, traduccion_incierta.
    """
    # ── C_F ───────────────────────────────────────────────────────────────────
    result = _check_cf(block, use_cache)

    # ── C_I ───────────────────────────────────────────────────────────────────
    ci_candidates = _run_ci_stage_a(block, use_cache, ci_top_k, ci_threshold)
    if ci_candidates:
        ci_result = _run_ci_stage_b(block, ci_candidates, use_cache)
        result.existe_en_C_I = ci_result.existe_en_C_I
        result.match_C_I = ci_result.match_C_I
        result.llm_judge_verdict = ci_result.llm_judge_verdict
        if ci_result.traduccion_incierta:
            result.traduccion_incierta = True

    return result


# ---------------------------------------------------------------------------
# Árbol de decisión D2→D1 mínimo (adelanto del orchestrator.py del Día 8)
# ---------------------------------------------------------------------------

def check_novelty_verdict_simple(
    block: Dict[str, Any],
    lean_statement: str,
    lean_project_dir: Optional[str | Path] = None,
    lean_imports: str = "import Mathlib",
    use_cache: bool = True,
    ci_top_k: int = 3,
    ci_threshold: float = CI_SIMILARITY_THRESHOLD_A,
) -> NoveltyVerdict:
    """Orquestación mínima D2 → D1 → NoveltyVerdict.

    Implementa el árbol de decisión de la spec (§6) según DECISIÓN A
    (2026-06-09): C_F prevalece sobre C_I — si hay match en Mathlib, se
    emite MATCH_ENCONTRADO_PENDIENTE_D3 sin correr C_I.

    D3 (distancia de premisas) queda pendiente — se completa en
    orchestrator.py (Día 8) cuando D3 se implementa.

    Árbol:
      1. D2 (trivialidad):
         Si trivial → NO_NOVEDOSO_trivial, fin.
      2. D1 C_F (Leandex / Mathlib):
         Si match → MATCH_ENCONTRADO_PENDIENTE_D3, fin. (NO corre C_I)
      3. D1 C_I (Semantic Scholar + llm_judge), solo si C_F no dio match:
         - equivalent → CONOCIDO_LITERATURA
         - generalization / specialization → ZONA_GRIS
         - different / vacío → NOVEDAD_ENUNCIADO

    Args:
        block: dict con "title" y "content_latex".
        lean_statement: enunciado Lean 4 del teorema (para D2).
        lean_project_dir: ruta al lean_project/ con Mathlib compilado.
        lean_imports: imports para el archivo Lean de D2.
        use_cache: compartido con los módulos de src/novelty/.
        ci_top_k: candidatos Semantic Scholar que pasan a llm_judge.
        ci_threshold: umbral de similitud MiniLM para C_I etapa A.
    """
    d2 = D2Result()
    d1 = D1Result()
    d3 = D3Result()

    # ── Paso 1: D2 ────────────────────────────────────────────────────────────
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
                f"D2: táctica '{d2.tactica}' cerró el enunciado "
                f"en {d2.tiempo_segundos:.1f}s. No requiere idea matemática."
            ),
            stage_detenido=2,
        )

    # ── Paso 2: D1 C_F ────────────────────────────────────────────────────────
    d1 = _check_cf(block, use_cache)

    if d1.existe_en_C_F:
        # DECISIÓN A: C_F match → MATCH_ENCONTRADO_PENDIENTE_D3. NO corre C_I.
        lean_name = (d1.match_C_F or {}).get("lean_name", "?")
        sim = (d1.match_C_F or {}).get("similarity", 0.0)
        return NoveltyVerdict(
            veredicto=Verdict.MATCH_ENCONTRADO_PENDIENTE_D3,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=False,
            razonamiento=(
                f"D1 C_F: match en Mathlib — '{lean_name}' (sim={sim:.2f}). "
                f"Enunciado conocido. Novedad de prueba pendiente de D3 "
                f"(análisis offline con LeanDojo)."
            ),
            stage_detenido=1,
        )

    # ── Paso 3: D1 C_I (solo si C_F no dio match) ─────────────────────────────
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
                f"D1 C_I: juez LLM marcó '{llm_v}' con candidato "
                f"'{(d1.match_C_I or {}).get('title', '?')}'. "
                f"Tipos relacionados pero no iguales — revisión humana."
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
                f"D1 C_I: match en literatura informal — "
                f"'{(d1.match_C_I or {}).get('title', '?')}'. "
                f"Sin match en Mathlib. Formalización puede ser aporte de ingeniería."
            ),
            stage_detenido=1,
        )

    # Sin match en C_F ni C_I → enunciado genuinamente nuevo
    return NoveltyVerdict(
        veredicto=Verdict.NOVEDAD_ENUNCIADO,
        d1=d1,
        d2=d2,
        d3=d3,
        revision_humana=d1.traduccion_incierta,
        razonamiento=(
            "D1: sin match en C_F (Mathlib) ni en C_I (arXiv/SS). "
            "Enunciado genuinamente nuevo."
            + (" [traducción incierta — revisar]" if d1.traduccion_incierta else "")
        ),
        stage_detenido=1,
    )


# ---------------------------------------------------------------------------
# Demo: tres NoveltyVerdicts end-to-end (adelanto Día 6)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json
    import sys
    from pathlib import Path

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

    parser = argparse.ArgumentParser(description="Demo D1+D2 end-to-end")
    parser.add_argument(
        "--lean-project",
        default=None,
        help="Ruta al lean_project/ con Mathlib compilado",
    )
    args = parser.parse_args()
    lean_project = Path(args.lean_project) if args.lean_project else None

    def _demo(label: str, block: dict, lean_stmt: str, imports: str = "import Mathlib.Tactic"):
        print(f"\n{'='*64}")
        print(f"Demo: {label}")
        print("="*64)
        v = check_novelty_verdict_simple(
            block=block,
            lean_statement=lean_stmt,
            lean_project_dir=lean_project,
            lean_imports=imports,
        )
        print(f"Veredicto:       {v.veredicto.value}")
        print(f"Stage detenido:  {v.stage_detenido}")
        print(f"Razonamiento:    {v.razonamiento}")
        print(f"D2 trivial:      {v.d2.trivial}, tactica: {v.d2.tactica}")
        print(f"D1 C_F match:    {v.d1.existe_en_C_F} | C_I match: {v.d1.existe_en_C_I}")
        if v.d1.match_C_F:
            print(f"  C_F: {v.d1.match_C_F.get('lean_name')} (sim={v.d1.match_C_F.get('similarity', 0):.2f})")
        return v

    # ── Caso 1: trivial — T15 "2+2=4" ─────────────────────────────────────────
    # Esperado: NO_NOVEDOSO_trivial (D2 cierra; D1 no corre)
    v1 = _demo(
        "T15 — trivial: (2:Nat)+2=4",
        block={"title": "2 + 2 = 4", "content_latex": "2 + 2 = 4"},
        lean_stmt="(2 : Nat) + 2 = 4",
        imports="import Mathlib.Tactic",
    )

    # ── Caso 2: clásico en Mathlib — T01 raíz de 2 irracional ─────────────────
    # Esperado: MATCH_ENCONTRADO_PENDIENTE_D3 (Leandex devuelve irrational_sqrt_two)
    _IMP_REAL = (
        "import Mathlib.Tactic\n"
        "import Mathlib.Analysis.SpecialFunctions.Pow.Real\n"
        "import Mathlib.Data.Real.Irrational"
    )
    v2 = _demo(
        "T01 — clásico en Mathlib: Irrational (sqrt 2)",
        block={
            "title": "Irrationality of sqrt(2)",
            "content_latex": r"$\sqrt{2}$ is irrational",
        },
        lean_stmt="Irrational (Real.sqrt 2)",
        imports=_IMP_REAL,
    )

    # ── Caso 3: potencial novedad — T26 suma n enteros pares es par ─────────────
    # Esperado: NOVEDAD_ENUNCIADO o MATCH_ENCONTRADO_PENDIENTE_D3 según Leandex
    # No requiere ANTHROPIC_API_KEY (C_I no corre si C_F da match; si no da match,
    # C_I falla silenciosamente sin clave y el veredicto es NOVEDAD_ENUNCIADO).
    _IMP_PARITY_FINSET = (
        "import Mathlib.Tactic\n"
        "import Mathlib.Data.Int.Parity\n"
        "import Mathlib.Algebra.BigOperators.Group.Finset"
    )
    v3 = _demo(
        "T26 — generalización: suma de n enteros pares es par",
        block={
            "title": "Sum of n even integers is even",
            "content_latex": r"If $f(i)$ is even for all $i$, then $\sum_{i} f(i)$ is even",
        },
        lean_stmt=(
            "∀ (n : ℕ) (f : Fin n → ℤ), (∀ i, Even (f i)) → Even (∑ i, f i)"
        ),
        imports=_IMP_PARITY_FINSET,
    )

    print("\n" + "="*64)
    print("Resumen:")
    for label, v in [("T15 (trivial)", v1), ("T01 (en Mathlib)", v2), ("T26 (potencial novedad)", v3)]:
        print(f"  {label:35s} → {v.veredicto.value}")
