"""Tests for src.formalization.error_parser."""

import pytest
from src.formalization.error_parser import (
    parse_lean_errors,
    format_errors_for_llm,
    explain_common_errors,
)


class TestParseLeanErrors:
    def test_parse_single_error(self):
        stdout = "/tmp/test.lean:10:5: error: type mismatch"
        stderr = ""
        code_lines = ["line1", "line2", "line3", "line4", "line5", 
                      "line6", "line7", "line8", "line9", "line10", "line11", "line12", "line13"]
        
        errors = parse_lean_errors(stdout, stderr, code_lines)
        
        assert len(errors) == 1
        assert errors[0]["line"] == 10
        assert errors[0]["column"] == 5
        assert errors[0]["severity"] == "error"
        assert "type mismatch" in errors[0]["message"]
        assert "line10" in errors[0]["context"]

    def test_parse_multiple_errors(self):
        stdout = (
            "/tmp/test.lean:5:3: error: unknown identifier\n"
            "/tmp/test.lean:10:7: error: type mismatch"
        )
        stderr = ""
        code_lines = ["line" + str(i) for i in range(1, 15)]
        
        errors = parse_lean_errors(stdout, stderr, code_lines)
        
        assert len(errors) == 2
        assert errors[0]["line"] == 5
        assert errors[1]["line"] == 10

    def test_parse_warning(self):
        stdout = "/tmp/test.lean:3:1: warning: unused variable"
        stderr = ""
        code_lines = ["line1", "line2", "line3", "line4", "line5", "line6"]
        
        errors = parse_lean_errors(stdout, stderr, code_lines)
        
        assert len(errors) == 1
        assert errors[0]["severity"] == "warning"
        assert "unused variable" in errors[0]["message"]

    def test_parse_no_errors(self):
        stdout = "Success"
        stderr = ""
        code_lines = ["line1"]
        
        errors = parse_lean_errors(stdout, stderr, code_lines)
        
        assert len(errors) == 0

    def test_context_includes_surrounding_lines(self):
        stdout = "/tmp/test.lean:5:1: error: test"
        stderr = ""
        code_lines = ["line1", "line2", "line3", "line4", "line5", "line6", "line7", "line8"]
        
        errors = parse_lean_errors(stdout, stderr, code_lines)
        
        assert "line2" in errors[0]["context"]
        assert "line5" in errors[0]["context"]
        assert "line8" in errors[0]["context"]


class TestFormatErrorsForLLM:
    def test_format_single_error(self):
        errors = [{
            "line": 10,
            "column": 5,
            "severity": "error",
            "message": "type mismatch",
            "context": "    7 | line7\n    8 | line8\n>>> 10 | line10",
            "code_line": "line10",
        }]
        
        formatted = format_errors_for_llm(errors)
        
        assert "Error 1 at line 10" in formatted
        assert "type mismatch" in formatted
        assert "line10" in formatted

    def test_format_multiple_errors(self):
        errors = [
            {"line": 5, "column": 1, "severity": "error", "message": "err1", "context": "", "code_line": ""},
            {"line": 10, "column": 1, "severity": "error", "message": "err2", "context": "", "code_line": ""},
        ]
        
        formatted = format_errors_for_llm(errors)
        
        assert "Found 2 error(s)" in formatted
        assert "Error 1" in formatted
        assert "Error 2" in formatted

    def test_format_with_mathlib_hints(self):
        errors = [{"line": 1, "column": 1, "severity": "error", "message": "test", "context": "", "code_line": ""}]
        hints = ["Nat.add_comm", "Nat.zero_add"]
        
        formatted = format_errors_for_llm(errors, mathlib_hints=hints)
        
        assert "Nat.add_comm" in formatted
        assert "Nat.zero_add" in formatted

    def test_format_no_errors(self):
        formatted = format_errors_for_llm([])
        assert "No errors found" in formatted


class TestExplainCommonErrors:
    def test_type_mismatch(self):
        explanation = explain_common_errors("type mismatch at position 5")
        assert explanation is not None
        assert "Type mismatch" in explanation

    def test_unknown_identifier(self):
        explanation = explain_common_errors("unknown identifier 'foo'")
        assert explanation is not None
        assert "Unknown identifier" in explanation

    def test_duplicate_declaration(self):
        explanation = explain_common_errors("declaration already been declared")
        assert explanation is not None
        assert "Duplicate" in explanation

    def test_instance_synth(self):
        explanation = explain_common_errors("failed to synthesize instance")
        assert explanation is not None
        assert "Instance synthesis" in explanation

    def test_tactic_failed(self):
        explanation = explain_common_errors("tactic 'simp' failed")
        assert explanation is not None
        assert "Tactic failed" in explanation

    def test_sorry(self):
        explanation = explain_common_errors("uses sorry")
        assert explanation is not None
        assert "sorry" in explanation

    def test_unknown_error(self):
        explanation = explain_common_errors("some random error message")
        assert explanation is None
