"""D1 — No-existencia previa.

Verifica si el teorema candidato ya existe en:
  C_F (corpus formal):   Mathlib, vía Leandex (búsqueda semántica sobre declaraciones Lean).
  C_I (corpus informal): arXiv/Semantic Scholar/TheoremSearch, con filtro grueso MiniLM + juez LLM fino.

Spec: paper/metric_spec.md §4.1
Decisiones de diseño: paper/decisions.md

Interface pública:
  check_d1(block, use_cache=True, ci_top_k=3, ci_threshold=0.40) → D1Result

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
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.novelty.arxiv_search import PaperCandidate, search_semantic_scholar, search_arxiv
from src.novelty.llm_judge import judge_theorem_pair
from src.novelty.mathlib_checker import check_in_mathlib
from src.novelty.theoremsearch import search_theoremsearch
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
# C_F — Corpus formal (Mathlib vía Leandex + exact?)
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
    if mathlib_res.found and mathlib_res.matches:
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
    """Etapa A: búsqueda arXiv + Semantic Scholar + TheoremSearch + filtro de similitud MiniLM.

    Ejecuta las fuentes en secuencia (cada una con su propio manejo de errores),
    deduplica por arxiv_id, y devuelve los top_k candidatos que superan
    similarity_threshold ordenados por similitud desc.

    arXiv es la fuente primaria (mejor cobertura para matemática).
    Semantic Scholar es secundaria (más rápida pero menor recall en math).
    TheoremSearch es terciaria (theorem-level, activada con THEOREMSEARCH_ENABLED).
    """
    query = _block_text(block)
    if not query:
        return []

    all_candidates: List[PaperCandidate] = []

    # ── arXiv (fuente primaria) ──────────────────────────────────────────
    try:
        arxiv_candidates = search_arxiv(
            query, top_k=20, reference_text=query, use_cache=use_cache
        )
        all_candidates.extend(arxiv_candidates)
        logger.info("C_I arXiv: %d candidates for query '%s'", len(arxiv_candidates), query[:80])
    except Exception as exc:
        logger.warning("arXiv search failed: %s", exc)

    # ── Semantic Scholar (fuente secundaria) ─────────────────────────────
    try:
        ss_candidates = search_semantic_scholar(query, top_k=20, use_cache=use_cache)
        all_candidates.extend(ss_candidates)
    except Exception as exc:
        logger.warning("Semantic Scholar search failed: %s", exc)

    # ── TheoremSearch (fuente terciaria, theorem-level, opcional) ───────
    if os.getenv("THEOREMSEARCH_ENABLED", "").strip().lower() in ("1", "true", "yes"):
        try:
            ts_candidates = search_theoremsearch(query, top_k=20, use_cache=use_cache)
            all_candidates.extend(ts_candidates)
            logger.info(
                "C_I TheoremSearch: %d candidates for query '%s'",
                len(ts_candidates),
                query[:80],
            )
        except Exception as exc:
            logger.warning("TheoremSearch search failed: %s", exc)

    if not all_candidates:
        return []

    # ── Score + filter + dedup ───────────────────────────────────────────
    block_text = _block_text(block)
    scored: Dict[str, tuple[PaperCandidate, float]] = {}  # keyed by arxiv_id

    for cand in all_candidates:
        aid = (cand.arxiv_id or cand.paper_id or "").strip().lower()
        if not aid:
            continue
        cand_text = f"{cand.title} {cand.abstract}"
        sim = _cosine_sim(block_text, cand_text)
        if sim < similarity_threshold:
            continue
        # Conservar el mejor score por arxiv_id
        if aid not in scored or sim > scored[aid][1]:
            scored[aid] = (cand, sim)

    # Ordenar y limitar a top_k
    result = sorted(scored.values(), key=lambda x: -x[1])
    return result[:top_k]


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
