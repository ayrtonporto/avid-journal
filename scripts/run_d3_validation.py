#!/usr/bin/env python3
"""Script completo de validación D3: Judge LLM + validate_d3.py.

Ejecuta:
  1. Juez LLM sobre 3 pares (T07, T08, T09).
  2. validate_d3.py sobre 5 pares (3 test + control_self + control_unrelated).
  3. Verifica que T08 = 0.7222 (número de regresión intocable).
  4. Guarda todo en results/pair_judgments.json y results/d3_validation.csv.

Uso:
    .venv/Scripts/python.exe scripts/run_d3_validation.py [--skip-judge] [--skip-d3]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# Add repo root to path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.novelty_v2.proof_pair_judge import judge_proof_pair, ProofPairJudgment

# ---------------------------------------------------------------------------
# Load Lean source texts
# ---------------------------------------------------------------------------


def load_lean_theorem_text(
    file_path: Path,
    start_line: int,
    end_line: int,
) -> str:
    """Extrae el texto completo de un teorema de un archivo .lean."""
    with open(file_path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    # Lines are 1-indexed in YAML, 0-indexed in Python
    return "".join(lines[start_line - 1 : end_line])


def get_paper_path() -> Path:
    """Path to the D3 calibration paper."""
    return _REPO_ROOT / "lean_project" / "Papers" / "D3_Calibration" / "Paper.lean"


# Pairs definition for the judge
JUDGE_PAIRS = [
    {
        "pair_id": "T07_euclid_vs_factorial",
        "proof_a_lines": (25, 26),
        "proof_b_lines": (28, 30),
    },
    {
        "pair_id": "T08_parity_vs_valuation",
        "proof_a_lines": (42, 91),
        "proof_b_lines": (100, 158),
    },
    {
        "pair_id": "T09_induction_vs_gauss",
        "proof_a_lines": (168, 193),  # Updated induction proof
        "proof_b_lines": (197, 202),  # Gauss pairing proof
    },
]


# ---------------------------------------------------------------------------
# Run judge
# ---------------------------------------------------------------------------


def run_judge(output_dir: Path) -> list[dict]:
    """Ejecuta el juez LLM sobre los 3 pares y guarda resultados."""
    paper_path = get_paper_path()
    judgments = []

    print("\n" + "=" * 64)
    print("PROOF PAIR JUDGE — LLM DeepSeek V4 Flash (temperature=0)")
    print("=" * 64)

    for pair_def in JUDGE_PAIRS:
        pid = pair_def["pair_id"]
        proof_a = load_lean_theorem_text(
            paper_path, *pair_def["proof_a_lines"]
        )
        proof_b = load_lean_theorem_text(
            paper_path, *pair_def["proof_b_lines"]
        )

        print(f"\n  Judging: {pid}")
        print(f"    Proof A: {len(proof_a)} chars, Proof B: {len(proof_b)} chars")

        judgment = judge_proof_pair(
            proof_a_text=proof_a,
            proof_b_text=proof_b,
            pair_id=pid,
        )

        judgments.append(judgment.to_dict())
        print(f"    statement_match: {judgment.statement_match}")
        print(f"    verdict: {judgment.verdict}")
        if judgment.idea_a:
            print(f"    idea_a: {judgment.idea_a[:120]}...")
        if judgment.idea_b:
            print(f"    idea_b: {judgment.idea_b[:120]}...")
        if judgment.justification:
            print(f"    justification: {judgment.justification[:200]}...")

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    judgments_path = output_dir / "pair_judgments.json"
    with open(judgments_path, "w", encoding="utf-8") as fh:
        json.dump(judgments, fh, ensure_ascii=False, indent=2)
    print(f"\n  Judge results saved to: {judgments_path}")

    return judgments


# ---------------------------------------------------------------------------
# Run validate_d3
# ---------------------------------------------------------------------------


def run_validate_d3() -> None:
    """Ejecuta validate_d3.py."""
    print("\n" + "=" * 64)
    print("D3 VALIDATION — compute_d3 (Jaccard)")
    print("=" * 64)

    import subprocess

    validate_script = _REPO_ROOT / "scripts" / "validate_d3.py"
    result = subprocess.run(
        [
            sys.executable,
            str(validate_script),
            "--config",
            str(_REPO_ROOT / "config" / "validation_pairs.yaml"),
            "--output-dir",
            str(_REPO_ROOT / "results"),
        ],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    if result.returncode != 0:
        print(f"WARNING: validate_d3.py exited with code {result.returncode}")


# ---------------------------------------------------------------------------
# Verify T08 regresión
# ---------------------------------------------------------------------------


def verify_t08_regression() -> tuple[bool, Optional[float]]:
    """Verifica que T08 = 0.7222 exacto. Si cambió, FRENAR."""
    import csv

    csv_path = _REPO_ROOT / "results" / "d3_validation.csv"
    if not csv_path.exists():
        print("WARNING: d3_validation.csv not found, skipping T08 regression check")
        return False, None

    target = 0.7222
    tolerance = 0.0001

    with open(csv_path, "r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("pair_id") == "T08_E1_E2":
                dist_str = row.get("distance", "")
                if not dist_str or dist_str == "None":
                    print("WARNING: T08 distance is None!")
                    return False, None
                dist = float(dist_str)
                if abs(dist - target) > tolerance:
                    print(f"\n{'!' * 64}")
                    print(f"T08 REGRESSION DETECTED!")
                    print(f"  Expected: {target:.4f}")
                    print(f"  Got:      {dist:.4f}")
                    print(f"  Delta:    {abs(dist - target):.6f}")
                    print(f"{'!' * 64}\n")
                    return False, dist
                else:
                    print(f"\n{'=' * 64}")
                    print(f"T08 REGRESSION CHECK: PASS")
                    print(f"  Expected: {target:.4f}")
                    print(f"  Got:      {dist:.4f}")
                    print(f"  Delta:    {abs(dist - target):.6f} < {tolerance}")
                    print(f"{'=' * 64}\n")
                    return True, dist

    print("WARNING: T08_E1_E2 not found in d3_validation.csv")
    return False, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Full D3 Validation")
    parser.add_argument(
        "--skip-judge", action="store_true", help="Skip LLM judge"
    )
    parser.add_argument(
        "--skip-d3", action="store_true", help="Skip validate_d3.py"
    )
    args = parser.parse_args()

    output_dir = _REPO_ROOT / "results"

    # ── 1. Judge ────────────────────────────────────────────────────────
    if not args.skip_judge:
        run_judge(output_dir)

    # ── 2. validate_d3 ──────────────────────────────────────────────────
    if not args.skip_d3:
        run_validate_d3()

    # ── 3. T08 regression check ─────────────────────────────────────────
    ok, dist = verify_t08_regression()

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("VALIDATION SUMMARY")
    print("=" * 64)

    if ok:
        print("  ✅ T08 regression: PASS (distance = 0.7222)")
    else:
        if dist is not None:
            print(f"  ❌ T08 regression: FAIL (got {dist:.4f}, expected 0.7222)")
        else:
            print("  ⚠  T08 regression: UNKNOWN (no data)")

    print(f"\n  Results saved to: {output_dir}")
    print(f"    pair_judgments.json — LLM judge verdicts")
    print(f"    d3_validation.csv   — D3 distances\n")


if __name__ == "__main__":
    main()
