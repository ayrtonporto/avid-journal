"""D3 sobre matches informales — descarga arXiv, extracción de proof,
y orquestación de formalización de prueba ajena.

PoC: 2 papers, registro detallado en docs/scout_d3_informal.md.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# arXiv source endpoint
ARXIV_SRC_URL = "https://arxiv.org/src/{arxiv_id}"

# ---------------------------------------------------------------------------
# Download + extract .tex from arXiv
# ---------------------------------------------------------------------------

def _download_arxiv_source(arxiv_id: str, cache_dir: Path) -> Optional[Path]:
    """Download arXiv LaTeX source, cache by arXiv ID.

    Returns path to extracted directory, or None.
    """
    cache_key = hashlib.sha256(arxiv_id.encode()).hexdigest()[:16]
    cache_path = cache_dir / f"arxiv_{cache_key}"
    if cache_path.exists():
        logger.info("arXiv cache hit: %s", arxiv_id)
        # Return the main .tex file path if we cached it
        tex_files = list(cache_path.rglob("*.tex"))
        if tex_files:
            return cache_path
        # Corrupt cache: remove and re-download
        import shutil
        shutil.rmtree(cache_path)

    url = ARXIV_SRC_URL.format(arxiv_id=arxiv_id)
    logger.info("Downloading arXiv source: %s", url)

    try:
        resp = requests.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("arXiv download failed for %s: %s", arxiv_id, exc)
        return None

    # Check if we got HTML (arXiv sometimes returns "source not available" page)
    content_type = resp.headers.get("content-type", "")
    if "text/html" in content_type:
        logger.warning("arXiv returned HTML for %s — source likely unavailable", arxiv_id)
        return None

    # Save and extract
    cache_path.mkdir(parents=True, exist_ok=True)
    tar_path = cache_path / "source.tar.gz"
    tar_path.write_bytes(resp.content)

    try:
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(cache_path)
    except (tarfile.ReadError, OSError) as exc:
        logger.warning("arXiv tar extraction failed for %s: %s", arxiv_id, exc)
        return None

    logger.info("arXiv source extracted: %s → %s", arxiv_id, cache_path)
    return cache_path


def _find_main_tex(extract_dir: Path) -> Optional[Path]:
    """Find the main .tex file in an extracted arXiv source directory."""
    tex_files = list(extract_dir.rglob("*.tex"))
    if not tex_files:
        return None
    # Prefer largest file
    tex_files.sort(key=lambda p: p.stat().st_size, reverse=True)
    return tex_files[0]


# ---------------------------------------------------------------------------
# Proof extraction from LaTeX
# ---------------------------------------------------------------------------

# Theorem-like environments to recognize
_THEOREM_ENVS = r"(?:theorem|lemma|proposition|corollary|claim|conjecture|fact|definition|remark|example)"

# Pattern to find a theorem-like environment with its body
_STATEMENT_BLOCK_RE = re.compile(
    rf"\\begin\{{{_THEOREM_ENVS}\}}"
    r"(.*?)"
    rf"\\end\{{{_THEOREM_ENVS}\}}",
    re.DOTALL,
)

# Pattern for proof environment
_PROOF_BLOCK_RE = re.compile(
    r"\\begin\{proof\}(.*?)\\end\{proof\}",
    re.DOTALL,
)

# Minimum fraction of statement hint words that must appear in the env body
_MIN_WORD_OVERLAP = 0.3


def _normalize_tex(text: str) -> str:
    """Normalize LaTeX text for comparison: strip commands, normalize whitespace."""
    # Remove LaTeX commands like \mathbb, \sqrt, \frac, etc.
    # Keep only the argument content (simplified)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\{[^}]*\})*", " ", text)
    # Remove math mode delimiters
    text = re.sub(r"\$+", " ", text)
    text = re.sub(r"\\\[|\\\]|\\\(|\\\)", " ", text)
    # Remove braces
    text = text.replace("{", " ").replace("}", " ")
    # Collapse whitespace
    text = " ".join(text.split())
    return text.lower()


def _word_overlap(hint: str, candidate: str) -> float:
    """Fraction of hint words that appear in candidate text."""
    hint_words = set(_normalize_tex(hint).split())
    candidate_words = set(_normalize_tex(candidate).split())
    if not hint_words:
        return 0.0
    return len(hint_words & candidate_words) / len(hint_words)


def _extract_proof_block(
    tex_content: str,
    statement_hint: str = "",
) -> Optional[str]:
    """Extract the proof block associated with a matched theorem statement.

    Two-capas approach:
      1. Find all theorem-like environments, match the one whose body best
         matches the statement_hint from TheoremSearch.
      2. Take the \\begin{proof}...\\end{proof} IMMEDIATELY after that env.
         If another theorem env appears before the proof → no proof associated.

    Safety net: if the best match is below _MIN_WORD_OVERLAP, return None.

    Args:
        tex_content: full LaTeX source.
        statement_hint: snippet of the theorem statement (from TheoremSearch).

    Returns:
        Proof body text (between \\begin{proof} and \\end{proof}), or None.
    """
    if not statement_hint:
        # No hint → just take the first proof
        match = _PROOF_BLOCK_RE.search(tex_content)
        if match:
            return match.group(1).strip()
        return None

    # ── Capa 1: Find all theorem-like environments with positions ──────
    env_matches: List[Tuple[int, int, str]] = []  # (start, end, body)
    for m in _STATEMENT_BLOCK_RE.finditer(tex_content):
        env_matches.append((m.start(), m.end(), m.group(1)))

    if not env_matches:
        logger.debug("_extract_proof_block: no theorem-like environments found")
        return None

    # ── Score each environment against the statement hint ─────────────
    best_idx = -1
    best_score = 0.0
    for i, (_, _, body) in enumerate(env_matches):
        score = _word_overlap(statement_hint, body)
        if score > best_score:
            best_score = score
            best_idx = i

    # ── Safety net: threshold check ───────────────────────────────────
    if best_score < _MIN_WORD_OVERLAP:
        logger.info(
            "_extract_proof_block: best match score %.2f below threshold %.2f",
            best_score, _MIN_WORD_OVERLAP,
        )
        return None

    logger.debug(
        "_extract_proof_block: best match idx=%d score=%.2f",
        best_idx, best_score,
    )

    # ── Capa 2: Find proof immediately after the matched env ──────────
    env_end = env_matches[best_idx][1]

    # Check: is there another theorem env between our env and its proof?
    next_env_idx = best_idx + 1
    if next_env_idx < len(env_matches):
        next_env_start = env_matches[next_env_idx][0]
        # Find the next proof after our env
        proof_match = _PROOF_BLOCK_RE.search(tex_content, env_end)
        if proof_match and proof_match.start() > next_env_start:
            # The next proof comes AFTER another theorem env →
            # our matched theorem has no proof of its own
            logger.debug(
                "_extract_proof_block: matched env has no proof "
                "(next env at pos %d, next proof at pos %d)",
                next_env_start, proof_match.start(),
            )
            return None

    # Extract the proof
    proof_match = _PROOF_BLOCK_RE.search(tex_content, env_end)
    if not proof_match:
        logger.debug("_extract_proof_block: no proof found after matched env")
        return None

    proof_body = proof_match.group(1).strip()
    logger.info(
        "_extract_proof_block: extracted proof (%d chars), score=%.2f",
        len(proof_body), best_score,
    )
    return proof_body


# ---------------------------------------------------------------------------
# Fidelity check: informalize back and compare
# ---------------------------------------------------------------------------

_FIDELITY_PROMPT = """You are checking whether a formalized Lean theorem matches its
original informal statement. The formalization was auto-generated from a paper.

Original informal statement from the paper:
---
{informal_statement}
---

Formalized Lean code:
```lean
{lean_code}
```

Task: Determine if the Lean code formalizes the SAME statement as the informal one.
- Answer ONLY "MATCH" or "MISMATCH".
- Then provide a ONE-SENTENCE justification.

A MISMATCH means: the Lean code proves a DIFFERENT theorem (different hypotheses,
different conclusion, or different objects). Superficial differences in phrasing
are OK if the mathematical content is identical.
"""


def check_fidelity(
    informal_statement: str,
    lean_code: str,
    model: str = "deepseek-v4-flash",
) -> Tuple[bool, str]:
    """Check if a formalization matches the original informal statement.

    Uses LLM judge (same provider as D1) for binary fidelity check.

    Returns:
        (is_faithful, justification) where is_faithful is True if MATCH.
    """
    prompt = _FIDELITY_PROMPT.format(
        informal_statement=informal_statement,
        lean_code=lean_code[:3000],
    )

    try:
        from src.novelty.llm_judge import _call_llm
        response = _call_llm(prompt, model=model, temperature=0)
    except Exception as exc:
        logger.warning("Fidelity check LLM call failed: %s", exc)
        return False, f"LLM error: {exc}"

    response_upper = response.strip().upper()
    is_match = response_upper.startswith("MATCH") and not response_upper.startswith("MISMATCH")

    justification = response.strip()
    # Extract just the justification (remove MATCH/MISMATCH prefix)
    justification = re.sub(r"^(MATCH|MISMATCH)\s*[:\-]?\s*", "", justification, flags=re.IGNORECASE)

    return is_match, justification


# ---------------------------------------------------------------------------
# Proof delegation check
# ---------------------------------------------------------------------------

_DELEGATION_PATTERNS = [
    r"\\ref\{",           # \ref{thm:xyz}
    r"\\cite\{",           # \cite{...}
    r"\\eqref\{",          # \eqref{...}
    r"\\thref\{",          # \thref{...}
    r"\bLemma\b",          # "Lemma"
    r"\bCorollary\b",      # "Corollary"
    r"\bfollows from\b",   # "follows from"
    r"\bby the previous\b",# "by the previous"
    r"\bimmediate\b",      # "immediate consequence"
    r"\btrivial\b",        # "trivial"
    r"\bobvious\b",        # "obvious"
]

_DELEGATION_RE = re.compile("|".join(_DELEGATION_PATTERNS), re.IGNORECASE)

_SHORT_PROOF_THRESHOLD = 400  # chars


def _check_proof_delegation(proof_text: str) -> bool:
    """Check if a proof is suspiciously short or delegates to lemmas.

    A proof "delegates" if it is:
      - Very short (< 400 chars), OR
      - Consists mostly of references to other results.

    Returns True if the flag should be set.
    """
    if len(proof_text) < _SHORT_PROOF_THRESHOLD:
        return True

    # Count how much of the text is "reference-like"
    matches = _DELEGATION_RE.findall(proof_text)
    # If more than 30% of words are delegation patterns, flag it
    words = proof_text.split()
    if len(words) > 0:
        delegation_ratio = len(matches) / len(words)
        if delegation_ratio > 0.3:
            return True

    return False


# ---------------------------------------------------------------------------
# Main PoC pipeline
# ---------------------------------------------------------------------------

def process_informal_match(
    match_candidate,       # PaperCandidate from TheoremSearch
    lean_project_dir: Path,
    cache_dir: Path,
    *,
    max_attempts: int = 3,
    model: str = "deepseek-v4-flash",
) -> dict:
    """Run the full informal match → D3 pipeline for one candidate.

    Returns a dict with full results for logging.
    """
    result = {
        "arxiv_id": match_candidate.arxiv_id,
        "title": match_candidate.title,
        "statement": match_candidate.abstract[:200],
        "status": "pending",
        "attempts": [],
        "d3_jaccard": None,
        "d3_source": "informal_autoformalized",
        "flags": [],
        "error": None,
    }

    # 1) Download arXiv source
    src_dir = _download_arxiv_source(match_candidate.arxiv_id, cache_dir)
    if src_dir is None:
        result["status"] = "failed_download"
        result["error"] = "arXiv source unavailable"
        return result

    # 2) Find main .tex
    main_tex = _find_main_tex(src_dir)
    if main_tex is None:
        result["status"] = "failed_no_tex"
        result["error"] = "No .tex file found"
        return result

    tex_content = main_tex.read_text(encoding="utf-8", errors="replace")

    # 3) Extract proof
    proof_text = _extract_proof_block(tex_content, match_candidate.abstract)
    if proof_text is None:
        result["status"] = "failed_no_proof"
        result["error"] = "No \\begin{proof} found"
        return result

    result["proof_extracted"] = True
    result["proof_length"] = len(proof_text)

    # Check for proof delegation
    if _check_proof_delegation(proof_text):
        result["flags"].append("proof_delegates_to_lemmas")

    # 4) Attempt formalization (PoC: we simulate/mock for now)
    #    In production, this calls the ModelProvider
    result["status"] = "formalization_pending"
    result["note"] = (
        "PoC: formalization step requires live ModelProvider. "
        "See docs/scout_d3_informal.md for manual run results."
    )

    return result
