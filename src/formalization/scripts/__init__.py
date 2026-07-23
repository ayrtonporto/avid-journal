"""
AViD Journal — Scripts for model-agnostic formalization.

This package contains:
- lean_checker:      Verify .lean files compile without errors/sorry.
- safe_verify:       Kernel-level proof replay via SafeVerify.
- extract_sublemmas: Parse Lean code to extract blocks/statements/proofs.
- mcp_stats:         Analyze MCP tool call logs (Claude Code specific).
- statement_tracker: Detect changes in theorem/lemma statements across rounds.
- verification_loop: Model-agnostic retry loop for API-based providers.
"""

from .lean_checker import check_lean_file, check_lean_files_parallel, find_lean_files
from .safe_verify import SafeVerifyResult, snapshot_target, run_safe_verify
from .statement_tracker import StatementTracker, RoundResult, StatementChange
from .extract_sublemmas import LeanCodeParser

__all__ = [
    "check_lean_file",
    "check_lean_files_parallel",
    "find_lean_files",
    "SafeVerifyResult",
    "snapshot_target",
    "run_safe_verify",
    "StatementTracker",
    "RoundResult",
    "StatementChange",
    "LeanCodeParser",
]
