"""Tests for proof extraction in informal_match.py.

Verifies the two-capas approach:
  1. Statement-based matching (not position-based)
  2. Safety net (low confidence → None)
  3. Real cases from arXiv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Synthetic LaTeX tests
# ---------------------------------------------------------------------------

def test_lemma_proof_then_theorem_proof_selects_correct_one():
    """Bug case: lemma→proof→theorem→proof. Asking for the theorem
    must return the THEOREM's proof, not the lemma's."""
    from src.novelty_v2.informal_match import _extract_proof_block

    tex = r"""
\begin{lemma}[Auxiliary result]
For all x, P(x) holds.
\end{lemma}
\begin{proof}
This is the lemma proof. It uses induction.
\end{proof}

\begin{theorem}[Main result]
For all x, Q(x) implies P(x).
\end{theorem}
\begin{proof}
This is the theorem proof. Apply the lemma.
\end{proof}
"""
    # Ask for the theorem
    result = _extract_proof_block(tex, "Q(x) implies P(x)")
    assert result is not None, "Should find the theorem's proof"
    assert "theorem proof" in result.lower(), (
        f"Expected theorem proof, got: {result[:100]}"
    )
    assert "lemma proof" not in result.lower(), (
        "Should NOT return the lemma's proof"
    )


def test_no_proof_between_two_environments():
    """Theorem env followed by another env with no proof in between → None."""
    from src.novelty_v2.informal_match import _extract_proof_block

    tex = r"""
\begin{theorem}[No proof theorem]
Something interesting.
\end{theorem}

\begin{lemma}[Next lemma]
Another result.
\end{lemma}
\begin{proof}
Proof of the lemma, not the theorem.
\end{proof}
"""
    result = _extract_proof_block(tex, "Something interesting")
    assert result is None, (
        "Should return None: theorem has no proof (next env appears before any proof)"
    )


def test_statement_not_found_returns_none():
    """Statement hint that doesn't match any theorem body → None."""
    from src.novelty_v2.informal_match import _extract_proof_block

    tex = r"""
\begin{theorem}[Some theorem]
All triangles have three sides.
\end{theorem}
\begin{proof}
Trivial.
\end{proof}
"""
    result = _extract_proof_block(tex, "quantum entanglement in Hilbert spaces")
    assert result is None, "Should return None: statement doesn't match"


def test_empty_hint_returns_first_proof():
    """With no statement hint, return the first proof found."""
    from src.novelty_v2.informal_match import _extract_proof_block

    tex = r"""
\begin{theorem}[First]
A.
\end{theorem}
\begin{proof}
Proof of first.
\end{proof}

\begin{theorem}[Second]
B.
\end{theorem}
\begin{proof}
Proof of second.
\end{proof}
"""
    result = _extract_proof_block(tex, "")
    assert result is not None
    assert "Proof of first" in result


def test_partial_word_overlap_sufficient():
    """Partial word overlap above threshold should still match."""
    from src.novelty_v2.informal_match import _extract_proof_block

    tex = r"""
\begin{theorem}[Prime numbers]
There are infinitely many prime numbers in the set of natural numbers.
\end{theorem}
\begin{proof}
Euclid's classic proof...
\end{proof}
"""
    # Statement hint has some different words but core overlap
    result = _extract_proof_block(tex, "infinitely many primes exist")
    assert result is not None
    assert "Euclid" in result


def test_normalize_tex_strips_commands():
    """_normalize_tex removes LaTeX commands for comparison."""
    from src.novelty_v2.informal_match import _normalize_tex

    tex = r"\mathbb{N} and \sqrt{2} is \frac{a}{b}"
    result = _normalize_tex(tex)
    # Should have stripped commands, kept arguments roughly
    assert "mathbb" not in result
    assert "sqrt" not in result
    assert "frac" not in result


def test_word_overlap_identical():
    from src.novelty_v2.informal_match import _word_overlap

    assert _word_overlap("infinitely many primes", "infinitely many primes") == 1.0


def test_word_overlap_partial():
    from src.novelty_v2.informal_match import _word_overlap

    score = _word_overlap("infinitely many prime numbers exist",
                          "there are infinitely many primes")
    # "infinitely" and "many" and "prime"/"primes" overlap
    assert 0.2 < score < 0.9


def test_word_overlap_no_match():
    from src.novelty_v2.informal_match import _word_overlap

    assert _word_overlap("quantum physics", "prime numbers") == 0.0


# ---------------------------------------------------------------------------
# Proof delegation flag
# ---------------------------------------------------------------------------

def test_short_proof_gets_delegation_flag():
    """Proof < 400 chars with \ref{} gets the flag."""
    from src.novelty_v2.informal_match import _check_proof_delegation

    short_proof = r"Direct consequence of Lemma~\ref{lem:cauchy} and \cite{author}."
    assert _check_proof_delegation(short_proof) is True


def test_long_substantial_proof_no_flag():
    """Proof > 400 chars without heavy delegation gets no flag."""
    from src.novelty_v2.informal_match import _check_proof_delegation

    long_proof = (
        "We proceed by induction on n. "
        + "For the base case n=0, the result is trivial. "
        + "For the inductive step, assume the statement holds for n. "
        + "Then we compute f(n+1) = f(n) + g(n) by the recurrence relation. "
        + "By the induction hypothesis, f(n) satisfies the bound. "
        + "Adding g(n) preserves the inequality because g is non-negative. "
        + "Therefore the statement holds for n+1, completing the induction. "
    ) * 5  # ~500+ chars
    assert _check_proof_delegation(long_proof) is False


def test_proof_with_delegation_words_flagged():
    """Proof with many 'follows from' / 'Lemma' references."""
    from src.novelty_v2.informal_match import _check_proof_delegation

    proof = ("follows from Lemma A. follows from Corollary B. "
             "by the previous result. immediate from Lemma C. "
             "trivial. obvious. ") * 10  # many delegation words, < 400 chars
    assert _check_proof_delegation(proof) is True


# ---------------------------------------------------------------------------
# Real case: arXiv 1303.0730 (should still work)
# ---------------------------------------------------------------------------

def test_real_arxiv_1303_0730_primes_proof():
    """The infinitude of primes proof is correctly extracted."""
    import tempfile
    from src.novelty_v2.informal_match import (
        _download_arxiv_source, _find_main_tex, _extract_proof_block,
    )

    cache = Path(tempfile.gettempdir()) / "avid_informal_cache"
    cache.mkdir(exist_ok=True)

    src = _download_arxiv_source("1303.0730", cache)
    if src is None:
        pytest.skip("arXiv source unavailable")
    tex = _find_main_tex(src)
    assert tex is not None

    content = tex.read_text(encoding="utf-8", errors="replace")
    proof = _extract_proof_block(
        content, "There are infinitely many prime numbers",
    )
    assert proof is not None, "Should find the primes proof"
    assert len(proof) > 500, f"Proof too short: {len(proof)} chars"
    assert "prime" in proof.lower()


# ---------------------------------------------------------------------------
# Real case: arXiv 1607.03618 (the bug case)
# ---------------------------------------------------------------------------

def test_real_arxiv_1607_03618_not_caught_by_lemma():
    """The extractor should NOT return a lemma's proof when asking for
    Cauchy-Schwarz. It should either return the correct short proof
    or None (safety net)."""
    import tempfile
    from src.novelty_v2.informal_match import (
        _download_arxiv_source, _find_main_tex, _extract_proof_block,
    )

    cache = Path(tempfile.gettempdir()) / "avid_informal_cache"
    cache.mkdir(exist_ok=True)

    src = _download_arxiv_source("1607.03618", cache)
    if src is None:
        pytest.skip("arXiv source unavailable")
    tex = _find_main_tex(src)
    assert tex is not None

    content = tex.read_text(encoding="utf-8", errors="replace")

    # The OLD behavior returned a lemma's proof (supremum, ~1224 chars).
    # The NEW behavior should either:
    #   (a) return the correct Cauchy-Schwarz proof, OR
    #   (b) return None (safety net, statement not well-matched)
    proof = _extract_proof_block(
        content, "Cauchy-Schwarz inequality in inner product spaces",
    )

    if proof is None:
        # (b) is acceptable — safety net triggered
        return

    # If we got a proof, it must NOT be the supremum lemma
    # (which talks about "supremum", "upper bound", "L-eps")
    assert "supremum" not in proof.lower() or len(proof) < 300, (
        f"Got the wrong proof (supremum lemma): {proof[:150]}"
    )
    assert "Cauchy" in proof.lower() or "schwarz" in proof.lower(), (
        f"Proof doesn't mention Cauchy-Schwarz: {proof[:150]}"
    )
