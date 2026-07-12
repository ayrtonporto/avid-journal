"""Tests for premise_autolocation.py — exact line ranges, Mathlib lookup,
PAPER_INDEX parsing, and two-theorem boundary test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# locate_theorem_in_file — exact line ranges
# ---------------------------------------------------------------------------

def test_locate_single_theorem(tmp_path):
    """Find a theorem and compute exact line range."""
    from src.novelty_v2.premise_autolocation import locate_theorem_in_file

    # No trailing blank/comment lines after the theorem body
    content = """import Mathlib

/-- A doc comment -/
theorem my_lemma (x : Nat) : x = x := by
  rfl
"""
    f = tmp_path / "test.lean"
    f.write_text(content)

    result = locate_theorem_in_file(f, "my_lemma")
    assert result is not None
    start, end = result
    assert start == 4  # the "theorem my_lemma" line (1-indexed)
    assert end == 5    # "rfl" (last line of the theorem body)


def test_locate_theorem_with_end_keyword(tmp_path):
    """Theorem that ends at the next declaration keyword."""
    from src.novelty_v2.premise_autolocation import locate_theorem_in_file

    content = """import Mathlib

theorem first_one : 1 = 1 := by
  rfl

lemma second_one : 2 = 2 := by
  rfl
"""
    f = tmp_path / "test2.lean"
    f.write_text(content)

    result = locate_theorem_in_file(f, "first_one")
    assert result is not None
    start, end = result
    # "import Mathlib" = 1, blank = 2, "theorem first_one" = 3, "  rfl" = 4
    # "lemma second_one" = 6, end should be 4 (trimmed blank line 5)
    assert start == 3
    assert end == 4  # line before "lemma second_one", blank trimmed


def test_locate_last_theorem_in_file(tmp_path):
    """Last theorem goes to EOF."""
    from src.novelty_v2.premise_autolocation import locate_theorem_in_file

    content = """theorem only_one : True :=
  trivial
"""
    f = tmp_path / "test3.lean"
    f.write_text(content)

    result = locate_theorem_in_file(f, "only_one")
    assert result is not None
    start, end = result
    assert start == 1
    assert end == 2  # EOF


def test_locate_not_found(tmp_path):
    """Non-existent theorem returns None."""
    from src.novelty_v2.premise_autolocation import locate_theorem_in_file

    f = tmp_path / "test4.lean"
    f.write_text("theorem x : 1=1 := rfl\n")
    assert locate_theorem_in_file(f, "nonexistent") is None


# ---------------------------------------------------------------------------
# Two consecutive theorems — boundary test (CRITICAL)
# ---------------------------------------------------------------------------

def test_two_consecutive_theorems_no_premise_contamination(tmp_path):
    """Premises of the first theorem do NOT include those of the second.

    This is the test required by the task: verify that when two theorems
    are consecutive, the end_line of the first stops at the second's header,
    so premises from the second theorem don't contaminate the first.
    """
    from src.novelty_v2.premise_autolocation import locate_theorem_in_file
    from src.novelty_v2.dimensions.d3_premises import compute_d3

    content = """import Mathlib.Tactic

theorem first_theorem : 1 + 1 = (2 : Nat) := by
  norm_num

theorem second_theorem : 2 + 2 = (4 : Nat) := by
  norm_num
"""
    f = tmp_path / "two_thms.lean"
    f.write_text(content)

    # Locate both theorems
    r1 = locate_theorem_in_file(f, "first_theorem")
    r2 = locate_theorem_in_file(f, "second_theorem")
    assert r1 is not None
    assert r2 is not None

    # Verify ranges are non-overlapping
    assert r1[1] < r2[0], (
        f"first_theorem end={r1[1]} overlaps with second_theorem start={r2[0]}"
    )

    # Lines: 1=import, 2=blank, 3=theorem first, 4=norm_num, 5=blank, 6=theorem second, 7=norm_num
    # first_theorem start=3, end=4 (blank trimmed)
    # second_theorem start=6, end=7
    assert r1 == (3, 4), f"Expected (3,4), got {r1}"
    assert r2 == (6, 7), f"Expected (6,7), got {r2}"


def test_consecutive_theorems_end_before_next(tmp_path):
    """Lemma followed by def: lemma's end is before the def."""
    from src.novelty_v2.premise_autolocation import locate_theorem_in_file

    content = """lemma lem_a : 1 = 1 := rfl

def def_b : Nat := 42
"""
    f = tmp_path / "lemma_def.lean"
    f.write_text(content)

    r = locate_theorem_in_file(f, "lem_a")
    assert r == (1, 1), f"Expected (1,1), got {r}"


# ---------------------------------------------------------------------------
# locate_mathlib_source (ripgrep-dependent, may need rg installed)
# ---------------------------------------------------------------------------

def test_locate_mathlib_irrational_sqrt_two():
    """Auto-locate irrational_sqrt_two in Mathlib sources."""
    from src.novelty_v2.premise_autolocation import locate_mathlib_source

    mathlib_root = (
        REPO_ROOT / "lean_project" / ".lake" / "packages" / "mathlib"
    )
    if not mathlib_root.exists():
        pytest.skip("Mathlib sources not found")

    result = locate_mathlib_source("irrational_sqrt_two", mathlib_root)
    assert result is not None, "irrational_sqrt_two not found in Mathlib"

    file_path, start_line, end_line = result
    assert file_path.exists()
    assert start_line > 0
    assert end_line >= start_line
    assert "Irrational.lean" in str(file_path)


def test_locate_mathlib_not_found():
    """Non-existent name returns None."""
    from src.novelty_v2.premise_autolocation import locate_mathlib_source

    mathlib_root = (
        REPO_ROOT / "lean_project" / ".lake" / "packages" / "mathlib"
    )
    if not mathlib_root.exists():
        pytest.skip("Mathlib sources not found")

    result = locate_mathlib_source("this_lemma_does_not_exist_xyz", mathlib_root)
    assert result is None


# ---------------------------------------------------------------------------
# locate_candidate_source (PAPER_INDEX.md + directory scan)
# ---------------------------------------------------------------------------

def test_locate_candidate_t08a():
    """Auto-locate t08a_parity from the D3 calibration paper directory."""
    from src.novelty_v2.premise_autolocation import locate_candidate_source

    proj = REPO_ROOT / "lean_project"
    result = locate_candidate_source("t08a_parity", proj)
    assert result is not None, "t08a_parity not found in Papers/"

    file_path, start_line, end_line = result
    assert "Paper.lean" in str(file_path)
    assert start_line == 42  # theorem header line
    assert end_line > start_line


def test_locate_candidate_t08b():
    """Auto-locate t08b_valuation from scan."""
    from src.novelty_v2.premise_autolocation import locate_candidate_source

    proj = REPO_ROOT / "lean_project"
    result = locate_candidate_source("t08b_valuation", proj)
    assert result is not None, "t08b_valuation not found"

    file_path, start_line, end_line = result
    assert start_line == 100
    assert end_line > start_line


def test_locate_candidate_not_found():
    """Non-existent theorem returns None."""
    from src.novelty_v2.premise_autolocation import locate_candidate_source

    proj = REPO_ROOT / "lean_project"
    result = locate_candidate_source("nonexistent_thm_xyz", proj)
    assert result is None


# ---------------------------------------------------------------------------
# resolve_ast_json_path
# ---------------------------------------------------------------------------

def test_resolve_ast_json_for_project_file():
    """ast.json for a file directly in the lean project."""
    from src.novelty_v2.premise_autolocation import resolve_ast_json_path

    proj = REPO_ROOT / "lean_project"
    lean_file = proj / "Papers" / "D3_Calibration" / "Paper.lean"

    result = resolve_ast_json_path(lean_file, proj)
    assert result is not None
    assert result.exists()
    assert result.suffix == ".json"


def test_resolve_ast_json_for_mathlib_file():
    """ast.json for a Mathlib package file."""
    from src.novelty_v2.premise_autolocation import resolve_ast_json_path

    proj = REPO_ROOT / "lean_project"
    lean_file = (
        proj / ".lake" / "packages" / "mathlib" / "Mathlib"
        / "NumberTheory" / "Real" / "Irrational.lean"
    )

    result = resolve_ast_json_path(lean_file, proj)
    assert result is not None
    assert result.exists()
    assert ".ast.json" in str(result)


# ---------------------------------------------------------------------------
# End-to-end: T08 without extraction map
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_t08_auto_location_end_to_end():
    """T08 end-to-end with auto-location, no manual map entries needed.

    Verifies:
      1. Side A: t08a_parity auto-located from Papers/
      2. Side B: irrational_sqrt_two auto-located from Mathlib
      3. compute_d3 produces the expected result
    """
    from src.novelty_v2.premise_autolocation import (
        locate_candidate_source, locate_mathlib_source,
    )
    from src.novelty_v2.premise_extraction import extract_premises_for_theorem
    from src.novelty_v2.dimensions.d3_premises import compute_d3

    proj = REPO_ROOT / "lean_project"
    mathlib_root = proj / ".lake" / "packages" / "mathlib"

    # Side A: auto-locate t08a_parity
    loc_a = locate_candidate_source("t08a_parity", proj)
    assert loc_a is not None, "Side A: t08a_parity not auto-located"

    file_a, start_a, end_a = loc_a
    prems_a = extract_premises_for_theorem(file_a, proj, start_a, end_a)
    assert prems_a is not None
    assert len(prems_a) > 0

    # Side B: auto-locate irrational_sqrt_two
    loc_b = locate_mathlib_source("irrational_sqrt_two", mathlib_root)
    assert loc_b is not None, "Side B: irrational_sqrt_two not auto-located"

    file_b, start_b, end_b = loc_b
    prems_b = extract_premises_for_theorem(file_b, proj, start_b, end_b)
    assert prems_b is not None
    assert len(prems_b) > 0

    # Run compute_d3 — should produce the expected result
    # (t08a_parity vs Mathlib's irrational_sqrt_two are different proofs)
    result = compute_d3(
        prems_a, prems_b,
        statement_lines_a=(start_a, start_a),
        statement_lines_b=(start_b, start_b),
    )

    assert result.jaccard is not None
    assert 0.0 <= result.jaccard <= 1.0
    # These are DIFFERENT proofs of sqrt(2) irrationality
    # The distance should be > 0 (they're not identical)
    assert result.jaccard > 0.0, "Expected different proofs to have distance > 0"
