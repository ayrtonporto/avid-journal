"""
AViD Journal — Demo backend (D1-only).
Deploy en Hugging Face Spaces. Expone API via Gradio.

Usage:
    python app.py          # servidor local en http://localhost:7860
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List

# Asegurar que el repo root esta en sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import gradio as gr

from src.novelty_v2.dimensions.d1_existence import check_d1, CI_SIMILARITY_THRESHOLD_A
from src.novelty_v2.types import D1Result, Verdict
from src.parser.latex_parser import parse_latex

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("avid-demo")


# ── Verdict mapping (D1-only) ─────────────────────────────────────────────


def map_verdict(result: D1Result) -> dict:
    """Mapea un D1Result a un veredicto legible para la UI."""
    verdict = Verdict.NOVEDAD_ENUNCIADO
    status = "new"
    detail = ""

    if result.existe_en_C_F:
        verdict = Verdict.MATCH_ENCONTRADO_PENDIENTE_D3
        status = "known_formal"
        match = result.match_C_F or {}
        detail = (
            f"Found in Mathlib: **{match.get('lean_name', 'unknown')}**. "
            f"Proof distance (D3) requires local Lean 4 install."
        )
    elif result.existe_en_C_I:
        if result.llm_judge_verdict in ("generalization", "specialization"):
            verdict = Verdict.ZONA_GRIS
            status = "gray"
            detail = (
                f"Possible related result in arXiv. "
                f"LLM judge verdict: **{result.llm_judge_verdict}**. "
                f"Human review recommended."
            )
        else:
            verdict = Verdict.CONOCIDO_LITERATURA
            status = "known_informal"
            match = result.match_C_I or {}
            detail = (
                f"Found in literature: **{match.get('title', 'unknown')}**. "
                f"Not yet formalized in Mathlib — formalization may be a "
                f"contribution, but the result is known."
            )
    else:
        detail = "No matches found in Mathlib or arXiv literature. Likely original."

    return {
        "veredicto": verdict.value,
        "status": status,
        "detail": detail,
        "existe_en_C_F": result.existe_en_C_F,
        "existe_en_C_I": result.existe_en_C_I,
        "match_C_F": {k: str(v) for k, v in (result.match_C_F or {}).items()},
        "match_C_I": {k: str(v) for k, v in (result.match_C_I or {}).items()},
        "llm_judge_verdict": result.llm_judge_verdict,
        "traduccion_incierta": result.traduccion_incierta,
    }


# ── Core pipeline ─────────────────────────────────────────────────────────


def process_tex(file_obj: Any, progress: gr.Progress = None) -> dict:
    """Procesa un archivo .tex: parsea bloques y ejecuta D1 en cada uno.

    Args:
        file_obj: archivo subido (str path o file-like desde Gradio).

    Returns:
        dict con resultados globales y por-teorema.
    """
    if file_obj is None:
        return {"error": "No file uploaded", "results": []}

    # Resolver path: Gradio puede mandar str, Path, o file-like con .name
    if hasattr(file_obj, "name"):
        tex_path = file_obj.name
    else:
        tex_path = str(file_obj)

    logger.info(f"Processing: {tex_path}")

    # ── 1. Parse ──────────────────────────────────────────────────────────
    try:
        if progress:
            progress(0.1, desc="Parsing LaTeX...")
        blocks = parse_latex(tex_path)
        logger.info(f"Parsed {len(blocks)} blocks")
    except Exception as e:
        logger.exception("Parser failed")
        return {"error": f"Parser error: {e}", "results": []}

    if not blocks:
        return {"error": "No mathematical blocks found in .tex", "results": []}

    # ── 2. D1 per block ───────────────────────────────────────────────────
    results: List[dict] = []
    n = len(blocks)
    errors = 0

    for i, block in enumerate(blocks):
        label = block.get("label") or f"block_{i}"
        title = block.get("title") or label

        if progress:
            progress(0.1 + 0.9 * (i / n), desc=f"D1: {title}")

        try:
            d1_result = check_d1(block)
            mapped = map_verdict(d1_result)
            mapped["label"] = label
            mapped["title"] = title
            mapped["content_preview"] = (
                block.get("content_latex", "")[:200].strip()
            )
            results.append(mapped)
            logger.info(f"  {label}: {mapped['veredicto']}")
        except Exception as e:
            logger.exception(f"D1 failed for {label}")
            errors += 1
            results.append({
                "label": label,
                "title": title,
                "veredicto": "ERROR",
                "status": "error",
                "detail": str(e)[:500],
                "content_preview": block.get("content_latex", "")[:200].strip(),
            })

    if progress:
        progress(1.0, desc="Done.")

    # ── 3. Summary ────────────────────────────────────────────────────────
    summary = _build_summary(results)

    return {
        "summary": summary,
        "results": results,
        "n_blocks": n,
        "n_errors": errors,
    }


def _build_summary(results: List[dict]) -> dict:
    """Construye resumen agregado de resultados."""
    counts: Dict[str, int] = {}
    for r in results:
        v = r.get("veredicto", "ERROR")
        counts[v] = counts.get(v, 0) + 1

    return {
        "total": len(results),
        "counts": counts,
        "highlight": (
            "NOVEDAD_ENUNCIADO" if counts.get("NOVEDAD_ENUNCIADO", 0) > 0
            else "CONOCIDO_LITERATURA" if counts.get("CONOCIDO_LITERATURA", 0) > 0
            else list(counts.keys())[0] if counts else "N/A"
        ),
    }


# ── Gradio UI ─────────────────────────────────────────────────────────────

CSS = """
.gradio-container { max-width: 900px !important; margin: 0 auto; }
footer { display: none !important; }
"""

with gr.Blocks(
    title="AViD Journal — Demo",
    theme=gr.themes.Soft(primary_hue="red", secondary_hue="gray"),
    css=CSS,
) as demo:
    gr.Markdown(
        """
        # 🔬 AViD Journal — Demo

        **Automated Verification in Demonstrations.**
        Upload a `.tex` file and check if its theorems are novel
        against Mathlib and arXiv literature.

        ⚠️ This demo runs **D1 (existence check) only.**
        D2 (triviality) and D3 (proof distance) require a local
        Lean 4 + Mathlib installation. [Full pipeline →](https://github.com/ayrtonporto/avid-journal)
        """
    )

    with gr.Row():
        file_input = gr.File(
            label="Upload .tex file",
            file_types=[".tex"],
            height=80,
        )
        submit_btn = gr.Button("🔍 Analyze", variant="primary", size="lg")

    progress_bar = gr.Progress()

    with gr.Row():
        summary_box = gr.JSON(
            label="Summary",
            value={"status": "Upload a .tex file to begin"},
            scale=1,
        )

    with gr.Row():
        results_table = gr.JSON(
            label="Per-Theorem Results",
            value=[],
            scale=2,
        )

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
        [Paper (arXiv)](https://arxiv.org) ·
        [GitHub](https://github.com/ayrtonporto/avid-journal) ·
        [Landing Page](https://avid-journal.github.io)
        """
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
