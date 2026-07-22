"""Matlas provider para búsqueda semántica a nivel de teorema.

Matlas (https://matlas.ai/) indexa 8.07M de enunciados de revistas
peer-reviewed que cubren de 1826 a 2025, más 1,900 libros de texto.
Proporciona una API REST pública sin autenticación.

Este módulo implementa la misma interfaz que `search_semantic_scholar()`:
recibe un query en lenguaje natural, devuelve `List[PaperCandidate]`.

Cada PaperCandidate de Matlas:
  - arxiv_id = None (Matlas no tiene arXiv IDs)
  - paper_id = DOI o candidate_id
  - year (atributo dinámico) = año de publicación (int o None)
  - source = "matlas"

Integración en D1-informal:
  Se activa/desactiva con MATLAS_ENABLED=1.
  Por defecto DESACTIVADA (opt-in, igual que TheoremSearch).

Uso:
  from src.novelty.matlas import search_matlas
  candidates = search_matlas("sqrt(2) is irrational", top_k=10)
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, Iterable, List, Optional

import requests

from src.novelty import _cache
from src.novelty.arxiv_search import PaperCandidate

logger = logging.getLogger(__name__)

# ── Configuración ───────────────────────────────────────────────────────────

MATLAS_API_URL: str = os.getenv(
    "MATLAS_API_URL",
    "https://matlas.ai/api/search",
).rstrip("/")

MATLAS_TIMEOUT: int = int(os.getenv("MATLAS_TIMEOUT", "30"))
MATLAS_MIN_INTERVAL: float = float(os.getenv("MATLAS_MIN_INTERVAL", "1.0"))

REQUEST_TIMEOUT = MATLAS_TIMEOUT

# ── Rate limiting ───────────────────────────────────────────────────────────

_matlas_rate_lock = threading.Lock()
_matlas_last_call: float = 0.0


def _matlas_rate_limit() -> None:
    global _matlas_last_call
    with _matlas_rate_lock:
        now = time.monotonic()
        elapsed = now - _matlas_last_call
        if elapsed < MATLAS_MIN_INTERVAL:
            time.sleep(MATLAS_MIN_INTERVAL - elapsed)
        _matlas_last_call = time.monotonic()


# ── Llamada a la API ────────────────────────────────────────────────────────

def _fetch_matlas(query: str, top_k: int) -> List[Dict[str, Any]]:
    """Llama a la API de Matlas y devuelve la lista de resultados.

    Maneja errores de red, timeout, y respuesta no-JSON devolviendo [].
    Nunca lanza excepción.
    """
    _matlas_rate_limit()

    try:
        response = requests.post(
            MATLAS_API_URL,
            json={"query": query, "num_results": max(top_k, 10)},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.Timeout:
        logger.warning("Matlas request timed out after %ds", REQUEST_TIMEOUT)
        return []
    except requests.RequestException as exc:
        logger.warning("Matlas request failed: %s", exc)
        return []

    try:
        payload = response.json()
    except ValueError:
        logger.warning("Matlas returned non-JSON response")
        return []

    if not isinstance(payload, list):
        logger.warning("Matlas unexpected response format: %s", str(payload)[:200])
        return []

    return payload


# ── Conversión a PaperCandidate ─────────────────────────────────────────────

def _result_to_candidate(result: Dict[str, Any]) -> Optional[PaperCandidate]:
    """Convierte un resultado de Matlas a PaperCandidate.

    Añade un atributo dinámico `year` (int o None) para el filtro temporal.
    """
    doi = (result.get("doi") or "").strip()
    entity_name = (result.get("entity_name") or "").strip()
    title = (result.get("title") or "").strip()
    statement = (result.get("statement") or "").strip()
    authors = (result.get("authors") or "").strip()
    journal = (result.get("journal") or "").strip()
    year_str = (result.get("year") or "").strip()
    candidate_id = (result.get("candidate_id") or "").strip()

    # Armar abstract informativo
    parts = []
    if authors:
        parts.append(authors)
    if journal:
        parts.append(journal)
    if year_str:
        parts.append(f"({year_str})")
    meta = ", ".join(parts)
    abstract = f"[{entity_name}] {statement}"
    if meta:
        abstract = f"{meta}\n{abstract}"

    paper_id = doi if doi else candidate_id
    if not paper_id:
        return None

    # Parse year
    year: Optional[int] = None
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            pass

    cand = PaperCandidate(
        paper_id=paper_id,
        title=title or entity_name,
        abstract=abstract,
        arxiv_id=None,
        similarity_score=0.0,
        embedding=None,
        source="matlas",
    )
    # Dynamic attribute for temporal filter
    cand.year = year  # type: ignore[attr-defined]
    return cand


def _payload_to_candidates(payload: List[Dict[str, Any]]) -> List[PaperCandidate]:
    """Convierte el payload completo a lista de PaperCandidate."""
    candidates: List[PaperCandidate] = []
    seen_ids: set[str] = set()

    for result in payload:
        cand = _result_to_candidate(result)
        if cand is None:
            continue
        pid = cand.paper_id
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        candidates.append(cand)

    return candidates


# ── API pública ─────────────────────────────────────────────────────────────

def search_matlas(
    query: str,
    top_k: int = 10,
    use_cache: bool = True,
    fallback_queries: Optional[Iterable[str]] = None,
) -> List[PaperCandidate]:
    """Busca teoremas similares en Matlas.

    Args:
        query: enunciado del teorema en lenguaje natural.
        top_k: número máximo de resultados (mínimo 10).
        use_cache: si usar el cache compartido de src/novelty/_cache.py.
        fallback_queries: queries alternativas si la principal no da resultados.

    Returns:
        Lista de PaperCandidate (sin arxiv_id, con atributo year dinámico).
        Lista vacía si la API falla o no hay resultados.
    """
    if not query or not query.strip():
        return []

    queries = [query]
    for fallback in fallback_queries or []:
        if fallback and fallback not in queries:
            queries.append(fallback)

    payload: List[Dict[str, Any]] = []
    for idx, candidate_query in enumerate(queries):
        cache_key = f"matlas::{top_k}::{candidate_query}"
        payload = _cache.cache_or_fetch(
            namespace="search_matlas",
            key=cache_key,
            fetch_fn=lambda q=candidate_query: _fetch_matlas(q, top_k),
            use_cache=use_cache,
        )
        if payload or idx == len(queries) - 1:
            break
        logger.info("Matlas returned 0 results; trying fallback query")

    return _payload_to_candidates(payload)
