#!/usr/bin/env python3
"""
AViD Journal — Integration test: Tiny Evens Paper.

Tests the model-agnostic orchestrator with the sample paper (3 blocks:
definition, lemma, theorem). Runs in three modes:

  1. Dry-run:      validates pipeline without invoking any model
  2. Claude Code:   uses Claude Code CLI (requires `claude auth login`)
  3. OpenCode API:  uses OpenCode Go API (requires OPENCODE_GO_API_KEY)

Usage:
    python avid-clean/tests/test_tiny_evens.py              # dry-run only
    python avid-clean/tests/test_tiny_evens.py --claude     # dry-run + Claude
    python avid-clean/tests/test_tiny_evens.py --opencode   # dry-run + OpenCode
    python avid-clean/tests/test_tiny_evens.py --all        # all three
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[2]  # avid-clean/.. → repo root
_STAGING = _REPO_ROOT / "avid-clean"

# Add staging to sys.path so `from formalization.orchestrator import ...` works
if str(_STAGING) not in sys.path:
    sys.path.insert(0, str(_STAGING))
# Add repo root for original src/* imports (used by orchestrator internally)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Force UTF-8 for Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

from formalization.orchestrator import formalize_paper

# ── Config ──────────────────────────────────────────────────────
FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "sample_paper.tex"
PAPER_TITLE = "Tiny Evens Paper — Integration Test"


def load_env():
    """Load API keys from repo .env and Hermes config (gitignored)."""
    # 1) Repo root .env (gitignored, place your keys here)
    env_files = [
        _REPO_ROOT / ".env",
        Path.home() / "AppData" / "Local" / "hermes" / ".env",
        Path.home() / ".hermes" / ".env",
    ]
    for env_file in env_files:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and val and key not in os.environ:
                        os.environ[key] = val
            print(f"[env] Loaded keys from {env_file}")


def run_dry_run():
    """Dry-run: validates pipeline without models."""
    print("\n" + "=" * 60)
    print(" MODE 1: DRY-RUN (no model)")
    print("=" * 60)

    summary = formalize_paper(
        tex_path=str(FIXTURE),
        paper_title=PAPER_TITLE,
        dry_run=True,
        # usa lean_project/ compartido con Mathlib pre-compilado
    )
    _print_summary("dry-run", summary)
    return True


def run_claude():
    """Real run with Claude Code CLI."""
    print("\n" + "=" * 60)
    print(" MODE 2: CLAUDE CODE CLI")
    print("=" * 60)

    import shutil
    if not shutil.which("claude"):
        print("[SKIP] Claude CLI not found on PATH. Run `claude auth login` first.")
        return False

    summary = formalize_paper(
        tex_path=str(FIXTURE),
        paper_title=PAPER_TITLE + " (Claude)",
        dry_run=False,
        model="claude",
    )
    _print_summary("claude", summary)
    return True


def run_opencode():
    """Real run with OpenCode Go API."""
    print("\n" + "=" * 60)
    print(" MODE 3: OPENCODE GO API")
    print("=" * 60)

    if not os.environ.get("OPENCODE_GO_API_KEY"):
        print("[SKIP] OPENCODE_GO_API_KEY not set. Export it or add to ~/.hermes/.env")
        return False

    model_name = os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-pro")
    print(f"[info] Model: {model_name}")

    summary = formalize_paper(
        tex_path=str(FIXTURE),
        paper_title=PAPER_TITLE + " (OpenCode)",
        dry_run=False,
        model="opencode",
    )
    _print_summary("opencode", summary)
    return True


def _print_summary(label: str, summary: dict):
    """Print formatted summary."""
    counts = summary["counts"]
    print(f"\n[{label}] Results:")
    print(f"  Project:  {summary['project_dir']}")
    print(f"  Provider: {summary.get('model_provider', 'N/A')}")
    print(f"  Total:    {summary['total_blocks']} blocks")
    print(f"  Verified: {counts['verified']}")
    print(f"  Axioms:   {counts['axiom']}")
    print(f"  Failed:   {counts['failed']}")
    if counts.get("rate_limited"):
        print(f"  ⚠️  Rate limited: {counts['rate_limited']}")

    for r in summary["results"]:
        status = r.get("status", "?")
        label_blk = r.get("label", "?")
        error = r.get("error", "")
        err_str = f" → {error}" if error else ""
        print(f"    [{status}] {label_blk}{err_str}")


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="AViD Tiny Evens Integration Test")
    ap.add_argument("--claude", action="store_true", help="Run with Claude Code CLI")
    ap.add_argument("--opencode", action="store_true", help="Run with OpenCode API")
    ap.add_argument("--all", action="store_true", help="Run all modes")
    ap.add_argument("--dry-run", action="store_true", default=True,
                    help="Run dry-run mode (default: True)")
    args = ap.parse_args()

    load_env()

    if not FIXTURE.exists():
        print(f"[ERROR] Fixture not found: {FIXTURE}")
        sys.exit(1)

    results = {}

    # 1) Always run dry-run
    results["dry-run"] = run_dry_run()

    # 2) Optional real modes
    if args.all or args.claude:
        results["claude"] = run_claude()
    if args.all or args.opencode:
        results["opencode"] = run_opencode()

    # Summary
    print("\n" + "=" * 60)
    print(" OVERALL")
    print("=" * 60)
    for mode, ok in results.items():
        print(f"  {mode}: {'✅ OK' if ok else '⏭️ SKIPPED'}")
    print("=" * 60)
