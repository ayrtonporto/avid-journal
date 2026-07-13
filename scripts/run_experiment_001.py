"""
Experiment Run 001 — Retracted Papers Smoke Test.

Reads config/experiment_run_001.yaml, enforces confirmed:true gate,
and runs the full AViD pipeline (formalization → D2 → D1 → D3) on
each confirmed entry.

Usage:
  .venv/Scripts/python.exe scripts/run_experiment_001.py [--force] [--limit N]

The --force flag is required to bypass the confirmed gate (for testing only).
Without --force, entries with confirmed:false are SKIPPED with a clear message.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repo root is on sys.path for src.* imports
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ── Config ─────────────────────────────────────────────────────────────

DEFAULT_CONFIG = "config/experiment_run_001.yaml"
DEFAULT_OUTPUT_CSV = "results/experiment_run_001.csv"
DEFAULT_REPORT = "docs/experiment_run_001_report.md"
LEAN_PROJECT_DIR = "lean_project"

# Ensure Claude Code CLI is on PATH (npm global install on Windows)
_NPM_BIN = Path.home() / "AppData" / "Roaming" / "npm"
if _NPM_BIN.is_dir() and str(_NPM_BIN) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(_NPM_BIN) + os.pathsep + os.environ.get("PATH", "")


# ── Gate enforcement ───────────────────────────────────────────────────

def load_config(path: str, force: bool = False) -> List[dict]:
    """Load experiment config and enforce confirmed gate.

    Args:
        path: YAML config path.
        force: if True, bypass the gate (for testing).

    Returns:
        List of confirmed entries.

    Raises:
        SystemExit: if no confirmed entries and not force.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    papers = data.get("papers", [])
    if not papers:
        logger.error("No papers found in config")
        sys.exit(1)

    if force:
        logger.warning("⚠️  --force: BYPASSING confirmed gate. All entries will be processed.")
        return papers

    confirmed = [p for p in papers if p.get("confirmed", False)]
    unconfirmed = [p for p in papers if not p.get("confirmed", False)]

    if unconfirmed:
        logger.info(
            "Gate: %d/%d entries have confirmed:false — SKIPPING.",
            len(unconfirmed), len(papers),
        )
        for p in unconfirmed:
            logger.info("  • %s (%s): confirmed=false", p["arxiv_id"], p["role"])

    if not confirmed:
        logger.error(
            "Gate: 0 confirmed entries. Edit %s and set confirmed:true "
            "for the entries you want to process. Then re-run WITHOUT --force.",
            path,
        )
        sys.exit(1)

    logger.info("Gate: %d confirmed entries will be processed.", len(confirmed))
    return confirmed


# ── Minimal .tex wrapper ───────────────────────────────────────────────

def make_minimal_tex(arxiv_id: str, theorem_latex: str) -> str:
    """Wrap a theorem statement in a minimal compilable .tex file."""
    return rf"""\documentclass{{article}}
\usepackage{{amsmath,amssymb,amsthm}}
\newtheorem{{theorem}}{{Theorem}}
\begin{{document}}
\begin{{theorem}}
{theorem_latex}
\end{{theorem}}
\end{{document}}
"""


# ── Formalization (via AViD pipeline → Claude Code) ──────────────────


def formalize_statement(
    arxiv_id: str,
    theorem_latex: str,
    lean_project_dir: str = LEAN_PROJECT_DIR,
    max_attempts: int = 1,
) -> dict:
    """Formalize a LaTeX theorem into Lean 4 using the AViD formalization pipeline.

    Writes a minimal .tex, invokes ``formalize_paper()`` from
    ``src.formalization.orchestrator`` (Claude Code with compile→fix cycle),
    extracts the resulting .lean code, and copies it to
    ``results/formalizations/<arxiv_id>.lean``.

    Returns dict with:
      - lean_statement: str or None
      - lean_imports: str
      - attempts: int
      - errors: list of error messages
      - success: bool
      - lean_path: str
    """
    import shutil
    import tempfile

    from src.formalization.orchestrator import formalize_paper

    result: dict = {
        "lean_statement": None,
        "lean_imports": "import Mathlib",
        "attempts": 0,
        "errors": [],
        "success": False,
        "lean_path": "",
    }

    safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", arxiv_id)
    formal_dir = _REPO_ROOT / "results" / "formalizations"
    formal_dir.mkdir(parents=True, exist_ok=True)
    lean_file = formal_dir / f"{safe_id}.lean"

    # ── Write minimal .tex ────────────────────────────────────────
    tmpdir = Path(tempfile.mkdtemp(prefix="avid_exp_"))
    try:
        tex_path = tmpdir / f"{safe_id}.tex"
        tex_path.write_text(make_minimal_tex(arxiv_id, theorem_latex), encoding="utf-8")

        logger.info("  Invoking AViD formalization pipeline for %s", arxiv_id)
        result["attempts"] = 1

        paper_result = formalize_paper(
            tex_path=str(tex_path),
            paper_title=arxiv_id,
            base_dir=str(tmpdir / "lean_out"),
            dry_run=False,
            parent_project=lean_project_dir,
            blocks_range="1",  # only the first (and only) block
            resume=False,
        )

        # ── Extract verified block ────────────────────────────────
        verified_blocks = [
            b for b in paper_result.get("results", [])
            if b.get("status") == "✅ verified"
        ]

        if verified_blocks:
            block = verified_blocks[0]
            project_dir = Path(paper_result["project_dir"])
            lean_name = block.get("lean_name", "")
            block_path = project_dir / "Blocks" / f"{lean_name}.lean"

            if block_path.exists():
                lean_code = block_path.read_text(encoding="utf-8")
                # Copy to results/formalizations/
                lean_file.write_text(lean_code, encoding="utf-8")
                result["lean_statement"] = lean_code
                result["lean_path"] = str(lean_file)
                result["success"] = True
                logger.info("  ✅ Formalization successful (%d bytes)", len(lean_code))
            else:
                result["errors"].append(f"Block .lean not found at {block_path}")
                logger.warning("  Block file not found")
        else:
            # Collect errors from failed blocks
            failed = [b for b in paper_result.get("results", []) if b.get("status") != "✅ verified"]
            for b in failed:
                err = b.get("error", str(b.get("status", "unknown")))
                result["errors"].append(err)
            statuses = [b.get("status", "?") for b in paper_result.get("results", [])]
            logger.warning("  No verified blocks. Statuses: %s", statuses)

    except Exception as exc:
        result["errors"].append(f"Pipeline error: {exc}")
        logger.error("  Pipeline exception: %s", exc)
    finally:
        # Clean up temp dir (keep results/formalizations/<id>.lean)
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass

    return result


def _has_lean_declaration(code: str) -> bool:
    """Check whether `code` contains at least one Lean declaration.

    Strips single-line comments (``--``) and block comments (``/- ... -/``)
    before searching for ``theorem``, ``lemma``, ``def``, ``example``,
    ``inductive``, ``structure``, ``class``, or ``instance`` keyword.
    """
    # Strip block comments
    no_block = re.sub(r"/-.*?-/\n?", "", code, flags=re.DOTALL)
    # Strip single-line comments
    no_comments = re.sub(r"--[^\n]*", "", no_block)
    # Check for declarations (keyword followed by whitespace)
    return bool(
        re.search(
            r"\b(?:theorem|lemma|def|example|inductive|structure|class|instance)\s+",
            no_comments,
        )
    )


def _verify_lean(lean_code: str, arxiv_id: str, lean_project_dir: str) -> tuple:
    """Verify Lean code compiles. Returns (ok: bool, error: str).

    Saves the .lean file to results/formalizations/<arxiv_id>.lean BEFORE
    compiling, so the generated code is preserved even on failure.
    """
    import subprocess

    safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", arxiv_id)
    formal_dir = _REPO_ROOT / "results" / "formalizations"
    formal_dir.mkdir(parents=True, exist_ok=True)

    lean_file = formal_dir / f"{safe_id}.lean"
    lean_file.write_text(lean_code, encoding="utf-8")

    # ── Anti-empty guard ──────────────────────────────────────────
    if not lean_code.strip():
        return False, "Empty Lean code (0 bytes after strip)"
    if not _has_lean_declaration(lean_code):
        return False, "No Lean declaration found (theorem/lemma/def/example/...)"

    try:
        proc = subprocess.run(
            ["lake", "env", "lean", str(lean_file)],
            cwd=lean_project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            return True, ""
        error_lines = [l for l in proc.stderr.split("\n") if "error" in l.lower()]
        return False, error_lines[0] if error_lines else proc.stderr[:300]
    except subprocess.TimeoutExpired:
        return False, "Compilation timed out (120s)"
    except FileNotFoundError:
        return False, "lake command not found — is Lean 4 installed?"


# ── Run pipeline on one entry ──────────────────────────────────────────

def run_one_entry(entry: dict, output_csv: str) -> dict:
    """Run full AViD pipeline on one experiment entry.

    Returns a dict with all results for the report.
    """
    arxiv_id = entry["arxiv_id"]
    role = entry["role"]
    theorem_latex = entry.get("target_theorem", "")

    row = {
        "arxiv_id": arxiv_id,
        "role": role,
        "paired_with": entry.get("paired_with", ""),
        "known_duplicator": entry.get("known_duplicator", ""),
        "veredicto": "ERROR",
        "d1_top5": "",
        "d1_match_cf": "",
        "d1_match_ci": "",
        "d1_llm_verdict": "",
        "d2_trivial": "",
        "d2_tactic": "",
        "d3_jaccard": "",
        "d3_source": "",
        "formalization_success": False,
        "formalization_path": "",
        "formalization_errors": "",
        "error": "",
    }

    logger.info("=" * 60)
    logger.info("Processing: %s (%s)", arxiv_id, role)

    # ── Step 1: Formalization ──────────────────────────────────────
    formal = formalize_statement(arxiv_id, theorem_latex)
    row["formalization_success"] = formal["success"]
    row["formalization_path"] = formal.get("lean_path", "")
    row["formalization_errors"] = " | ".join(formal["errors"][:3])

    if not formal["success"]:
        row["veredicto"] = "FORMALIZATION_FAILED"
        row["error"] = row["formalization_errors"]
        logger.warning("  Formalization failed, skipping D1/D2/D3")
        return row

    lean_stmt = formal["lean_statement"]

    # ── Step 2: Query TheoremSearch for top-5 (informal) ────────────
    try:
        from src.novelty.theoremsearch import search_theoremsearch
        os.environ["THEOREMSEARCH_ENABLED"] = "1"
        # Use the normalized query from extraction
        ts_results = search_theoremsearch(
            theorem_latex[:500], top_k=5, use_cache=False,
            exclude_arxiv_ids=[arxiv_id],
        )
        row["d1_top5"] = json.dumps([
            {
                "title": c.title[:100],
                "arxiv_id": c.arxiv_id,
                "score": round(c.similarity_score, 3),
                "source": c.source,
            }
            for c in ts_results[:5]
        ])
    except Exception as exc:
        logger.warning("  TheoremSearch query failed: %s", exc)
        row["d1_top5"] = json.dumps([])

    # ── Step 3: Novelty pipeline (D2 → D1 → D3) ────────────────────
    try:
        from src.novelty_v2.orchestrator import check_novelty
        from src.novelty_v2.types import Verdict

        block = {
            "title": entry.get("arxiv_id", ""),
            "content_latex": theorem_latex,
        }

        novelty_result = check_novelty(
            block=block,
            lean_statement=lean_stmt,
            lean_project_dir=LEAN_PROJECT_DIR,
            use_cache=False,
        )

        row["veredicto"] = novelty_result.veredicto.value

        # D1 results (best formal + informal match)
        d1 = novelty_result.d1
        if d1.existe_en_C_F:
            row["d1_match_cf"] = json.dumps(d1.match_C_F or {})
        if d1.existe_en_C_I:
            row["d1_match_ci"] = json.dumps(d1.match_C_I or {})
        if d1.llm_judge_verdict:
            row["d1_llm_verdict"] = d1.llm_judge_verdict

        # D2
        if novelty_result.d2:
            row["d2_trivial"] = str(novelty_result.d2.trivial)
            if novelty_result.d2.trivial:
                row["d2_tactic"] = novelty_result.d2.tactica or ""

        # D3
        if novelty_result.d3 and novelty_result.d3.jaccard is not None:
            row["d3_jaccard"] = round(novelty_result.d3.jaccard, 3)
            row["d3_source"] = novelty_result.d3.d3_source or ""

    except Exception as exc:
        row["veredicto"] = "PIPELINE_ERROR"
        row["error"] = str(exc)[:300]
        logger.error("  Pipeline error: %s", exc)

    logger.info("  Verdict: %s", row["veredicto"])
    return row


# ── CSV output ─────────────────────────────────────────────────────────

def write_csv(rows: List[dict], path: str):
    """Write results to CSV, creating file if needed."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "arxiv_id", "role", "paired_with", "known_duplicator",
        "veredicto", "d1_top5", "d1_match_cf", "d1_match_ci", "d1_llm_verdict",
        "d2_trivial", "d2_tactic", "d3_jaccard", "d3_source",
        "formalization_success", "formalization_errors", "error",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to %s", len(rows), path)


# ── Report ─────────────────────────────────────────────────────────────

def write_report(rows: List[dict], config_path: str, output_path: str):
    """Generate human-readable markdown report."""
    lines = []
    lines.append("# Experiment Run 001 — Report")
    lines.append("")
    lines.append(f"**Config:** `{config_path}`  ")
    lines.append(f"**Entries processed:** {len(rows)}  ")
    lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M UTC-3')}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| arXiv ID | Role | Verdict | D2 trivial? | D3 Jaccard | Formalized? | Duplicator found? |")
    lines.append("|----------|------|---------|-------------|------------|-------------|-------------------|")
    for r in rows:
        d2 = r.get("d2_trivial", "")
        d3 = r.get("d3_jaccard", "")
        formal_ok = "✅" if r.get("formalization_success") else "❌"
        # Leave duplicator column empty for user to fill
        lines.append(
            f"| [{r['arxiv_id']}](https://arxiv.org/abs/{r['arxiv_id']}) "
            f"| {r['role']} | {r['veredicto']} | {d2} | {d3} | {formal_ok} | |"
        )
    lines.append("")
    lines.append("> *Duplicator found? column is for manual verification. Fill after reviewing the evidence below.*")
    lines.append("")

    # Per-paper sections
    for i, r in enumerate(rows):
        lines.append(f"### {i+1}. {r['arxiv_id']} ({r['role']})")
        lines.append("")
        lines.append(f"**Veredicto:** `{r['veredicto']}`  ")
        lines.append(f"**Known duplicator:** {r.get('known_duplicator', 'N/A')}")
        lines.append("")

        if r.get("error"):
            lines.append(f"**Error:** {r['error']}")
            lines.append("")

        if r.get("formalization_errors"):
            lines.append(f"**Formalization errors:** {r['formalization_errors']}")
            lines.append("")

        # D1 top-5
        d1_top5 = r.get("d1_top5", "")
        if d1_top5 and d1_top5 != "[]":
            lines.append("#### D1 Top-5 (Informal Search)")
            lines.append("")
            lines.append("| # | Score | Title | arXiv ID | Source |")
            lines.append("|---|-------|-------|----------|--------|")
            try:
                top5 = json.loads(d1_top5)
                for j, c in enumerate(top5):
                    aid = c.get("arxiv_id", "")
                    aid_link = f"[{aid}](https://arxiv.org/abs/{aid})" if aid else "—"
                    lines.append(
                        f"| {j+1} | {c['score']:.3f} | {c['title'][:80]} | {aid_link} | {c.get('source','?')} |"
                    )
            except Exception:
                lines.append(f"```\n{d1_top5}\n```")
            lines.append("")

        # D2
        if r.get("d2_trivial"):
            lines.append(f"**D2 (triviality):** `{r['d2_trivial']}`")
            lines.append("")

        # D3
        if r.get("d3_jaccard"):
            lines.append(f"**D3 (Jaccard):** `{r['d3_jaccard']}`")
            lines.append("")

        # Known duplicator comparison
        lines.append(f"**🔍 Did D1 find the known duplicator?** — *manual check needed*")
        lines.append(f"> Known: {r.get('known_duplicator', 'N/A')}")
        lines.append(f"> Top D1 result: see above. Do they match?")
        lines.append("")

        lines.append("---")
        lines.append("")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Wrote report to %s", output_path)


# ── Main ───────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run Experiment 001 — Retracted Papers")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-report", default=DEFAULT_REPORT)
    parser.add_argument("--force", action="store_true",
                        help="Bypass confirmed:false gate (for testing)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of entries to process")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load config, check gate, but don't run pipeline")
    args = parser.parse_args()

    # ── Load and gate ──────────────────────────────────────────────
    entries = load_config(args.config, force=args.force)
    if args.limit > 0:
        entries = entries[:args.limit]

    if args.dry_run:
        logger.info("Dry-run: would process %d entries", len(entries))
        for e in entries:
            logger.info("  • %s (%s)", e["arxiv_id"], e["role"])
        return

    # ── Process entries ────────────────────────────────────────────
    rows = []
    for i, entry in enumerate(entries):
        logger.info("Entry %d/%d", i + 1, len(entries))
        row = run_one_entry(entry, args.output_csv)
        rows.append(row)

        # Periodic save (every entry)
        write_csv(rows, args.output_csv)

    # ── Final report ───────────────────────────────────────────────
    write_report(rows, args.config, args.output_report)

    # Summary
    verdicts = {}
    for r in rows:
        v = r["veredicto"]
        verdicts[v] = verdicts.get(v, 0) + 1
    logger.info("Verdict summary: %s", json.dumps(verdicts, indent=2))
    formal_ok = sum(1 for r in rows if r.get("formalization_success"))
    logger.info("Formalization success: %d/%d", formal_ok, len(rows))


if __name__ == "__main__":
    main()
