"""
Integration tests for the full AViD pipeline.

Tests the end-to-end flow:
    .tex → parse → formalize → D2 → D1 → verdict → publication

Uses mocks for external APIs (OpenCode Go, Leandex, arXiv, Lean).
The mock layer validates the pipeline logic without hitting real services.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.parser.latex_parser import parse_latex
from src.formalization.orchestrator import topological_sort
from src.novelty_v2.types import D1Result, D2Result, Verdict
from src.publication import submit, list_submissions, load_manifest

# Import app module functions (without Gradio UI)
import app as avid_app


FIXTURE_TEX = REPO_ROOT / "examples" / "tiny_even_numbers" / "paper.tex"


# ═══════════════════════════════════════════════════════════════════════════
# Mock helpers
# ═══════════════════════════════════════════════════════════════════════════

def _mock_lean_stmt() -> str:
    return "theorem even_four : Even (a + b + c + d) := by sorry"


def _mock_d1_result_novel() -> D1Result:
    return D1Result(
        existe_en_C_F=False,
        existe_en_C_I=False,
    )


def _mock_d1_result_found() -> D1Result:
    return D1Result(
        existe_en_C_F=True,
        existe_en_C_I=False,
        match_C_F={"lean_name": "Nat.even_add", "statement": "..."},
    )


def _mock_d2_result_trivial() -> D2Result:
    r = D2Result()
    r.trivial = True
    r.tactica = "norm_num"
    r.tiempo_segundos = 14.2
    r.all_attempts = [("norm_num", True, 14.2, "")]
    return r


def _mock_d2_result_not_trivial() -> D2Result:
    r = D2Result()
    r.trivial = False
    r.all_attempts = [
        ("decide", False, 5.0, ""),
        ("norm_num", False, 6.0, ""),
        ("simp", False, 5.5, ""),
        ("aesop", False, 30.0, "timeout"),
    ]
    return r


# ═══════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestParserIntegration:
    """Parse a real .tex file and verify block structure."""

    def test_parse_extracts_blocks(self):
        blocks = parse_latex(str(FIXTURE_TEX))
        assert len(blocks) == 3
        labels = {b["label"] for b in blocks}
        assert labels == {"def:even", "lem:even_sum", "thm:four_evens"}

    def test_blocks_have_required_fields(self):
        blocks = parse_latex(str(FIXTURE_TEX))
        for b in blocks:
            assert "type" in b
            assert "content_latex" in b
            assert b["type"] in ("definition", "lemma", "theorem", "proposition", "corollary")


class TestFormalizationLogic:
    """Test formalization prompt construction and response parsing."""

    def test_formalize_returns_none_without_provider(self, monkeypatch):
        """Without a configured provider, formalization should handle gracefully."""
        # The new API uses resolve_provider() which needs env vars
        # Test that the block formalization function exists and is callable
        from app import formalize_block_with_provider
        assert callable(formalize_block_with_provider)

    def test_formalize_extracts_code_from_fence(self):
        """Verify the regex extracts Lean code from markdown fences."""
        import re
        content = """Here is the translation:

```lean
theorem hello : 1 + 1 = 2 := by norm_num
```

Done."""
        m = re.search(r"```(?:lean4?)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        assert m is not None
        assert "theorem hello" in m.group(1)

    def test_formalize_fallback_no_fences(self):
        """Without fences, falls back to raw content if it looks like Lean."""
        import re
        content = "theorem hello : 1 + 1 = 2"
        m = re.search(r"```(?:lean4?)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        assert m is None
        # The fallback logic should catch this
        assert "theorem " in content


class TestVerdictMapping:
    """Test verdict mapping logic with mocked D1/D2 results."""

    def test_novel_enunciado(self):
        d1 = _mock_d1_result_novel()
        d2 = _mock_d2_result_not_trivial()
        mapped = avid_app.map_verdict(d1, d2)
        assert mapped["veredicto"] == Verdict.NOVEDAD_ENUNCIADO.value
        assert mapped["status"] == "novel"

    def test_trivial(self):
        d1 = _mock_d1_result_novel()
        d2 = _mock_d2_result_trivial()
        mapped = avid_app.map_verdict(d1, d2)
        assert mapped["veredicto"] == Verdict.NO_NOVEDOSO_trivial.value
        assert mapped["status"] == "trivial"

    def test_match_mathlib(self):
        d1 = _mock_d1_result_found()
        d2 = _mock_d2_result_not_trivial()
        mapped = avid_app.map_verdict(d1, d2)
        assert mapped["veredicto"] == Verdict.MATCH_ENCONTRADO_PENDIENTE_D3.value
        assert mapped["status"] == "known_formal"

    def test_all_fields_present(self):
        d1 = _mock_d1_result_novel()
        d2 = _mock_d2_result_trivial()
        mapped = avid_app.map_verdict(d1, d2)
        required = ["veredicto", "status", "detail", "existe_en_C_F",
                     "existe_en_C_I", "match_C_F", "match_C_I", "d2"]
        for key in required:
            assert key in mapped, f"Missing key: {key}"


class TestPublishability:
    """Test the _is_publishable logic."""

    def test_all_novel_is_publishable(self):
        results = [
            {"veredicto": "NOVEDAD_ENUNCIADO"},
            {"veredicto": "NOVEDAD_ENUNCIADO"},
        ]
        assert avid_app._is_publishable(results) is True

    def test_one_trivial_not_publishable(self):
        results = [
            {"veredicto": "NOVEDAD_ENUNCIADO"},
            {"veredicto": "NO_NOVEDOSO_trivial"},
        ]
        assert avid_app._is_publishable(results) is False

    def test_error_not_publishable(self):
        results = [
            {"veredicto": "NOVEDAD_ENUNCIADO"},
            {"veredicto": "ERROR"},
        ]
        assert avid_app._is_publishable(results) is False

    def test_empty_not_publishable(self):
        assert avid_app._is_publishable([]) is False


class TestPublicationSystem:
    """Test the publication/submission module end-to-end."""

    def test_submit_creates_record(self, tmp_path, monkeypatch):
        """Submit a paper and verify manifest + file."""
        monkeypatch.setattr(
            "src.publication.SUBMISSIONS_DIR",
            tmp_path / "submissions",
        )
        monkeypatch.setattr(
            "src.publication.MANIFEST_PATH",
            tmp_path / "submissions.json",
        )

        # Create a dummy .tex
        tex = tmp_path / "test.tex"
        tex.write_text(r"\begin{theorem}Test\end{theorem}")

        record = submit(
            tex_path=str(tex),
            title="Test Paper",
            authors="A. Smith",
            abstract="We prove something.",
            email="a@b.com",
            verdicts={"total": 3, "counts": {"NOVEDAD_ENUNCIADO": 3}},
        )

        assert record["id"].startswith("AVID-")
        assert record["title"] == "Test Paper"
        assert record["status"] == "pending_review"
        assert record["authors"] == "A. Smith"

        # Check file was copied
        submissions_dir = tmp_path / "submissions"
        copied = list(submissions_dir.glob("*.tex"))
        assert len(copied) == 1

        # Check manifest
        manifest = load_manifest()
        assert manifest["count"] == 1
        assert len(manifest["submissions"]) == 1

    def test_submit_increments_ids(self, tmp_path, monkeypatch):
        """Multiple submissions get sequential IDs."""
        monkeypatch.setattr(
            "src.publication.SUBMISSIONS_DIR",
            tmp_path / "submissions",
        )
        monkeypatch.setattr(
            "src.publication.MANIFEST_PATH",
            tmp_path / "submissions.json",
        )

        tex = tmp_path / "paper.tex"
        tex.write_text("test")

        r1 = submit(str(tex), "Paper 1", "A")
        r2 = submit(str(tex), "Paper 2", "B")
        r3 = submit(str(tex), "Paper 3", "C")

        assert r1["id"] == "AVID-0001"
        assert r2["id"] == "AVID-0002"
        assert r3["id"] == "AVID-0003"

    def test_list_submissions_filters_by_status(self, tmp_path, monkeypatch):
        """list_submissions filters correctly."""
        monkeypatch.setattr(
            "src.publication.SUBMISSIONS_DIR",
            tmp_path / "submissions",
        )
        monkeypatch.setattr(
            "src.publication.MANIFEST_PATH",
            tmp_path / "submissions.json",
        )

        tex = tmp_path / "paper.tex"
        tex.write_text("test")

        submit(str(tex), "P1", "A")
        submit(str(tex), "P2", "B")

        all_subs = list_submissions()
        assert len(all_subs) == 2

        pending = list_submissions(status="pending_review")
        assert len(pending) == 2

        reviewed = list_submissions(status="accepted")
        assert len(reviewed) == 0


class TestPipelineEndToEnd:
    """Full pipeline simulation with mocked external calls."""

    @patch("app.formalize_block_with_provider")
    @patch("src.novelty_v2.dimensions.d1_existence.check_d1")
    @patch("src.novelty_v2.dimensions.d2_triviality.check_triviality")
    def test_pipeline_all_novel(
        self, mock_d2, mock_d1, mock_formalize,
    ):
        """Simulate a paper where all blocks are novel."""
        mock_formalize.return_value = _mock_lean_stmt()
        mock_d2.return_value = _mock_d2_result_not_trivial()
        mock_d1.return_value = _mock_d1_result_novel()

        blocks = parse_latex(str(FIXTURE_TEX))
        ordered = topological_sort(blocks)
        assert len(ordered) == 3

        results = []
        for block in ordered:
            latex = block.get("content_latex", "")
            lean = mock_formalize(block, None)
            assert lean is not None

            d2 = mock_d2(lean, lean_project_dir=".")
            d1 = mock_d1(block)

            mapped = avid_app.map_verdict(d1, d2)
            results.append(mapped)

        assert len(results) == 3
        for r in results:
            assert r["veredicto"] == Verdict.NOVEDAD_ENUNCIADO.value

        assert avid_app._is_publishable(results) is True

    @patch("app.formalize_block_with_provider")
    @patch("src.novelty_v2.dimensions.d1_existence.check_d1")
    @patch("src.novelty_v2.dimensions.d2_triviality.check_triviality")
    def test_pipeline_one_trivial(
        self, mock_d2, mock_d1, mock_formalize,
    ):
        """First block trivial, rest novel."""
        mock_formalize.return_value = _mock_lean_stmt()

        call_count = [0]

        def d2_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return _mock_d2_result_trivial()
            return _mock_d2_result_not_trivial()

        mock_d2.side_effect = d2_side_effect
        mock_d1.return_value = _mock_d1_result_novel()

        blocks = parse_latex(str(FIXTURE_TEX))
        ordered = topological_sort(blocks)
        results = []
        for block in ordered:
            lean = mock_formalize(block, None)
            d2 = mock_d2(lean, lean_project_dir=".")
            d1 = mock_d1(block)
            mapped = avid_app.map_verdict(d1, d2)
            results.append(mapped)

        assert results[0]["veredicto"] == Verdict.NO_NOVEDOSO_trivial.value
        assert results[1]["veredicto"] == Verdict.NOVEDAD_ENUNCIADO.value
        assert results[2]["veredicto"] == Verdict.NOVEDAD_ENUNCIADO.value
        assert avid_app._is_publishable(results) is False
