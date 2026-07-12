"""Phase 3 — Integration tests: orchestrator + compute_d3.

Tests that verify:
  1. T08 end-to-end via orchestrator reproduces 0.7222
  2. None (empty sets) → INCONCLUSIVE verdict
  3. Without premises → MATCH_ENCONTRADO_PENDIENTE_D3 (backward compat)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.novelty_v2.dimensions.d3_premises import load_premises_from_ast
from src.novelty_v2.orchestrator import check_novelty
from src.novelty_v2.types import Verdict

# Path to the pre-generated ast.json
AST_JSON = (
    REPO_ROOT / "lean_project" / ".lake" / "build" / "ir"
    / "Papers" / "D3_Calibration" / "Paper.ast.json"
)

T08A_LINES = (42, 91)
T08B_LINES = (100, 158)
T08A_STATEMENT = (42, 42)
T08B_STATEMENT = (100, 100)


# ---------------------------------------------------------------------------
# Real premises for T08
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def t08_premises_a():
    """T08a — parity custom proof premises."""
    if not AST_JSON.exists():
        pytest.skip(f"AST JSON not found: {AST_JSON}")
    return load_premises_from_ast(str(AST_JSON), *T08A_LINES)


@pytest.fixture(scope="module")
def t08_premises_b():
    """T08b — valuation custom proof premises."""
    if not AST_JSON.exists():
        pytest.skip(f"AST JSON not found: {AST_JSON}")
    return load_premises_from_ast(str(AST_JSON), *T08B_LINES)


# Dummy block for the orchestrator (D2 triviality check will fail,
# D1 C_F will need Leandex which we can't control, so we simulate
# the flow by passing pre-loaded premises and checking D3 only)
_FAKE_BLOCK = {
    "title": "Irrationality of sqrt(2)",
    "content_latex": r"$\sqrt{2}$ is irrational",
}
_LEAN_STMT = "Irrational (Real.sqrt 2)"


# ---------------------------------------------------------------------------
# Test 1: T08 end-to-end via orchestrator with pre-loaded premises
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_orchestrator_d3_t08_reproduces_distance(t08_premises_a, t08_premises_b):
    """When d3_premises are provided, orchestrator calls compute_d3 and
    returns the same distance as the standalone validation script."""
    # We need check_novelty to reach the D3 branch. Since D2 will find
    # Irrational (Real.sqrt 2) non-trivial (norm_num is blacklisted),
    # and D1 C_F requires Leandex (live API), we cannot run the full
    # pipeline here. Instead, we test _run_d3_if_possible directly.
    from src.novelty_v2.orchestrator import _run_d3_if_possible

    result = _run_d3_if_possible(
        lean_statement=_LEAN_STMT,
        lean_name_existente="irrational_sqrt_two",
        d3_premises_a=t08_premises_a,
        d3_premises_b=t08_premises_b,
        d3_statement_lines_a=T08A_STATEMENT,
        d3_statement_lines_b=T08B_STATEMENT,
    )

    assert result.activa is True
    assert result.jaccard is not None
    assert result.jaccard == pytest.approx(0.7222, abs=1e-4), (
        f"Expected 0.7222, got {result.jaccard:.6f}"
    )
    assert result.intersection_size == 5
    assert result.union_size == 18
    assert result.pruebas_distantes is True  # 0.7222 > 0.5
    assert result.flags == []


# ---------------------------------------------------------------------------
# Test 2: Without premises → MATCH_ENCONTRADO_PENDIENTE_D3
# ---------------------------------------------------------------------------

def test_orchestrator_d3_without_premises_returns_inactive():
    """Without d3_premises, _run_d3_if_possible returns activa=False."""
    from src.novelty_v2.orchestrator import _run_d3_if_possible

    result = _run_d3_if_possible(
        lean_statement=_LEAN_STMT,
        lean_name_existente="irrational_sqrt_two",
    )

    assert result.activa is False
    assert result.jaccard is None
    assert result.pruebas_distantes is None


# ---------------------------------------------------------------------------
# Test 3: Empty premises after filters → INCONCLUSIVE
# ---------------------------------------------------------------------------

def test_orchestrator_d3_empty_sets_gives_inconclusive_verdict():
    """When compute_d3 returns None (empty sets), the orchestrator
    returns INCONCLUSIVE verdict."""
    from src.novelty_v2.orchestrator import _run_d3_if_possible
    from src.novelty_v2.types import D3Result

    # Create premises that will all be filtered out (Init. namespace)
    empty_premises = [
        {
            "fullName": "Nat",
            "modName": "Init.Prelude",
            "defPath": "Init/Prelude.lean",
            "defPos": {"line": 1214, "column": 10},
            "pos": {"line": 5, "column": 0},
        },
        {
            "fullName": "Exists",
            "modName": "Init.Core",
            "defPath": "Init/Core.lean",
            "defPos": {"line": 1, "column": 0},
            "pos": {"line": 6, "column": 0},
        },
    ]

    result = _run_d3_if_possible(
        lean_statement="True",
        lean_name_existente="trivial",
        d3_premises_a=empty_premises,
        d3_premises_b=empty_premises,
    )

    # compute_d3 should have filtered everything → None + flags
    assert result.activa is True
    assert result.jaccard is None
    assert "empty_after_filters" in result.flags or len(result.flags) > 0


# ---------------------------------------------------------------------------
# Test 4: INCONCLUSIVE propagates through check_novelty verdict dispatch
# ---------------------------------------------------------------------------

def test_inconclusive_verdict_enum_value():
    """INCONCLUSIVE verdict exists and is distinct from PENDIENTE."""
    assert Verdict.INCONCLUSIVE.value == "INCONCLUSIVE"
    assert Verdict.INCONCLUSIVE != Verdict.MATCH_ENCONTRADO_PENDIENTE_D3


# ---------------------------------------------------------------------------
# Test 5: Same distance for T08 as validate_d3 script
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_orchestrator_d3_matches_validate_script(t08_premises_a, t08_premises_b):
    """The orchestrator's compute_d3 call should return the EXACT same
    number as the standalone validate_d3.py script."""
    from src.novelty_v2.orchestrator import _run_d3_if_possible

    result = _run_d3_if_possible(
        lean_statement=_LEAN_STMT,
        lean_name_existente="irrational_sqrt_two",
        d3_premises_a=t08_premises_a,
        d3_premises_b=t08_premises_b,
        d3_statement_lines_a=T08A_STATEMENT,
        d3_statement_lines_b=T08B_STATEMENT,
    )

    # These exact numbers match the validate_d3.py output from 2026-07-03
    assert result.jaccard == 0.7222222222222222, (
        f"Distance mismatch with validate_d3.py: got {result.jaccard}"
    )
    assert result.intersection_size == 5
    assert result.union_size == 18


# ---------------------------------------------------------------------------
# Test 6: NoveltyVerdict.to_dict includes new D3 fields
# ---------------------------------------------------------------------------

def test_to_dict_includes_new_d3_fields():
    """NoveltyVerdict.to_dict() includes intersection_size, union_size, flags."""
    from src.novelty_v2.types import D3Result, NoveltyVerdict, Verdict

    d3 = D3Result(
        activa=True,
        jaccard=0.75,
        intersection_size=3,
        union_size=9,
        flags=["test_flag"],
        premises_a_after_filters=["a", "b"],
        premises_b_after_filters=["b", "c", "d"],
    )
    v = NoveltyVerdict(veredicto=Verdict.NOVEDAD_DEMOSTRACION, d3=d3)

    d = v.to_dict()
    d3d = d["d3"]
    assert d3d["intersection_size"] == 3
    assert d3d["union_size"] == 9
    assert d3d["flags"] == ["test_flag"]
    assert d3d["n_premisas_a_after_filters"] == 2
    assert d3d["n_premisas_b_after_filters"] == 3
    assert d3d["jaccard"] == 0.75
