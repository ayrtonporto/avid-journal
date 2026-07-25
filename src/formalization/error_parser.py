"""Parse Lean compiler output into structured errors with context."""

import re
from pathlib import Path
from typing import List, Dict, Optional


def parse_lean_errors(stdout: str, stderr: str, code_lines: List[str]) -> List[Dict]:
    """Parse Lean 4 compiler output into structured errors with context.
    
    Args:
        stdout: stdout from `lake env lean`
        stderr: stderr from `lake env lean`
        code_lines: lines of the .lean file that was compiled
        
    Returns:
        List of dicts with keys:
        - line: int (1-indexed line number)
        - column: int (1-indexed column)
        - severity: 'error' or 'warning'
        - message: str (the error message)
        - context: str (3 lines before + error line + 3 lines after)
        - code_line: str (the exact line with the error)
    """
    combined = stdout + "\n" + stderr
    errors = []
    
    # Match: /path/file.lean:10:5: error: message here
    # or:    /path/file.lean:10:5: warning: message here
    pattern = r"[^:]+\.lean:(\d+):(\d+):\s*(error|warning):\s*(.+?)(?=\n[^:]+\.lean:|$)"
    
    for match in re.finditer(pattern, combined, re.DOTALL | re.MULTILINE):
        line_num = int(match.group(1))
        column = int(match.group(2))
        severity = match.group(3)
        message = match.group(4).strip()
        
        # Get context: 3 lines before, the error line, 3 lines after
        start = max(0, line_num - 4)  # -4 because 1-indexed to 0-indexed, -3 more
        end = min(len(code_lines), line_num + 3)  # +3 more
        
        context_lines = []
        for i in range(start, end):
            prefix = ">>> " if i == line_num - 1 else "    "
            context_lines.append(f"{prefix}{i+1:4d} | {code_lines[i]}")
        
        context = "\n".join(context_lines)
        code_line = code_lines[line_num - 1] if line_num <= len(code_lines) else ""
        
        errors.append({
            "line": line_num,
            "column": column,
            "severity": severity,
            "message": message,
            "context": context,
            "code_line": code_line,
        })
    
    return errors


def format_errors_for_llm(errors: List[Dict], mathlib_hints: Optional[List[str]] = None) -> str:
    """Format parsed errors into a helpful message for the LLM.
    
    Args:
        errors: output from parse_lean_errors
        mathlib_hints: optional list of relevant Mathlib lemma names
        
    Returns:
        Formatted string with context and hints
    """
    if not errors:
        return "No errors found."
    
    parts = [f"Found {len(errors)} error(s):\n"]
    
    for i, err in enumerate(errors, 1):
        parts.append(f"Error {i} at line {err['line']}, column {err['column']}:")
        parts.append(f"  Type: {err['severity']}")
        parts.append(f"  Message: {err['message']}")
        parts.append(f"  Problematic line: `{err['code_line']}`")
        parts.append(f"  Context:")
        parts.append(err["context"])
        parts.append("")
    
    if mathlib_hints:
        parts.append("\nRelevant Mathlib lemmas that might help:")
        for hint in mathlib_hints[:5]:
            parts.append(f"  - {hint}")
    
    return "\n".join(parts)


def explain_common_errors(message: str) -> Optional[str]:
    """Explain common Lean errors in plain language.
    
    Returns an explanation string, or None if the error is not recognized.
    """
    lower = message.lower()
    
    if "type mismatch" in lower:
        return (
            "Type mismatch: you're using a value of the wrong type. "
            "Check what type is expected vs what you're providing. "
            "For ℕ vs Int, use Int.ofNat or cast explicitly. "
            "For Prop vs Bool, Prop is for proofs, Bool for computation."
        )
    
    if "unknown identifier" in lower:
        return (
            "Unknown identifier: you're using a name that's not in scope. "
            "Either import the right Mathlib module, or check if you meant "
            "a different name (Lean is case-sensitive)."
        )
    
    if "already been declared" in lower or "duplicate" in lower:
        return (
            "Duplicate declaration: you're defining something that already exists. "
            "Rename your definition (e.g., `MyEven` instead of `Even`) to avoid "
            "shadowing Mathlib names."
        )
    
    if "synth" in lower or "instance" in lower:
        return (
            "Instance synthesis failed: Lean can't find a typeclass instance. "
            "Check if you're missing an import, or if the type doesn't have "
            "the required instance (e.g., no `Add` for a type that needs it)."
        )
    
    if "tactic" in lower and "failed" in lower:
        return (
            "Tactic failed: the proof tactic didn't work. Try a different tactic "
            "or provide more information (e.g., `simp [lemma_name]` instead of `simp`)."
        )
    
    if "sorry" in lower:
        return (
            "Using sorry: you must provide a complete proof, not a placeholder. "
            "Replace `sorry` with an actual proof."
        )
    
    return None
