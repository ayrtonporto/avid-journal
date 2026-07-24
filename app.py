"""
AViD Journal — Demo backend (full pipeline: formalization + D2 + D1 + publication).
Deploy via Docker with Mathlib included.

Usage:
    python app.py          # servidor en http://localhost:7860
    docker compose up -d   # deploy con Mathlib
"""

from __future__ import annotations

import logging
import os
import re
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import gradio as gr
import requests

from src.novelty_v2.dimensions.d1_existence import check_d1, CI_SIMILARITY_THRESHOLD_A
from src.novelty_v2.dimensions.d2_triviality import check_triviality, LEAN_STARTUP_OVERHEAD_S
from src.novelty_v2.types import D1Result, D2Result, Verdict
from src.parser.latex_parser import parse_latex
from src.publication import submit, list_submissions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("avid-demo")

# ═══════════════════════════════════════════════════════════════════════════
# Config (server defaults — user can override via API key input)
# ═══════════════════════════════════════════════════════════════════════════

LEAN_PROJECT_DIR = Path(os.environ.get("LEAN_PROJECT_DIR", REPO_ROOT / "lean_project"))
SERVER_API_KEY = os.environ.get("OPENCODE_GO_API_KEY", "")
OPENCODE_GO_BASE_URL = os.environ.get(
    "OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1"
)
FORMALIZATION_MODEL = os.environ.get("AVID_FORMALIZATION_MODEL", "deepseek-v4-pro")
JUDGE_MODEL = os.environ.get("AVID_JUDGE_MODEL", "deepseek-v4-flash")
FORMALIZATION_ENABLED = os.environ.get("AVID_FORMALIZATION_ENABLED", "1") == "1"
D2_ENABLED = os.environ.get("AVID_D2_ENABLED", "1") == "1" and LEAN_PROJECT_DIR.exists()
PUBLICATION_ENABLED = True  # always on

# ═══════════════════════════════════════════════════════════════════════════
# API key resolution
# ═══════════════════════════════════════════════════════════════════════════

def resolve_api_key(user_key: str = "") -> str:
    """Use user-provided key if given, otherwise fall back to server key."""
    key = (user_key or "").strip()
    if key:
        return key
    return SERVER_API_KEY


# ═══════════════════════════════════════════════════════════════════════════
# Formalization: LaTeX → Lean 4
# ═══════════════════════════════════════════════════════════════════════════

FORMALIZE_PROMPT = """You are a Lean 4 expert. Translate the following LaTeX mathematical
statement into Lean 4 code using Mathlib 4.

Rules:
- Output ONLY the Lean 4 code, no explanations.
- Use `import Mathlib` at the top.
- Use proper Mathlib 4 notation (Real, Nat, Finset, etc.).
- Do NOT include a proof — only the statement. Never use `sorry`.
- Use `{keyword}` for the declaration.
- Wrap your response in ```lean ... ```.

LaTeX statement:
{latex}"""

FORMALIZE_RETRY_PROMPT = """Your previous translation was incomplete or contained `sorry`.
Translate this LaTeX statement to Lean 4 again. This time:
- Output ONLY valid Lean 4 code.
- Use `{keyword}` for the declaration.
- Do NOT use `sorry`, `:=`, `:= by`, or include any proof.
- Just the type signature, nothing more.
- Wrap in ```lean ... ```.

LaTeX statement:
{latex}"""


def _is_good_lean(code: str) -> bool:
    """Check if Lean code looks valid: has a declaration, no sorry, not too short."""
    if not code or len(code.strip()) < 10:
        return False
    if re.search(r":=\s*(by\s+)?sorry\b", code):
        return False
    has_decl = any(kw in code for kw in ["theorem ", "lemma ", "def ", "example "])
    return has_decl


def _call_deepseek(prompt: str, api_key: str) -> Optional[str]:
    """Make a single API call to DeepSeek and extract Lean code."""
    try:
        resp = requests.post(
            f"{OPENCODE_GO_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": FORMALIZATION_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 2048,
            },
            timeout=120,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        content = data["choices"][0]["message"].get("content", "") or ""
        if not content.strip():
            content = data["choices"][0]["message"].get("reasoning_content", "") or ""
        if not content.strip():
            return None
        m = re.search(r"```(?:lean4?)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if m:
            return m.group(1).strip()
        kw = ["theorem ", "lemma ", "def ", "example ", "import "]
        if any(k in content for k in kw):
            return content.strip()
        return None
    except Exception as e:
        logger.warning(f"DeepSeek call failed: {e}")
        return None


def formalize_statement(latex: str, api_key: str = "", block_type: str = "theorem") -> Optional[str]:
    """Translate LaTeX → Lean 4 via DeepSeek V4 Pro, with quality retry.

    Args:
        latex: LaTeX statement content.
        api_key: User-provided API key (uses server key if empty).
        block_type: 'definition', 'theorem', 'lemma', 'proposition', 'corollary'.

    Returns:
        Lean 4 code, or None if formalization failed after retries.
    """
    key = resolve_api_key(api_key)
    if not key:
        return None

    # Map block type to Lean keyword
    lean_keyword = "def" if block_type == "definition" else "theorem"

    # Attempt 1: normal prompt
    prompt = FORMALIZE_PROMPT.format(keyword=lean_keyword, latex=latex[:3000])
    code = _call_deepseek(prompt, key)
    if code and _is_good_lean(code):
        return code

    # Attempt 2: stricter retry prompt
    logger.info(f"Retrying formalization (block_type={block_type})")
    retry_prompt = FORMALIZE_RETRY_PROMPT.format(keyword=lean_keyword, latex=latex[:3000])
    code = _call_deepseek(retry_prompt, key)
    if code and _is_good_lean(code):
        return code

    # Return whatever we got on last attempt (even if imperfect)
    return code


# ═══════════════════════════════════════════════════════════════════════════
# Verdict mapping
# ═══════════════════════════════════════════════════════════════════════════

def map_verdict(d1: D1Result, d2: Optional[D2Result] = None) -> dict:
    """Map D1 + D2 results to a UI-friendly verdict dict."""
    verdict = Verdict.NOVEDAD_ENUNCIADO
    status = "novel"
    detail_parts = []

    if d2 and d2.trivial:
        verdict = Verdict.NO_NOVEDOSO_trivial
        status = "trivial"
        detail_parts.append(
            f"Closed by `{d2.tactica}` in {d2.tiempo_segundos:.1f}s. "
            f"No mathematical novelty."
        )
        return _build_dict(verdict, status, " ".join(detail_parts), d1, d2)

    if d2:
        detail_parts.append(f"D2: not trivial ({len(d2.all_attempts)} tactics tried).")

    if d1.existe_en_C_F:
        verdict = Verdict.MATCH_ENCONTRADO_PENDIENTE_D3
        status = "known_formal"
        match = d1.match_C_F or {}
        detail_parts.append(
            f"Found in Mathlib: **{match.get('lean_name', 'unknown')}**. "
            f"Proof distance (D3) requires local LeanDojo."
        )
        return _build_dict(verdict, status, " ".join(detail_parts), d1, d2)

    if d1.existe_en_C_I:
        if d1.llm_judge_verdict in ("generalization", "specialization"):
            verdict = Verdict.ZONA_GRIS
            status = "gray"
            detail_parts.append(
                f"Related result (judge: **{d1.llm_judge_verdict}**). "
                f"Human review recommended."
            )
        else:
            verdict = Verdict.CONOCIDO_LITERATURA
            status = "known_informal"
            match = d1.match_C_I or {}
            detail_parts.append(f"Found in literature: **{match.get('title', 'unknown')}**.")
        return _build_dict(verdict, status, " ".join(detail_parts), d1, d2)

    detail_parts.append("No matches in Mathlib or arXiv. Likely original.")
    return _build_dict(verdict, status, " ".join(detail_parts), d1, d2)


def _build_dict(
    verdict: Verdict, status: str, detail: str,
    d1: D1Result, d2: Optional[D2Result] = None,
) -> dict:
    d2_info = {}
    if d2:
        d2_info = {
            "trivial": d2.trivial,
            "tactica": d2.tactica,
            "tiempo_segundos": d2.tiempo_segundos,
            "attempts": [
                {"tactic": t, "success": s, "runtime": r}
                for t, s, r, _ in d2.all_attempts
            ],
        }
    return {
        "veredicto": verdict.value,
        "status": status,
        "detail": detail,
        "existe_en_C_F": d1.existe_en_C_F,
        "existe_en_C_I": d1.existe_en_C_I,
        "match_C_F": {k: str(v) for k, v in (d1.match_C_F or {}).items()},
        "match_C_I": {k: str(v) for k, v in (d1.match_C_I or {}).items()},
        "llm_judge_verdict": d1.llm_judge_verdict,
        "traduccion_incierta": d1.traduccion_incierta,
        "d2": d2_info,
    }


def _is_publishable(results: List[dict]) -> bool:
    """A paper is publishable if ALL blocks are novel (no matches, no trivial, no errors)."""
    if not results:
        return False
    publishable_verdicts = {
        Verdict.NOVEDAD_ENUNCIADO.value,
    }
    for r in results:
        if r.get("veredicto") not in publishable_verdicts:
            return False
    return True


# ═══════════════════════════════════════════════════════════════════════════
# Core pipeline
# ═══════════════════════════════════════════════════════════════════════════

def process_tex(
    file_obj: Any,
    api_key_input: str = "",
    progress: gr.Progress = None,
    on_progress = None,
) -> tuple:
    """Full pipeline: .tex → parse → formalize → D2 → D1 → verdicts.

    Returns:
        (summary_dict, results_list, publication_html)
    """
    if file_obj is None:
        return (
            {"error": "No file uploaded"},
            [],
            "<p style='color:#9a988f'>Upload a .tex file to begin.</p>",
        )

    tex_path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
    api_key = resolve_api_key(api_key_input)
    logger.info(f"Processing: {tex_path} (api_key={'user' if api_key_input.strip() else 'server'})")

    # ── 1. Parse ──────────────────────────────────────────────────────────
    try:
        if progress:
            progress(0.05, desc="Parsing LaTeX...")
        if on_progress: on_progress("parse", f"Parsing {Path(tex_path).name}...", 5)
        blocks = parse_latex(tex_path)
        logger.info(f"Parsed {len(blocks)} blocks")
    except Exception as e:
        logger.exception("Parser failed")
        return (
            {"error": f"Parser error: {e}"},
            [],
            "<p style='color:#d98c95'>Parser error.</p>",
        )

    if not blocks:
        return (
            {"error": "No mathematical blocks found"},
            [],
            "<p style='color:#9a988f'>No theorems found in file.</p>",
        )

    # ── 2. Per-block pipeline ─────────────────────────────────────────────
    results: List[dict] = []
    n = len(blocks)
    errors = 0
    formalized_count = 0

    for i, block in enumerate(blocks):
        label = block.get("label") or f"block_{i}"
        title = block.get("title") or label
        latex = block.get("content_latex", "")
        pct = 0.05 + 0.85 * (i / n)

        # --- 2a. Formalization ---
        lean_stmt = None
        formalized = False
        if FORMALIZATION_ENABLED and latex.strip() and api_key:
            if progress:
                progress(pct, desc=f"Formalizing: {title}")
            if on_progress: on_progress("formalize", f"Formalizing [{i+1}/{n}]: {title}", int(pct*100))
            lean_stmt = formalize_statement(latex, api_key, block_type=block.get("type", "theorem"))
            formalized = lean_stmt is not None
            if formalized:
                formalized_count += 1

        # --- 2b. D2 ---
        d2_result = None
        if D2_ENABLED and lean_stmt:
            if progress:
                progress(pct + 0.02, desc=f"D2: {title}")
            if on_progress: on_progress("d2", f"D2 (triviality) [{i+1}/{n}]: {title}", int(pct*100)+2)
            try:
                d2_result = check_triviality(lean_stmt, lean_project_dir=str(LEAN_PROJECT_DIR))
            except Exception as e:
                logger.warning(f"D2 failed for {label}: {e}")

        # --- 2c. D1 ---
        if progress:
            progress(pct + 0.04, desc=f"D1: {title}")
        if on_progress: on_progress("d1", f"D1 (existence) [{i+1}/{n}]: {title}", int(pct*100)+4)
        try:
            d1_block = dict(block)
            if lean_stmt:
                d1_block["lean_statement"] = lean_stmt
            # Pass api_key so LLM judge uses it
            if api_key:
                os.environ["OPENCODE_GO_API_KEY"] = api_key
            d1_result = check_d1(d1_block)
        except Exception as e:
            logger.exception(f"D1 failed for {label}")
            errors += 1
            results.append({
                "label": label, "title": title,
                "veredicto": "ERROR", "status": "error",
                "detail": str(e)[:500],
                "content_preview": latex[:200].strip(),
                "lean_statement": lean_stmt, "formalized": formalized,
            })
            continue

        # --- 2d. Map to verdict ---
        mapped = map_verdict(d1_result, d2_result)
        mapped["label"] = label
        mapped["title"] = title
        mapped["content_preview"] = latex[:200].strip()
        mapped["lean_statement"] = lean_stmt
        mapped["formalized"] = formalized
        results.append(mapped)
        logger.info(f"  {label}: {mapped['veredicto']} (formalized={formalized})")

    # Restore server key after pipeline (in case user key was set)
    if SERVER_API_KEY:
        os.environ["OPENCODE_GO_API_KEY"] = SERVER_API_KEY

    if progress:
        progress(1.0, desc="Done.")

    # Build downloadable Lean file
    lean_path = _build_lean_file(results, tex_path)

    summary = _build_summary(results, formalized_count)
    pub_html = _build_publication_section(results, tex_path)

    return (summary, results, lean_path, pub_html)


def _build_lean_file(results: List[dict], tex_path: str) -> str | None:
    """Build a clean .lean file from all successfully formalized blocks.

    Cleans up: removes sorry, duplicate imports, incomplete statements.
    Returns the path to the generated file, or None if no blocks were formalized.
    """
    import re as _re

    clean_blocks = []
    seen_imports = set()

    for r in results:
        code = r.get("lean_statement", "")
        if not code or not r.get("formalized"):
            continue

        # Extract import lines
        imports = _re.findall(r"^import\s+.*$", code, _re.MULTILINE)
        for imp in imports:
            seen_imports.add(imp.strip())

        # Remove import lines from body
        body = _re.sub(r"^import\s+.*\n?", "", code, flags=_re.MULTILINE).strip()

        # Strip `:= sorry`, `:= by sorry`, `:= sorry` with variations
        body = _re.sub(r":=\s*(by\s+)?sorry\b.*$", ":= ", body, flags=_re.MULTILINE).strip()

        # Remove trailing empty colon
        body = _re.sub(r":=\s*$", "", body).strip()

        if body:
            clean_blocks.append(body)

    if not clean_blocks:
        return None

    import tempfile
    base = Path(tex_path).stem

    lines = ["import Mathlib"] + sorted(seen_imports - {"import Mathlib"})
    content = "\n".join(lines) + "\n\n" + "\n\n".join(clean_blocks) + "\n"

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".lean", prefix=f"{base}_", delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.close()
    return tmp.name


def _build_summary(results: List[dict], formalized: int) -> dict:
    counts: Dict[str, int] = {}
    for r in results:
        v = r.get("veredicto", "ERROR")
        counts[v] = counts.get(v, 0) + 1
    notes = []
    if formalized < len([r for r in results if r.get("formalized") is not None]):
        notes.append(f"{formalized} blocks formalized successfully")
    if not D2_ENABLED:
        notes.append("D2 skipped — Mathlib not found")
    return {
        "total": len(results),
        "counts": counts,
        "formalized": formalized,
        "d2_enabled": D2_ENABLED,
        "notes": notes,
    }


def _build_publication_section(results: List[dict], tex_path: str) -> str:
    """Build interactive publication form HTML."""
    if not results:
        return ""

    publishable = _is_publishable(results)
    filename = Path(tex_path).name

    if publishable:
        return f"""
        <div class="pub-section" style="border:1px solid #7a1f2b;padding:28px;margin-top:28px;background:rgba(122,31,43,0.04);max-width:720px">
          <h3 style="color:#7a1f2b;margin-top:0;font-family:Crimson Pro,serif">&#x1F4F0; Publish in AViD Journal</h3>
          <p style="color:#3a3a37">All theorems passed novelty checks. Your paper is eligible for publication.</p>
          <div style="margin-top:18px">
            <label style="display:block;font-family:IBM Plex Mono,monospace;font-size:11px;color:#7a1f2b;margin-bottom:4px">AUTHOR NAME *</label>
            <input id="pub-author" type="text" placeholder="A. Smith" style="width:100%;padding:8px 12px;border:1px solid #cfcec8;font-family:IBM Plex Mono,monospace;font-size:13px">
          </div>
          <div style="margin-top:12px">
            <label style="display:block;font-family:IBM Plex Mono,monospace;font-size:11px;color:#7a1f2b;margin-bottom:4px">EMAIL (for confirmation)</label>
            <input id="pub-email" type="email" placeholder="author@example.com" style="width:100%;padding:8px 12px;border:1px solid #cfcec8;font-family:IBM Plex Mono,monospace;font-size:13px">
          </div>
          <div style="margin-top:12px">
            <label style="display:block;font-family:IBM Plex Mono,monospace;font-size:11px;color:#7a1f2b;margin-bottom:4px">LLM MODEL(S) USED *</label>
            <input id="pub-llm" type="text" placeholder="DeepSeek V4 Pro + Claude Sonnet 4" style="width:100%;padding:8px 12px;border:1px solid #cfcec8;font-family:IBM Plex Mono,monospace;font-size:13px">
          </div>
          <div class="pub-terms" style="margin-top:20px;padding:16px;background:#faf9f6;border:1px solid #e3e2dd;font-family:Inter,sans-serif;font-size:12.5px;color:#73726c;max-height:160px;overflow-y:auto;line-height:1.5">
            <b style="color:#111110">AViD Journal — Terms of Publication</b><br><br>
            <b>1. Originality.</b> You certify that this paper was generated by an LLM and represents a novel mathematical contribution not previously published elsewhere. The novelty has been verified by the AViD automated pipeline (D1 existence + D2 triviality).<br><br>
            <b>2. License.</b> You grant AViD Journal a non-exclusive, irrevocable, royalty-free license to publish, reproduce, distribute, and archive this paper in any medium. You retain copyright.<br><br>
            <b>3. AI Authorship Disclosure.</b> You must truthfully disclose which LLM model(s) were used. AViD Journal only publishes AI-generated mathematics. Human-authored papers will be rejected.<br><br>
            <b>4. Editorial Review.</b> Submission does not guarantee publication. All papers undergo editorial review for quality, correctness, and adherence to community standards. Review is conducted by qualified mathematicians.<br><br>
            <b>5. Plagiarism.</b> You certify that the paper does not plagiarize existing work. AViD's D1 check searches Mathlib and arXiv, but final responsibility lies with the author.<br><br>
            <b>6. Withdrawal.</b> You may withdraw your submission at any time before publication by contacting the editorial board. After publication, papers are permanently archived.<br><br>
            <b>7. Privacy.</b> Your email is used solely for communication about your submission and will not be shared with third parties.
          </div>
          <div style="margin-top:14px">
            <label style="font-family:Inter,sans-serif;font-size:13px;color:#3a3a37;display:flex;align-items:center;gap:8px">
              <input id="pub-agree" type="checkbox" style="width:16px;height:16px">
              I agree to the Terms of Publication
            </label>
          </div>
          <div style="margin-top:16px;display:flex;gap:12px">
            <button onclick="submitPublication('{filename}')" style="font-family:Inter,sans-serif;font-size:14px;font-weight:500;padding:10px 20px;background:#111110;color:#fff;border:1px solid #111110;cursor:pointer">&#x1F4EC; Submit for Publication</button>
            <button onclick="this.closest('.pub-section').remove()" style="font-family:Inter,sans-serif;font-size:13px;padding:10px 16px;background:transparent;color:#73726c;border:1px solid #cfcec8;cursor:pointer">Not now</button>
          </div>
          <div id="pub-result" style="margin-top:12px;font-family:Inter,sans-serif;font-size:13px"></div>
        </div>
        """
    else:
        failed = [r for r in results if r.get("veredicto") != Verdict.NOVEDAD_ENUNCIADO.value]
        failed_list = "".join(
            f"<li><b>{r['title']}</b>: {r['veredicto']}</li>"
            for r in failed[:5]
        )
        return f"""
        <div class="pub-section" style="border:1px solid #cfcec8;padding:24px;margin-top:28px;background:#faf9f6;max-width:720px">
          <h3 style="color:#73726c;margin-top:0;font-family:Crimson Pro,serif">&#x1F4F0; Publication not available</h3>
          <p style="color:#73726c;font-size:15px">Some theorems didn't pass all novelty checks. All must be novel to publish.</p>
          <ul style="color:#3a3a37;font-size:14px">{failed_list}</ul>
        </div>
        """


# ═══════════════════════════════════════════════════════════════════════════
# Publication handler
# ═══════════════════════════════════════════════════════════════════════════

def publish_paper(
    file_obj: Any,
    results: Any,
    author_name: str,
    paper_title: str,
    paper_abstract: str,
    author_email: str,
    llm_model: str,
    llm_strategy: str,
    llm_declaration: bool,
) -> str:
    """Submit a paper to AViD Journal."""
    if file_obj is None:
        return "❌ No file to publish."

    if not author_name.strip():
        return "❌ Author name is required."

    if not paper_title.strip():
        return "❌ Paper title is required."

    if not llm_declaration:
        return "❌ You must declare that this paper was generated by an LLM. AViD Journal only publishes AI-generated papers."

    if not llm_model.strip():
        return "❌ You must specify which LLM model(s) were used."

    tex_path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)

    # Parse verdicts from results
    verdicts = {}
    if isinstance(results, list):
        verdicts = {
            "total": len(results),
            "counts": {},
        }
        for r in results:
            if isinstance(r, dict):
                v = r.get("veredicto", "UNKNOWN")
                verdicts["counts"][v] = verdicts["counts"].get(v, 0) + 1

    try:
        record = submit(
            tex_path=tex_path,
            title=paper_title.strip(),
            authors=author_name.strip(),
            abstract=paper_abstract.strip(),
            email=author_email.strip(),
            verdicts=verdicts,
            llm_model=llm_model.strip(),
            llm_strategy=llm_strategy.strip(),
        )

        # Send confirmation email
        from src.notifications import send_submission_confirmation
        if author_email.strip():
            send_submission_confirmation(
                email=author_email.strip(),
                name=author_name.strip(),
                title=paper_title.strip(),
                submission_id=record["id"],
                llm_model=llm_model.strip(),
                n_theorems=verdicts.get("total", 0),
                verdict_summary=str(verdicts.get("counts", {})),
            )

        return (
            f"✅ **Submitted!** Your paper has been received.\n\n"
            f"**ID:** `{record['id']}`\n"
            f"**Title:** {record['title']}\n"
            f"**LLM:** {record.get('llm_model', 'N/A')}\n"
            f"**Status:** {record['status']}\n\n"
            f"📧 A confirmation email has been sent to `{record['email']}`.\n"
            f"Your paper is now under editorial review.\n"
            f"Thank you for contributing to AViD Journal."
        )
    except Exception as e:
        logger.exception("Publication failed")
        return f"❌ Publication error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# Gradio UI — Custom theme matching avid-journal.github.io
# ═══════════════════════════════════════════════════════════════════════════

CSS = """
/* ── Import landing page fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ── Root variables (matching landing page) ── */
:root {
  --maroon: #7a1f2b;
  --maroon-soft: #9c3b46;
  --maroon-lite: #d98c95;
  --ink: #111110;
  --ink-2: #3a3a37;
  --ink-3: #73726c;
  --bg: #ffffff;
  --wash: #faf9f6;
  --rule: #e3e2dd;
  --rule-2: #cfcec8;
}

/* ── Base ── */
.gradio-container {
  max-width: 960px !important;
  margin: 0 auto;
  font-family: "Crimson Pro", Georgia, serif !important;
  font-size: 18px;
  line-height: 1.62;
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
}

/* ── Headings ── */
.gradio-container h1, .gradio-container h2, .gradio-container h3,
.gradio-container .md h1, .gradio-container .md h2, .gradio-container .md h3 {
  font-family: "Crimson Pro", Georgia, serif !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em !important;
  color: var(--ink) !important;
}
.gradio-container h1 { font-size: 42px !important; line-height: 1.1 !important; }
.gradio-container h2 { font-size: 30px !important; }
.gradio-container h3 { font-size: 22px !important; }
.gradio-container .md h1 em, .gradio-container h1 em {
  font-style: italic;
  color: var(--maroon);
}

/* ── Links ── */
.gradio-container a, .gradio-container .md a {
  color: var(--maroon) !important;
  text-decoration: none;
}
.gradio-container a:hover { text-decoration: underline; text-underline-offset: 3px; }

/* ── Labels ── */
.gradio-container label, .gradio-container .label-text {
  font-family: "IBM Plex Mono", monospace !important;
  font-size: 12px !important;
  letter-spacing: .08em !important;
  text-transform: uppercase !important;
  color: var(--maroon) !important;
  font-weight: 500 !important;
}

/* ── Text inputs ── */
.gradio-container textarea, .gradio-container input[type="text"],
.gradio-container input[type="email"], .gradio-container input[type="password"] {
  font-family: "IBM Plex Mono", monospace !important;
  font-size: 14px !important;
  border: 1px solid var(--rule-2) !important;
  border-radius: 0 !important;
  background: var(--bg) !important;
  color: var(--ink) !important;
  padding: 10px 14px !important;
  transition: border-color .15s !important;
}
.gradio-container textarea:focus, .gradio-container input:focus {
  border-color: var(--maroon) !important;
  outline: none !important;
  box-shadow: 0 0 0 2px rgba(122,31,43,0.12) !important;
}

/* ── Buttons: match landing page .btn ── */
.gradio-container button, .gradio-container .btn,
.gradio-container .gr-button {
  font-family: "Inter", system-ui, sans-serif !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  padding: 11px 22px !important;
  border-radius: 0 !important;
  text-transform: none !important;
  transition: background .15s, color .15s, border-color .15s !important;
}
.gradio-container button.primary, .gradio-container .gr-button-primary {
  background: var(--ink) !important;
  color: var(--bg) !important;
  border: 1px solid var(--ink) !important;
}
.gradio-container button.primary:hover, .gradio-container .gr-button-primary:hover {
  background: var(--maroon) !important;
  border-color: var(--maroon) !important;
}
.gradio-container button.secondary {
  background: transparent !important;
  color: var(--ink) !important;
  border: 1px solid var(--ink) !important;
}
.gradio-container button.secondary:hover {
  border-color: var(--maroon) !important;
  color: var(--maroon) !important;
}

/* ── File upload: match landing page .upload ── */
.gradio-container .file-preview, .gradio-container .upload-container {
  border: 1.5px dashed var(--rule-2) !important;
  border-radius: 0 !important;
  background: var(--wash) !important;
  padding: 24px !important;
  text-align: center !important;
  font-family: "Inter", sans-serif !important;
  transition: border-color .2s !important;
}
.gradio-container .file-preview:hover {
  border-color: var(--maroon-soft) !important;
}

/* ── JSON output: terminal-style ── */
.gradio-container .json-container, .gradio-container .gr-json {
  font-family: "IBM Plex Mono", monospace !important;
  font-size: 12.5px !important;
  background: var(--ink) !important;
  color: #d9d6cc !important;
  border: 1px solid #2b2a26 !important;
  border-radius: 0 !important;
  padding: 18px !important;
  line-height: 1.7 !important;
}

/* ── Accordion: match landing page .spectrum ── */
.gradio-container .accordion {
  border: 1px solid var(--rule-2) !important;
  background: var(--wash) !important;
  border-radius: 0 !important;
}
.gradio-container .accordion > .label-wrap {
  font-family: "IBM Plex Mono", monospace !important;
  font-size: 12px !important;
  letter-spacing: .1em !important;
  text-transform: uppercase !important;
  color: var(--maroon) !important;
}

/* ── Checkbox ── */
.gradio-container .checkbox-group label, .gradio-container input[type="checkbox"] + span {
  font-family: "Inter", sans-serif !important;
  font-size: 14px !important;
  color: var(--ink-2) !important;
}

/* ── Progress bar ── */
.gradio-container .progress-bar {
  background: var(--rule) !important;
  border-radius: 0 !important;
}
.gradio-container .progress-bar .progress-fill {
  background: var(--maroon) !important;
}

/* ── Footer: hide Gradio branding ── */
footer { display: none !important; }

/* ── Markdown paragraphs ── */
.gradio-container .md p { color: var(--ink-2); max-width: 62ch; }
.gradio-container .md code {
  font-family: "IBM Plex Mono", monospace !important;
  background: var(--wash);
  border: 1px solid var(--rule);
  border-radius: 3px;
  padding: 1px 5px;
  font-size: .85em;
}
.gradio-container .md blockquote {
  border-left: 2px solid var(--maroon);
  padding-left: 16px;
  color: var(--ink-3);
  font-style: italic;
  margin: 16px 0;
}
"""

with gr.Blocks(title="AViD Journal — Demo") as demo:
    status_msg = ""
    if not FORMALIZATION_ENABLED:
        status_msg += "\n\n⚠️ Formalization disabled (`AVID_FORMALIZATION_ENABLED=0`)."
    if not D2_ENABLED:
        status_msg += (
            f"\n\n⚠️ D2 disabled — Mathlib not found at `{LEAN_PROJECT_DIR}`."
        )
    if SERVER_API_KEY:
        status_msg += "\n\n🔑 Server provides DeepSeek V4 Pro (formalization) + V4 Flash (LLM judge). Bring your own key for higher limits."

    gr.Markdown(
        f"""
        # 🔬 AViD Journal — Demo

        **Automated novelty assessment for formalized mathematics.**
        Upload a `.tex` file and get a novelty verdict for each theorem.
        {status_msg}

        **Pipeline:** Parse → Formalize (DeepSeek V4 Pro) → D2 (triviality) → D1 (existence).
        """
    )

    with gr.Row():
        with gr.Column(scale=2):
            file_input = gr.File(
                label="Upload .tex file",
                file_types=[".tex"],
                height=80,
            )
        with gr.Column(scale=1):
            api_key_input = gr.Textbox(
                label="Your OpenCode Go API Key (optional)",
                placeholder="sk-... — leave empty to use server DeepSeek V4 Pro + Flash",
                type="password",
            )

    with gr.Row():
        submit_btn = gr.Button("🔍 Analyze", variant="primary", size="lg")

    progress_bar = gr.Progress()

    with gr.Row():
        summary_box = gr.JSON(
            label="Summary",
            value={"status": "Upload a .tex file to begin"},
            scale=1,
        )

    with gr.Row():
        results_table = gr.JSON(label="Per-Theorem Results", value=[], scale=2)

    with gr.Row():
        lean_download = gr.File(label="📥 Download Formalized Lean Code", visible=True)

    # Publication section
    publication_html = gr.HTML(
        value="<p style='color:#9a988f'>Results will appear here after analysis.</p>"
    )

    with gr.Accordion("📰 Publish to AViD Journal", open=False) as pub_accordion:
        gr.Markdown(
            """
            > ⚠️ **AViD Journal publishes papers generated by LLMs only.**
            > By submitting, you declare this paper was written by an AI.
            """
        )
        with gr.Row():
            with gr.Column():
                pub_author = gr.Textbox(label="Author name(s)", placeholder="A. Smith, B. Jones")
                pub_title = gr.Textbox(label="Paper title", placeholder="On the Novelty of...")
                pub_llm_model = gr.Textbox(
                    label="LLM Model(s) used *",
                    placeholder="DeepSeek V4 Pro + Claude Sonnet 4 / GPT-4o / mixture of 3 agents...",
                )
            with gr.Column():
                pub_abstract = gr.Textbox(
                    label="Abstract (optional)",
                    placeholder="We prove that...",
                    lines=3,
                )
                pub_email = gr.Textbox(
                    label="Contact email (optional)",
                    placeholder="author@example.com",
                )
                pub_llm_strategy = gr.Textbox(
                    label="Prompt strategy / Agent architecture (optional)",
                    placeholder="Multi-agent debate, self-critique loop, chain-of-thought...",
                )
        pub_llm_declaration = gr.Checkbox(
            label="I declare this paper was generated by an LLM and meets AViD Journal's AI-only policy",
            value=False,
        )
        pub_btn = gr.Button("📬 Submit for Publication", variant="primary")
        pub_result = gr.Markdown("")

    # Wire pipeline
    submit_btn.click(
        fn=process_tex,
        inputs=[file_input, api_key_input],
        outputs=[summary_box, results_table, lean_download, publication_html],
        api_name="analyze",
    )

    # Wire publication
    pub_btn.click(
        fn=publish_paper,
        inputs=[
            file_input, results_table,
            pub_author, pub_title, pub_abstract, pub_email,
            pub_llm_model, pub_llm_strategy, pub_llm_declaration,
        ],
        outputs=[pub_result],
    )

    gr.Markdown(
        """
        ---
        **AViD Journal v1.0** · Ayrton Porto (UNICEN, Argentina) ·
        [GitHub](https://github.com/ayrtonporto/avid-journal) ·
        [Landing Page](https://avid-journal.github.io)
        """
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        css=CSS,
    )
