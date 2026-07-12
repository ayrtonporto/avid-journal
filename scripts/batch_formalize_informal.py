#!/usr/bin/env python3
"""Batch formalization of informal matches (arXiv papers → Lean proofs).

Pipeline per match:
  download arXiv source → extract proof → formalize (up to 3 attempts)
  → fidelity check → cache results.

Reanudable: skips already-cached arXiv IDs.
Orden: shortest proof first (prioridad por longitud).
Timeout: 20 minutos por intento de formalización (configurable).

Uso:
    .venv/Scripts/python.exe scripts/batch_formalize_informal.py \
        --input config/informal_matches.yaml \
        --lean-project lean_project \
        --provider opencode

Input YAML format:
    matches:
      - arxiv_id: "1303.0730"
        statement: "There are infinitely many prime numbers"
        source: "theoremsearch"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv

load_dotenv()  # Load OPENCODE_GO_API_KEY from .env

# Add repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.novelty_v2.informal_match import (
    _download_arxiv_source,
    _find_main_tex,
    _extract_proof_block,
    _check_proof_delegation,
    check_fidelity,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 1200  # 20 minutes per formalization attempt
MAX_ATTEMPTS = 3
CACHE_DIR_NAME = "informal_formalizations"


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------

def load_matches(config_path: str) -> List[Dict[str, str]]:
    """Load informal matches from YAML config."""
    path = Path(config_path)
    if not path.exists():
        logger.error("Config not found: %s", path)
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    matches = data.get("matches", [])
    logger.info("Loaded %d informal matches", len(matches))
    return matches


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_dir(lean_project_dir: Path) -> Path:
    d = lean_project_dir / "cache" / CACHE_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_path(lean_project_dir: Path, arxiv_id: str) -> Path:
    key = hashlib.sha256(arxiv_id.encode()).hexdigest()[:16]
    return _cache_dir(lean_project_dir) / f"{key}.json"


def _read_result(cache_path: Path) -> Optional[dict]:
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def _write_result(cache_path: Path, result: dict) -> None:
    tmp = cache_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2, default=str)
    tmp.replace(cache_path)


# ---------------------------------------------------------------------------
# Lean project setup for a match
# ---------------------------------------------------------------------------

def _setup_lean_target(
    arxiv_id: str,
    lean_name: str,
    lean_project_dir: Path,
) -> Tuple[Path, Path]:
    """Create a minimal Lean target file for the formalization.

    Returns (blocks_dir, target_path).
    """
    paper_dir = lean_project_dir / "Papers" / "InformalMatches" / arxiv_id
    blocks_dir = paper_dir / "Blocks"
    blocks_dir.mkdir(parents=True, exist_ok=True)

    target_path = blocks_dir / f"{lean_name}.lean"
    stub = (
        f"-- AViD informal match stub\n"
        f"-- arXiv: {arxiv_id}\n"
        f"-- Lean name: {lean_name}\n"
        f"--\n"
        f"-- Write the formalized Lean declaration(s) below this line.\n"
        f"\n"
        f"import Mathlib\n"
    )
    target_path.write_text(stub, encoding="utf-8")
    return blocks_dir, target_path


# ---------------------------------------------------------------------------
# Formalization attempt
# ---------------------------------------------------------------------------

def _try_formalize(
    target_path: Path,
    prompt: str,
    cwd: Path,
    provider_name: str,
    timeout: int,
    max_rounds: int = 3,
) -> Tuple[bool, str, float]:
    """Single formalization attempt. Returns (success, info, elapsed_s)."""
    t0 = time.monotonic()

    try:
        # Import provider machinery
        sys.path.insert(0, str(_REPO_ROOT / "avid-clean"))
        from formalization.providers.config import resolve_provider

        provider = resolve_provider(provider_name)
    except Exception as exc:
        elapsed = time.monotonic() - t0
        return False, f"Provider init error: {exc}", elapsed

    try:
        import subprocess as sp

        # The provider.formalize() call can hang; wrap with subprocess timeout
        # But since it's in-process, we use signal.alarm or threading.
        # For simplicity, we call directly and trust the provider's internal timeout.
        result = provider.formalize(
            target_path=target_path,
            prompt=prompt,
            max_rounds=max_rounds,
            cwd=cwd,
        )
        elapsed = time.monotonic() - t0

        if not result.success:
            return False, f"Provider failed: {result.info}", elapsed

        # Verify compilation
        from src.formalization.scripts.lean_checker import check_lean_file

        has_error, has_sorry, stdout, stderr = check_lean_file(target_path)
        if has_error:
            return False, f"Compilation error", elapsed
        if has_sorry:
            return False, f"Uses 'sorry'", elapsed

        # Extract code
        extracted = target_path.read_text(encoding="utf-8")
        return True, extracted, elapsed

    except Exception as exc:
        elapsed = time.monotonic() - t0
        return False, f"Exception: {exc}", elapsed


# ---------------------------------------------------------------------------
# Process a single match
# ---------------------------------------------------------------------------

def process_match(
    match: Dict[str, str],
    lean_project_dir: Path,
    provider_name: str,
    timeout: int,
    max_rounds: int = 6,
) -> dict:
    """Run the full pipeline for one informal match."""
    arxiv_id = match["arxiv_id"]
    statement_hint = match.get("statement", "")
    source = match.get("source", "theoremsearch")

    result = {
        "arxiv_id": arxiv_id,
        "statement_hint": statement_hint[:200],
        "source": source,
        "status": "pending",
        "attempts": [],
        "flags": [],
        "fidelity_match": None,
        "fidelity_justification": "",
        "proof_length": 0,
        "total_time_s": 0.0,
        "error": "",
    }

    t_total = time.monotonic()

    # 1) Download + extract
    cache_tmp = Path(tempfile.gettempdir()) / "avid_informal_cache"
    cache_tmp.mkdir(exist_ok=True)

    src_dir = _download_arxiv_source(arxiv_id, cache_tmp)
    if src_dir is None:
        result["status"] = "FAILED"
        result["error"] = "arXiv source unavailable"
        result["total_time_s"] = time.monotonic() - t_total
        return result

    main_tex = _find_main_tex(src_dir)
    if main_tex is None:
        result["status"] = "FAILED"
        result["error"] = "No .tex file in source"
        result["total_time_s"] = time.monotonic() - t_total
        return result

    tex_content = main_tex.read_text(encoding="utf-8", errors="replace")
    proof_text = _extract_proof_block(tex_content, statement_hint)

    if proof_text is None:
        result["status"] = "FAILED"
        result["error"] = "No proof block found"
        result["total_time_s"] = time.monotonic() - t_total
        return result

    result["proof_length"] = len(proof_text)

    # Flag delegation but do NOT skip — let it run with flag visible
    if _check_proof_delegation(proof_text):
        result["flags"].append("proof_delegates_to_lemmas")
        logger.info("[%s] Flagged: proof_delegates_to_lemmas (%d chars)", arxiv_id, len(proof_text))

    # 2) Set up Lean target
    lean_name = f"thm_{arxiv_id.replace('.', '_').replace('/', '_')}"
    blocks_dir, target_path = _setup_lean_target(
        arxiv_id, lean_name, lean_project_dir,
    )

    # 3) Build prompt
    # Extract a cleaner statement from the tex
    stmt_clean = statement_hint if statement_hint else "See proof below"
    prompt = (
        f"# Formalization Task\n\n"
        f"## Informal Statement\n{stmt_clean}\n\n"
        f"## Informal Proof\n{proof_text}\n\n"
        f"## Instructions\n"
        f"Formalize this theorem and proof in Lean 4 using Mathlib.\n"
        f"The Lean identifier must be `{lean_name}`.\n"
        f"Write your code in the target file. Do NOT use `sorry`.\n"
        f"The proof must compile with `lake env lean`.\n"
    )

    # 4) Attempt formalization (up to MAX_ATTEMPTS)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info(
            "[%s] Attempt %d/%d (proof: %d chars)",
            arxiv_id, attempt, MAX_ATTEMPTS, len(proof_text),
        )
        success, info, elapsed = _try_formalize(
            target_path, prompt, lean_project_dir, provider_name, timeout, max_rounds,
        )
        attempt_record = {
            "attempt": attempt,
            "success": success,
            "info": str(info)[:300],
            "elapsed_s": round(elapsed, 1),
        }
        result["attempts"].append(attempt_record)

        if success:
            # Fidelity check
            lean_code = info  # info contains extracted code on success
            is_faithful, justification = check_fidelity(stmt_clean, lean_code)
            result["fidelity_match"] = is_faithful
            result["fidelity_justification"] = justification[:300]
            if is_faithful:
                result["status"] = "SUCCESS"
            else:
                result["status"] = "FAILED"
                result["error"] = f"Fidelity mismatch: {justification[:200]}"
            break
        else:
            logger.warning("[%s] Attempt %d failed: %s", arxiv_id, attempt, info)

    if result["status"] == "pending":
        result["status"] = "FAILED"
        result["error"] = f"All {MAX_ATTEMPTS} attempts failed"

    result["total_time_s"] = round(time.monotonic() - t_total, 1)
    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(results: List[dict]) -> None:
    """Print summary report."""
    total = len(results)
    success = sum(1 for r in results if r["status"] == "SUCCESS")
    failed = sum(1 for r in results if r["status"] == "FAILED")

    print("\n" + "=" * 72)
    print("BATCH FORMALIZATION REPORT")
    print("=" * 72)
    print(f"  Total matches:  {total}")
    print(f"  Successful:     {success} ({100*success/total:.0f}%)" if total else "  Successful: 0")
    print(f"  Failed:         {failed}")
    print()

    # By failure reason
    reasons: Dict[str, int] = defaultdict(int)
    for r in results:
        if r["status"] == "FAILED":
            err = r.get("error", "unknown")
            # Classify
            if "arXiv" in err or "No .tex" in err:
                reasons["source_unavailable"] += 1
            elif "No proof block" in err:
                reasons["no_proof"] += 1
            elif "Fidelity" in err:
                reasons["infidelity"] += 1
            elif "All" in err and "attempts failed" in err:
                reasons["all_attempts_failed"] += 1
            elif "proof_delegates" in err:
                reasons["proof_delegates_to_lemmas"] += 1
            else:
                reasons["other"] += 1

    if reasons:
        print("  Failure reasons:")
        for reason, count in sorted(reasons.items()):
            print(f"    {reason}: {count}")

    # Timing
    times = [r.get("total_time_s", 0) for r in results]
    if times:
        print(f"\n  Total time: {sum(times):.0f}s")
        print(f"  Avg per match: {sum(times)/len(times):.0f}s")

    # Proof lengths (for successful ones)
    success_lengths = [r["proof_length"] for r in results if r["status"] == "SUCCESS"]
    if success_lengths:
        print(f"\n  Successful proof lengths: min={min(success_lengths)}, "
              f"max={max(success_lengths)}, avg={sum(success_lengths)//len(success_lengths)}")

    # Per-match detail
    print("\n" + "-" * 72)
    print("PER-MATCH DETAIL")
    print("-" * 72)
    for r in results:
        status_icon = "✅" if r["status"] == "SUCCESS" else "❌"
        attempts_used = len(r.get("attempts", []))
        print(f"  {status_icon} {r['arxiv_id']:15s} | {r['status']:8s} | "
              f"attempts={attempts_used} | proof={r.get('proof_length', 0)} chars | "
              f"{r.get('total_time_s', 0):.0f}s")
        err = r.get("error", "")
        if err:
            print(f"     error: {err[:120]}")
        fid = r.get("fidelity_match")
        if fid is not None:
            print(f"     fidelity: {'MATCH' if fid else 'MISMATCH'} — "
                  f"{r.get('fidelity_justification', '')[:100]}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Batch formalization of informal matches (arXiv → Lean)",
    )
    parser.add_argument(
        "--input", required=True,
        help="YAML file with informal matches",
    )
    parser.add_argument(
        "--lean-project", required=True,
        help="Path to lean_project/ with Mathlib compiled",
    )
    parser.add_argument(
        "--provider", default="opencode",
        help="Model provider name (default: opencode)",
    )
    parser.add_argument(
        "--model", default=None,
        help="Model name override (e.g., deepseek-v4-pro). Sets OPENCODE_GO_MODEL env var.",
    )
    parser.add_argument(
        "--max-rounds", type=int, default=6,
        help="Max verification loop rounds per attempt (default: 6)",
    )
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"Timeout per attempt in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit to N matches (0 = all)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Detailed logging",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Download and extract proofs, but skip API formalization",
    )
    args = parser.parse_args()

    # Set model override
    if args.model:
        os.environ["OPENCODE_GO_MODEL"] = args.model
        logger.info("Model override: %s", args.model)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    lean_project_dir = Path(args.lean_project).resolve()
    if not lean_project_dir.exists():
        logger.error("Lean project not found: %s", lean_project_dir)
        sys.exit(1)

    # Load matches
    matches = load_matches(args.input)
    if not matches:
        logger.error("No matches found in %s", args.input)
        sys.exit(1)

    # Sort by proof length: shortest first (need to download first to know)
    # For initial sort, we approximate: download all, extract proofs, sort
    logger.info("Pre-scanning %d matches for proof lengths...", len(matches))
    pre_scanned = []
    cache_tmp = Path(tempfile.gettempdir()) / "avid_informal_cache"
    cache_tmp.mkdir(exist_ok=True)

    for match in matches:
        arxiv_id = match["arxiv_id"]
        cp = _cache_path(lean_project_dir, arxiv_id)
        cached = _read_result(cp)
        if cached:
            logger.info("[%s] Already cached: %s", arxiv_id, cached.get("status"))
            pre_scanned.append((match, cached.get("proof_length", 0), False))
            continue

        # Quick download + proof extraction to get length
        src_dir = _download_arxiv_source(arxiv_id, cache_tmp)
        proof_len = 0
        is_delegated = False
        if src_dir:
            main_tex = _find_main_tex(src_dir)
            if main_tex:
                tex_content = main_tex.read_text(encoding="utf-8", errors="replace")
                proof_text = _extract_proof_block(
                    tex_content, match.get("statement", ""),
                )
                if proof_text:
                    proof_len = len(proof_text)
                    is_delegated = _check_proof_delegation(proof_text)

        pre_scanned.append((match, proof_len, is_delegated))
        logger.info("[%s] Proof length: %d chars, delegated=%s", arxiv_id, proof_len, is_delegated)

    # Sort: shortest proof first
    pre_scanned.sort(key=lambda x: (x[1] == 0, x[1]))

    if args.limit > 0:
        pre_scanned = pre_scanned[: args.limit]

    # Also clean any stale cache entries from pre-scan phase
    # (pre-scan should not write to the same cache as results)

    # Process
    results = []
    for i, (match, proof_len, _is_delegated) in enumerate(pre_scanned):
        arxiv_id = match["arxiv_id"]
        cp = _cache_path(lean_project_dir, arxiv_id)

        # Check cache again (might have been cached during pre-scan)
        cached = _read_result(cp)
        if cached:
            logger.info("[%d/%d] %s: CACHED (%s)", i+1, len(pre_scanned),
                        arxiv_id, cached.get("status"))
            results.append(cached)
            continue

        logger.info("[%d/%d] Processing %s...", i+1, len(pre_scanned), arxiv_id)
        if args.dry_run:
            logger.info("[%d/%d] DRY-RUN: would formalize (skipping API call)", i+1, len(pre_scanned))
            result = {
                "arxiv_id": arxiv_id,
                "status": "dry_run",
                "proof_length": proof_len,
                "flags": [],
                "attempts": [],
                "total_time_s": 0,
                "error": "",
            }
            _write_result(cp, result)
            results.append(result)
            continue

        result = process_match(
            match, lean_project_dir, args.provider, args.timeout, args.max_rounds,
        )
        _write_result(cp, result)
        results.append(result)

    # Report
    print_report(results)

    # Save report to file
    report_path = lean_project_dir / "cache" / CACHE_DIR_NAME / "batch_report.json"
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2, default=str)
    logger.info("Report saved to %s", report_path)


if __name__ == "__main__":
    main()
