"""Nivel 1 — Tests unitarios de Jaccard.

Verifica el cómputo de distancia de Jaccard sobre conjuntos fabricados a mano.
No requiere Lean, ExtractData, ni archivos externos.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.novelty_v2.dimensions.d3_premises import compute_d3


# ---------------------------------------------------------------------------
# Helper: build a premise dict
# ---------------------------------------------------------------------------

def _p(name: str, mod: str = "Mathlib.Test", dpath: str = "Test.lean",
      dline: int = 1, dcol: int = 0, pline: int = 10, pcol: int = 0) -> dict:
    """Create a minimal premise dict for testing."""
    return {
        "fullName": name,
        "modName": mod,
        "defPath": dpath,
        "defPos": {"line": dline, "column": dcol},
        "pos": {"line": pline, "column": pcol},
    }


# ---------------------------------------------------------------------------
# Identical sets → distance 0.0
# ---------------------------------------------------------------------------

def test_identical_sets_give_zero():
    prems = [
        _p("a", dpath="A.lean", dline=1),
        _p("b", dpath="B.lean", dline=1),
        _p("c", dpath="C.lean", dline=1),
    ]
    result = compute_d3(prems, prems)
    assert result.jaccard == 0.0
    assert result.intersection_size == 3
    assert result.union_size == 3
    assert result.flags == []


def test_identical_singleton():
    prems = [_p("x", dpath="X.lean", dline=5)]
    result = compute_d3(prems, prems)
    assert result.jaccard == 0.0
    assert result.intersection_size == 1
    assert result.union_size == 1


# ---------------------------------------------------------------------------
# Disjoint sets → distance 1.0
# ---------------------------------------------------------------------------

def test_disjoint_sets_give_one():
    a = [_p("x", dpath="X.lean", dline=1)]
    b = [_p("y", dpath="Y.lean", dline=1)]
    result = compute_d3(a, b)
    assert result.jaccard == 1.0
    assert result.intersection_size == 0
    assert result.union_size == 2
    assert result.flags == []


def test_disjoint_larger():
    a = [_p("a", dpath="A.lean", dline=1), _p("b", dpath="B.lean", dline=1)]
    b = [_p("c", dpath="C.lean", dline=1), _p("d", dpath="D.lean", dline=1)]
    result = compute_d3(a, b)
    assert result.jaccard == 1.0
    assert result.intersection_size == 0
    assert result.union_size == 4


# ---------------------------------------------------------------------------
# {a,b,c} vs {b,c,d} → distance 0.5
# ---------------------------------------------------------------------------

def test_partial_overlap_exact_half():
    a = [
        _p("a", dpath="A.lean", dline=1),
        _p("b", dpath="B.lean", dline=1),
        _p("c", dpath="C.lean", dline=1),
    ]
    b = [
        _p("b", dpath="B.lean", dline=1),
        _p("c", dpath="C.lean", dline=1),
        _p("d", dpath="D.lean", dline=1),
    ]
    result = compute_d3(a, b)
    assert result.jaccard == 0.5
    assert result.intersection_size == 2
    assert result.union_size == 4


# ---------------------------------------------------------------------------
# Empty sets → None + flag (no exception, no crash)
# ---------------------------------------------------------------------------

def test_one_empty_set():
    a: list = []
    b = [_p("x", dpath="X.lean", dline=1)]
    result = compute_d3(a, b)
    assert result.jaccard is None
    assert "empty_a_after_filters" in result.flags
    assert result.intersection_size == 0
    assert result.union_size == 1


def test_both_empty_sets():
    a: list = []
    b: list = []
    result = compute_d3(a, b)
    assert result.jaccard is None
    assert "empty_after_filters" in result.flags
    assert result.intersection_size == 0
    assert result.union_size == 0


def test_filtered_to_empty():
    """If filters remove all premises, result is None with flag."""
    a = [_p("x", dpath="X.lean", dline=1)]
    b = [_p("x", dpath="X.lean", dline=1)]
    # Use a blacklist that removes everything
    result = compute_d3(a, b, blacklist_config_path="/nonexistent/path.yaml")
    # Fallback blacklist is Init. and Lean. — these won't match Mathlib.Test
    # So they'll pass. Let's test with Init. premises instead.
    a_init = [_p("x", mod="Init.Prelude", dpath="Init.lean", dline=1)]
    b_init = [_p("y", mod="Init.Core", dpath="Init.lean", dline=2)]
    result2 = compute_d3(a_init, b_init)
    assert result2.jaccard is None
    assert "empty_after_filters" in result2.flags


# ---------------------------------------------------------------------------
# Symmetry
# ---------------------------------------------------------------------------

def test_symmetry():
    a = [
        _p("a", dpath="A.lean", dline=1),
        _p("b", dpath="B.lean", dline=1),
        _p("c", dpath="C.lean", dline=1),
    ]
    b = [
        _p("b", dpath="B.lean", dline=1),
        _p("d", dpath="D.lean", dline=1),
    ]
    r_ab = compute_d3(a, b)
    r_ba = compute_d3(b, a)
    assert r_ab.jaccard == r_ba.jaccard
    assert r_ab.intersection_size == r_ba.intersection_size
    assert r_ab.union_size == r_ba.union_size
    # 1 - 1/4 = 0.75
    assert r_ab.jaccard == 0.75


def test_symmetry_with_filters():
    """Symmetry with filters: swapping BOTH premise lists AND their
    statement line ranges should give the same result."""
    a = [
        _p("a", dpath="A.lean", dline=1, pline=5),   # proof body
        _p("stmt", dpath="S.lean", dline=1, pline=1),  # statement
    ]
    b = [
        _p("a", dpath="A.lean", dline=1, pline=5),
    ]
    r_ab = compute_d3(a, b, statement_lines_a=(1, 1), statement_lines_b=None)
    r_ba = compute_d3(b, a, statement_lines_a=None, statement_lines_b=(1, 1))
    assert r_ab.jaccard == r_ba.jaccard
    # After statement filter: a has 1 premise (a), b has 1 premise (a)
    # Same set → distance 0.0
    assert r_ab.jaccard == 0.0
