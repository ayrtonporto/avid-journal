#!/usr/bin/env python3
"""D3 Validation Script.

Lee config/validation_pairs.yaml, ejecuta compute_d3 sobre cada par,
y genera results/d3_validation.csv con un resumen por tipo.

Uso:
    .venv/Scripts/python.exe scripts/validate_d3.py [--config PATH]
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Add repo root to path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.novelty.dimensions.d3_premises import (
    compute_d3,
    load_premises_from_ast,
)
from src.novelty.types import D3Result


# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

def load_validation_pairs(config_path: str) -> List[Dict[str, Any]]:
    """Load and validate the validation pairs YAML."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    pairs = data.get("pairs", [])
    if not pairs:
        print("WARNING: No pairs defined in config.")
    return pairs


# ---------------------------------------------------------------------------
# Run validation
# ---------------------------------------------------------------------------

def run_pair(pair: Dict[str, Any], repo_root: Path) -> Tuple[str, str, Optional[float], int, int, str]:
    """Run compute_d3 on a single validation pair.

    Returns:
        (pair_id, type, distance, intersection_size, union_size, flags_str)
    """
    pair_id = pair["pair_id"]
    pair_type = pair["type"]

    proof_a = pair["proof_a"]
    proof_b = pair["proof_b"]

    # Resolve ast_json paths relative to repo root
    ast_a = repo_root / proof_a["ast_json"]
    ast_b = repo_root / proof_b["ast_json"]

    # Load premises
    lines_a = proof_a["theorem_lines"]
    lines_b = proof_b["theorem_lines"]
    prems_a = load_premises_from_ast(str(ast_a), lines_a[0], lines_a[1])
    prems_b = load_premises_from_ast(str(ast_b), lines_b[0], lines_b[1])

    # Statement line ranges
    stmt_a = tuple(proof_a.get("statement_lines", []) or [])
    stmt_b = tuple(proof_b.get("statement_lines", []) or [])
    stmt_a = stmt_a if len(stmt_a) == 2 else None
    stmt_b = stmt_b if len(stmt_b) == 2 else None

    # Run compute_d3
    result = compute_d3(
        prems_a, prems_b,
        statement_lines_a=stmt_a,
        statement_lines_b=stmt_b,
    )

    flags_str = ",".join(result.flags) if result.flags else ""
    return (
        pair_id,
        pair_type,
        result.jaccard,
        result.intersection_size,
        result.union_size,
        flags_str,
    )


# ---------------------------------------------------------------------------
# Generate CSV and summary
# ---------------------------------------------------------------------------

def generate_output(
    results: List[Tuple[str, str, Optional[float], int, int, str]],
    output_dir: Path,
):
    """Generate results/d3_validation.csv and print summary by type."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "d3_validation.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "pair_id", "type", "distance",
            "intersection_size", "union_size", "flags",
        ])
        for row in results:
            writer.writerow(row)

    print(f"\nCSV written to: {csv_path}")

    # ── Summary by type ──────────────────────────────────────────────────
    by_type: Dict[str, List[float]] = defaultdict(list)
    for _, ptype, dist, _, _, _ in results:
        if dist is not None:
            by_type[ptype].append(dist)

    print("\n" + "=" * 64)
    print("SUMMARY BY TYPE")
    print("=" * 64)

    for ptype in ["control_self", "same_disguised", "genuinely_different", "control_unrelated"]:
        vals = by_type.get(ptype, [])
        if not vals:
            print(f"\n  {ptype}: (no data)")
            continue

        mean_dist = sum(vals) / len(vals)
        min_dist = min(vals)
        max_dist = max(vals)
        print(f"\n  {ptype} ({len(vals)} pairs):")
        print(f"    mean:  {mean_dist:.4f}")
        print(f"    range: [{min_dist:.4f}, {max_dist:.4f}]")

        # Expected ranges (informational only — script does NOT fail)
        if ptype == "control_self":
            if mean_dist > 0.01:
                print(f"    ⚠  Expected ≈0.0, got {mean_dist:.4f} — review")
            else:
                print(f"    ✅ As expected (≈0.0)")

        elif ptype == "control_unrelated":
            if mean_dist < 0.9:
                print(f"    ⚠  Expected ≈1.0, got {mean_dist:.4f} — review")
            else:
                print(f"    ✅ As expected (≈1.0)")

        elif ptype == "genuinely_different":
            if mean_dist < 0.5:
                print(f"    ℹ  Distance < 0.5 — proofs may be structurally similar")
            else:
                print(f"    ✅ Distance > 0.5 — genuinely distinct")

        elif ptype == "same_disguised":
            if mean_dist > 0.2:
                print(f"    ℹ  Distance > 0.2 — cosmetic changes may be substantial")
            else:
                print(f"    ✅ As expected (≈0.0–0.2)")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="D3 Validation Script")
    parser.add_argument(
        "--config",
        default=str(_REPO_ROOT / "config" / "validation_pairs.yaml"),
        help="Path to validation_pairs.yaml",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_REPO_ROOT / "results"),
        help="Directory for output CSV",
    )
    args = parser.parse_args()

    print(f"Loading pairs from: {args.config}")
    pairs = load_validation_pairs(args.config)
    print(f"Found {len(pairs)} pair(s)")

    results = []
    for pair in pairs:
        pair_id = pair["pair_id"]
        print(f"  Processing: {pair_id}...", end=" ", flush=True)
        try:
            row = run_pair(pair, _REPO_ROOT)
            results.append(row)
            dist_str = f"{row[2]:.4f}" if row[2] is not None else "None"
            print(f"distance={dist_str}, inter={row[3]}, union={row[4]}"
                  + (f", flags={row[5]}" if row[5] else ""))
        except Exception as exc:
            print(f"ERROR: {exc}")
            results.append((pair_id, pair["type"], None, 0, 0, f"ERROR: {exc}"))

    if results:
        generate_output(results, Path(args.output_dir))


if __name__ == "__main__":
    main()
