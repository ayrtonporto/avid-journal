"""Nivel 3 — Test de integración D3 con T08.

Ejecuta compute_d3 end-to-end sobre el par T08a/T08b del D3 Calibration Paper.
Marcado como 'slow' porque lee el archivo ast.json (4.6 MB).

Excluir de corridas rápidas con: pytest -m "not slow"
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.novelty.dimensions.d3_premises import (
    compute_d3,
    load_premises_from_ast,
)

# Path to the pre-generated ast.json
AST_JSON = (
    REPO_ROOT / "lean_project" / ".lake" / "build" / "ir"
    / "Papers" / "D3_Calibration" / "Paper.ast.json"
)

# Theorem line ranges in Paper.lean
T08A_LINES = (42, 91)
T08B_LINES = (100, 158)
T08A_STATEMENT = (42, 42)  # Just the type signature line
T08B_STATEMENT = (100, 100)


@pytest.mark.slow
class TestD3IntegrationT08:
    """Integration tests that read real ExtractData output."""

    @pytest.fixture(scope="class")
    def premises_a(self):
        if not AST_JSON.exists():
            pytest.skip(f"AST JSON not found: {AST_JSON}")
        return load_premises_from_ast(str(AST_JSON), *T08A_LINES)

    @pytest.fixture(scope="class")
    def premises_b(self):
        if not AST_JSON.exists():
            pytest.skip(f"AST JSON not found: {AST_JSON}")
        return load_premises_from_ast(str(AST_JSON), *T08B_LINES)

    def test_returns_valid_float(self, premises_a, premises_b):
        """compute_d3 on T08 E1/E2 returns a float between 0 and 1."""
        result = compute_d3(
            premises_a, premises_b,
            statement_lines_a=T08A_STATEMENT,
            statement_lines_b=T08B_STATEMENT,
        )
        assert result.jaccard is not None, f"Got None, flags={result.flags}"
        assert isinstance(result.jaccard, float)
        assert 0.0 <= result.jaccard <= 1.0
        assert result.intersection_size >= 0
        assert result.union_size > 0

    def test_determinism(self, premises_a, premises_b):
        """Two consecutive runs give exactly the same number."""
        r1 = compute_d3(
            premises_a, premises_b,
            statement_lines_a=T08A_STATEMENT,
            statement_lines_b=T08B_STATEMENT,
        )
        r2 = compute_d3(
            premises_a, premises_b,
            statement_lines_a=T08A_STATEMENT,
            statement_lines_b=T08B_STATEMENT,
        )
        assert r1.jaccard == r2.jaccard, (
            f"Non-deterministic: {r1.jaccard} != {r2.jaccard}"
        )
        assert r1.intersection_size == r2.intersection_size
        assert r1.union_size == r2.union_size
        assert r1.flags == r2.flags

    def test_genuinely_different_proofs_detected(self, premises_a, premises_b):
        """T08a (parity) and T08b (valuation) are genuinely distinct proofs.
        Jaccard distance should be substantially above 0."""
        result = compute_d3(
            premises_a, premises_b,
            statement_lines_a=T08A_STATEMENT,
            statement_lines_b=T08B_STATEMENT,
        )
        # The two proofs share setup lemmas (div_pow, Rat.num_div_den, etc.)
        # but diverge in their central strategies. Distance > 0.5 expected.
        assert result.jaccard is not None
        assert result.jaccard > 0.5, (
            f"Expected distance > 0.5 for distinct proofs, got {result.jaccard:.3f}"
        )
        # The intersection should be small relative to union
        assert result.intersection_size < result.union_size
        # At least 3 premises each after filters (they're non-trivial proofs)
        assert len(result.premises_a_after_filters) >= 3
        assert len(result.premises_b_after_filters) >= 3

    def test_self_comparison_gives_zero(self, premises_a):
        """Comparing a proof to itself should give distance 0."""
        result = compute_d3(
            premises_a, premises_a,
            statement_lines_a=T08A_STATEMENT,
            statement_lines_b=T08A_STATEMENT,
        )
        assert result.jaccard == 0.0

    def test_filters_not_empty(self, premises_a, premises_b):
        """After filters, neither set should be empty for non-trivial proofs."""
        result = compute_d3(
            premises_a, premises_b,
            statement_lines_a=T08A_STATEMENT,
            statement_lines_b=T08B_STATEMENT,
        )
        assert "empty_after_filters" not in result.flags, (
            "Both premise sets became empty after filters — check filter config"
        )
        assert result.premises_a_after_filters, "T08a premises empty after filters"
        assert result.premises_b_after_filters, "T08b premises empty after filters"
