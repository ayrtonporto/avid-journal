"""
AViD Journal — Publication store (SQLite-backed).

Persists every NOVEL-verified run as the journal's authoritative record: the
input .tex, the output .lean, novelty metadata, and the author's personal data
(empty until they fill the form). SQLite handles concurrent writes from
multiple clients on the server without the corruption a JSON manifest would
suffer under races.

Lifecycle of a record:
    1. A run passes and is verified novel  -> record_novel_run(...) inserts a
       row with status "auto_recorded" and EMPTY personal data. The novel
       result is never lost, even if the author walks away.
    2. The author fills the publish form and submits -> enrich_submission(...)
       (via submit(..., submission_id=...)) fills the personal data on the SAME
       row and flips status to "pending_review".

Public API kept backward-compatible with the old JSON-manifest version:
    submit(...)            create a record, or enrich an existing one by id
    list_submissions(...)  list records (optional status filter)
    load_manifest()        {"submissions": [...], "count": n, "updated": ...}

New:
    record_novel_run(...)  auto-persist a novel-verified run (empty author data)
    enrich_submission(...) fill personal data on a prior record
    get_submission(id)     fetch one record
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Module-level paths. Tests monkeypatch SUBMISSIONS_DIR (and MANIFEST_PATH), so
# read them dynamically inside functions — never cache a derived path (e.g. the
# db path) at import time.
SUBMISSIONS_DIR = Path(__file__).resolve().parent / "submissions"
MANIFEST_PATH = Path(__file__).resolve().parent / "submissions.json"  # legacy, unused

# Column order used for INSERTs. Personal-data columns start empty on auto
# records and get filled by enrich_submission().
_COLUMNS = [
    "id", "created_at", "updated_at", "status", "source", "novel",
    "title", "authors", "email", "abstract", "affiliation",
    "llm_model", "llm_strategy",
    "n_theorems", "verdicts", "tex_file", "lean_file",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    """Create the submissions directory if it doesn't exist."""
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _db_path() -> Path:
    # Derived from the (possibly monkeypatched) SUBMISSIONS_DIR at call time.
    return SUBMISSIONS_DIR / "submissions.db"


def _conn() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    # WAL improves concurrent read/write behaviour for multiple clients.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS submissions (
            id           TEXT PRIMARY KEY,
            created_at   TEXT,
            updated_at   TEXT,
            status       TEXT,
            source       TEXT,
            novel        INTEGER,
            title        TEXT,
            authors      TEXT,
            email        TEXT,
            abstract     TEXT,
            affiliation  TEXT,
            llm_model    TEXT,
            llm_strategy TEXT,
            n_theorems   INTEGER,
            verdicts     TEXT,
            tex_file     TEXT,
            lean_file    TEXT
        )"""
    )
    conn.commit()
    return conn


def _row_to_record(row: sqlite3.Row) -> Dict[str, Any]:
    rec = {k: row[k] for k in row.keys()}
    try:
        rec["verdicts"] = json.loads(rec.get("verdicts") or "{}")
    except (json.JSONDecodeError, TypeError):
        rec["verdicts"] = {}
    rec["novel"] = bool(rec.get("novel"))
    return rec


def _next_id() -> str:
    """Sequential id like AVID-0007 (count-based, matching legacy behaviour)."""
    conn = _conn()
    try:
        n = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    finally:
        conn.close()
    return f"AVID-{n + 1:04d}"


def _stored_name(submission_id: str, src: Optional[str | Path], suffix: str) -> str:
    """Return the stored filename for a source file, or "" if it's missing."""
    if not src:
        return ""
    if not Path(src).exists():
        return ""
    return f"{submission_id}_{suffix}"


def _create(
    *,
    status: str,
    source: str,
    tex_path: Optional[str | Path],
    lean_path: Optional[str | Path],
    title: str,
    authors: str,
    email: str,
    abstract: str,
    affiliation: str,
    llm_model: str,
    llm_strategy: str,
    verdicts: Optional[Dict[str, Any]],
    n_theorems: int,
    novel: bool,
) -> Dict[str, Any]:
    """Insert a new submission row (retrying the id on the rare collision),
    then copy the tex/lean files into the submissions dir."""
    ensure_dirs()
    last_err: Optional[Exception] = None
    for _ in range(5):
        sid = _next_id()
        tex_file = _stored_name(sid, tex_path, "input.tex")
        lean_file = _stored_name(sid, lean_path, "output.lean")
        now = _now()
        record = {
            "id": sid, "created_at": now, "updated_at": now,
            "status": status, "source": source, "novel": 1 if novel else 0,
            "title": title, "authors": authors, "email": email,
            "abstract": abstract, "affiliation": affiliation,
            "llm_model": llm_model, "llm_strategy": llm_strategy,
            "n_theorems": n_theorems,
            "verdicts": json.dumps(verdicts or {}, ensure_ascii=False),
            "tex_file": tex_file, "lean_file": lean_file,
        }
        conn = _conn()
        try:
            conn.execute(
                f"INSERT INTO submissions ({', '.join(_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in _COLUMNS)})",
                [record[c] for c in _COLUMNS],
            )
            conn.commit()
        except sqlite3.IntegrityError as e:  # id collided under concurrency
            last_err = e
            conn.rollback()
            conn.close()
            continue
        finally:
            if conn:  # noqa: SIM102
                try:
                    conn.close()
                except sqlite3.ProgrammingError:
                    pass
        # Insert succeeded — persist the files under the allocated id.
        if tex_file:
            shutil.copy2(Path(tex_path), SUBMISSIONS_DIR / tex_file)
        if lean_file:
            shutil.copy2(Path(lean_path), SUBMISSIONS_DIR / lean_file)
        return get_submission(sid)  # type: ignore[return-value]
    raise RuntimeError(f"could not allocate a submission id: {last_err}")


def record_novel_run(
    tex_path: str | Path,
    lean_path: Optional[str | Path] = None,
    verdicts: Optional[Dict[str, Any]] = None,
    n_theorems: int = 0,
    title: str = "",
    novel: bool = True,
) -> Dict[str, Any]:
    """Auto-persist a run with empty author data.

    Called at the end of every analysis. Stores the input .tex and the output
    .lean plus novelty metadata. Personal data is left empty; enrich_submission()
    fills it if/when the author submits.

    Args:
        novel: whether the paper passed all novelty checks (affects publishability).
    """
    return _create(
        status="auto_recorded", source="auto", novel=novel,
        tex_path=tex_path, lean_path=lean_path,
        title=title, authors="", email="", abstract="", affiliation="",
        llm_model="", llm_strategy="",
        verdicts=verdicts, n_theorems=n_theorems,
    )


def enrich_submission(
    submission_id: str,
    title: Optional[str] = None,
    authors: Optional[str] = None,
    email: Optional[str] = None,
    abstract: Optional[str] = None,
    affiliation: Optional[str] = None,
    llm_model: Optional[str] = None,
    llm_strategy: Optional[str] = None,
    status: str = "pending_review",
) -> Optional[Dict[str, Any]]:
    """Fill personal data on an existing record (author submitted the form).

    Only non-None fields overwrite. Returns the updated record, or None if the
    id doesn't exist.
    """
    updates: Dict[str, Any] = {
        k: v for k, v in {
            "title": title, "authors": authors, "email": email,
            "abstract": abstract, "affiliation": affiliation,
            "llm_model": llm_model, "llm_strategy": llm_strategy,
        }.items() if v is not None
    }
    conn = _conn()
    try:
        exists = conn.execute(
            "SELECT 1 FROM submissions WHERE id=?", (submission_id,)
        ).fetchone()
        if exists is None:
            return None
        updates["status"] = status
        updates["source"] = "submitted"
        updates["updated_at"] = _now()
        assignments = ", ".join(f"{k}=?" for k in updates)
        conn.execute(
            f"UPDATE submissions SET {assignments} WHERE id=?",
            list(updates.values()) + [submission_id],
        )
        conn.commit()
    finally:
        conn.close()
    return get_submission(submission_id)


def submit(
    tex_path: str | Path,
    title: str,
    authors: str,
    abstract: str = "",
    email: str = "",
    verdicts: Optional[Dict[str, Any]] = None,
    llm_model: str = "",
    llm_strategy: str = "",
    submission_id: Optional[str] = None,
    lean_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Submit a paper to AViD Journal (manual publish form).

    If `submission_id` refers to an existing auto-recorded run, the author's
    data enriches that same row (no duplicate). Otherwise a new record is
    created. Return shape is backward-compatible (id, title, status, authors…).
    """
    if submission_id and get_submission(submission_id) is not None:
        enriched = enrich_submission(
            submission_id,
            title=title or None,
            authors=authors,
            email=email,
            abstract=abstract,
            llm_model=llm_model,
            llm_strategy=llm_strategy,
        )
        if enriched is not None:
            return enriched

    return _create(
        status="pending_review", source="submitted", novel=True,
        tex_path=tex_path, lean_path=lean_path,
        title=title, authors=authors, email=email, abstract=abstract,
        affiliation="", llm_model=llm_model, llm_strategy=llm_strategy,
        verdicts=verdicts, n_theorems=(verdicts or {}).get("total", 0),
    )


def get_submission(submission_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single submission record by id, or None."""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM submissions WHERE id=?", (submission_id,)
        ).fetchone()
    finally:
        conn.close()
    return _row_to_record(row) if row else None


def list_submissions(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all submissions, optionally filtered by status (oldest first)."""
    conn = _conn()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM submissions WHERE status=? ORDER BY created_at, id",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM submissions ORDER BY created_at, id"
            ).fetchall()
    finally:
        conn.close()
    return [_row_to_record(r) for r in rows]


def load_manifest() -> Dict[str, Any]:
    """Backward-compatible manifest view over the SQLite store."""
    subs = list_submissions()
    return {"submissions": subs, "count": len(subs), "updated": _now()}
