"""TheoremSearch provider para búsqueda semántica a nivel de teorema.

TheoremSearch (https://www.theoremsearch.com/) indexa 9.2M de enunciados
de teoremas extraídos de arXiv y 7 fuentes adicionales. Proporciona una
API REST pública sin autenticación.

Este módulo implementa la misma interfaz que `search_semantic_scholar()`
en `arxiv_search.py`: recibe un query en lenguaje natural, devuelve
`List[PaperCandidate]`.

Integración en D1-informal:
  Se activa/desactiva con la variable de entorno THEOREMSEARCH_ENABLED.
  Por defecto DESACTIVADA para no alterar el pipeline existente.

Uso:
  from src.novelty.theoremsearch import search_theoremsearch
  candidates = search_theoremsearch("sqrt(2) is irrational", top_k=10)
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Any, Dict, Iterable, List, Optional

import requests
from dotenv import load_dotenv

from src.novelty import _cache
from src.novelty.arxiv_search import PaperCandidate, _normalize_arxiv_id

load_dotenv()

logger = logging.getLogger(__name__)

# ── Configuración ───────────────────────────────────────────────────────────

THEOREMSEARCH_API_URL: str = os.getenv(
    "THEOREMSEARCH_API_URL",
    "https://api.theoremsearch.com/search",
).rstrip("/")

THEOREMSEARCH_TIMEOUT: int = int(
    os.getenv("THEOREMSEARCH_TIMEOUT", "30")
)

THEOREMSEARCH_MIN_INTERVAL: float = float(
    os.getenv("THEOREMSEARCH_MIN_INTERVAL", "1.0")
)

REQUEST_TIMEOUT = THEOREMSEARCH_TIMEOUT

# ── Rate limiting ───────────────────────────────────────────────────────────

_ts_rate_lock = threading.Lock()
_ts_last_call: float = 0.0


def _ts_rate_limit() -> None:
    """Bloquea hasta que hayan pasado THEOREMSEARCH_MIN_INTERVAL segundos."""
    global _ts_last_call
    with _ts_rate_lock:
        now = time.monotonic()
        elapsed = now - _ts_last_call
        if elapsed < THEOREMSEARCH_MIN_INTERVAL:
            time.sleep(THEOREMSEARCH_MIN_INTERVAL - elapsed)
        _ts_last_call = time.monotonic()


# ── Helpers ─────────────────────────────────────────────────────────────────

def _extract_arxiv_id_from_paper(paper: Dict[str, Any]) -> Optional[str]:
    """Extrae un arXiv ID normalizado de los metadatos del paper.

    TheoremSearch devuelve `paper.paper_id` con formato "2103.03942v2"
    para papers de arXiv. Para otras fuentes, devolvemos None.
    """
    source = (paper.get("source") or "").strip().lower()
    paper_id = (paper.get("paper_id") or "").strip()

    if source == "arxiv" and paper_id:
        # paper_id tiene formato "2103.03942v2" o "math/0410536v2"
        # Normalizar con la misma función que usa arxiv_search.py
        return _normalize_arxiv_id(paper_id)

    # Intentar extraer de paper.link si paper_id no tiene formato arXiv
    link = (paper.get("link") or "").strip()
    if link:
        m = re.search(r"arxiv\.org/abs/([^/\s]+)", link)
        if m:
            return _normalize_arxiv_id(m.group(1))

    return None


def _truncate_query(text: str, max_chars: int = 500) -> str:
    """Trunca el query a max_chars para no enviar textos enormes a la API."""
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0]


# ── Llamada a la API ────────────────────────────────────────────────────────

def _fetch_theoremsearch(query: str, top_k: int) -> Dict[str, Any]:
    """Llama a la API de TheoremSearch y devuelve el payload JSON.

    Maneja errores de red, timeout, y respuesta no-JSON devolviendo
    {"theorems": [], "error": "..."}. Nunca lanza excepción.
    """
    _ts_rate_limit()

    try:
        response = requests.post(
            THEOREMSEARCH_API_URL,
            json={"query": query, "n_results": top_k},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.Timeout:
        logger.warning("TheoremSearch request timed out after %ds", REQUEST_TIMEOUT)
        return {"theorems": [], "error": "timeout"}
    except requests.RequestException as exc:
        logger.warning("TheoremSearch request failed: %s", exc)
        return {"theorems": [], "error": str(exc)}

    try:
        payload = response.json()
    except ValueError:
        logger.warning("TheoremSearch returned non-JSON response")
        return {"theorems": [], "error": "invalid_json"}

    if not isinstance(payload, dict) or "theorems" not in payload:
        logger.warning("TheoremSearch unexpected response format: %s",
                       str(payload)[:200])
        return {"theorems": [], "error": "unexpected_format"}

    return payload


# ── Conversión a PaperCandidate ─────────────────────────────────────────────

def _theorem_to_candidate(theorem: Dict[str, Any]) -> Optional[PaperCandidate]:
    """Convierte un teorema de TheoremSearch a PaperCandidate.

    Devuelve None si no se puede extraer información suficiente.
    """
    paper = theorem.get("paper") or {}

    # Armar abstract: slogan (NL) + body (LaTeX)
    slogan = (theorem.get("slogan") or "").strip()
    body = (theorem.get("body") or "").strip()
    abstract = f"{slogan}\n{body}".strip()
    if not abstract:
        abstract = slogan or body

    title = (paper.get("title") or theorem.get("name") or "").strip()
    paper_id = str(theorem.get("theorem_id") or theorem.get("slogan_id") or "")
    arxiv_id = _extract_arxiv_id_from_paper(paper)

    # Usar el similarity_score que ya viene de la API
    similarity_score = float(theorem.get("similarity", 0.0))

    return PaperCandidate(
        paper_id=paper_id,
        title=title,
        abstract=abstract,
        arxiv_id=arxiv_id,
        similarity_score=similarity_score,
        embedding=None,  # TheoremSearch no devuelve embeddings
        source="theoremsearch",
    )


def _payload_to_candidates(payload: Dict[str, Any]) -> List[PaperCandidate]:
    """Convierte el payload completo a lista de PaperCandidate."""
    theorems = payload.get("theorems") or []
    candidates: List[PaperCandidate] = []
    seen_ids: set[str] = set()

    for theorem in theorems:
        cand = _theorem_to_candidate(theorem)
        if cand is None:
            continue
        # Deduplicar por paper_id (TheoremSearch puede devolver
        # múltiples teoremas del mismo paper)
        pid = cand.paper_id
        if pid and pid in seen_ids:
            continue
        seen_ids.add(pid)
        candidates.append(cand)

    return candidates


# ── API pública ─────────────────────────────────────────────────────────────

def search_theoremsearch(
    query: str,
    top_k: int = 20,
    use_cache: bool = True,
    fallback_queries: Optional[Iterable[str]] = None,
    exclude_arxiv_ids: Optional[Iterable[str]] = None,
) -> List[PaperCandidate]:
    """Busca teoremas similares en TheoremSearch.

    Args:
        query: enunciado del teorema en lenguaje natural.
        top_k: número máximo de resultados a pedir.
        use_cache: si usar el cache compartido de src/novelty/_cache.py.
        fallback_queries: queries alternativas si la principal no da resultados.
        exclude_arxiv_ids: arXiv IDs a excluir (para filtrar el propio paper).

    Returns:
        Lista de PaperCandidate ordenados por similarity_score desc.
        Lista vacía si la API falla o no hay resultados.
    """
    if not query or not query.strip():
        return []

    query = _truncate_query(query)
    queries = [query]
    for fallback in fallback_queries or []:
        fallback_query = _truncate_query(fallback)
        if fallback_query and fallback_query not in queries:
            queries.append(fallback_query)

    payload: Dict[str, Any] = {"theorems": []}
    for idx, candidate_query in enumerate(queries):
        cache_key = f"ts::{top_k}::{candidate_query}"
        payload = _cache.cache_or_fetch(
            namespace="search_theoremsearch",
            key=cache_key,
            fetch_fn=lambda q=candidate_query: _fetch_theoremsearch(q, top_k),
            use_cache=use_cache,
        )
        theorems = payload.get("theorems") or []
        if theorems or idx == len(queries) - 1:
            break
        logger.info(
            "TheoremSearch returned 0 results for primary query; "
            "trying fallback query"
        )

    candidates = _payload_to_candidates(payload)

    # ── Excluir el propio paper ──────────────────────────────────────────
    excluded = {
        _normalize_arxiv_id(aid)
        for aid in (exclude_arxiv_ids or [])
        if _normalize_arxiv_id(aid)
    }
    if excluded:
        candidates = [
            cand
            for cand in candidates
            if (cand.arxiv_id is None or _normalize_arxiv_id(cand.arxiv_id) not in excluded)
        ]

    # Ya vienen ordenados por similarity de la API, pero re-ordenamos
    # para consistencia (y porque la dedup puede alterar el orden).
    candidates.sort(key=lambda c: c.similarity_score, reverse=True)
    return candidates


# ── Demo / smoke test ───────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    queries = [
        "the square root of 2 is irrational",
        "Cauchy-Schwarz inequality",
        "every continuous function on a compact set is uniformly continuous",
    ]

    for q in queries:
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        print("=" * 60)
        results = search_theoremsearch(q, top_k=5, use_cache=False)
        print(f"Results: {len(results)}")
        for i, c in enumerate(results[:5]):
            aid = c.arxiv_id or "(no arXiv ID)"
            print(f"  {i+1}. [{c.similarity_score:.3f}] {c.title[:80]}")
            print(f"     arXiv: {aid}  |  source: {c.source}")
            if c.abstract:
                abstract_preview = c.abstract[:120].replace("\n", " ")
                print(f"     Abstract: {abstract_preview}...")
