"""Nivel 2 — Tests unitarios de filtros D3.

Verifica Filtro 1 (namespace blacklist) y Filtro 2 (statement premises)
con listas de premisas fabricadas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.novelty_v2.dimensions.d3_premises import (
    _canonical_id,
    _deduplicate,
    _filter1_blacklist,
    _filter2_statement,
    compute_d3,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _p(name: str, mod: str = "Mathlib.NumberTheory.Real.Irrational",
      dpath: str = "Mathlib/NumberTheory/Real/Irrational.lean",
      dline: int = 1, dcol: int = 0,
      pline: int = 10, pcol: int = 0) -> dict:
    """Create a minimal premise dict for testing."""
    return {
        "fullName": name,
        "modName": mod,
        "defPath": dpath,
        "defPos": {"line": dline, "column": dcol},
        "pos": {"line": pline, "column": pcol},
    }


# ---------------------------------------------------------------------------
# Filter 1 — Blacklist prefix matching
# ---------------------------------------------------------------------------

BLACKLIST = ["Init.", "Lean."]


def test_f1_removes_init_premises():
    premises = [
        _p("Nat", mod="Init.Prelude", dpath="Init/Prelude.lean"),
        _p("Exists", mod="Init.Core", dpath="Init/Core.lean"),
        _p("Irrational", mod="Mathlib.NumberTheory.Real.Irrational",
           dpath="Mathlib/NumberTheory/Real/Irrational.lean"),
    ]
    filtered = _filter1_blacklist(premises, BLACKLIST)
    names = {p["fullName"] for p in filtered}
    assert names == {"Irrational"}
    assert len(filtered) == 1


def test_f1_removes_lean_premises():
    premises = [
        _p("Parser", mod="Lean.Parser", dpath="Lean/Parser.lean"),
        _p("Irrational", mod="Mathlib.NumberTheory.Real.Irrational",
           dpath="Mathlib/NumberTheory/Real/Irrational.lean"),
    ]
    filtered = _filter1_blacklist(premises, BLACKLIST)
    names = {p["fullName"] for p in filtered}
    assert names == {"Irrational"}


def test_f1_keeps_mathlib_premises():
    premises = [
        _p("Nat.Prime", mod="Mathlib.Data.Nat.Prime.Defs",
           dpath="Mathlib/Data/Nat/Prime/Defs.lean"),
        _p("padicValNat.mul", mod="Mathlib.NumberTheory.Padics.PadicVal.Basic",
           dpath="Mathlib/NumberTheory/Padics/PadicVal/Basic.lean"),
        _p("Real.sqrt", mod="Mathlib.Data.Real.Sqrt",
           dpath="Mathlib/Data/Real/Sqrt.lean"),
    ]
    filtered = _filter1_blacklist(premises, BLACKLIST)
    assert len(filtered) == 3


def test_f1_typo_in_prefix_does_not_match():
    """'Iniit.' (typo) should NOT match 'Init.Prelude'."""
    premises = [
        _p("Nat", mod="Init.Prelude", dpath="Init/Prelude.lean"),
    ]
    # Use a typo blacklist
    filtered = _filter1_blacklist(premises, ["Iniit."])
    assert len(filtered) == 1  # Not filtered!

    # Verify with correct prefix
    filtered_correct = _filter1_blacklist(premises, ["Init."])
    assert len(filtered_correct) == 0  # Filtered


def test_f1_empty_blacklist_keeps_all():
    premises = [
        _p("Nat", mod="Init.Prelude", dpath="Init/Prelude.lean"),
        _p("Irrational", mod="Mathlib.NumberTheory.Real.Irrational",
           dpath="Mathlib/NumberTheory/Real/Irrational.lean"),
    ]
    filtered = _filter1_blacklist(premises, [])
    assert len(filtered) == 2


def test_f1_prefix_match_is_by_startswith():
    """Prefix matching uses str.startswith().

    'Init' DOES match 'Init.Prelude' (it's a prefix).
    'Iniit' (typo) does NOT.
    'InitPrelude' does NOT match prefix 'Init.' (no dot in source).
    """
    premises = [
        _p("Nat", mod="Init.Prelude", dpath="Init/Prelude.lean"),
    ]
    # "Init" is a valid prefix of "Init.Prelude"
    filtered = _filter1_blacklist(premises, ["Init"])
    assert len(filtered) == 0  # Filtered — "Init" IS prefix of "Init.Prelude"

    # "Init." is also a valid prefix
    filtered_dot = _filter1_blacklist(premises, ["Init."])
    assert len(filtered_dot) == 0  # Filtered

    # Typo "Iniit" does NOT match
    filtered_typo = _filter1_blacklist(premises, ["Iniit"])
    assert len(filtered_typo) == 1  # NOT filtered

    # "InitPrelude" source would NOT match prefix "Init."
    fake_premise = _p("Fake", mod="InitPrelude", dpath="Fake.lean")
    filtered_fake = _filter1_blacklist([fake_premise], ["Init."])
    assert len(filtered_fake) == 1  # NOT filtered — "InitPrelude" doesn't start with "Init."


# ---------------------------------------------------------------------------
# Filter 2 — Statement premises
# ---------------------------------------------------------------------------

def test_f2_removes_statement_premises():
    premises = [
        _p("Irrational", pline=1, pcol=10),   # statement line
        _p("Real.sqrt", pline=1, pcol=22),     # statement line
        _p("div_pow", pline=5, pcol=6),         # proof body
        _p("Nat.gcd", pline=12, pcol=4),        # proof body
    ]
    filtered = _filter2_statement(premises, (1, 1))
    names = {p["fullName"] for p in filtered}
    assert names == {"div_pow", "Nat.gcd"}


def test_f2_keeps_all_when_no_range():
    premises = [
        _p("Irrational", pline=1),
        _p("div_pow", pline=5),
    ]
    filtered = _filter2_statement(premises, None)
    assert len(filtered) == 2


def test_f2_range_inclusive():
    premises = [
        _p("a", pline=1),
        _p("b", pline=2),
        _p("c", pline=3),
        _p("d", pline=4),
    ]
    filtered = _filter2_statement(premises, (2, 3))
    names = {p["fullName"] for p in filtered}
    assert names == {"a", "d"}  # b and c are filtered


def test_f2_premises_without_pos_are_kept():
    """Premises with pos=None (e.g., Lean.Meta.Simp.Config) are kept by F2
    because they can't be attributed to the statement. F1 handles them."""
    premises = [
        {"fullName": "Lean.Meta.Simp.Config", "modName": "Init.MetaTypes",
         "defPath": "Init/MetaTypes.lean",
         "defPos": {"line": 213, "column": 10},
         "pos": None},  # No position
        _p("Real.sqrt", pline=1),
    ]
    filtered = _filter2_statement(premises, (1, 1))
    names = {p["fullName"] for p in filtered}
    # pos=None premise is KEPT (can't determine if it's in statement)
    assert "Lean.Meta.Simp.Config" in names
    assert "Real.sqrt" not in names  # filtered (in statement)


# ---------------------------------------------------------------------------
# Deduplication by (defPath, defPos)
# ---------------------------------------------------------------------------

def test_dedup_collapses_same_canonical_id():
    """Same defPath and defPos → same logical object → dedup to 1."""
    premises = [
        _p("Nat", dpath="Init/Prelude.lean", dline=1214, dcol=10, pline=25),
        _p("Nat", dpath="Init/Prelude.lean", dline=1214, dcol=10, pline=30),
        _p("Nat", dpath="Init/Prelude.lean", dline=1214, dcol=10, pline=42),
    ]
    result = _deduplicate(premises)
    assert len(result) == 1
    assert result[0]["pos"]["line"] == 25  # first occurrence kept


def test_dedup_keeps_distinct_definitions():
    """Same fullName but different defPath → different objects."""
    premises = [
        _p("foo", dpath="A.lean", dline=1, dcol=0),
        _p("foo", dpath="B.lean", dline=5, dcol=0),
    ]
    result = _deduplicate(premises)
    assert len(result) == 2


def test_canonical_id_format():
    p = _p("Nat", dpath="Init/Prelude.lean", dline=1214, dcol=10)
    cid = _canonical_id(p)
    assert cid == "Init/Prelude.lean:1214:10"


# ---------------------------------------------------------------------------
# Integration: filters applied in correct order inside compute_d3
# ---------------------------------------------------------------------------

def test_compute_d3_applies_both_filters_in_order():
    """End-to-end test with premises that exercise both filters."""
    a = [
        # Statement premise (should be filtered by F2)
        _p("Irrational", mod="Mathlib.NumberTheory.Real.Irrational",
           dpath="M/NT/Real/Irrational.lean", dline=10, dcol=4, pline=1),
        # Infrastructure (should be filtered by F1)
        _p("Nat", mod="Init.Prelude", dpath="Init/Prelude.lean",
           dline=1214, dcol=10, pline=5),
        # Genuine math premise
        _p("Prime.dvd_of_dvd_pow", mod="Mathlib.Algebra.Prime.Defs",
           dpath="Mathlib/Algebra/Prime/Defs.lean", dline=74, dcol=8, pline=8),
    ]
    b = [
        _p("padicValNat.mul", mod="Mathlib.NumberTheory.Padics.PadicVal.Basic",
           dpath="Mathlib/NT/Padics/PadicVal/Basic.lean", dline=375, dcol=18, pline=12),
        _p("Irrational", mod="Mathlib.NumberTheory.Real.Irrational",
           dpath="M/NT/Real/Irrational.lean", dline=10, dcol=4, pline=1),  # statement
    ]
    result = compute_d3(a, b, statement_lines_a=(1, 1), statement_lines_b=(1, 1))
    # After filters:
    #   a: only Prime.dvd_of_dvd_pow (Nat filtered by F1, Irrational by F2)
    #   b: only padicValNat.mul (Irrational filtered by F2)
    # Disjoint → distance 1.0
    assert result.jaccard == 1.0
    assert result.intersection_size == 0
    assert result.union_size == 2
    assert len(result.premises_a_after_filters) == 1
    assert len(result.premises_b_after_filters) == 1
