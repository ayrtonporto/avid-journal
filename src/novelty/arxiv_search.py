"""Stage 1: Busqueda de papers candidatos en Semantic Scholar y ArXiv.

Recupera papers cuyo abstract es semanticamente similar al del paper nuevo
para acotar el espacio de comparacion antes de Stages 2-3 (mas caros).

Estrategia v1:
  - Semantic Scholar paper/search: usa el ranking del propio servicio + el
    embedding SPECTER2 que devuelve la API cuando se pide en `fields`.
    Como SS no expone "embed arbitrary text", calculamos `similarity_score`
    via MiniLM (block_comparator) entre el abstract de consulta y el del
    candidato. Si SS devuelve `embedding.vector` lo guardamos para usos
    futuros pero no lo combinamos en el score base.
  - ArXiv: paquete `arxiv` con sort_by=Relevance.
  - Deduplicar por arxiv_id, filtrar por threshold, ordenar desc.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import requests
from dotenv import load_dotenv

from src.novelty import _cache

load_dotenv()

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_ENDPOINT = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = "title,abstract,externalIds,embedding"
REQUEST_TIMEOUT = 30

# Rate limiting: SS permite 1 req/s sin key y ~10 req/s con key.
# Usamos 1.1 s como intervalo minimo conservador para el modo anonimo;
# con API key el pipeline puede reducirlo, pero 1.1 s es seguro para ambos.
SS_MIN_INTERVAL: float = 1.1  # segundos entre llamadas a SS

_ss_rate_lock = threading.Lock()
_ss_last_call: float = 0.0  # tiempo monotónico del último request SS

# Warning de modo anónimo: se emite solo una vez por proceso.
_ss_anon_warning_emitted = False

# Backoff para llamadas a ArXiv (search y descarga de tarballs).
# La librería `arxiv` tiene retries internos (num_retries=3, delay plano),
# pero reintentan TODOS los HTTP errors incluido 404, sin backoff exponencial.
# Solución: Client(num_retries=0, delay_seconds=0) + nuestro propio loop que
# distingue 429/503 (retryable) de otros 4xx (no retryable).
ARXIV_RETRY_DELAYS: tuple = (5, 15, 45)  # segundos; 3 reintentos = 4 intentos


@dataclass
class PaperCandidate:
    paper_id: str
    title: str
    abstract: str
    arxiv_id: Optional[str]
    similarity_score: float = 0.0
    embedding: Optional[List[float]] = None
    source: str = "semantic_scholar"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperCandidate":
        return cls(
            paper_id=data.get("paper_id", ""),
            title=data.get("title", ""),
            abstract=data.get("abstract", ""),
            arxiv_id=data.get("arxiv_id"),
            similarity_score=float(data.get("similarity_score", 0.0)),
            embedding=data.get("embedding"),
            source=data.get("source", "semantic_scholar"),
        )


# ---------------------------------------------------------------------------
# Similitud (importacion lazy para evitar cargar MiniLM si no hace falta)
# ---------------------------------------------------------------------------

def _cosine_similarity_text(a: str, b: str) -> float:
    """Cosine similarity entre dos textos via MiniLM (lazy import)."""
    from src.novelty import block_comparator

    if not a or not b:
        return 0.0
    model = block_comparator.get_model()
    embeddings = model.encode([a, b], convert_to_numpy=True, normalize_embeddings=True)
    return float(embeddings[0] @ embeddings[1])


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------

def _ss_headers() -> Dict[str, str]:
    """Construye los headers HTTP para Semantic Scholar.

    Si `SEMANTIC_SCHOLAR_API_KEY` está configurada, la incluye como
    `x-api-key`. Si no, emite un warning una sola vez por proceso informando
    que se usará el modo anónimo con rate limits estrictos (1 req/s).
    """
    global _ss_anon_warning_emitted
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    elif not _ss_anon_warning_emitted:
        logger.warning(
            "SEMANTIC_SCHOLAR_API_KEY not configured — using anonymous mode "
            "with strict rate limits (1 req/s). Set the key in .env to increase "
            "throughput. See .env.example for the variable name."
        )
        _ss_anon_warning_emitted = True
    return headers


def _ss_key_preview(headers: Dict[str, str]) -> str:
    """Devuelve una version segura de la API key para logs verbose."""
    api_key = headers.get("x-api-key", "").strip()
    if not api_key:
        return "(anonymous)"
    return f"{api_key[:6]}..."


def _ss_rate_limit() -> None:
    """Bloquea hasta que hayan pasado al menos SS_MIN_INTERVAL segundos desde
    la última llamada a Semantic Scholar. Thread-safe.
    """
    global _ss_last_call
    with _ss_rate_lock:
        now = time.monotonic()
        elapsed = now - _ss_last_call
        if elapsed < SS_MIN_INTERVAL:
            time.sleep(SS_MIN_INTERVAL - elapsed)
        _ss_last_call = time.monotonic()


def _truncate_query(text: str, max_chars: int = 250) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0]


def _fetch_semantic_scholar(query: str, top_k: int) -> Dict[str, Any]:
    _ss_rate_limit()
    headers = _ss_headers()
    print(f"[V] Using API key: {_ss_key_preview(headers)}")
    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_ENDPOINT,
            params={
                "query": query,
                "limit": top_k,
                "fields": SEMANTIC_SCHOLAR_FIELDS,
            },
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        status_code = response.status_code
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Semantic Scholar request failed: %s", exc)
        return {"data": [], "error": str(exc)}
    try:
        payload = response.json()
    except ValueError:
        return {"data": [], "error": "invalid_json"}
    if isinstance(payload, dict):
        raw_papers = payload.get("data") or []
        total = payload.get("total")
        payload["_meta"] = {
            "status_code": status_code,
            "used_api_key": "x-api-key" in headers,
            "data_len": len(raw_papers),
            "total": total,
        }
        if status_code == 200 and not raw_papers:
            print(
                "[V] Semantic Scholar returned 0 real results "
                f"(HTTP 200, total={total}, api_key={_ss_key_preview(headers)})"
            )
    return payload


def _payload_to_candidates(payload: Dict[str, Any]) -> List[PaperCandidate]:
    raw_papers = payload.get("data") or []
    candidates: List[PaperCandidate] = []
    for paper in raw_papers:
        external = paper.get("externalIds") or {}
        arxiv_id = external.get("ArXiv") or external.get("arxiv")
        if not arxiv_id:
            continue
        embedding_obj = paper.get("embedding") or {}
        embedding_vector = (
            embedding_obj.get("vector") if isinstance(embedding_obj, dict) else None
        )
        candidates.append(
            PaperCandidate(
                paper_id=str(paper.get("paperId") or ""),
                title=paper.get("title") or "",
                abstract=paper.get("abstract") or "",
                arxiv_id=str(arxiv_id),
                similarity_score=0.0,
                embedding=embedding_vector,
                source="semantic_scholar",
            )
        )
    return candidates


def search_semantic_scholar(
    abstract: str,
    top_k: int = 20,
    use_cache: bool = True,
    fallback_queries: Optional[Iterable[str]] = None,
    exclude_arxiv_ids: Optional[Iterable[str]] = None,
) -> List[PaperCandidate]:
    """Busca candidatos via Semantic Scholar y los rankea por similitud MiniLM."""
    if not abstract or not abstract.strip():
        return []

    query = _truncate_query(abstract)
    queries = [query]
    for fallback in fallback_queries or []:
        fallback_query = _truncate_query(fallback)
        if fallback_query and fallback_query not in queries:
            queries.append(fallback_query)

    payload: Dict[str, Any] = {"data": []}
    for idx, candidate_query in enumerate(queries):
        cache_key = f"ss::{top_k}::{candidate_query}"
        payload = _cache.cache_or_fetch(
            namespace="search_ss",
            key=cache_key,
            fetch_fn=lambda q=candidate_query: _fetch_semantic_scholar(q, top_k),
            use_cache=use_cache,
        )
        raw_papers = payload.get("data") or []
        if raw_papers or idx == len(queries) - 1:
            break
        logger.info(
            "Semantic Scholar returned 0 results for primary query; "
            "trying fallback query"
        )

    candidates = _payload_to_candidates(payload)
    excluded = {
        _normalize_arxiv_id(arxiv_id)
        for arxiv_id in (exclude_arxiv_ids or [])
        if _normalize_arxiv_id(arxiv_id)
    }
    if excluded:
        candidates = [
            cand
            for cand in candidates
            if _normalize_arxiv_id(cand.arxiv_id) not in excluded
        ]

    # Score por similitud MiniLM entre abstract de consulta y de cada candidato.
    for cand in candidates:
        try:
            cand.similarity_score = _cosine_similarity_text(abstract, cand.abstract)
        except Exception as exc:  # noqa: BLE001
            logger.warning("MiniLM scoring failed for %s: %s", cand.paper_id, exc)
            cand.similarity_score = 0.0

    candidates.sort(key=lambda c: c.similarity_score, reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# ArXiv
# ---------------------------------------------------------------------------

def _arxiv_fetch_once(client: Any, search: Any) -> List[Dict[str, Any]]:
    """Un solo intento de búsqueda ArXiv. Puede lanzar arxiv.HTTPError o
    requests.RequestException — el llamador decide si reintenta.

    Recibe `client` y `search` ya construidos para desacoplar la lógica de
    retry de la de parsing, y facilitar el mock en tests.
    """
    results = []
    for r in client.results(search):
        arxiv_id = r.entry_id.rsplit("/", 1)[-1]
        arxiv_id = arxiv_id.replace("abs/", "")
        if "v" in arxiv_id:
            arxiv_id = (
                arxiv_id.split("v", 1)[0]
                if arxiv_id.split("v", 1)[1].isdigit()
                else arxiv_id
            )
        results.append(
            {
                "paper_id": r.entry_id,
                "title": r.title or "",
                "abstract": r.summary or "",
                "arxiv_id": arxiv_id,
            }
        )
    return results


def _fetch_arxiv(query: str, top_k: int) -> List[Dict[str, Any]]:
    """Busca en ArXiv con backoff exponencial ante 429/503 y errores de red.

    Usa arxiv.Client(num_retries=0, delay_seconds=0) para desactivar los
    retries internos de la librería (que reintentan todos los HTTP errors,
    incluido 404) y gestionar el backoff nosotros con lógica selectiva:
      - 429, 503           → retryable (rate limit / overload transitorio)
      - otros 4xx (≠ 429)  → no retryable (error del cliente, no volver a intentar)
      - errores de red     → retryable

    Delays: ARXIV_RETRY_DELAYS (5s, 15s, 45s). Máximo 3 reintentos (4 intentos).
    Si todos fallan, devuelve [] y loguea ERROR (no lanza excepción).
    """
    try:
        import arxiv
    except ImportError:
        logger.warning("arxiv package not installed")
        return []

    client = arxiv.Client(num_retries=0, delay_seconds=0)
    search = arxiv.Search(
        query=query,
        max_results=top_k,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    total_attempts = len(ARXIV_RETRY_DELAYS) + 1

    for attempt, delay in enumerate((*ARXIV_RETRY_DELAYS, None), start=1):
        try:
            return _arxiv_fetch_once(client, search)

        except arxiv.HTTPError as exc:
            status = exc.status
            if status != 429 and 400 <= status < 500:
                # Error de cliente no retryable (e.g. 404 bad query)
                logger.warning(
                    "ArXiv search returned HTTP %d (not retrying): %s", status, exc
                )
                return []
            if delay is None:
                logger.error(
                    "ArXiv search failed after %d/%d attempts (HTTP %d): %s",
                    attempt, total_attempts, status, exc,
                )
                return []
            logger.warning(
                "ArXiv search attempt %d/%d returned HTTP %d — retrying in %ds",
                attempt, total_attempts, status, delay,
            )
            time.sleep(delay)

        except requests.RequestException as exc:
            if delay is None:
                logger.error(
                    "ArXiv search failed after %d/%d attempts (network): %s",
                    attempt, total_attempts, exc,
                )
                return []
            logger.warning(
                "ArXiv search attempt %d/%d failed (network): %s — retrying in %ds",
                attempt, total_attempts, exc, delay,
            )
            time.sleep(delay)

        except Exception as exc:  # noqa: BLE001
            logger.warning("ArXiv search unexpected error: %s", exc)
            return []

    return []  # nunca se alcanza, pero satisface al type checker


def search_arxiv(
    query: str,
    top_k: int = 10,
    reference_text: Optional[str] = None,
    use_cache: bool = True,
) -> List[PaperCandidate]:
    """Busca candidatos directamente en ArXiv.

    `reference_text` (opcional) se usa para calcular `similarity_score` via
    MiniLM. Si no se pasa, el score queda en 0.0 (los candidatos solo aportan
    cobertura adicional para el dedup).
    """
    if not query or not query.strip():
        return []

    cache_key = f"arxiv::{top_k}::{query.strip()}"
    raw = _cache.cache_or_fetch(
        namespace="search_arxiv",
        key=cache_key,
        fetch_fn=lambda: _fetch_arxiv(query, top_k),
        use_cache=use_cache,
    )

    candidates: List[PaperCandidate] = []
    for entry in raw:
        cand = PaperCandidate(
            paper_id=entry.get("paper_id", ""),
            title=entry.get("title", ""),
            abstract=entry.get("abstract", ""),
            arxiv_id=entry.get("arxiv_id"),
            similarity_score=0.0,
            embedding=None,
            source="arxiv",
        )
        candidates.append(cand)

    if reference_text:
        for cand in candidates:
            try:
                cand.similarity_score = _cosine_similarity_text(
                    reference_text, cand.abstract
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("MiniLM scoring failed for %s: %s", cand.paper_id, exc)
                cand.similarity_score = 0.0

    candidates.sort(key=lambda c: c.similarity_score, reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Combinacion / dedup / filtro
# ---------------------------------------------------------------------------

def _normalize_arxiv_id(arxiv_id: Optional[str]) -> Optional[str]:
    if not arxiv_id:
        return None
    aid = arxiv_id.strip()
    aid = aid.replace("arXiv:", "").replace("arxiv:", "")
    aid = aid.split("/")[-1]
    aid = re.sub(r"v\d+$", "", aid)
    aid = aid.lower()
    return aid or None


def combine_and_filter(
    candidates: Iterable[PaperCandidate],
    threshold: float = 0.3,
) -> List[PaperCandidate]:
    """Deduplica por arxiv_id, filtra por umbral y ordena desc."""
    by_id: Dict[str, PaperCandidate] = {}
    for cand in candidates:
        key = _normalize_arxiv_id(cand.arxiv_id)
        if not key:
            continue
        cand.arxiv_id = key
        existing = by_id.get(key)
        if existing is None:
            by_id[key] = cand
            continue
        # Conservar la entrada con mas metadata o mayor score.
        if (
            cand.similarity_score > existing.similarity_score
            or (not existing.abstract and cand.abstract)
            or (not existing.embedding and cand.embedding)
        ):
            # Combinar campos utiles
            cand.embedding = cand.embedding or existing.embedding
            cand.abstract = cand.abstract or existing.abstract
            cand.title = cand.title or existing.title
            cand.similarity_score = max(cand.similarity_score, existing.similarity_score)
            by_id[key] = cand

    filtered = [c for c in by_id.values() if c.similarity_score >= threshold]
    filtered.sort(key=lambda c: c.similarity_score, reverse=True)
    return filtered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_abs = (
        "We prove a new bound on the number of squarefree integers in short intervals "
        "by combining sieve methods with bounds on character sums."
    )
    ss = search_semantic_scholar(sample_abs, top_k=5, use_cache=False)
    print(f"SS candidates: {len(ss)}")
    for c in ss[:3]:
        print(f"  {c.arxiv_id} sim={c.similarity_score:.3f} - {c.title[:60]}")
