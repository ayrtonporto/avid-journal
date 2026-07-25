"""Unit tests for the Lean REPL pool facade — pure logic only (no subprocess,
no Lean), so they run anywhere in the normal suite.

The end-to-end warm-REPL behaviour (real Mathlib, concurrency) is validated
separately since it needs a built REPL + compiled Mathlib.
"""

import os

import pytest

from src.lean_repl.pool import _resp_to_tuple, _neutralize_imports, pool_enabled


def test_neutralize_imports_preserves_line_count():
    # env 0 already has Mathlib; a stray `import` line in a REPL command is
    # illegal, so it must become a comment WITHOUT shifting line numbers.
    src = "import Mathlib\n\ndef PaperEven (n : Nat) : Prop := True"
    out = _neutralize_imports(src)
    assert out.split("\n")[0] == "--"
    assert len(out.split("\n")) == len(src.split("\n"))
    assert "import" not in out


def test_neutralize_imports_handles_narrow_and_indented():
    src = "  import Mathlib.Data.Real.Basic\nimport Mathlib.Tactic\ntheorem t : True := trivial"
    out = _neutralize_imports(src)
    lines = out.split("\n")
    assert lines[0] == "--" and lines[1] == "--"
    assert lines[2] == "theorem t : True := trivial"


def test_neutralize_imports_empty():
    assert _neutralize_imports("") == ""


def test_resp_valid_no_messages():
    he, hs, out, err = _resp_to_tuple({"env": 1, "messages": []})
    assert he is False
    assert hs is False
    assert out == ""
    assert err == ""


def test_resp_error_sets_has_error_and_formats_stdout():
    resp = {
        "env": 1,
        "messages": [
            {
                "severity": "error",
                "pos": {"line": 5, "column": 26},
                "data": "unsolved goals\n⊢ False",
            }
        ],
    }
    he, hs, out, err = _resp_to_tuple(resp)
    assert he is True
    assert hs is False
    # Lean-CLI-shaped so error_parser.parse_lean_errors consumes it unchanged,
    # newlines in the goal state flattened to keep one diagnostic per line.
    assert out == "repl.lean:5:26: error: unsolved goals ⊢ False"
    assert "\n" not in out


def test_resp_sorries_sets_has_sorry():
    resp = {
        "env": 1,
        "messages": [],
        "sorries": [{"pos": {"line": 5, "column": 8}, "goal": "n = n"}],
    }
    he, hs, out, err = _resp_to_tuple(resp)
    assert he is False
    assert hs is True
    assert "declaration uses 'sorry'" in out


def test_resp_sorry_via_message_data():
    resp = {
        "env": 1,
        "messages": [
            {"severity": "warning", "pos": {"line": 3, "column": 0},
             "data": "declaration uses 'sorry'"}
        ],
    }
    _, hs, _, _ = _resp_to_tuple(resp)
    assert hs is True


def test_resp_warning_only_is_not_error():
    resp = {
        "env": 1,
        "messages": [
            {"severity": "warning", "pos": {"line": 1, "column": 0}, "data": "unused variable"}
        ],
    }
    he, hs, _, _ = _resp_to_tuple(resp)
    assert he is False
    assert hs is False


def test_pool_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AVID_REPL_POOL", raising=False)
    assert pool_enabled() is False


def test_pool_disabled_without_binary(monkeypatch):
    monkeypatch.setenv("AVID_REPL_POOL", "1")
    monkeypatch.setenv("AVID_REPL_BIN", "/nonexistent/repl-binary")
    assert pool_enabled() is False
