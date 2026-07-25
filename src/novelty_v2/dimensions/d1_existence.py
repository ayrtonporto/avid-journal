"""D1 — No-existencia previa.

Verifica si el teorema candidato ya existe en:
  C_F (corpus formal):   Mathlib, vía Leandex (búsqueda semántica sobre declaraciones Lean).
  C_I (corpus informal): arXiv (primaria) + TheoremSearch (opcional, THEOREMSEARCH_ENABLED),
                         con filtro grueso MiniLM + juez LLM fino DeepSeek. Semantic Scholar
                         quedó fuera del path activo (reemplazado por TheoremSearch).

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
  - arxiv_search.search_arxiv → C_I etapa A (fuente primaria)
  - theoremsearch.search_theoremsearch → C_I etapa A (opcional, theorem-level)
  - block_comparator (MiniLM) → C_I etapa A (similitud, filtro grueso)
  - llm_judge.judge_theorem_pair → C_I etapa B (verificación fina, DeepSeek)
"""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.novelty.arxiv_search import (
    PaperCandidate, _normalize_arxiv_id, search_arxiv,
)
from src.novelty.block_comparator import strip_latex_for_query
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

# Topes de pared (segundos) para las llamadas de red de D1. Las funciones
# congeladas de src/novelty tienen sus propios timeouts (a veces largos o con
# backoff que come minutos); acá ponemos un cap MÁS chico desde el caller para
# que la novedad no se cuelgue en la web. Si se pasa, fail-open.
CI_JUDGE_TIMEOUT: int = int(os.getenv("AVID_JUDGE_TIMEOUT", "30"))     # por candidato (etapa B)
CI_SOURCE_TIMEOUT: int = int(os.getenv("AVID_CI_SOURCE_TIMEOUT", "20"))  # por fuente (etapa A)


def _call_with_timeout(fn, timeout, *args, **kwargs):
    """Corre fn(*args, **kwargs) bajo un timeout de pared. En timeout levanta
    concurrent.futures.TimeoutError y deja el hilo huérfano terminando en
    background (acotado por el timeout interno de la fuente) en vez de bloquear,
    así el pipeline nunca se cuelga esperando una llamada de red."""
    ex = ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(fn, *args, **kwargs)
    try:
        return fut.result(timeout=timeout)
    finally:
        ex.shutdown(wait=False)


# ── arXiv ID date extraction ─────────────────────────────────────────────────

def _extract_year_month(arxiv_id: Optional[str]) -> Optional[int]:
    """Extrae YYYYMM desde un arXiv ID, o None si no se puede parsear.

    Soportados ambos formatos:
      - Nuevo (2007+):  YYMM.NNNNN[vN]   → ej. 1207.0631v1 → 201207
      - Viejo (pre-2007): category/YYMMNNN[vN] → ej. math/0604362v2 → 200604

    Mapeo de año de 2 dígitos: YY >= 91 → 19YY, YY <= 90 → 20YY.
    (arXiv empezó en 1991; papers actuales son 2000+.)
    Retorna None si no se puede extraer año+mese.
    """
    if not arxiv_id:
        return None
    aid = arxiv_id.strip()

    # Nuevo formato: YYMM.NNNNN[vN]
    m = re.match(r"^(\d{2})(\d{2})\.\d{4,}(v\d+)?$", aid)
    if m:
        yy, mm = int(m.group(1)), int(m.group(2))
        year = 1900 + yy if yy >= 91 else 2000 + yy
        if 1 <= mm <= 12:
            return year * 100 + mm
        return year * 100  # mes inválido — granularidad de año

    # Viejo formato: category/YYMMNNN[vN]
    m = re.match(r"^[a-z-]+/(\d{2})(\d{2})\d{3,}(v\d+)?$", aid)
    if m:
        yy, mm = int(m.group(1)), int(m.group(2))
        year = 1900 + yy if yy >= 91 else 2000 + yy
        if 1 <= mm <= 12:
            return year * 100 + mm
        return year * 100

    # Viejo formato sin prefijo: YYMMNNN (7 dígitos, pre-2007)
    m = re.match(r"^(\d{2})(\d{2})\d{3}$", aid)
    if m:
        yy, mm = int(m.group(1)), int(m.group(2))
        year = 1900 + yy if yy >= 91 else 2000 + yy
        if 1 <= mm <= 12:
            return year * 100 + mm
        return year * 100

    return None

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
        mathlib_res = _call_with_timeout(
            check_in_mathlib, CI_SOURCE_TIMEOUT, block, use_cache=use_cache
        )
    except Exception as exc:
        logger.warning("check_in_mathlib failed/timed out: %s", exc)
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
    query_raw = _block_text(block)
    if not query_raw:
        return []

    # Cleaned query for search APIs (strip LaTeX markup, no arXiv ID prefix)
    content_latex = block.get("content_latex", "")
    query_clean = strip_latex_for_query(content_latex) if content_latex else query_raw
    if not query_clean.strip():
        query_clean = query_raw

    # ── Paper self-exclusion ──────────────────────────────────────────────
    paper_arxiv_id = block.get("arxiv_id") or block.get("title", "")
    paper_arxiv_id_norm = _normalize_arxiv_id(paper_arxiv_id) if paper_arxiv_id else None
    exclude_ids = [paper_arxiv_id] if paper_arxiv_id else []

    all_candidates: List[PaperCandidate] = []

    # ── arXiv (fuente primaria) ──────────────────────────────────────────
    # NOTA: search_arxiv NO soporta exclude_arxiv_ids — se filtra post-búsqueda.
    try:
        arxiv_candidates = _call_with_timeout(
            search_arxiv, CI_SOURCE_TIMEOUT,
            query_clean, top_k=20, reference_text=query_raw, use_cache=use_cache,
        )
        if paper_arxiv_id_norm:
            arxiv_candidates = [
                c for c in arxiv_candidates
                if _normalize_arxiv_id(c.arxiv_id) != paper_arxiv_id_norm
            ]
        all_candidates.extend(arxiv_candidates)
        logger.info("C_I arXiv: %d candidates for query '%s'", len(arxiv_candidates), query_clean[:80])
    except Exception as exc:
        logger.warning("arXiv search failed: %s", exc)

    # ── Matlas (fuente secundaria: revistas peer-reviewed 1826-2025) ────
    if os.getenv("MATLAS_ENABLED", "").strip().lower() in ("1", "true", "yes"):
        try:
            from src.novelty.matlas import search_matlas
            matlas_candidates = _call_with_timeout(
                search_matlas, CI_SOURCE_TIMEOUT, query_clean, top_k=10, use_cache=use_cache
            )
            all_candidates.extend(matlas_candidates)
            logger.info(
                "C_I Matlas: %d candidates for query '%s'",
                len(matlas_candidates),
                query_clean[:80],
            )
        except Exception as exc:
            logger.warning("Matlas search failed: %s", exc)

    # ── TheoremSearch (fuente terciaria, theorem-level, opcional) ───────
    if os.getenv("THEOREMSEARCH_ENABLED", "").strip().lower() in ("1", "true", "yes"):
        try:
            ts_candidates = _call_with_timeout(
                search_theoremsearch, CI_SOURCE_TIMEOUT,
                query_clean, top_k=20, use_cache=use_cache, exclude_arxiv_ids=exclude_ids,
            )
            all_candidates.extend(ts_candidates)
            logger.info(
                "C_I TheoremSearch: %d candidates for query '%s'",
                len(ts_candidates),
                query_clean[:80],
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


# ── Temporal filter (date) ────────────────────────────────────────────────────

def _filter_by_date(
    candidates: List[Tuple[PaperCandidate, float]],
    paper_arxiv_id: Optional[str],
) -> Tuple[List[Tuple[PaperCandidate, float]], int]:
    """Descarta candidatos cuya fecha sea POSTERIOR a la del paper evaluado.

    Un candidato válido como duplicador debe ser anterior al paper.
    Candidatos sin arXiv ID (fecha desconocida) pasan igual pero se cuentan.

    Args:
        candidates: lista de (PaperCandidate, similarity_score) de etapa A.
        paper_arxiv_id: arXiv ID del paper bajo evaluación (para extraer año).

    Returns:
        (filtered_candidates, count_unknown_dates)
    """
    paper_ym = _extract_year_month(paper_arxiv_id)
    if paper_ym is None:
        # No se puede determinar la fecha del paper → dejar pasar todo
        return candidates, 0

    kept: List[Tuple[PaperCandidate, float]] = []
    unknown_dates = 0
    discarded = 0

    for cand, sim in candidates:
        # Prefer explicit year attribute (Matlas) over arXiv ID extraction
        if hasattr(cand, "year") and cand.year is not None:
            cand_ym = cand.year * 100  # year-only granularity (YYYY00)
        else:
            cand_ym = _extract_year_month(cand.arxiv_id)

        if cand_ym is None:
            kept.append((cand, sim))
            unknown_dates += 1
        elif cand_ym <= paper_ym:
            kept.append((cand, sim))
        else:
            cand_id = getattr(cand, "paper_id", cand.arxiv_id or "?")
            logger.info(
                "C_I temporal filter: DISCARDED %s (date %d > paper %d)",
                cand_id, cand_ym, paper_ym,
            )
            discarded += 1

    if discarded:
        logger.info(
            "C_I temporal filter: %d candidate(s) discarded (newer than paper), "
            "%d passed, %d with unknown date",
            discarded, len(kept), unknown_dates,
        )
    return kept, unknown_dates


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
            judge = _call_with_timeout(
                judge_theorem_pair, CI_JUDGE_TIMEOUT,
                block_new, block_candidate, use_cache=use_cache,
            )
        except FuturesTimeout:
            logger.warning(
                "llm_judge timed out (%ss) for candidate '%s' — skipping (fail-open)",
                CI_JUDGE_TIMEOUT, cand.title,
            )
            result.traduccion_incierta = True
            continue
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

    # ── Temporal filter: discard candidates newer than the paper ─────────────
    paper_arxiv_id = block.get("arxiv_id") or block.get("title", "")
    ci_candidates, _fechas_desconocidas = _filter_by_date(ci_candidates, paper_arxiv_id)

    if ci_candidates:
        ci_result = _run_ci_stage_b(block, ci_candidates, use_cache)
        result.existe_en_C_I = ci_result.existe_en_C_I
        result.match_C_I = ci_result.match_C_I
        result.llm_judge_verdict = ci_result.llm_judge_verdict
        if ci_result.traduccion_incierta:
            result.traduccion_incierta = True

    return result
