"""
AViD Journal — Demo backend (full pipeline: formalization + D2 + D1).
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("avid-demo")

# ═══════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════

LEAN_PROJECT_DIR = Path(os.environ.get("LEAN_PROJECT_DIR", REPO_ROOT / "lean_project"))
OPENCODE_GO_API_KEY = os.environ.get("OPENCODE_GO_API_KEY", "")
OPENCODE_GO_BASE_URL = os.environ.get(
    "OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1"
)
FORMALIZATION_MODEL = os.environ.get("AVID_FORMALIZATION_MODEL", "deepseek-v4-pro")
FORMALIZATION_ENABLED = os.environ.get("AVID_FORMALIZATION_ENABLED", "1") == "1"
D2_ENABLED = os.environ.get("AVID_D2_ENABLED", "1") == "1" and LEAN_PROJECT_DIR.exists()

# ═══════════════════════════════════════════════════════════════════════════
# Formalization: LaTeX → Lean 4
# ═══════════════════════════════════════════════════════════════════════════

FORMALIZE_PROMPT = """You are a Lean 4 expert. Translate the following LaTeX mathematical
statement into Lean 4 code using Mathlib 4.

Rules:
- Output ONLY the Lean 4 code, no explanations.
- Use `import Mathlib` at the top.
- Define the theorem using `theorem` or `lemma`.
- Use proper Mathlib 4 notation (Real, Nat, Finset, etc.).
- Do NOT include a proof — only the statement.
- Wrap your response in ```lean ... ```.

LaTeX statement:
{latex}"""


def formalize_statement(latex: str) -> Optional[str]:
    """Translate a LaTeX statement to Lean 4 using DeepSeek via OpenCode Go.

    Args:
        latex: LaTeX content of the theorem statement.

    Returns:
        Lean 4 code string, or None if formalization failed.
    """
    if not OPENCODE_GO_API_KEY:
        logger.warning("OPENCODE_GO_API_KEY not set — skipping formalization")
        return None

    prompt = FORMALIZE_PROMPT.format(latex=latex[:3000])

    try:
        resp = requests.post(
            f"{OPENCODE_GO_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENCODE_GO_API_KEY}",
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
            logger.warning(f"Formalization API error: HTTP {resp.status_code}")
            return None

        data = resp.json()
        content = data["choices"][0]["message"].get("content", "") or ""
        # DeepSeek v4: reasoning_content fallback
        if not content.strip():
            content = data["choices"][0]["message"].get("reasoning_content", "") or ""

        if not content.strip():
            return None

        # Extract Lean code from markdown fences
        m = re.search(r"```(?:lean4?)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if m:
            return m.group(1).strip()

        # No fences — return raw content if it looks like Lean
        if "theorem " in content or "lemma " in content or "import " in content:
            return content.strip()

        logger.warning("Formalization response didn't contain Lean code")
        return None

    except Exception as e:
        logger.warning(f"Formalization failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Verdict mapping
# ═══════════════════════════════════════════════════════════════════════════

def map_verdict(d1: D1Result, d2: Optional[D2Result] = None) -> dict:
    """Map D1 + D2 results to a UI-friendly verdict dict."""
    verdict = Verdict.NOVEDAD_ENUNCIADO
    status = "novel"
    detail_parts = []

    # D2 first (cheapest)
    if d2 and d2.trivial:
        verdict = Verdict.NO_NOVEDOSO_trivial
        status = "trivial"
        detail_parts.append(
            f"Closed by `{d2.tactica}` in {d2.tiempo_segundos:.1f}s. "
            f"No mathematical novelty — statement is trivial with current automation."
        )
        return _build_dict(verdict, status, " ".join(detail_parts), d1, d2)

    if d2:
        detail_parts.append(
            f"D2: not trivial (tried {len(d2.all_attempts)} tactics)."
        )

    # D1 C_F
    if d1.existe_en_C_F:
        verdict = Verdict.MATCH_ENCONTRADO_PENDIENTE_D3
        status = "known_formal"
        match = d1.match_C_F or {}
        detail_parts.append(
            f"Found in Mathlib: **{match.get('lean_name', 'unknown')}**. "
            f"Proof distance (D3) requires local LeanDojo install."
        )
        return _build_dict(verdict, status, " ".join(detail_parts), d1, d2)

    # D1 C_I
    if d1.existe_en_C_I:
        if d1.llm_judge_verdict in ("generalization", "specialization"):
            verdict = Verdict.ZONA_GRIS
            status = "gray"
            detail_parts.append(
                f"Related result found (judge: **{d1.llm_judge_verdict}**). "
                f"Human review recommended."
            )
        else:
            verdict = Verdict.CONOCIDO_LITERATURA
            status = "known_informal"
            match = d1.match_C_I or {}
            detail_parts.append(
                f"Found in literature: **{match.get('title', 'unknown')}**."
            )
        return _build_dict(verdict, status, " ".join(detail_parts), d1, d2)

    # No matches at all
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


# ═══════════════════════════════════════════════════════════════════════════
# Core pipeline
# ═══════════════════════════════════════════════════════════════════════════

def process_tex(file_obj: Any, progress: gr.Progress = None) -> dict:
    """Full pipeline: .tex → parse → formalize → D2 → D1 → verdicts.

    Args:
        file_obj: uploaded .tex file (str path or Gradio file object).

    Returns:
        dict with summary + per-theorem results.
    """
    if file_obj is None:
        return {"error": "No file uploaded", "results": []}

    tex_path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
    logger.info(f"Processing: {tex_path}")

    # ── 1. Parse ──────────────────────────────────────────────────────────
    try:
        if progress:
            progress(0.05, desc="Parsing LaTeX...")
        blocks = parse_latex(tex_path)
        logger.info(f"Parsed {len(blocks)} blocks")
    except Exception as e:
        logger.exception("Parser failed")
        return {"error": f"Parser error: {e}", "results": []}

    if not blocks:
        return {"error": "No mathematical blocks found in .tex", "results": []}

    # ── 2. Per-block pipeline ─────────────────────────────────────────────
    results: List[dict] = []
    n = len(blocks)
    errors = 0
    formalized_count = 0
    d2_skipped = not D2_ENABLED

    for i, block in enumerate(blocks):
        label = block.get("label") or f"block_{i}"
        title = block.get("title") or label
        latex = block.get("content_latex", "")
        pct = 0.05 + 0.95 * (i / n)

        # --- 2a. Formalization: LaTeX → Lean ---
        lean_stmt = None
        formalized = False
        if FORMALIZATION_ENABLED and latex.strip():
            if progress:
                progress(pct, desc=f"Formalizing: {title}")
            lean_stmt = formalize_statement(latex)
            formalized = lean_stmt is not None
            if formalized:
                formalized_count += 1
            else:
                logger.warning(f"Formalization failed for {label}")

        # --- 2b. D2: Triviality ---
        d2_result = None
        if D2_ENABLED and lean_stmt:
            if progress:
                progress(pct + 0.02, desc=f"D2 (triviality): {title}")
            try:
                d2_result = check_triviality(
                    lean_stmt,
                    lean_project_dir=str(LEAN_PROJECT_DIR),
                )
            except Exception as e:
                logger.warning(f"D2 failed for {label}: {e}")

        # --- 2c. D1: Existence ---
        if progress:
            progress(pct + 0.04, desc=f"D1 (existence): {title}")
        try:
            # Use Lean statement as query if available (more precise for Leandex)
            d1_block = dict(block)
            if lean_stmt:
                d1_block["lean_statement"] = lean_stmt
            d1_result = check_d1(d1_block)
        except Exception as e:
            logger.exception(f"D1 failed for {label}")
            errors += 1
            results.append({
                "label": label, "title": title,
                "veredicto": "ERROR", "status": "error",
                "detail": str(e)[:500],
                "content_preview": latex[:200].strip(),
                "lean_statement": lean_stmt,
                "formalized": formalized,
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

    if progress:
        progress(1.0, desc="Done.")

    summary = _build_summary(results, formalized_count, d2_skipped)

    return {
        "summary": summary,
        "results": results,
        "n_blocks": n,
        "n_errors": errors,
    }


def _build_summary(results: List[dict], formalized: int, d2_skipped: bool) -> dict:
    counts: Dict[str, int] = {}
    for r in results:
        v = r.get("veredicto", "ERROR")
        counts[v] = counts.get(v, 0) + 1

    notes = []
    if formalized < len(results):
        notes.append(f"{formalized}/{len(results)} blocks formalized successfully")
    if d2_skipped:
        notes.append("D2 (triviality) skipped — Mathlib not found")

    return {
        "total": len(results),
        "counts": counts,
        "formalized": formalized,
        "d2_enabled": D2_ENABLED,
        "notes": notes,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Gradio UI
# ═══════════════════════════════════════════════════════════════════════════

CSS = """
.gradio-container { max-width: 960px !important; margin: 0 auto; }
footer { display: none !important; }
"""

with gr.Blocks(
    title="AViD Journal — Demo",
    theme=gr.themes.Soft(primary_hue="red", secondary_hue="gray"),
    css=CSS,
) as demo:
    status_msg = ""
    if not FORMALIZATION_ENABLED:
        status_msg += "\n\n⚠️ Formalization disabled (`AVID_FORMALIZATION_ENABLED=0`)."
    if not D2_ENABLED:
        status_msg += (
            f"\n\n⚠️ D2 disabled — Mathlib not found at `{LEAN_PROJECT_DIR}`. "
            f"Install with: `lake exe cache get`"
        )

    gr.Markdown(
        f"""
        # 🔬 AViD Journal — Demo

        **Automated novelty assessment for formalized mathematics.**
        Upload a `.tex` file and get a novelty verdict for each theorem.
        {status_msg}

        **Pipeline:** Parse → Formalize (LaTeX→Lean) → D2 (triviality) → D1 (existence).
        D3 (proof distance) requires LeanDojo and runs offline.
        """
    )

    with gr.Row():
        file_input = gr.File(label="Upload .tex file", file_types=[".tex"], height=80)
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

    submit_btn.click(
        fn=process_tex,
        inputs=[file_input],
        outputs=[summary_box, results_table],
        api_name="analyze",
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
    demo.launch(server_name="0.0.0.0", server_port=7860)
