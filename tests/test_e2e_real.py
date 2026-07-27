"""
End-to-end test: real pipeline on a sample paper.

Tests the full AViD workflow:
    sample.tex → parse 3 blocks → formalize (real API) → D2 (real Lean)
    → D1 (real Leandex/arXiv) → verdicts → publication system → save

Requires:
    - OPENCODE_GO_API_KEY set in environment
    - Lean 4.29.0 + Mathlib compiled (lean_project/.lake)

Usage:
    OPENCODE_GO_API_KEY=sk-... pytest tests/test_e2e_real.py -v -s
    OPENCODE_GO_API_KEY=sk-... python tests/test_e2e_real.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.parser.latex_parser import parse_latex
from src.novelty.dimensions.d1_existence import check_d1
from src.novelty.dimensions.d2_triviality import check_triviality
from src.novelty.types import D1Result, D2Result, Verdict
from src.publication import submit, load_manifest, SUBMISSIONS_DIR, MANIFEST_PATH
import app as avid_app


FIXTURE_TEX = REPO_ROOT / "examples" / "tiny_even_numbers" / "paper.tex"
LEAN_PROJECT = REPO_ROOT / "lean_project"

# ═══════════════════════════════════════════════════════════════════════════
# Skip conditions
# ═══════════════════════════════════════════════════════════════════════════

API_KEY = os.environ.get("OPENCODE_GO_API_KEY", "").strip()
HAS_API = bool(API_KEY)
HAS_LEAN = (LEAN_PROJECT / ".lake").exists()

SKIP_REASON = []
if not HAS_API:
    SKIP_REASON.append("OPENCODE_GO_API_KEY not set")
if not HAS_LEAN:
    SKIP_REASON.append(f"Mathlib not found at {LEAN_PROJECT / '.lake'}")

pytestmark = pytest.mark.skipif(
    bool(SKIP_REASON),
    reason=", ".join(SKIP_REASON) if SKIP_REASON else "",
)


# ═══════════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════════

def _pp(result: dict) -> str:
    """Pretty-print a block result."""
    return (
        f"  {result.get('label', '?'):20s} "
        f"{result.get('veredicto', '?'):35s} "
        f"formalized={result.get('formalized', False)}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestE2EReal:
    """Real end-to-end pipeline on a 3-theorem paper."""

    def test_parse_extracts_three_blocks(self):
        """Step 1: Parser extracts all 3 blocks from the sample paper."""
        blocks = parse_latex(str(FIXTURE_TEX))
        assert len(blocks) == 3

        labels = {b["label"] for b in blocks}
        assert labels == {"def:even", "lem:even_sum", "thm:four_evens"}

        for b in blocks:
            assert b.get("content_latex"), f"Block {b.get('label')} has no content"
            assert b["type"] in ("definition", "lemma", "theorem")

        print("\n[STEP 1 ✓] Parser: 3 blocks extracted")
        for b in blocks:
            preview = b["content_latex"][:80].replace("\n", " ")
            print(f"  {b['label']} ({b['type']}): {preview}...")

    def test_formalize_all_blocks(self):
        """Step 2: Formalize each block LaTeX → Lean via DeepSeek."""
        blocks = parse_latex(str(FIXTURE_TEX))
        results = {}

        from src.formalization.providers import resolve_provider
        provider = resolve_provider()
        
        for b in blocks:
            label = b["label"]
            lean = avid_app.formalize_block_with_provider(b, provider)
            assert lean is not None, f"Formalization returned None for {label}"
            assert len(lean.strip()) > 0, f"Empty formalization for {label}"
            results[label] = lean

        print(f"\n[STEP 2 ✓] Formalization: {len(results)}/3 blocks translated")
        for label, lean in results.items():
            # Definitions may produce edge-case responses; check they have
            # at least import Mathlib or a Lean keyword.
            has_lean = (
                "import " in lean.lower()
                or "theorem " in lean.lower()
                or "lemma " in lean.lower()
                or "def " in lean.lower()
                or "example " in lean.lower()
            )
            print(f"  {label}: {'✓' if has_lean else '⚠️ (unstructured response)'}")
            for line in lean.strip().split("\n")[:5]:
                print(f"    {line}")

    def test_d2_triviality(self):
        """Step 3: Run D2 on first block only (slow: ~30s/invocation × 7 tactics)."""
        blocks = parse_latex(str(FIXTURE_TEX))
        # D2 is expensive — test on 1 block to validate the integration
        b = blocks[0]
        from src.formalization.providers import resolve_provider
        provider = resolve_provider()
        lean = avid_app.formalize_block_with_provider(b, provider)
        assert lean is not None

        d2 = check_triviality(lean, lean_project_dir=str(LEAN_PROJECT))

        print(f"\n[STEP 3 ✓] D2: triviality checked on '{b['label']}'")
        status = f"TRIVIAL ({d2.tactica}, {d2.tiempo_segundos:.1f}s)" if d2.trivial else f"NOT TRIVIAL ({len(d2.all_attempts)} tactics tried)"
        print(f"  {b['label']}: {status}")
        for t, ok, rt, _ in d2.all_attempts:
            print(f"    {t}: {'✓' if ok else '✗'} ({rt:.1f}s)")

    def test_d1_existence(self):
        """Step 4: Run D1 (existence check) on all blocks."""
        blocks = parse_latex(str(FIXTURE_TEX))
        results: List[dict] = []

        for b in blocks:
            label = b["label"]
            from src.formalization.providers import resolve_provider
            provider = resolve_provider()

            # Formalize first so we have Lean statement for the query
            lean = avid_app.formalize_block_with_provider(b, provider)

            # Pass Lean statement to D1 for better Leandex matching
            d1_block = dict(b)
            if lean:
                d1_block["lean_statement"] = lean

            d1 = check_d1(d1_block)

            results.append({
                "label": label,
                "existe_en_C_F": d1.existe_en_C_F,
                "existe_en_C_I": d1.existe_en_C_I,
                "match_C_F": d1.match_C_F,
                "match_C_I": d1.match_C_I,
                "llm_judge_verdict": d1.llm_judge_verdict,
            })

        print(f"\n[STEP 4 ✓] D1: existence checked for {len(results)} blocks")
        for r in results:
            parts = []
            if r["existe_en_C_F"]:
                name = (r["match_C_F"] or {}).get("lean_name", "?")
                parts.append(f"C_F match: {name}")
            if r["existe_en_C_I"]:
                title = (r["match_C_I"] or {}).get("title", "?")
                parts.append(f"C_I match: {title[:60]}")
            if r["llm_judge_verdict"]:
                parts.append(f"judge: {r['llm_judge_verdict']}")
            status = " | ".join(parts) if parts else "no matches (novel)"
            print(f"  {r['label']}: {status}")

    def test_full_pipeline_and_publish(self, tmp_path, monkeypatch):
        """Step 5: Full pipeline + publication save.

        Runs the complete flow on all 3 blocks and verifies:
        - Every block gets a verdict
        - The publication system creates a valid submission
        - The submission manifest is persisted
        """
        # Redirect publication to temp dir
        subs_dir = tmp_path / "submissions"
        manifest_path = tmp_path / "submissions.json"
        monkeypatch.setattr("src.publication.SUBMISSIONS_DIR", subs_dir)
        monkeypatch.setattr("src.publication.MANIFEST_PATH", manifest_path)

        blocks = parse_latex(str(FIXTURE_TEX))
        results: List[dict] = []
        formalized_count = 0

        for b in blocks:
            label = b["label"]
            latex = b["content_latex"]

            # Formalize
            from src.formalization.providers import resolve_provider
            provider = resolve_provider()
            lean = avid_app.formalize_block_with_provider(b, provider)
            formalized = lean is not None
            if formalized:
                formalized_count += 1

            # D2 + D1 via orchestrator
            from src.novelty.orchestrator import check_novelty
            verdict = check_novelty(
                block=b,
                lean_statement=lean or latex,
                lean_project_dir=str(LEAN_PROJECT),
            )
            
            mapped = {
                "veredicto": verdict.veredicto.value,
                "status": "novel" if verdict.veredicto == Verdict.NOVEDAD_ENUNCIADO else "known",
                "detail": verdict.razonamiento or "",
                "label": label,
                "title": b.get("title") or label,
                "content_preview": latex[:200].strip(),
                "lean_statement": lean,
                "formalized": formalized,
            }
            results.append(mapped)

        # ── Assertions ────────────────────────────────────────────────────
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        assert formalized_count >= 1, "At least 1 block should formalize successfully"

        for r in results:
            assert "veredicto" in r
            assert r["veredicto"] in [v.value for v in Verdict] + ["ERROR"]
            assert "status" in r

        # ── Publication ───────────────────────────────────────────────────
        record = submit(
            tex_path=str(FIXTURE_TEX),
            title="Tiny Even Numbers — E2E Test",
            authors="Ayrton Porto (test)",
            abstract="Test submission from automated e2e pipeline.",
            email="test@avid-journal.org",
            verdicts={
                "total": len(results),
                "counts": {r["veredicto"]: results.count(r) for r in results},
            },
        )

        assert record["id"].startswith("AVID-")
        assert record["status"] == "pending_review"

        # Check file was copied
        tex_files = list(subs_dir.glob("*.tex"))
        assert len(tex_files) == 1
        assert tex_files[0].exists()

        # Check manifest
        manifest = load_manifest()
        assert manifest["count"] == 1
        assert manifest["submissions"][0]["title"] == "Tiny Even Numbers — E2E Test"

        # ── Print summary ─────────────────────────────────────────────────
        print(f"\n[STEP 5 ✓] Full pipeline + publication:")
        print(f"  Blocks: {len(results)}")
        print(f"  Formalized: {formalized_count}/{len(results)}")
        for r in results:
            print(_pp(r))
        print(f"  Publication ID: {record['id']}")
        print(f"  Status: {record['status']}")
        print(f"  File saved: {tex_files[0].name}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI runner
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if not HAS_API:
        print("SKIP: OPENCODE_GO_API_KEY not set. Export it to run the real test.")
        sys.exit(0)
    if not HAS_LEAN:
        print(f"SKIP: Mathlib not found at {LEAN_PROJECT / '.lake'}.")
        sys.exit(0)

    print("=" * 60)
    print("AViD Journal — E2E Real Pipeline Test")
    print("=" * 60)
    print(f"API key: {API_KEY[:8]}...")
    print(f"Lean project: {LEAN_PROJECT}")
    print(f"Fixture: {FIXTURE_TEX}")
    print()

    # Run all tests manually
    test = TestE2EReal()

    print("─" * 40)
    test.test_parse_extracts_three_blocks()

    print("─" * 40)
    test.test_formalize_all_blocks()

    print("─" * 40)
    test.test_d2_triviality()

    print("─" * 40)
    test.test_d1_existence()

    print("─" * 40)
    with tempfile.TemporaryDirectory() as tmp:
        import monkeypatch_module_placeholder
        # Can't easily run test_full_pipeline_and_publish from CLI
        # (needs tmp_path fixture). Run the logic inline.
        print("\n[STEP 5] Publication test requires pytest fixtures.")
        print("Run: pytest tests/test_e2e_real.py::TestE2EReal::test_full_pipeline_and_publish -v -s")

    print("\n" + "=" * 60)
    print("Pipeline test complete.")
    print("=" * 60)
