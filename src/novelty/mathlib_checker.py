"""Stage 0: Comprueba si un bloque ya existe en Mathlib via Leandex.

Leandex (https://leandex.projectnumina.ai) es un servicio de busqueda
semantica sobre Mathlib. Si el bloque ya esta probado alli, no es novedoso
y se etiqueta IN_MATHLIB.

API: GET https://leandex.projectnumina.ai/api/v1/search?q=<query>&limit=<n>
Respuesta: Server-Sent Events (lineas `data: {...}`); el ultimo evento sin
`error` y con `data.search_results` poblado contiene los matches.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests

from src.novelty import _cache

logger = logging.getLogger(__name__)

LEANDEX_ENDPOINT = "https://leandex.projectnumina.ai/api/v1/search"
SIMILARITY_THRESHOLD = 0.85
REQUEST_TIMEOUT = 30
QUERY_MAX_CHARS = 400


@dataclass
class MathlibMatch:
    lean_name: str
    statement: str
    similarity: float
    url: str


@dataclass
class MathlibResult:
    found: bool
    matches: List[MathlibMatch] = field(default_factory=list)
    best_similarity: float = 0.0


def _strip_latex(text: str) -> str:
    """Limpieza minima de LaTeX para construir una query de busqueda."""
    text = re.sub(r"\\(begin|end)\{[^}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    text = re.sub(r"[\${}\\&_^~]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _build_query(block: Dict[str, Any]) -> str:
    title = (block.get("title") or "").strip()
    content = _strip_latex(block.get("content_latex") or "")
    parts = []
    if title:
        parts.append(title)
    if content:
        parts.append(content)
    query = ". ".join(parts)
    if len(query) > QUERY_MAX_CHARS:
        query = query[:QUERY_MAX_CHARS].rsplit(" ", 1)[0]
    return query or (block.get("type") or "theorem")


def _parse_sse(text: str) -> List[Dict[str, Any]]:
    """Parsea el cuerpo SSE de Leandex en una lista de eventos JSON."""
    events: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :].strip()
        if not payload:
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return events


def _mathlib_url(lean_name: str) -> str:
    """URL aproximada en Mathlib4 docs (puede no ser exacta para todos)."""
    if not lean_name:
        return ""
    return f"https://leanprover-community.github.io/mathlib4_docs/find/?pattern={quote_plus(lean_name)}"


def _extract_matches(events: List[Dict[str, Any]]) -> List[MathlibMatch]:
    """Recorre los eventos SSE y devuelve los matches del mejor evento útil.

    Leandex v2 (post-2025) devuelve un formato plano sin puntajes de similitud:
      data.search_results[i] = {
        "name": str,           # lean_name (e.g. "irrational_sqrt_two")
        "module": str,         # módulo Mathlib
        "source_text": str,    # declaración Lean completa
        "docstring": str,      # docstring en Mathlib
        "source_link": str,    # URL al source en GitHub
        "dependencies": [...], # dependencias
        "informalization": str # descripción informal generada
      }

    Como Leandex no asigna puntajes, usamos el orden de resultados como proxy
    de relevancia: el primer resultado es el mejor match (similarity = 1.0),
    los siguientes decrecen (0.9, 0.8, ...).
    """
    best_results: Optional[List[Dict[str, Any]]] = None

    for event in events:
        if event.get("error"):
            continue
        data = event.get("data") or {}
        results = data.get("search_results")
        if results:
            best_results = results

    if not best_results:
        return []

    matches: List[MathlibMatch] = []
    for i, entry in enumerate(best_results):
        # Leandex v2: flat structure with "name", "source_text"
        lean_name = (
            entry.get("name")
            or entry.get("lean_name")
            or entry.get("full_name")
            or ""
        )
        statement = (
            entry.get("source_text")
            or entry.get("statement")
            or entry.get("type")
            or entry.get("signature")
            or ""
        )

        # Intentar extraer similarity de cualquier campo que pudiera tenerlo
        # (compatibilidad hacia atrás con Leandex v1)
        similarity = (
            entry.get("similarity")
            or entry.get("score")
            or entry.get("relevance")
        )
        if similarity is not None:
            try:
                similarity = float(similarity)
            except (TypeError, ValueError):
                similarity = 0.0
        else:
            # Leandex v2 no da puntajes → orden como proxy (1.0, 0.9, 0.8, ...)
            similarity = max(0.0, 1.0 - i * 0.1)

        matches.append(
            MathlibMatch(
                lean_name=str(lean_name),
                statement=str(statement),
                similarity=similarity,
                url=_mathlib_url(str(lean_name)),
            )
        )

    return matches


def _fetch_leandex(query: str) -> Dict[str, Any]:
    """Llama a Leandex y devuelve un dict serializable con matches."""
    try:
        response = requests.get(
            LEANDEX_ENDPOINT,
            params={"q": query, "limit": 5},
            timeout=REQUEST_TIMEOUT,
            headers={"Accept": "text/event-stream"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Leandex request failed: %s", exc)
        return {"matches": [], "best_similarity": 0.0, "error": str(exc)}

    events = _parse_sse(response.text)
    matches = _extract_matches(events)
    best = matches[0].similarity if matches else 0.0
    return {
        "matches": [asdict(m) for m in matches],
        "best_similarity": best,
    }


def check_in_mathlib(block: Dict[str, Any], use_cache: bool = True) -> MathlibResult:
    """Busca el bloque en Mathlib via Leandex.

    Si la mejor similitud supera SIMILARITY_THRESHOLD el bloque se considera
    encontrado (IN_MATHLIB). Ante fallo de red se devuelve `found=False`.
    """
    query = _build_query(block)
    if not query.strip():
        return MathlibResult(found=False, matches=[], best_similarity=0.0)

    payload = _cache.cache_or_fetch(
        namespace="mathlib",
        key=query,
        fetch_fn=lambda: _fetch_leandex(query),
        use_cache=use_cache,
    )

    matches = [MathlibMatch(**m) for m in payload.get("matches", [])]
    best = float(payload.get("best_similarity", 0.0))
    return MathlibResult(
        found=best >= SIMILARITY_THRESHOLD,
        matches=matches,
        best_similarity=best,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample = {
        "type": "theorem",
        "title": "Commutativity of natural number addition",
        "content_latex": "For all $a, b \\in \\mathbb{N}$, $a + b = b + a$.",
    }
    result = check_in_mathlib(sample, use_cache=False)
    print(f"found={result.found} best_similarity={result.best_similarity:.3f}")
    for m in result.matches:
        print(f"  - {m.lean_name} (sim={m.similarity:.3f})")
