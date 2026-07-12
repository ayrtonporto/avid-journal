"""Tests for premise_extraction.py — cache, subprocess mock, degradation.

Markers:
  - slow: tests that run real ExtractData (requires lean_project with Mathlib)
  - wsl: not used (ExtractData runs on Windows natively)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_premise(full_name: str, line: int = 10) -> dict:
    """Create a minimal premise dict for testing."""
    return {
        "fullName": full_name,
        "modName": "Mathlib.Test",
        "defPath": f"Mathlib/Test/{full_name}.lean",
        "defPos": {"line": 1, "column": 0},
        "pos": {"line": line, "column": 0},
    }


def _hash_file(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        sha.update(fh.read())
    return sha.hexdigest()


# ---------------------------------------------------------------------------
# Cache hit tests
# ---------------------------------------------------------------------------

def test_cache_hit_returns_cached_without_subprocess(tmp_path):
    """When cache exists, result is returned without invoking subprocess."""
    from src.novelty_v2.premise_extraction import (
        extract_premises, _cache_path, _write_cache,
    )

    # Create a fake .lean file
    lean_file = tmp_path / "test.lean"
    lean_file.write_text("import Mathlib.Tactic\n\ntheorem foo : 1+1=2 := by rfl\n")

    # Create a fake lean_project with ExtractData.lean
    proj = tmp_path / "lean_project"
    proj.mkdir()
    (proj / "ExtractData.lean").write_text("-- stub")

    # Plant cached premises
    file_hash = _hash_file(lean_file)
    cached_premises = [_make_premise("Nat.add_comm", 3), _make_premise("rfl", 4)]
    cp = _cache_path(proj, file_hash)
    cp.parent.mkdir(parents=True, exist_ok=True)
    _write_cache(cp, cached_premises)

    # Call extract_premises — should be cache hit
    with mock.patch("subprocess.run") as mock_run:
        result = extract_premises(lean_file, proj)

    # Verify: subprocess was NOT called
    mock_run.assert_not_called()
    assert result is not None
    assert len(result) == 2
    assert result[0]["fullName"] == "Nat.add_comm"
    assert result[1]["fullName"] == "rfl"


def test_cache_hit_instant(tmp_path):
    """Cache hit returns in << 1 second."""
    import time
    from src.novelty_v2.premise_extraction import (
        extract_premises, _cache_path, _write_cache,
    )

    lean_file = tmp_path / "test2.lean"
    lean_file.write_text("theorem bar : True := trivial\n")

    proj = tmp_path / "lean_proj"
    proj.mkdir()
    (proj / "ExtractData.lean").write_text("-- stub")

    file_hash = _hash_file(lean_file)
    cached = [_make_premise("trivial", 1)]
    cp = _cache_path(proj, file_hash)
    cp.parent.mkdir(parents=True, exist_ok=True)
    _write_cache(cp, cached)

    t0 = time.monotonic()
    result = extract_premises(lean_file, proj)
    elapsed = time.monotonic() - t0

    assert result is not None
    assert elapsed < 0.5, f"Cache hit took {elapsed:.2f}s — expected <0.5s"


# ---------------------------------------------------------------------------
# Subprocess failure → None (no exception)
# ---------------------------------------------------------------------------

def test_subprocess_failure_returns_none(tmp_path):
    """When subprocess fails, returns None without raising."""
    from src.novelty_v2.premise_extraction import extract_premises

    lean_file = tmp_path / "fail.lean"
    lean_file.write_text("import Mathlib\n")

    proj = tmp_path / "lean_proj2"
    proj.mkdir()
    # NO ExtractData.lean → should fail at file-exists check
    # But we want to test subprocess failure specifically
    (proj / "ExtractData.lean").write_text("-- stub")

    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = OSError("Simulated subprocess crash")
        result = extract_premises(lean_file, proj, timeout=10)

    assert result is None  # Never raises
    mock_run.assert_called_once()


def test_timeout_returns_none(tmp_path):
    """When subprocess times out, returns None without raising."""
    import subprocess
    from src.novelty_v2.premise_extraction import extract_premises

    lean_file = tmp_path / "timeout.lean"
    lean_file.write_text("import Mathlib\n")

    proj = tmp_path / "lean_proj3"
    proj.mkdir()
    (proj / "ExtractData.lean").write_text("-- stub")

    # Ensure no cache hit
    # (different file → different hash → cache miss)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["lake"], timeout=5,
            output=b"partial stdout", stderr=b"partial stderr",
        )
        result = extract_premises(lean_file, proj, timeout=5)

    assert result is None  # Never raises


def test_missing_file_returns_none():
    """Non-existent .lean file → None."""
    from src.novelty_v2.premise_extraction import extract_premises

    result = extract_premises(
        "/nonexistent/path/file.lean",
        "/nonexistent/proj",
    )
    assert result is None


def test_missing_extractdata_returns_none(tmp_path):
    """Project without ExtractData.lean → None."""
    from src.novelty_v2.premise_extraction import extract_premises

    lean_file = tmp_path / "test.lean"
    lean_file.write_text("theorem x : 1=1 := rfl\n")

    proj = tmp_path / "no_extract"
    proj.mkdir()
    # No ExtractData.lean created

    result = extract_premises(lean_file, proj)
    assert result is None


# ---------------------------------------------------------------------------
# Corrupt cache → re-extract
# ---------------------------------------------------------------------------

def test_corrupt_cache_triggers_reextraction(tmp_path):
    """JSON malformed in cache → ignored, subprocess is called."""
    from src.novelty_v2.premise_extraction import (
        extract_premises, _cache_path,
    )

    lean_file = tmp_path / "corrupt_test.lean"
    lean_file.write_text("theorem c : 1=1 := rfl\n")

    proj = tmp_path / "lean_proj4"
    proj.mkdir()
    (proj / "ExtractData.lean").write_text("-- stub")

    # Plant corrupt cache
    file_hash = _hash_file(lean_file)
    cp = _cache_path(proj, file_hash)
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text("this is not valid json {{{")

    # Mock subprocess to return success and simulate ast.json generation
    with mock.patch("subprocess.run") as mock_run:
        # Simulate successful extraction that would produce premises
        mock_run.return_value = mock.Mock(
            returncode=0, stdout="ok", stderr="",
        )
        # Also need to mock the ast.json reading — the extraction
        # would fail at "ast.json not found" after subprocess.
        # For this test, we just verify subprocess WAS called
        # (meaning corrupt cache was ignored).
        result = extract_premises(lean_file, proj, timeout=5)

    # Subprocess should have been called (corrupt cache ignored)
    mock_run.assert_called_once()
    # Result may be None if ast.json path resolution fails,
    # but we're testing that the corrupt cache doesn't crash


# ---------------------------------------------------------------------------
# extract_premises_for_theorem filters by line range
# ---------------------------------------------------------------------------

def test_extract_for_theorem_filters_by_line(tmp_path):
    """extract_premises_for_theorem applies line range filter correctly."""
    from src.novelty_v2.premise_extraction import (
        extract_premises, extract_premises_for_theorem,
        _cache_path, _write_cache,
    )

    lean_file = tmp_path / "filter_test.lean"
    lean_file.write_text("-- dummy\n" * 20)

    proj = tmp_path / "lean_proj5"
    proj.mkdir()
    (proj / "ExtractData.lean").write_text("-- stub")

    # Plant cache with premises at various lines
    file_hash = _hash_file(lean_file)
    all_premises = [
        _make_premise("stmt_type", 1),     # statement
        _make_premise("lemma_a", 5),        # proof
        _make_premise("lemma_b", 8),        # proof
        _make_premise("lemma_c", 15),       # proof
    ]
    cp = _cache_path(proj, file_hash)
    cp.parent.mkdir(parents=True, exist_ok=True)
    _write_cache(cp, all_premises)

    # Extract with filter: lines 5-10
    result = extract_premises_for_theorem(lean_file, proj, 5, 10)

    assert result is not None
    names = {p["fullName"] for p in result}
    assert names == {"lemma_a", "lemma_b"}
    assert "stmt_type" not in names  # filtered (line 1)
    assert "lemma_c" not in names     # filtered (line 15)


# ---------------------------------------------------------------------------
# SHA256 determinism
# ---------------------------------------------------------------------------

def test_sha256_deterministic(tmp_path):
    """Same content → same hash."""
    from src.novelty_v2.premise_extraction import _sha256_hex

    f1 = tmp_path / "a.lean"
    f2 = tmp_path / "b.lean"
    content = "theorem x : 1=1 := rfl\n"
    f1.write_text(content)
    f2.write_text(content)

    assert _sha256_hex(f1) == _sha256_hex(f2)


def test_sha256_different_for_different_content(tmp_path):
    """Different content → different hash."""
    from src.novelty_v2.premise_extraction import _sha256_hex

    f1 = tmp_path / "c.lean"
    f2 = tmp_path / "d.lean"
    f1.write_text("theorem x : 1=1 := rfl\n")
    f2.write_text("theorem x : 2=2 := rfl\n")

    assert _sha256_hex(f1) != _sha256_hex(f2)


# ---------------------------------------------------------------------------
# Integration: real extraction (slow)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_real_extraction_t08a():
    """Real extraction of T08a from Paper.lean via ExtractData.

    Requires lean_project with Mathlib compiled and ExtractData.lean.
    """
    from src.novelty_v2.premise_extraction import extract_premises_for_theorem

    proj = REPO_ROOT / "lean_project"
    lean_file = proj / "Papers" / "D3_Calibration" / "Paper.lean"

    if not lean_file.exists() or not (proj / "ExtractData.lean").exists():
        pytest.skip("lean_project not available")

    # Extract T08a (lines 42-91)
    result = extract_premises_for_theorem(lean_file, proj, 42, 91)

    assert result is not None, "Extraction returned None"
    assert len(result) > 0, "No premises extracted"

    # Verify the premises can be used with compute_d3 and produce 0.7222
    from src.novelty_v2.dimensions.d3_premises import compute_d3

    # Extract T08b for comparison
    result_b = extract_premises_for_theorem(lean_file, proj, 100, 158)
    assert result_b is not None
    assert len(result_b) > 0

    d3 = compute_d3(
        result, result_b,
        statement_lines_a=(42, 42),
        statement_lines_b=(100, 100),
    )

    assert d3.jaccard is not None
    assert d3.jaccard == pytest.approx(0.7222, abs=1e-4), (
        f"Expected 0.7222, got {d3.jaccard:.6f}"
    )
    assert d3.intersection_size == 5
    assert d3.union_size == 18


@pytest.mark.slow
def test_real_extraction_cache_hit_second_call():
    """Second call to extract_premises should be a cache hit (instant)."""
    import time
    from src.novelty_v2.premise_extraction import extract_premises

    proj = REPO_ROOT / "lean_project"
    lean_file = proj / "Papers" / "D3_Calibration" / "Paper.lean"

    if not lean_file.exists() or not (proj / "ExtractData.lean").exists():
        pytest.skip("lean_project not available")

    # First call may be cache hit or fresh extraction
    result1 = extract_premises(lean_file, proj)
    assert result1 is not None

    # Second call MUST be cache hit (< 1 second)
    t0 = time.monotonic()
    result2 = extract_premises(lean_file, proj)
    elapsed = time.monotonic() - t0

    assert result2 is not None
    assert len(result2) == len(result1)
    assert elapsed < 1.0, f"Second call took {elapsed:.2f}s — expected cache hit"
