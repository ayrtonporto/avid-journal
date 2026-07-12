"""
FASE 1-2: Build retracted candidates dataset from arXiv API.

Queries math.* withdrawn papers, filters for "result already known" /
duplication reasons, downloads LaTeX source for feasibility check.

Network courtesy:
  --delay N (default 3.0): seconds between consecutive arXiv requests
  Exponential backoff on 429/503/timeout: 5 retries (5s, 10s, 20s, 40s, 80s)
  Resumable: skipped items with cached results are not re-fetched

Output: config/retracted_candidates.yaml
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
from pathlib import Path
from typing import List, Optional, Tuple

import requests
import yaml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── arXiv API ──────────────────────────────────────────────────────────
ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_SRC = "https://arxiv.org/src/{arxiv_id}"

# Namespaces for XML parsing
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}

# ── Withdrawal reason patterns ─────────────────────────────────────────
DUPLICATION_PATTERNS = [
    r"already\s+known",
    r"previously\s+(proved|proven|established|known|shown)",
    r"was\s+already\s+(established|proved|proven|known|shown)",
    r"due\s+to\s+prior\s+work",
    r"main\s+result\s+(already|was|had\s+been|is)\s+(known|proved|proven|established)",
    r"result\s+(already|was|had\s+been)\s+(known|proved|proven|established)",
    r"not\s+new",
    r"already\s+exists?(s|ed)?\s+in\s+(the\s+)?literature",
    r"duplicate\s+(of|result|publication|work)",
    r"already\s+contained\s+in",
    r"overlap\s+with\s+(prior|previous|existing)",
    r"result\s+(is|was)\s+not\s+(new|original|novel)",
    r"theorem\s+(already|was|had\s+been)\s+(known|proved|proven|established)",
    r"result\s+(already|previously)\s+(appeared|appears)",
    r"follows\s+(directly\s+)?from\s+(prior|existing|known|previous)",
    r"already\s+been\s+(proved|proven|established|shown)",
    r"corollary\s+of\s+(a\s+)?(known|well.known|existing|prior)",
    r"special\s+case\s+of\s+(a\s+)?(known|existing|prior)",
    r"subsumed\s+by",
    r"already\s+published",
    r"rediscovery",
    r"pre.existing\s+(result|work|proof)",
    r"original\s+result\s+(already|was|had)",
]
_DUP_RE = re.compile("|".join(DUPLICATION_PATTERNS), re.IGNORECASE)

NON_DUP_PATTERNS = [
    r"error|mistake|gap|incorrect|flaw|bug|wrong",
    r"incomplete|unfinished|preliminary",
    r"merged|incorporated",
    r"policy|submission\s+error|accidental",
    r"will\s+be\s+replaced|to\s+be\s+updated|new\s+version",
    r"proof\s+is\s+incorrect|incorrect\s+proof",
]
_NON_DUP_RE = re.compile("|".join(NON_DUP_PATTERNS), re.IGNORECASE)

# Theorem env patterns (standard + abbreviated)
THEOREM_RE = re.compile(
    r"\\begin\{(?:theorem|lemma|proposition|corollary|claim|conjecture|"
    r"thm|lem|prop|cor|defn|definition|remark)\}",
    re.IGNORECASE,
)
PROOF_RE = re.compile(r"\\begin\{proof\}", re.IGNORECASE)

# ── Cache ──────────────────────────────────────────────────────────────
CACHE_DIR = Path("cache/retracted_dataset")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Network courtesy ───────────────────────────────────────────────────
_BACKOFF_SCHEDULE = [5, 10, 20, 40, 80]  # seconds
_MAX_RETRIES = len(_BACKOFF_SCHEDULE)
_RETRYABLE_STATUSES = {429, 503}


def _arxiv_get(url: str, timeout: int = 30, label: str = "") -> requests.Response:
    """GET with exponential backoff for retryable failures.

    Retries on: HTTP 429, 503, ConnectionError, Timeout, ReadTimeout.
    After _MAX_RETRIES attempts, raises the last exception.
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
                time.sleep(wait)
                continue
            raise
        except requests.RequestException as exc:
            logger.error("[%s] Non-retryable error: %s", label, exc)
            raise

    raise last_exc  # type: ignore[misc]


# ── Helpers ────────────────────────────────────────────────────────────

def _arxiv_id_from_url(url: str) -> str:
    return url.split("/abs/")[-1]


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


def _search_arxiv(
    query: str,
    start: int = 0,
    max_results: int = 100,
) -> Tuple[List[dict], int]:
    """Search arXiv API with backoff. Returns (entries, total_results)."""
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_results,
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{ARXIV_API}?{query_string}"
    label = f"search start={start}"

    resp = _arxiv_get(url, timeout=30, label=label)
    root = ET.fromstring(resp.content)

    entries: List[dict] = []
    for entry_elem in root.findall("atom:entry", NS):
        entry: dict = {}
        id_elem = entry_elem.find("atom:id", NS)
        if id_elem is not None:
            entry["id"] = id_elem.text
            entry["arxiv_id"] = _arxiv_id_from_url(id_elem.text or "")

        title_elem = entry_elem.find("atom:title", NS)
        entry["title"] = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

        summary_elem = entry_elem.find("atom:summary", NS)
        entry["summary"] = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""

        comment_elem = entry_elem.find("arxiv:comment", NS)
        entry["comment"] = comment_elem.text.strip() if comment_elem is not None and comment_elem.text else ""

        categories = []
        for cat_elem in entry_elem.findall("atom:category", NS):
            term = cat_elem.get("term", "")
            if term:
                categories.append(term)
        entry["categories"] = categories

        primary_elem = entry_elem.find("arxiv:primary_category", NS)
        entry["primary_category"] = primary_elem.get("term", "") if primary_elem is not None else ""

        pub_elem = entry_elem.find("atom:published", NS)
        entry["published"] = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

        authors = []
        for author_elem in entry_elem.findall("atom:author", NS):
            name_elem = author_elem.find("atom:name", NS)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())
        entry["authors"] = authors

        entries.append(entry)

    total_elem = root.find("opensearch:totalResults", NS)
    total = int(total_elem.text) if total_elem is not None and total_elem.text else 0
    return entries, total


def _is_duplication_withdrawal(comment: str, summary: str) -> Tuple[bool, str]:
    text = f"{comment} {summary}"
    if _NON_DUP_RE.search(text):
        dup_match = _DUP_RE.search(text)
        if dup_match:
            return True, dup_match.group(0)
        return False, ""
    dup_match = _DUP_RE.search(text)
    if dup_match:
        return True, dup_match.group(0)
    return False, ""


def _check_latex_availability(arxiv_id: str) -> dict:
    """Check LaTeX source for v1 of an arXiv paper (with cache and backoff)."""
    v1_id = _to_v1_id(arxiv_id)
    cache_key = hashlib.sha256(v1_id.encode()).hexdigest()[:16]
    meta_path = CACHE_DIR / f"meta_{cache_key}.json"
    cache_path = CACHE_DIR / f"src_{cache_key}"

    # Cache hit
    if meta_path.exists():
        try:
            cached = json.loads(meta_path.read_text())
            if cached.get("source_available") or cached.get("error"):
                return cached
        except (json.JSONDecodeError, OSError):
            pass

    result = {
        "arxiv_id_v1": v1_id,
        "source_available": False,
        "main_tex_found": False,
        "num_tex_files": 0,
        "main_tex_size_kb": 0,
        "theorem_envs_found": 0,
        "proof_envs_found": 0,
        "tarball_size_kb": 0,
        "error": None,
    }

    url = ARXIV_SRC.format(arxiv_id=v1_id)
    label = f"src {v1_id}"
    try:
        resp = _arxiv_get(url, timeout=60, label=label)
    except requests.RequestException as exc:
        result["error"] = f"Download failed after backoff: {exc}"
        meta_path.write_text(json.dumps(result, indent=2))
        return result

    if "text/html" in resp.headers.get("content-type", ""):
        result["error"] = "Source not available (HTML response)"
        meta_path.write_text(json.dumps(result, indent=2))
        return result

    result["tarball_size_kb"] = round(len(resp.content) / 1024, 1)
    if len(resp.content) < 512:
        result["error"] = f"Tarball too small ({len(resp.content)} bytes)"
        meta_path.write_text(json.dumps(result, indent=2))
        return result

    if cache_path.exists():
        shutil.rmtree(cache_path)
    cache_path.mkdir(parents=True, exist_ok=True)

    tex_files = _extract_arxiv_source(resp.content, cache_path)
    if not tex_files:
        result["error"] = "No .tex files extractable"
        meta_path.write_text(json.dumps(result, indent=2))
        return result

    result["source_available"] = True
    result["num_tex_files"] = len(tex_files)
    tex_files.sort(key=lambda p: p.stat().st_size, reverse=True)
    main_tex = tex_files[0]
    result["main_tex_found"] = True
    result["main_tex_size_kb"] = round(main_tex.stat().st_size / 1024, 1)

    try:
        content = main_tex.read_text(encoding="utf-8", errors="replace")
        result["theorem_envs_found"] = len(THEOREM_RE.findall(content))
        result["proof_envs_found"] = len(PROOF_RE.findall(content))
    except Exception as exc:
        result["error"] = f"Read error: {exc}"

    meta_path.write_text(json.dumps(result, indent=2))
    return result


# ── Main pipeline ──────────────────────────────────────────────────────

def search_and_filter(
    max_to_check: int = 200,
    target_candidates: int = 40,
    delay: float = 3.0,
) -> List[dict]:
    """Query arXiv for math withdrawn papers, filter for duplication reasons."""
    candidates: List[dict] = []
    start = 0
    batch_size = 100

    while len(candidates) < target_candidates and start < max_to_check:
        query = "cat:math.* AND co:withdrawn"
        logger.info("Querying arXiv: start=%d", start)
        entries, total = _search_arxiv(query, start=start, max_results=batch_size)
        logger.info("Got %d entries (total=%d)", len(entries), total)

        if not entries:
            break

        for entry in entries:
            comment = entry.get("comment", "")
            summary = entry.get("summary", "")
            is_dup, matched = _is_duplication_withdrawal(comment, summary)

            if is_dup:
                year = entry.get("published", "")[:4]
                candidates.append({
                    "arxiv_id": entry["arxiv_id"],
                    "title": entry["title"],
                    "primary_category": entry["primary_category"],
                    "categories": entry["categories"],
                    "year": year,
                    "comment": comment,
                    "summary": summary,
                    "matched_pattern": matched,
                    "authors": entry.get("authors", []),
                })
                logger.info(
                    "✓ %s | %s | matched: '%s'",
                    entry["arxiv_id"], entry["primary_category"], matched,
                )

        start += batch_size
        if start < max_to_check and len(candidates) < target_candidates:
            logger.debug("Pausing %.1fs between batches (courtesy delay)", delay)
            time.sleep(delay)

    logger.info("Found %d duplication-withdrawal candidates", len(candidates))
    return candidates


def run_feasibility(candidates: List[dict], delay: float = 3.0) -> List[dict]:
    """Check LaTeX source availability for all candidates (resumable via cache)."""
    results = []
    for i, cand in enumerate(candidates):
        arxiv_id = cand["arxiv_id"]
        v1_id = _to_v1_id(arxiv_id)
        cache_key = hashlib.sha256(v1_id.encode()).hexdigest()[:16]
        meta_path = CACHE_DIR / f"meta_{cache_key}.json"

        # Check if already cached
        if meta_path.exists():
            try:
                cached = json.loads(meta_path.read_text())
                if cached.get("source_available") or cached.get("error"):
                    logger.info("[%d/%d] %s (cached)", i + 1, len(candidates), arxiv_id)
                    cand["feasibility"] = cached
                    results.append(cand)
                    continue
            except (json.JSONDecodeError, OSError):
                pass

        logger.info("Feasibility [%d/%d]: %s", i + 1, len(candidates), arxiv_id)
        feasibility = _check_latex_availability(arxiv_id)
        cand["feasibility"] = feasibility
        results.append(cand)

        if i < len(candidates) - 1:
            time.sleep(delay)
    return results


# ── Entry point ────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build retracted candidates dataset")
    parser.add_argument("--max-check", type=int, default=200)
    parser.add_argument("--target", type=int, default=40)
    parser.add_argument("--skip-feasibility", action="store_true")
    parser.add_argument("--output", type=str, default="config/retracted_candidates.yaml")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Seconds between consecutive arXiv requests (default: 3.0)")
    args = parser.parse_args()

    print("=" * 70)
    print("FASE 1: Searching arXiv for math withdrawn papers (duplication)")
    print(f"        Delay: {args.delay}s, Backoff: {_BACKOFF_SCHEDULE}")
    print("=" * 70)

    candidates = search_and_filter(
        max_to_check=args.max_check,
        target_candidates=args.target,
        delay=args.delay,
    )
    print(f"\nFound {len(candidates)} duplication-withdrawal candidates.\n")

    if not args.skip_feasibility:
        print("=" * 70)
        print("FASE 2: Checking LaTeX source availability (resumable)")
        print("=" * 70)
        candidates = run_feasibility(candidates, delay=args.delay)

    # ── Build YAML ──────────────────────────────────────────────────
    yaml_data = {
        "source": "arXiv API — math.* withdrawn papers filtered for duplication",
        "source_paper": "Rao et al. 2024 (arXiv:2412.03775) — WithdrarXiv dataset reference",
        "total_candidates": len(candidates),
        "filter_patterns": DUPLICATION_PATTERNS,
        "candidates": [],
    }

    viable_count = 0
    for cand in candidates:
        feas = cand.get("feasibility", {})
        source_ok = feas.get("source_available", False)
        tex_ok = feas.get("main_tex_found", False)
        has_theorems = feas.get("theorem_envs_found", 0) > 0
        viable = source_ok and tex_ok and has_theorems

        if viable:
            viable_count += 1

        entry = {
            "arxiv_id": cand["arxiv_id"],
            "title": cand["title"],
            "primary_category": cand["primary_category"],
            "categories": cand["categories"],
            "year": cand["year"],
            "withdrawal_comment": cand["comment"],
            "matched_pattern": cand["matched_pattern"],
            "authors": cand["authors"],
            "viability": {
                "arxiv_id_v1": feas.get("arxiv_id_v1", ""),
                "source_available": source_ok,
                "main_tex_found": tex_ok,
                "num_tex_files": feas.get("num_tex_files", 0),
                "main_tex_size_kb": feas.get("main_tex_size_kb", 0),
                "theorem_envs_found": feas.get("theorem_envs_found", 0),
                "proof_envs_found": feas.get("proof_envs_found", 0),
                "tarball_size_kb": feas.get("tarball_size_kb", 0),
                "error": feas.get("error"),
                "is_viable": viable,
            },
        }
        yaml_data["candidates"].append(entry)

    yaml_data["viable_count"] = viable_count

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"\n{'=' * 70}")
    print(f"Output: {output_path}")
    print(f"Total candidates: {len(candidates)}")
    print(f"Viable (LaTeX + theorems): {viable_count}")
    print(f"{'=' * 70}")

    cat_counts: dict = {}
    for cand in candidates:
        cat = cand["primary_category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    print("\nBy primary category:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    viable_by_cat: dict = {}
    for cand in candidates:
        feas = cand.get("feasibility", {})
        if feas.get("source_available") and feas.get("main_tex_found") and feas.get("theorem_envs_found", 0) > 0:
            cat = cand["primary_category"]
            viable_by_cat[cat] = viable_by_cat.get(cat, 0) + 1
    if viable_by_cat:
        print("\nViable by primary category:")
        for cat, count in sorted(viable_by_cat.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
