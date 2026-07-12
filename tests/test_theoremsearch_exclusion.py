"""Test self-exclusion in TheoremSearch — critical: D1 must not match the paper being evaluated.

Ensures that passing an arXiv ID in exclude_arxiv_ids actually filters out
results pointing to that paper, including old-style IDs like math/0604362.
"""

import os
import pytest
from src.novelty.theoremsearch import search_theoremsearch


@pytest.mark.live
def test_theoremsearch_self_exclusion_math0604362():
    """TheoremSearch self-exclusion works for old-style arXiv IDs.

    Queries with a statement from math/0604362v1, excludes its own ID,
    and verifies no result points back to it.
    """
    os.environ["THEOREMSEARCH_ENABLED"] = "1"

    query = (
        "eigenvalues of a finite irreducible Markov chain "
        "spectral lower bound total variation distance"
    )
    exclude = ["math/0604362v1", "math/0604362", "math/0604362v4"]

    results = search_theoremsearch(query, top_k=10, use_cache=False, exclude_arxiv_ids=exclude)

    # Check: no result should normalize to "0604362"
    from src.novelty.arxiv_search import _normalize_arxiv_id

    for cand in results:
        norm = _normalize_arxiv_id(cand.arxiv_id) if cand.arxiv_id else ""
        assert "0604362" not in (norm or ""), (
            f"Self-exclusion failed: result points to {cand.arxiv_id} "
            f"(normalized: {norm}) which matches excluded paper math/0604362"
        )


@pytest.mark.live
def test_theoremsearch_self_exclusion_new_format():
    """TheoremSearch self-exclusion works for new-format IDs."""
    os.environ["THEOREMSEARCH_ENABLED"] = "1"

    query = "sqrt(2) is irrational"
    exclude = ["0711.2941v2", "0711.2941v1", "0711.2941"]

    results = search_theoremsearch(query, top_k=10, use_cache=False, exclude_arxiv_ids=exclude)

    from src.novelty.arxiv_search import _normalize_arxiv_id

    for cand in results:
        norm = _normalize_arxiv_id(cand.arxiv_id) if cand.arxiv_id else ""
        assert "0711.2941" not in (norm or ""), (
            f"Self-exclusion failed: result points to {cand.arxiv_id} "
            f"which matches excluded paper 0711.2941"
        )
