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
  Esta función es un orchestrador mínimo de D2→D1 creado como adelanto del Día 6.
  Será refactorizado y movido a novelty_v2/orchestrator.py en el Día 8 junto
  con el árbol de decisión completo (incluyendo D3). No eliminar el código aquí
  hasta que orchestrator.py esté completo.
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
) -> NoveltyVerdict:
    """Orquestación mínima D2 → D1 → NoveltyVerdict.

    Implementa los pasos 1-3 del árbol de decisión de la spec (§6).
    D3 (distancia de premisas) queda como None — se completará en orchestrator.py (Día 8).

    Árbol implementado:
      1. D2 (trivialidad):
         Si trivial → NO_NOVEDOSO_trivial, fin.
      2. D1 sobre C_F (Leandex):
         Si match → anotar existe_en_C_F, continuar a D3 (pendiente).
      3. D1 sobre C_I (Semantic Scholar + llm_judge):
         - Sin match en C_F ni C_I → NOVEDAD_ENUNCIADO
         - Match en C_I, no en C_F → CONOCIDO_LITERATURA
         - Generalization/Specialization → ZONA_GRIS
         - Match en C_F (y D3 aún no implementado) → NO_NOVEDOSO_redundante provisional

    Args:
        block: dict con "title" y "content_latex".
        lean_statement: enunciado Lean 4 del teorema (para D2).
        lean_project_dir: ruta al lean_project/ con Mathlib compilado.
        lean_imports: imports para el archivo Lean de D2.
        use_cache: compartido con los módulos de src/novelty/.
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

    # ── Pasos 2-3: D1 ─────────────────────────────────────────────────────────
    d1 = check_d1(block, use_cache=use_cache)

    # Determinar veredicto según árbol de la spec §6
    llm_v = d1.llm_judge_verdict or "different"

    if llm_v in ("generalization", "specialization"):
        return NoveltyVerdict(
            veredicto=Verdict.ZONA_GRIS,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=True,
            razonamiento=(
                f"D1: juez LLM marcó '{llm_v}' con candidato "
                f"'{(d1.match_C_I or {}).get('title', '?')}'. "
                f"Tipos relacionados pero no iguales — revisión humana."
            ),
            stage_detenido=1,
        )

    if not d1.existe_en_C_F and not d1.existe_en_C_I:
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

    if d1.existe_en_C_I and not d1.existe_en_C_F:
        return NoveltyVerdict(
            veredicto=Verdict.CONOCIDO_LITERATURA,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=d1.traduccion_incierta,
            razonamiento=(
                f"D1: sin match en C_F (Mathlib) pero match en C_I: "
                f"'{(d1.match_C_I or {}).get('title', '?')}'. "
                f"Formalización puede ser aporte de ingeniería, no contribución matemática nueva."
            ),
            stage_detenido=1,
        )

    if d1.existe_en_C_F:
        # Encontrado en Mathlib. D3 (distancia de premisas) aún no implementado.
        # Retornamos NO_NOVEDOSO_redundante provisional — D3 puede cambiarlo a
        # NOVEDAD_DEMOSTRACION si las premisas son distantes.
        return NoveltyVerdict(
            veredicto=Verdict.NO_NOVEDOSO_redundante,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=False,
            razonamiento=(
                f"D1: match en C_F (Mathlib): "
                f"'{(d1.match_C_F or {}).get('lean_name', '?')}' "
                f"(sim={((d1.match_C_F or {}).get('similarity', 0.0)):.2f}). "
                f"D3 (distancia de premisas) pendiente — si la prueba es distinta, "
                f"el veredicto cambiará a NOVEDAD_DEMOSTRACION (orchestrator.py Día 8)."
            ),
            stage_detenido=1,
        )

    # Fallback (no debería llegar acá)
    return NoveltyVerdict(
        veredicto=Verdict.NOVEDAD_ENUNCIADO,
        d1=d1,
        d2=d2,
        d3=d3,
        revision_humana=True,
        razonamiento="Estado inesperado en el árbol de decisión — revisar D1 manualmente.",
        stage_detenido=-1,
    )


# ---------------------------------------------------------------------------
# Demo: primer NoveltyVerdict end-to-end (adelanto Día 5)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

    # ── T15: "2 + 2 = 4" ──────────────────────────────────────────────────────
    # Esperado: NO_NOVEDOSO_trivial (D2 cierra con decide; D1 no corre)
    # No requiere ANTHROPIC_API_KEY ni red.
    print("=" * 64)
    print("Demo: primer NoveltyVerdict end-to-end")
    print("Caso T15: '2 + 2 = 4' (trivial — decide)")
    print("=" * 64)

    block_t15 = {
        "title": "2 + 2 = 4",
        "content_latex": "2 + 2 = 4",
    }
    lean_t15 = "(2 : Nat) + 2 = 4"

    verdict = check_novelty_verdict_simple(
        block=block_t15,
        lean_statement=lean_t15,
        lean_imports="import Mathlib.Tactic",
    )

    print(f"\nVeredicto: {verdict.veredicto.value}")
    print(f"Stage detenido: {verdict.stage_detenido}")
    print(f"Razonamiento: {verdict.razonamiento}")
    print(f"D2 trivial: {verdict.d2.trivial}, táctica: {verdict.d2.tactica}")
    print(f"D1 C_F: {verdict.d1.existe_en_C_F}, D1 C_I: {verdict.d1.existe_en_C_I}")
    print()
    print("to_dict():")
    import json
    print(json.dumps(verdict.to_dict(), indent=2, ensure_ascii=False))
