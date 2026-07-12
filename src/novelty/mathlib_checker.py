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
    similarity: Optional[float]  # None if Leandex doesn't provide scores
    url: str
    proof_status: str = "unknown"  # "proven", "statement_only", or "unknown"


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


def _proof_status_detect(statement: str) -> str:
    """Detect whether a Lean declaration contains a real proof or is a stub.

    Returns:
      - "statement_only": contains `sorry` or is an `axiom`/`example` with no proof
      - "proven": has a proof body (no top-level sorry)
      - "unknown": couldn't determine
    """
    if not statement:
        return "unknown"
    # Check for top-level sorry (body is just `:= sorry` or `:= by sorry`)
    if re.search(r":=\s*(by\s+)?sorry\b", statement):
        return "statement_only"
    # Check for axiom
    if re.search(r"\baxiom\b", statement.split("\n")[0] if "\n" in statement else statement):
        return "statement_only"
    # Has a proof body (not just `:=` with nothing after)
    if re.search(r":=\s*(by\b|fun\b|match\b|calc\b|refine\b|apply\b|intro\b|\{)|\n\s*\w", statement):
        return "proven"
    return "unknown"


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

    IMPORTANTE (FIX 2): Leandex v2 NO proporciona puntajes de similitud reales.
    No inventamos scores sintéticos. Si la API no devuelve similarity, el campo
    queda como None y se registra en el log.

    FIX 3: Cada match se inspecciona para detectar si contiene 'sorry' o es
    un 'axiom' (proof_status = "statement_only"). Los matches statement_only
    se reportan pero no cuentan como "encontrado en el corpus formal".
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

        # Try to extract similarity from API (Leandex v1 compat)
        raw_similarity = (
            entry.get("similarity")
            or entry.get("score")
            or entry.get("relevance")
        )
        similarity = None
        if raw_similarity is not None:
            try:
                similarity = float(raw_similarity)
            except (TypeError, ValueError):
                pass
        # Leandex v2: no scores — similarity stays None, no synthetic proxy.

        statement_str = str(statement)
        proof_status = _proof_status_detect(statement_str)

        matches.append(
            MathlibMatch(
                lean_name=str(lean_name),
                statement=statement_str,
                similarity=similarity,
                url=_mathlib_url(str(lean_name)),
                proof_status=proof_status,
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
        return {"matches": [], "error": str(exc)}

    events = _parse_sse(response.text)
    matches = _extract_matches(events)
    # Log if all matches have None similarity (Leandex v2, expected)
    if matches and all(m.similarity is None for m in matches):
        logger.info("Leandex: %d matches returned, no similarity scores (Leandex v2)", len(matches))
    return {
        "matches": [asdict(m) for m in matches],
    }


def check_in_mathlib(block: Dict[str, Any], use_cache: bool = True) -> MathlibResult:
    """Search the block in Mathlib via Leandex.

    A match counts as 'found' only if it has a proven proof_status
    (not statement_only) and Leandex returned a similarity score
    above SIMILARITY_THRESHOLD.  In Leandex v2 (no scores), we
    log a warning and set found=False — the user must interpret
    the match list manually.
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
    if not matches:
        return MathlibResult(found=False, matches=[], best_similarity=0.0)

    # Filter to proven matches only
    proven = [m for m in matches if m.proof_status == "proven"]
    # Determine found status: need a proven match with real similarity > threshold
    found = False
    best_sim = 0.0
    for m in proven:
        if m.similarity is not None:
            if m.similarity >= SIMILARITY_THRESHOLD:
                found = True
            best_sim = max(best_sim, m.similarity)
    # If no scores available (Leandex v2), best_similarity is 0.0
    if all(m.similarity is None for m in proven):
        logger.info(
            "Leandex: %d proven matches but no similarity scores available. "
            "Returning found=False for manual review. Matches: %s",
            len(proven),
            [m.lean_name for m in proven],
        )

    return MathlibResult(
        found=found,
        matches=matches,  # return ALL matches (including statement_only, for reporting)
        best_similarity=best_sim,
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
