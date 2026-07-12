#!/usr/bin/env python
"""Probe script: compara Semantic Scholar vs TheoremSearch para D1-informal.

Toma enunciados de teoremas hardcodeados, consulta AMBAS fuentes y muestra
una comparación lado a lado en consola.

Asegura que el pipeline de AViD pueda consumir TheoremSearch como fuente
adicional con el mismo contrato que Semantic Scholar.

Uso:
    python scripts/probe_theoremsearch.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List

# Asegurar que la raíz del repo está en sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.novelty.arxiv_search import PaperCandidate, search_semantic_scholar
from src.novelty.theoremsearch import search_theoremsearch

# ── Teoremas de prueba ─────────────────────────────────────────────────────
# TODO: pegar tus propios enunciados aquí.
# Cada entrada es (label, query_text).
TEST_THEOREMS = [
    (
        "T01 — sqrt(2) irrational",
        "the square root of 2 is irrational",
    ),
    (
        "T02 — Cauchy-Schwarz",
        "Cauchy-Schwarz inequality in inner product spaces",
    ),
    (
        "T03 — Heine-Cantor",
        "every continuous function on a compact set is uniformly continuous",
    ),
    # TODO: agregar más teoremas de interés
    # (
    #     "T04 — ...",
    #     "...",
    # ),
]

TOP_K = 5
TRUNCATE_ABSTRACT = 200


# ── Helpers ─────────────────────────────────────────────────────────────────

def _truncate(text: str, max_len: int) -> str:
    """Trunca `text` a `max_len` caracteres, agregando '…' si se corta."""
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"


def _format_candidate(idx: int, cand: PaperCandidate) -> str:
    """Formatea un PaperCandidate para display en consola."""
    aid = cand.arxiv_id or "(no arXiv ID)"
    title = _truncate(cand.title, 60)
    abstract = _truncate(cand.abstract or "(no abstract)", TRUNCATE_ABSTRACT)
    return (
        f"  {idx}. [{cand.similarity_score:.3f}] {title}\n"
        f"     arXiv: {aid}  |  source: {cand.source}\n"
        f"     {abstract}"
    )


def _search_with_timing(
    query: str,
    top_k: int,
    label: str,
) -> tuple[List[PaperCandidate], float]:
    """Ejecuta una búsqueda y devuelve (resultados, tiempo_en_segundos)."""
    t0 = time.monotonic()
    try:
        if label == "Semantic Scholar":
            results = search_semantic_scholar(query, top_k=top_k, use_cache=False)
        else:
            results = search_theoremsearch(query, top_k=top_k, use_cache=False)
    except Exception as exc:
        print(f"  [ERROR] {label} search failed: {exc}")
        results = []
    elapsed = time.monotonic() - t0
    return results, elapsed


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    # Configurar encoding para Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

    total_ss = 0
    total_ts = 0
    total_ss_time = 0.0
    total_ts_time = 0.0

    for theorem_label, query in TEST_THEOREMS:
        print(f"\n{'='*72}")
        print(f"  {theorem_label}")
        print(f"  Query: {query}")
        print(f"{'='*72}")

        # ── Semantic Scholar ──────────────────────────────────────────────
        print(f"\n  ── Semantic Scholar (top {TOP_K}) ──")
        ss_results, ss_time = _search_with_timing(query, TOP_K, "Semantic Scholar")
        if ss_results:
            for i, cand in enumerate(ss_results[:TOP_K], 1):
                print(_format_candidate(i, cand))
        else:
            print("  (no results)")
        print(f"  ⏱  {ss_time:.2f}s  |  {len(ss_results)} resultados totales")

        # ── TheoremSearch ─────────────────────────────────────────────────
        print(f"\n  ── TheoremSearch (top {TOP_K}) ──")
        ts_results, ts_time = _search_with_timing(query, TOP_K, "TheoremSearch")
        if ts_results:
            for i, cand in enumerate(ts_results[:TOP_K], 1):
                print(_format_candidate(i, cand))
        else:
            print("  (no results)")
        print(f"  ⏱  {ts_time:.2f}s  |  {len(ts_results)} resultados totales")

        total_ss += len(ss_results)
        total_ts += len(ts_results)
        total_ss_time += ss_time
        total_ts_time += ts_time

    # ── Resumen final ─────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print(f"  RESUMEN")
    print(f"{'='*72}")
    print(f"  Fuente            | Resultados | Tiempo total")
    print(f"  ------------------+------------+-------------")
    print(f"  Semantic Scholar  | {total_ss:>10} | {total_ss_time:.2f}s")
    print(f"  TheoremSearch     | {total_ts:>10} | {total_ts_time:.2f}s")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
