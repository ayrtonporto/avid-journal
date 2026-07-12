"""
FASE 3: Build control candidates for retracted papers experiment.

For each viable retracted candidate, find 1-2 control papers:
- Same primary category
- Same year ±1
- NOT withdrawn
- LaTeX source available + theorem environments present

Network courtesy:
  --delay N (default 3.0): seconds between consecutive arXiv requests
  Exponential backoff on 429/503/timeout: 5 retries (5s, 10s, 20s, 40s, 80s)
  Resumable: skips already-processed pairs and cached viability checks

Output: config/control_candidates.yaml
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
import re
import shutil
import tarfile
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import List, Optional

import requests
import yaml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Constants ─────────────────────────────────────────────────────────
ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_SRC = "https://arxiv.org/src/{}"
CACHE_DIR = Path("cache/retracted_dataset")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

# Theorem-like environment patterns (standard + abbreviated)
THEOREM_RE = re.compile(
    r"\\begin\{(?:theorem|lemma|proposition|corollary|claim|conjecture|"
    r"thm|lem|prop|cor|defn|definition|remark)\}",
    re.IGNORECASE,
)
PROOF_RE = re.compile(r"\\begin\{proof\}", re.IGNORECASE)

# ── Network courtesy ───────────────────────────────────────────────────
_BACKOFF_SCHEDULE = [5, 10, 20, 40, 80]  # seconds
_MAX_RETRIES = len(_BACKOFF_SCHEDULE)
_RETRYABLE_STATUSES = {429, 503}

# Bookkeeping for backoff statistics
_BACKOFF_LOG: List[dict] = []  # [{label, reason, attempt, wait}, ...]


def _arxiv_get(url: str, timeout: int = 30, label: str = "") -> requests.Response:
    """GET with exponential backoff for retryable failures.

    Retries on: HTTP 429, 503, ConnectionError, Timeout.
    Logs each backoff event to _BACKOFF_LOG and logger.
    """
    last_exc: Optional[requests.RequestException] = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code in _RETRYABLE_STATUSES:
                reason = f"HTTP {resp.status_code}"
                if attempt < _MAX_RETRIES:
                    wait = _BACKOFF_SCHEDULE[attempt]
                    logger.warning(
                        "[%s] %s — backoff %d/%d, waiting %ds",
                        label, reason, attempt + 1, _MAX_RETRIES, wait,
                    )
                    _BACKOFF_LOG.append({"label": label, "reason": reason, "attempt": attempt + 1, "wait": wait})
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            exc_name = type(exc).__name__
            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_SCHEDULE[attempt]
                logger.warning(
                    "[%s] %s — backoff %d/%d, waiting %ds",
                    label, exc_name, attempt + 1, _MAX_RETRIES, wait,
                )
                _BACKOFF_LOG.append({"label": label, "reason": exc_name, "attempt": attempt + 1, "wait": wait})
                time.sleep(wait)
                continue
            raise
        except requests.RequestException as exc:
            logger.error("[%s] Non-retryable error: %s", label, exc)
            raise

    raise last_exc  # type: ignore[misc]


# ── Helpers ───────────────────────────────────────────────────────────

def _to_v1_id(arxiv_id: str) -> str:
    base = re.sub(r"v\d+$", "", arxiv_id)
    return f"{base}v1"


def _extract_arxiv_source(content_bytes: bytes, extract_dir: Path) -> List[Path]:
    """Extract arXiv source (handles tar.gz and plain .gz)."""
    tex_files: List[Path] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(content_bytes), mode="r:gz") as tar:
            tar.extractall(extract_dir)
        tex_files = list(extract_dir.rglob("*.tex"))
        if tex_files:
            return tex_files
    except (tarfile.ReadError, OSError):
        pass
    try:
        decompressed = gzip.decompress(content_bytes)
        text = decompressed.decode("utf-8", errors="replace")
        filename = "main.tex"
        if len(content_bytes) > 10 and content_bytes[3] & 0x08:
            null_pos = content_bytes.find(b"\x00", 10)
            if null_pos > 10:
                try:
                    filename = content_bytes[10:null_pos].decode("ascii")
                except Exception:
                    pass
        tex_path = extract_dir / filename
        extract_dir.mkdir(parents=True, exist_ok=True)
        tex_path.write_text(text, encoding="utf-8")
        return [tex_path]
    except Exception:
        pass
    return []


def _check_source_viability(arxiv_id: str) -> dict:
    """Download v1 source and check theorem/proof environments (with cache and backoff)."""
    v1_id = _to_v1_id(arxiv_id)
    cache_key = hashlib.sha256(v1_id.encode()).hexdigest()[:16]
    meta_path = CACHE_DIR / f"ctrl_meta_{cache_key}.json"

    # Cache hit
    if meta_path.exists():
        try:
            cached = json.loads(meta_path.read_text())
            if cached.get("source_available") or cached.get("error"):
                return cached
        except Exception:
            pass

    result = {
        "arxiv_id_v1": v1_id,
        "source_available": False,
        "main_tex_found": False,
        "num_tex_files": 0,
        "theorem_envs": 0,
        "proof_envs": 0,
        "tarball_size_kb": 0,
        "error": None,
    }

    url = ARXIV_SRC.format(v1_id)
    label = f"ctrl-src {v1_id}"
    try:
        resp = _arxiv_get(url, timeout=60, label=label)
    except requests.RequestException as exc:
        result["error"] = f"Download failed after backoff: {exc}"
        meta_path.write_text(json.dumps(result, indent=2))
        return result

    if resp.status_code == 404:
        result["error"] = "404"
        meta_path.write_text(json.dumps(result, indent=2))
        return result
    if "text/html" in resp.headers.get("content-type", ""):
        result["error"] = "HTML response"
        meta_path.write_text(json.dumps(result, indent=2))
        return result

    result["tarball_size_kb"] = round(len(resp.content) / 1024, 1)
    if len(resp.content) < 512:
        result["error"] = "too small"
        meta_path.write_text(json.dumps(result, indent=2))
        return result

    cache_path = CACHE_DIR / f"ctrl_src_{cache_key}"
    if cache_path.exists():
        shutil.rmtree(cache_path)

    tex_files = _extract_arxiv_source(resp.content, cache_path)
    if not tex_files:
        result["error"] = "no tex extractable"
        meta_path.write_text(json.dumps(result, indent=2))
        return result

    result["source_available"] = True
    result["num_tex_files"] = len(tex_files)
    tex_files.sort(key=lambda p: p.stat().st_size, reverse=True)
    main_tex = tex_files[0]
    result["main_tex_found"] = True

    try:
        content = main_tex.read_text(encoding="utf-8", errors="replace")
        result["theorem_envs"] = len(THEOREM_RE.findall(content))
        result["proof_envs"] = len(PROOF_RE.findall(content))
    except Exception as exc:
        result["error"] = f"read: {exc}"

    meta_path.write_text(json.dumps(result, indent=2))
    return result


# ── arXiv search ──────────────────────────────────────────────────────

def _search_control_papers(
    category: str,
    year: int,
    exclude_ids: set,
    max_results: int = 20,
) -> List[dict]:
    """Search arXiv for non-withdrawn papers in a category+year range (with backoff)."""
    query = (
        f"cat:{category} AND "
        f"submittedDate:[{year - 1}0101 TO {year + 1}1231] "
        f"NOT co:withdrawn"
    )
    params = {
        "search_query": query,
        "start": 0,
        "max_results": min(max_results, 50),
        "sortBy": "relevance",
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{ARXIV_API}?{query_string}"
    label = f"search {category} {year - 1}-{year + 1}"

    resp = _arxiv_get(url, timeout=30, label=label)
    root = ET.fromstring(resp.content)
    papers: List[dict] = []

    for entry in root.findall("atom:entry", NS):
        id_el = entry.find("atom:id", NS)
        title_el = entry.find("atom:title", NS)
        summary_el = entry.find("atom:summary", NS)
        cat_el = entry.find("arxiv:primary_category", NS)
        pub_el = entry.find("atom:published", NS)
        comment_el = entry.find("arxiv:comment", NS)

        arxiv_url = id_el.text if id_el is not None else ""
        arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""
        title = (title_el.text or "").strip() if title_el is not None else ""
        summary = (summary_el.text or "").strip() if summary_el is not None else ""
        cat = cat_el.get("term", "") if cat_el is not None else ""
        pub_date = (pub_el.text or "").strip() if pub_el is not None else ""
        year_pub = pub_date[:4] if pub_date else ""
        comment = (comment_el.text or "").strip() if comment_el is not None else ""

        # Double-check: not withdrawn
        if "withdrawn" in (comment + summary).lower():
            continue
        if arxiv_id in exclude_ids:
            continue

        authors = []
        for author_el in entry.findall("atom:author", NS):
            name_el = author_el.find("atom:name", NS)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "primary_category": cat,
            "year": year_pub,
            "summary": summary[:300],
            "authors": authors,
        })

    return papers


# ── Main pipeline ──────────────────────────────────────────────────────

def _load_existing_controls(output_path: str) -> tuple[set, list]:
    """Load already-matched retracted IDs + their pairs from existing output (resume support).

    Returns (done_ids, existing_pairs).  On first run, both are empty.
    Existing pairs are merged into the final output so nothing is lost.
    """
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data and data.get("pairs"):
            pairs = list(data["pairs"])
            done_ids = {p["retracted_arxiv_id"] for p in pairs}
            return done_ids, pairs
    except Exception:
        pass
    return set(), []


def build_control_candidates(
    retracted_yaml_path: str,
    output_path: str,
    delay: float = 3.0,
):
    """Main pipeline: find control papers for each viable retracted candidate.

    Resumable: skips retracted papers that already have controls in the output file.
    Cached viability checks skip re-downloading arXiv sources.
    """
    # ── Load retracted candidates ───────────────────────────────────
    with open(retracted_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    viable = [c for c in data["candidates"] if c.get("viability", {}).get("is_viable")]
    logger.info("Loaded %d viable retracted candidates", len(viable))

    # ── Resume: load already-matched ────────────────────────────────
    already_done, existing_pairs = _load_existing_controls(output_path)
    if already_done:
        logger.info("Resuming — %d retracted papers already have controls, skipping", len(already_done))

    exclude_ids = {c["arxiv_id"] for c in data["candidates"]}
    # Merge existing pairs so they're included in final output
    control_pairs: List[dict] = list(existing_pairs)
    for ep in existing_pairs:
        for ctrl in ep.get("controls", []):
            exclude_ids.add(ctrl.get("arxiv_id", ""))
    stats = {
        "matched": len(already_done),
        "no_control_found": 0,
        "controls_checked": 0,
        "controls_viable": 0,
        "skipped_resume": len(already_done),
        "backoffs": 0,
    }

    t_start = time.monotonic()

    for i, retracted in enumerate(viable):
        rid = retracted["arxiv_id"]

        # Resume check
        if rid in already_done:
            logger.info("[%d/%d] %s — already has controls, skipping", i + 1, len(viable), rid)
            continue

        cat = retracted["primary_category"]
        year = int(retracted["year"])
        logger.info("[%d/%d] Searching controls for %s (%s, %d)", i + 1, len(viable), rid, cat, year)

        # Search for control candidates
        candidates = _search_control_papers(cat, year, exclude_ids, max_results=15)
        logger.info("  Found %d candidate control papers", len(candidates))

        controls_for_this: List[dict] = []
        for cand in candidates:
            cid = cand["arxiv_id"]
            backoffs_before = len(_BACKOFF_LOG)

            viability = _check_source_viability(cid)
            stats["controls_checked"] += 1

            is_viable = (
                viability.get("source_available")
                and viability.get("main_tex_found")
                and viability.get("theorem_envs", 0) > 0
            )
            if is_viable:
                stats["controls_viable"] += 1

            logger.info(
                "    %s: viable=%s thm=%d proof=%d",
                cid, is_viable,
                viability.get("theorem_envs", 0),
                viability.get("proof_envs", 0),
            )

            if is_viable and len(controls_for_this) < 2:
                controls_for_this.append({
                    "arxiv_id": cid,
                    "title": cand["title"],
                    "primary_category": cand["primary_category"],
                    "year": cand["year"],
                    "authors": cand["authors"],
                    "viability": viability,
                })
                exclude_ids.add(cid)

            # Delay between control checks
            if len(controls_for_this) < 2:
                time.sleep(delay)

        if controls_for_this:
            stats["matched"] += 1
            control_pairs.append({
                "retracted_arxiv_id": rid,
                "retracted_title": retracted["title"],
                "retracted_category": cat,
                "retracted_year": year,
                "controls": controls_for_this,
            })
        else:
            stats["no_control_found"] += 1
            logger.warning("  ⚠ No viable control found for %s", rid)

        # ── Periodic save (every 5 retracted papers) ────────────────
        if (stats["matched"] - stats["skipped_resume"]) % 5 == 0 and control_pairs:
            _write_output(output_path, control_pairs, stats, _BACKOFF_LOG)
            logger.info("  [checkpoint saved: %d pairs]", len(control_pairs))

        # Delay between retracted papers
        if i < len(viable) - 1:
            time.sleep(delay)

    t_elapsed = time.monotonic() - t_start
    stats["backoffs"] = len(_BACKOFF_LOG)
    stats["elapsed_seconds"] = round(t_elapsed)
    stats["elapsed_minutes"] = round(t_elapsed / 60, 1)

    # ── Final write ────────────────────────────────────────────────
    _write_output(output_path, control_pairs, stats, _BACKOFF_LOG)
    logger.info("Wrote %d control pairs to %s", len(control_pairs), output_path)
    logger.info("Stats: %s", json.dumps(stats, indent=2))

    return control_pairs


def _write_output(output_path: str, pairs: List[dict], stats: dict, backoff_log: List[dict]):
    """Write control candidates YAML (atomic via temp file)."""
    output = {
        "description": "Control papers matched to retracted candidates by category and year",
        "matching_criteria": (
            "Same primary arXiv category, year ±1, NOT withdrawn, "
            "LaTeX source available with ≥1 theorem environment"
        ),
        "total_retracted_with_controls": stats.get("matched", len(pairs)),
        "total_retracted_without_controls": stats.get("no_control_found", 0),
        "total_controls_checked": stats.get("controls_checked", 0),
        "total_controls_viable": stats.get("controls_viable", 0),
        "backoff_events": stats.get("backoffs", 0),
        "elapsed_seconds": stats.get("elapsed_seconds", 0),
        "elapsed_minutes": stats.get("elapsed_minutes", 0),
        "pairs": pairs,
    }

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    Path(tmp_path).replace(output_path)


# ── Entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build control candidates for retracted papers")
    parser.add_argument("--retracted", default="config/retracted_candidates.yaml")
    parser.add_argument("--output", default="config/control_candidates.yaml")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of retracted papers to process")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Seconds between consecutive arXiv requests (default: 3.0)")
    args = parser.parse_args()

    if args.limit > 0:
        with open(args.retracted, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        viable = [c for c in data["candidates"] if c.get("viability", {}).get("is_viable")]
        data["candidates"] = viable[:args.limit]
        tmp_path = "config/_retracted_limited.yaml"
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        args.retracted = tmp_path

    build_control_candidates(args.retracted, args.output, delay=args.delay)
