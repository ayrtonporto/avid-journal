#!/usr/bin/env python3
"""Precalentamiento de caché de premisas D3.

Recorre archivos .lean (o entradas del extraction map) y ejecuta
extract_premises sobre cada uno, secuencialmente. La caché por SHA256
hace que las corridas subsiguientes sean instantáneas.

Reanudable: si se corta a la mitad, la próxima corrida salta lo ya cacheado
(esto sale gratis del diseño de la caché).

Uso:
    .venv/Scripts/python.exe scripts/prewarm_premise_cache.py \\
        --lean-project lean_project \\
        --from-extraction-map

    .venv/Scripts/python.exe scripts/prewarm_premise_cache.py \\
        --lean-project lean_project \\
        --files Papers/D3_Calibration/Paper.lean
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List

# Add repo root to path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.novelty_v2.premise_extraction import extract_premises

logger = logging.getLogger(__name__)


def prewarm_files(
    lean_files: List[Path],
    lean_project_dir: Path,
) -> dict:
    """Run extract_premises on each file and report results.

    Returns:
        {hits: int, extracted: int, failures: int, total_time_s: float,
         details: [(file, status, elapsed_s, premises_count)]}
    """
    hits = 0
    extracted = 0
    failures = 0
    details = []
    t_total_start = time.monotonic()

    for i, fpath in enumerate(lean_files):
        fpath = fpath.resolve()
        if not fpath.exists():
            logger.warning("[%d/%d] NOT FOUND: %s", i + 1, len(lean_files), fpath)
            failures += 1
            details.append((str(fpath), "NOT_FOUND", 0, 0))
            continue

        t0 = time.monotonic()
        logger.info("[%d/%d] Extracting: %s", i + 1, len(lean_files), fpath.name)
        result = extract_premises(fpath, lean_project_dir)
        elapsed = time.monotonic() - t0

        if result is None:
            logger.error("[%d/%d] FAILED: %s (%.1fs)", i + 1, len(lean_files),
                         fpath.name, elapsed)
            failures += 1
            details.append((str(fpath), "FAILED", elapsed, 0))
        elif elapsed < 1.0:
            # Very fast → cache hit
            logger.info("[%d/%d] CACHE HIT: %s → %d premises (%.1fs)",
                        i + 1, len(lean_files), fpath.name, len(result), elapsed)
            hits += 1
            details.append((str(fpath), "CACHE_HIT", elapsed, len(result)))
        else:
            # Slower → fresh extraction
            logger.info("[%d/%d] EXTRACTED: %s → %d premises (%.1fs)",
                        i + 1, len(lean_files), fpath.name, len(result), elapsed)
            extracted += 1
            details.append((str(fpath), "EXTRACTED", elapsed, len(result)))

    total_time = time.monotonic() - t_total_start
    return {
        "hits": hits,
        "extracted": extracted,
        "failures": failures,
        "total_time_s": total_time,
        "details": details,
    }


def collect_files_from_args(args, lean_project_dir: Path) -> List[Path]:
    """Collect .lean files to process based on CLI args."""
    files: List[Path] = []

    if args.from_extraction_map:
        import yaml
        map_path = _REPO_ROOT / "config" / "d3_extraction_map.yaml"
        if not map_path.exists():
            logger.error("Extraction map not found: %s", map_path)
            return files
        with open(map_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        seen = set()
        for entry in data.get("pairs", []):
            lean_file = entry["lean_file"]
            if lean_file not in seen:
                seen.add(lean_file)
                files.append(lean_project_dir / lean_file)
        logger.info("Collected %d unique files from extraction map", len(files))

    if args.files:
        for f in args.files:
            fp = Path(f)
            if not fp.is_absolute():
                fp = lean_project_dir / fp
            if fp not in files:
                files.append(fp)

    if args.dir:
        d = Path(args.dir)
        if not d.is_absolute():
            d = lean_project_dir / d
        for fp in sorted(d.rglob("*.lean")):
            if fp not in files and "Blocks" not in str(fp):
                files.append(fp)

    return files


def main():
    parser = argparse.ArgumentParser(
        description="Precalentamiento de caché de premisas D3",
    )
    parser.add_argument(
        "--lean-project", required=True,
        help="Ruta al lean_project/ con ExtractData.lean",
    )
    parser.add_argument(
        "--files", nargs="*", default=[],
        help="Archivos .lean a procesar (relativos a lean-project o absolutos)",
    )
    parser.add_argument(
        "--dir",
        help="Directorio con archivos .lean a procesar recursivamente",
    )
    parser.add_argument(
        "--from-extraction-map", action="store_true",
        help="Cargar archivos desde config/d3_extraction_map.yaml",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Log detallado",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    lean_project_dir = Path(args.lean_project).resolve()
    if not lean_project_dir.exists():
        logger.error("Lean project not found: %s", lean_project_dir)
        sys.exit(1)

    files = collect_files_from_args(args, lean_project_dir)
    if not files:
        logger.error("No .lean files to process. Use --from-extraction-map, "
                     "--files, or --dir.")
        sys.exit(1)

    logger.info("Processing %d file(s)...", len(files))
    report = prewarm_files(files, lean_project_dir)

    # ── Print report ────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PREWARM COMPLETE")
    print("=" * 60)
    print(f"  Files processed:  {len(files)}")
    print(f"  Cache hits:       {report['hits']}")
    print(f"  Fresh extractions:{report['extracted']}")
    print(f"  Failures:         {report['failures']}")
    print(f"  Total time:       {report['total_time_s']:.1f}s")
    print()

    if report["failures"] > 0:
        print("Failures:")
        for fpath, status, elapsed, count in report["details"]:
            if status == "FAILED" or status == "NOT_FOUND":
                print(f"  [{status}] {fpath}")

    print()


if __name__ == "__main__":
    main()
