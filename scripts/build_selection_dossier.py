"""
Build selection dossier for retracted candidates experiment.

Reads cached LaTeX sources, extracts main theorems, queries TheoremSearch,
and produces docs/selection_dossier.md with per-candidate evidence fichas.

Network courtesy: 3s delay between TheoremSearch queries, exponential backoff.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple
from collections import Counter

import requests
import yaml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Constants ─────────────────────────────────────────────────────────
CACHE_DIR = Path("cache/retracted_dataset")
THEOREMSEARCH_URL = "https://api.theoremsearch.com/search"

# Theorem-like environments (expanded: includes thm, lem, prop, cor)
_THEOREM_ENVS = (
    r"(?:theorem|lemma|proposition|corollary|claim|conjecture|"
    r"thm|lem|prop|cor|fact)"
)

_STATEMENT_BLOCK_RE = re.compile(
    rf"\\begin\{{{_THEOREM_ENVS}\}}(.*?)\\end\{{{_THEOREM_ENVS}\}}",
    re.DOTALL,
)
_PROOF_BLOCK_RE = re.compile(r"\\begin\{proof\}(.*?)\\end\{proof\}", re.DOTALL)
_DEFINITION_BLOCK_RE = re.compile(r"\\begin\{definition\}(.*?)\\end\{definition\}", re.DOTALL | re.IGNORECASE)
_NEWCOMMAND_RE = re.compile(r"\\newcommand\s*\{", re.IGNORECASE)

# Delegation patterns (same as informal_match.py)
_DELEGATION_PATTERNS = [
    r"\\ref\{", r"\\cite\{", r"\\eqref\{", r"\\thref\{",
    r"\bLemma\b", r"\bCorollary\b", r"\bfollows from\b",
    r"\bby the previous\b", r"\bimmediate\b", r"\btrivial\b", r"\bobvious\b",
]
_DELEGATION_RE = re.compile("|".join(_DELEGATION_PATTERNS), re.IGNORECASE)
_SHORT_PROOF_THRESHOLD = 400  # chars

# Network courtesy
_BACKOFF_SCHEDULE = [5, 10, 20, 40, 80]
_MAX_RETRIES = len(_BACKOFF_SCHEDULE)
_RETRYABLE_STATUSES = {429, 503}


def _http_get(url: str, timeout: int = 30, label: str = "", json_data: dict = None) -> requests.Response:
    """GET/POST with exponential backoff."""
    last_exc = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            if json_data is not None:
                resp = requests.post(url, json=json_data, timeout=timeout)
            else:
                resp = requests.get(url, timeout=timeout)
            if resp.status_code in _RETRYABLE_STATUSES:
                reason = f"HTTP {resp.status_code}"
                if attempt < _MAX_RETRIES:
                    wait = _BACKOFF_SCHEDULE[attempt]
                    logger.warning("[%s] %s — backoff %d/%d, %ds", label, reason, attempt + 1, _MAX_RETRIES, wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_SCHEDULE[attempt]
                logger.warning("[%s] %s — backoff %d/%d, %ds", label, type(exc).__name__, attempt + 1, _MAX_RETRIES, wait)
                time.sleep(wait)
                continue
            raise
        except requests.RequestException as exc:
            logger.error("[%s] Non-retryable: %s", label, exc)
            raise
    raise last_exc  # type: ignore


def _to_v1_id(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", arxiv_id) + "v1"


def _normalize_tex(text: str) -> str:
    """Strip LaTeX commands for comparison."""
    text = re.sub(r"\\[a-zA-Z]+\\*?(?:\{[^}]*\})*", " ", text)
    text = re.sub(r"\$+", " ", text)
    text = re.sub(r"\\\[|\\\]|\\\(|\\\)", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    return " ".join(text.split()).lower()


def _check_delegation(proof_text: str) -> Tuple[bool, str]:
    """Check if proof delegates to lemmas. Returns (is_delegated, reason)."""
    if len(proof_text) < _SHORT_PROOF_THRESHOLD:
        return True, f"proof corta: {len(proof_text)} chars (< {_SHORT_PROOF_THRESHOLD})"
    words = proof_text.split()
    if len(words) > 0:
        matches = _DELEGATION_RE.findall(proof_text)
        ratio = len(matches) / len(words)
        if ratio > 0.3:
            return True, f"{len(matches)} patrones de delegación / {len(words)} palabras = {ratio:.1%}"
    return False, ""


def _extract_main_theorem(tex_content: str) -> dict:
    """Extract the first theorem-like environment and its proof from LaTeX.

    Returns dict with:
      - statement_raw: raw LaTeX body of first theorem
      - statement_clean: normalized version for search
      - proof_raw: raw proof body (or None)
      - proof_length_chars: int
      - proof_length_lines: int
      - is_delegated: bool
      - delegation_reason: str
      - num_theorems: total theorem envs found
      - num_definitions_before: definitions before main theorem
      - num_newcommands: \\newcommand count
      - error: str or None
    """
    result = {
        "statement_raw": None,
        "statement_clean": None,
        "proof_raw": None,
        "proof_length_chars": 0,
        "proof_length_lines": 0,
        "is_delegated": False,
        "delegation_reason": "",
        "num_theorems": 0,
        "num_definitions_before": 0,
        "num_newcommands": 0,
        "error": None,
    }

    # Find all theorem environments
    env_matches: List[Tuple[int, int, str, str]] = []  # (start, end, env_name, body)
    for m in _STATEMENT_BLOCK_RE.finditer(tex_content):
        env_name = m.group(0).split("{")[1].split("}")[0]  # crude but works
        env_matches.append((m.start(), m.end(), env_name, m.group(1)))

    if not env_matches:
        result["error"] = "no theorem-like environments found"
        return result

    result["num_theorems"] = len(env_matches)

    # Pick the first theorem/proposition/claim (skip lemmas/corollaries if possible)
    main_idx = 0
    for i, (_, _, env_name, _) in enumerate(env_matches):
        if env_name.lower() in ("theorem", "thm", "proposition", "prop", "claim"):
            main_idx = i
            break

    start, end, env_name, body = env_matches[main_idx]
    result["statement_raw"] = body.strip()
    result["statement_clean"] = _normalize_tex(body)
    result["env_name"] = env_name
    result["env_position"] = main_idx + 1  # 1-indexed

    # Count definitions before this env
    defs_before = _DEFINITION_BLOCK_RE.findall(tex_content[:start])
    result["num_definitions_before"] = len(defs_before)

    # Count newcommands in the preamble (before first theorem)
    preamble = tex_content[:env_matches[0][0]]
    result["num_newcommands"] = len(_NEWCOMMAND_RE.findall(preamble))

    # Find proof after this env
    proof_match = _PROOF_BLOCK_RE.search(tex_content, end)
    if proof_match:
        # Check no other theorem env between
        next_env_start = env_matches[main_idx + 1][0] if main_idx + 1 < len(env_matches) else len(tex_content)
        if proof_match.start() < next_env_start:
            proof_body = proof_match.group(1).strip()
            result["proof_raw"] = proof_body
            result["proof_length_chars"] = len(proof_body)
            result["proof_length_lines"] = proof_body.count("\n") + 1
            is_del, reason = _check_delegation(proof_body)
            result["is_delegated"] = is_del
            result["delegation_reason"] = reason
        else:
            result["error"] = f"proof belongs to later env (env {main_idx+1} has no proof)"
    else:
        result["error"] = "no \\begin{proof} found"

    return result


def _query_theoremsearch(statement_clean: str, delay: float = 3.0) -> dict:
    """Query TheoremSearch API. Returns dict with top_results list."""
    result = {"query": statement_clean[:200], "top_results": [], "error": None}
    try:
        resp = _http_get(
            THEOREMSEARCH_URL,
            timeout=30,
            label=f"TS {statement_clean[:50]}",
            json_data={"query": statement_clean[:500], "n_results": 5},
        )
        data = resp.json()
        theorems = data.get("theorems", data.get("results", []))
        for t in theorems[:3]:
            result["top_results"].append({
                "name": t.get("name", t.get("slogan", ""))[:100],
                "similarity": round(t.get("similarity", 0), 3),
                "paper_title": (t.get("paper", {}) or {}).get("title", "")[:120],
                "source": (t.get("paper", {}) or {}).get("source", ""),
            })
    except Exception as exc:
        result["error"] = str(exc)[:120]
    return result


# ── Main ──────────────────────────────────────────────────────────────

def build_dossier(retracted_path: str, control_path: str, output_path: str, delay: float = 3.0):
    # ── Load data ────────────────────────────────────────────────────
    with open(retracted_path, "r", encoding="utf-8") as f:
        retracted_data = yaml.safe_load(f)
    with open(control_path, "r", encoding="utf-8") as f:
        control_data = yaml.safe_load(f)

    viable = [c for c in retracted_data["candidates"] if c.get("viability", {}).get("is_viable")]
    control_map = {p["retracted_arxiv_id"]: p["controls"] for p in control_data["pairs"]}

    logger.info("Processing %d viable candidates", len(viable))

    fichas = []
    t_start = time.monotonic()

    for i, cand in enumerate(viable):
        rid = cand["arxiv_id"]
        v1_id = cand.get("viability", {}).get("arxiv_id_v1", _to_v1_id(rid))
        cache_key = hashlib.sha256(v1_id.encode()).hexdigest()[:16]
        meta_path = CACHE_DIR / f"meta_{cache_key}.json"
        src_dir = CACHE_DIR / f"src_{cache_key}"

        logger.info("[%d/%d] %s", i + 1, len(viable), rid)

        # ── Read cached LaTeX ──────────────────────────────────────
        tex_files = list(src_dir.rglob("*.tex")) if src_dir.exists() else []
        tex_content = ""
        if tex_files:
            tex_files.sort(key=lambda p: p.stat().st_size, reverse=True)
            tex_content = tex_files[0].read_text(encoding="utf-8", errors="replace")

        # ── Extract main theorem ───────────────────────────────────
        extraction = _extract_main_theorem(tex_content) if tex_content else {"error": "no cached tex"}

        # ── Query TheoremSearch ────────────────────────────────────
        ts_result = {"top_results": [], "error": "no statement to query"}
        if extraction.get("statement_clean"):
            ts_result = _query_theoremsearch(extraction["statement_clean"])
            time.sleep(delay)

        # ── Build ficha ────────────────────────────────────────────
        has_citation = "🎯 CITA AL DUPLICADOR" if cand.get("prior_work_reference") and cand["prior_work_reference"] not in ("Not cited", "Not cited specifically", "Not cited in withdrawal comment", "Unknown") else "sin cita explícita"

        controls = control_map.get(rid, [])
        control_strs = []
        for ctrl in controls:
            control_strs.append(f"[{ctrl['arxiv_id']}](https://arxiv.org/abs/{ctrl['arxiv_id']}) — *{ctrl.get('title','')[:100]}* ({ctrl.get('year','')})")

        ficha = {
            "arxiv_id": rid,
            "v1_id": v1_id,
            "title": cand["title"],
            "category": cand["primary_category"],
            "year": cand["year"],
            "authors": ", ".join(cand.get("authors", [])[:5]),
            "withdrawal_comment": cand["withdrawal_comment"],
            "prior_work": cand.get("prior_work_reference", "Not cited"),
            "has_citation": has_citation,
            "has_citation_bool": "🎯" in has_citation,
            "extraction": extraction,
            "theoremsearch": ts_result,
            "controls": controls,
            "control_strs": control_strs,
        }
        fichas.append(ficha)

    t_elapsed = time.monotonic() - t_start

    # ── Sort: 🎯 first, then by proof length ascending ──────────────
    fichas.sort(key=lambda f: (not f["has_citation_bool"], f["extraction"].get("proof_length_chars", 99999)))

    # ── Generate Markdown ──────────────────────────────────────────
    lines = []
    lines.append("# Selection Dossier — Retracted Candidates")
    lines.append("")
    lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M UTC-3')}  ")
    lines.append(f"**Total candidates:** {len(fichas)}  ")
    lines.append(f"**With duplication citation:** {sum(1 for f in fichas if f['has_citation_bool'])}  ")
    lines.append(f"**Elapsed:** {round(t_elapsed)}s")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Summary Table")
    lines.append("")
    lines.append("| # | arXiv ID | Year | Category | Duplicator cited? | Proof len | Delegation? | Best TS score |")
    lines.append("|---|----------|------|----------|-------------------|-----------|-------------|---------------|")
    for i, f in enumerate(fichas):
        ext = f["extraction"]
        proof_len = f"{ext.get('proof_length_chars', 0)}c" if ext.get("proof_raw") else "N/A"
        deleg = "⚠️ delegada" if ext.get("is_delegated") else ""
        best_ts = f["theoremsearch"]["top_results"]
        best_score = f"{best_ts[0]['similarity']:.2f}" if best_ts else "N/A"
        citation_mark = "🎯 YES" if f["has_citation_bool"] else "no"
        lines.append(
            f"| {i+1} | [{f['arxiv_id']}](https://arxiv.org/abs/{f['arxiv_id']}) "
            f"| {f['year']} | {f['category']} | {citation_mark} | {proof_len} | {deleg} | {best_score} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Fichas")
    lines.append("")

    for i, f in enumerate(fichas):
        ext = f["extraction"]
        ts = f["theoremsearch"]

        lines.append(f"### {i+1}. {f['arxiv_id']} — {f['title']}")
        lines.append("")
        lines.append(f"**Categoría:** {f['category']} | **Año:** {f['year']} | **v1:** `{f['v1_id']}`  ")
        lines.append(f"**Autores:** {f['authors']}  ")
        lines.append(f"**Link:** [arxiv.org/abs/{f['arxiv_id']}](https://arxiv.org/abs/{f['arxiv_id']})")
        lines.append("")

        # 2. Evidencia de retiro
        lines.append("#### 2. Evidencia de retiro")
        lines.append("")
        lines.append(f"> {f['withdrawal_comment']}")
        lines.append("")
        lines.append(f"**{f['has_citation']}**")
        lines.append("")

        # 3. Teorema principal
        lines.append("#### 3. Teorema principal")
        lines.append("")
        statement_error = ext.get("error") if ext.get("error") and not ext.get("statement_raw") else None
        proof_error = ext.get("error") if ext.get("error") and ext.get("statement_raw") else None

        # Show statement even if proof extraction failed
        if ext.get("statement_raw"):
            env_name = ext.get("env_name", "theorem")
            env_pos = ext.get("env_position", 1)
            statement = ext["statement_raw"]
            stmt_preview = statement[:800].replace("\n", " ").replace("  ", " ")
            if len(statement) > 800:
                stmt_preview += f" ... (+{len(statement)-800} chars)"
            lines.append(f"**Entorno:** `\\begin{{{env_name}}}` (#{env_pos} de {ext.get('num_theorems', 0)} total)")
            lines.append("")
            lines.append("```latex")
            lines.append(stmt_preview)
            lines.append("```")
            if proof_error:
                lines.append("")
                lines.append(f"⚠️ **Extracción del proof fallida:** {proof_error}")
        elif statement_error:
            lines.append(f"⚠️ **Extracción fallida:** {statement_error}")
        else:
            lines.append("⚠️ Sin contenido LaTeX cacheado.")
        lines.append("")

        # 4. Autocontención
        lines.append("#### 4. Evidencia de autocontención")
        lines.append("")
        lines.append(f"- `\\newcommand` en el preámbulo: **{ext.get('num_newcommands', 0)}**")
        lines.append(f"- `\\begin{{definition}}` antes del teorema principal: **{ext.get('num_definitions_before', 0)}**")
        lines.append("")

        # 5. Longitud del proof
        lines.append("#### 5. Longitud de la prueba")
        lines.append("")
        if ext.get("proof_raw"):
            lines.append(f"- Longitud: **{ext['proof_length_chars']} caracteres, {ext['proof_length_lines']} líneas**")
            if ext.get("is_delegated"):
                lines.append(f"- ⚠️ **Flag `proof_delegates_to_lemmas`:** {ext['delegation_reason']}")
            else:
                lines.append("- No dispara el flag de delegación")
        else:
            lines.append("- Sin proof explícito (ver error en §3)")
        lines.append("")

        # 6. Cobertura Mathlib
        lines.append("#### 6. Cobertura Mathlib (TheoremSearch top-3)")
        lines.append("")
        if ts.get("error"):
            lines.append(f"⚠️ TheoremSearch error: {ts['error']}")
        elif ts["top_results"]:
            lines.append("| # | Name | Score | Source |")
            lines.append("|---|------|-------|--------|")
            for r in ts["top_results"]:
                lines.append(f"| | {r['name']} | {r['similarity']:.3f} | {r.get('source','?')} |")
        else:
            lines.append("Sin resultados de TheoremSearch.")
        lines.append("")

        # 7. Controles
        lines.append("#### 7. Controles asignados")
        lines.append("")
        if f["control_strs"]:
            for cs in f["control_strs"]:
                lines.append(f"- {cs}")
        else:
            lines.append("Sin controles asignados.")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Write
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Wrote dossier to %s (%d fichas)", output_path, len(fichas))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--retracted", default="config/retracted_candidates.yaml")
    parser.add_argument("--control", default="config/control_candidates.yaml")
    parser.add_argument("--output", default="docs/selection_dossier.md")
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if args.limit > 0:
        # Quick test with limited candidates
        with open(args.retracted, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        viable = [c for c in data["candidates"] if c.get("viability", {}).get("is_viable")]
        data["candidates"] = viable[:args.limit]
        tmp_path = "config/_retracted_limited.yaml"
        with open(tmp_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        args.retracted = tmp_path

    build_dossier(args.retracted, args.control, args.output, delay=args.delay)
