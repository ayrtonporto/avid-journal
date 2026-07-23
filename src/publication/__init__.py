"""
AViD Journal — Publication module.

Handles paper submissions: after a paper passes novelty checks,
the author can submit it for publication. Submissions are accumulated
as .tex files + metadata in submissions/.

Directory structure:
    src/publication/
        submissions/          ← accumulated .tex papers
        submissions.json      ← manifest of all submissions
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SUBMISSIONS_DIR = Path(__file__).resolve().parent / "submissions"
MANIFEST_PATH = Path(__file__).resolve().parent / "submissions.json"


def ensure_dirs() -> None:
    """Create submissions directory if it doesn't exist."""
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)


def load_manifest() -> Dict[str, Any]:
    """Load the submissions manifest (or create if missing)."""
    ensure_dirs()
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    empty = {"submissions": [], "count": 0, "updated": ""}
    save_manifest(empty)
    return empty


def save_manifest(manifest: Dict[str, Any]) -> None:
    """Persist the manifest to disk."""
    ensure_dirs()
    manifest["updated"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def submit(
    tex_path: str | Path,
    title: str,
    authors: str,
    abstract: str = "",
    email: str = "",
    verdicts: Optional[Dict[str, Any]] = None,
    llm_model: str = "",
    llm_strategy: str = "",
) -> Dict[str, Any]:
    """Submit a paper to AViD Journal.

    Args:
        tex_path: Path to the .tex file.
        title: Paper title.
        authors: Author name(s).
        abstract: Optional abstract.
        email: Optional contact email.
        verdicts: Optional novelty verdict summary.

    Returns:
        Submission record dict with id, status, path.
    """
    ensure_dirs()

    tex_path = Path(tex_path)
    submission_id = _next_id()

    # Copy .tex to submissions dir
    dest = SUBMISSIONS_DIR / f"{submission_id}_{tex_path.name}"
    shutil.copy2(tex_path, dest)

    # Build record
    record = {
        "id": submission_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "email": email,
        "filename": dest.name,
        "original_path": str(tex_path),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",
        "verdicts": verdicts or {},
        "llm_model": llm_model,
        "llm_strategy": llm_strategy,
    }

    # Update manifest
    manifest = load_manifest()
    manifest["submissions"].append(record)
    manifest["count"] = len(manifest["submissions"])
    save_manifest(manifest)

    return record


def list_submissions(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all submissions, optionally filtered by status."""
    manifest = load_manifest()
    subs = manifest.get("submissions", [])
    if status:
        subs = [s for s in subs if s.get("status") == status]
    return subs


def _next_id() -> str:
    """Generate the next submission ID (e.g., AVID-0003)."""
    manifest = load_manifest()
    n = manifest.get("count", 0) + 1
    return f"AVID-{n:04d}"
