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

from src.novelty_v2.orchestrator import check_novelty
from src.novelty_v2.types import Verdict
from src.parser.latex_parser import parse_latex
from src.formalization.orchestrator import (
    topological_sort,
    formalize_paper,
    _extract_declarations,
)
from src.formalization.providers.config import resolve_provider
from src.formalization.providers.base import AgenticProvider
from src.formalization.providers.claude_code import ClaudeCodeProvider
from src.formalization.providers.openai_compatible import OpenAIChatProvider
from src.formalization.providers.anthropic import AnthropicProvider
from src.formalization.scripts.lean_checker import check_lean_file
from src.lean_repl import compile_check
from src.publication import submit, list_submissions, record_novel_run

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
# Ephemeral scratch project (agentic formalization)
# ═══════════════════════════════════════════════════════════════════════════
# Each agentic run formalizes into a UNIQUE, throwaway Lean project that is
# deleted (sources + compiled oleans) as soon as the run finishes. Nothing is
# cached between runs and no Papers/<name> leftovers accumulate. The output
# .lean is rebuilt from the in-memory results, so deleting the scratch loses
# nothing. Unique-per-run names also avoid concurrent clients clobbering each
# other's scratch.

def _scratch_module_name(title: str) -> str:
    """Lean module name that create_paper_project derives from a paper title."""
    from src.formalization.lean_project import slugify
    return "".join(w.capitalize() for w in slugify(title).split("_") if w)


def _wipe_scratch(lean_project_dir: Path, title: str) -> None:
    """Delete a scratch project's sources and compiled oleans (best-effort)."""
    import shutil as _shutil
    module = _scratch_module_name(title)
    if not module:
        return
    base = Path(lean_project_dir)
    for p in (
        base / "Papers" / module,
        base / ".lake" / "build" / "lib" / "Papers" / module,
    ):
        _shutil.rmtree(p, ignore_errors=True)

# ═══════════════════════════════════════════════════════════════════════════
# API key resolution
# ═══════════════════════════════════════════════════════════════════════════

def resolve_api_key(user_key: str = "") -> str:
    """Use user-provided key if given, otherwise fall back to server key."""
    key = (user_key or "").strip()
    if key:
        return key
    return SERVER_API_KEY


# Providers a client can pick with their OWN API key: name -> (base_url,
# default_model). "anthropic"/"claude" is special-cased to AnthropicProvider.
# Note: the "Claude" option here means the Anthropic API (client's Anthropic
# key) — NOT the Claude Code CLI, which is OAuth-only and server-local.
CLIENT_PROVIDERS: Dict[str, tuple] = {
    "opencode": ("https://opencode.ai/zen/go/v1", "deepseek-v4-pro"),
    "openrouter": ("https://openrouter.ai/api/v1", "anthropic/claude-sonnet-4"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-pro"),
    "openai": ("https://api.openai.com/v1", "gpt-4o"),
    "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat"),
    "mistral": ("https://api.mistral.ai/v1", "mistral-large-latest"),
}


def build_client_provider(provider_name: str, api_key: str, model: str = ""):
    """Build a per-request ModelProvider from a client's provider choice + key.

    The key is used only for this single request — never stored, never logged.
    Returns None if provider_name or api_key is empty; raises ValueError on an
    unknown provider name.
    """
    name = (provider_name or "").strip().lower()
    key = (api_key or "").strip()
    if not name or not key:
        return None
    if name in ("anthropic", "claude"):
        return AnthropicProvider(api_key=key, model=(model or "claude-sonnet-4-20250514"))
    if name in CLIENT_PROVIDERS:
        base_url, default_model = CLIENT_PROVIDERS[name]
        return OpenAIChatProvider(api_key=key, base_url=base_url, model=(model or default_model))
    raise ValueError(f"Unknown provider: {provider_name}")


# ═══════════════════════════════════════════════════════════════════════════
# Formalization: LaTeX → Lean 4 (using provider abstraction + topological sort)
# ═══════════════════════════════════════════════════════════════════════════

FORMALIZE_BLOCK_PROMPT = """You are a Lean 4 expert using Mathlib 4. Formalize the following
mathematical block (statement + proof) into Lean 4 code.

Rules:
- Output ONLY valid Lean 4 code. No explanations.
- Use `import Mathlib` at the top.
- Write a proper `{keyword}` declaration with the statement and its proof.
- The proof must be complete — no `sorry`, no placeholders.
- If the block is a definition, use `def` with `:=`.
- IMPORTANT: never redeclare a name that already exists in Mathlib (e.g. `Even`,
  `Prime`, `Continuous`). Redeclaring causes a `'X' has already been declared`
  error. If the paper defines a concept Mathlib already has, give your `def` a
  fresh, unused name (e.g. prefix it, `PaperEven`) and use that name consistently
  in every later statement and proof.
- Reference previously defined theorems and definitions by their exact Lean names
  as they appear in the context below.
- Available context (already formalized above):
{context}
- Wrap your response in ```lean ... ```.

LaTeX block:
{latex}"""


def formalize_block_with_provider(
    block: dict,
    provider,
    context_lean: str = "",
    lean_project_dir: Optional[str] = None,
    max_rounds: int = 10,
    on_progress = None,
    progress_desc: str = "",
    progress_pct: int = 0,
) -> Optional[str]:
    """Formalize a single block (statement + proof) using the model provider.

    Args:
        block: parser block dict (type, content_latex, proof_latex).
        provider: ModelProvider instance.
        context_lean: previously formalized Lean declarations.
        lean_project_dir: path to lean_project/ for compilation (optional).
        max_rounds: max verification rounds.

    Returns:
        Lean code string or None.
    """
    keyword_map = {"definition": "def", "theorem": "theorem", "lemma": "lemma",
                   "proposition": "theorem", "corollary": "theorem"}
    block_type = (block.get("type") or "theorem").lower()
    keyword = keyword_map.get(block_type, "theorem")

    latex = (block.get("content_latex") or "") + "\n\n" + (block.get("proof_latex") or "")
    prompt = FORMALIZE_BLOCK_PROMPT.format(
        keyword=keyword,
        context=context_lean or "(none — this is the first declaration)",
        latex=latex[:4000],
    )

    # Create temp file inside lean project if available (so lake env lean can find it)
    if lean_project_dir and Path(lean_project_dir).exists():
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".lean", delete=False, encoding="utf-8",
            dir=str(lean_project_dir),
        )
    else:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".lean", delete=False, encoding="utf-8",
        )
    target = Path(tmp.name)
    stub = f"import Mathlib\n\n{context_lean}\n\n"
    tmp.write(stub)
    tmp.close()

    # Only attempt compilation if inside a Lean project
    can_compile = lean_project_dir and Path(lean_project_dir).exists()

    def _emit(msg: str):
        if on_progress and progress_desc:
            on_progress("formalize", f"{progress_desc} — {msg}", progress_pct)

    try:
        for round_num in range(1, max_rounds + 1):
            _emit(f"round {round_num}/{max_rounds}: asking model for Lean…")
            response = provider.generate([{"role": "user", "content": prompt}])
            if not response:
                logger.warning(f"Formalization round {round_num}: provider returned empty for {block.get('label')}")
                continue

            m = re.search(r"```(?:lean4?)?\s*\n?(.*?)\n?```", response, re.DOTALL)
            code = m.group(1).strip() if m else ""
            if not code:
                code = response.strip()

            logger.info(f"Formalization round {round_num} for {block.get('label')}: "
                       f"got {len(code)} chars, starts with: {code[:80]}")

            # Quality check: reject sorry, missing declaration, too short
            if re.search(r":=\s*(by\s+)?sorry\b", code):
                logger.info(f"Formalization round {round_num}: got sorry, retrying for {block.get('label')}")
                prompt = (
                    f"Your output contains `sorry`. This is unacceptable. "
                    f"Provide a COMPLETE proof without any sorry.\n\n"
                    f"Original task:\n{FORMALIZE_BLOCK_PROMPT.format(keyword=keyword, context=context_lean or '(none)', latex=latex[:4000])}"
                )
                continue
            if not any(kw in code for kw in ["theorem ", "lemma ", "def ", "example "]):
                logger.info(f"Formalization round {round_num}: no declaration keyword, retrying for {block.get('label')}")
                prompt = (
                    f"Your output does not contain a valid Lean declaration "
                    f"(missing `{keyword}`, `theorem`, `lemma`, or `def`). Fix it.\n\n"
                    f"Original task:\n{FORMALIZE_BLOCK_PROMPT.format(keyword=keyword, context=context_lean or '(none)', latex=latex[:4000])}"
                )
                continue

            full_code = f"import Mathlib\n\n{context_lean}\n\n{code}\n"
            target.write_text(full_code, encoding="utf-8")

            # Compile check. We compile definitions too: a definition that
            # shadows a Mathlib name (`Even`, `Prime`, …) compiles fine on its
            # own but poisons every later block's context with an
            # `already been declared` error. Catching it here lets the retry
            # loop rename the definition before it enters the context.
            if can_compile:
                _emit(f"round {round_num}/{max_rounds}: compiling in Lean…")
                # compile_check uses a resident Mathlib REPL (env 0) when the
                # pool is enabled — no per-check `import Mathlib` (~27s saved),
                # falling back to the cold check_lean_file when the pool is off
                # or unavailable. It rewrites `target` in the fallback path, so
                # `full_code` above stays the reference frame for line numbers.
                has_error, has_sorry, stdout, stderr = compile_check(
                    code, context_lean, target, lean_project_dir
                )
                logger.info(f"Compilation check: has_error={has_error}, has_sorry={has_sorry}")
                if has_error or has_sorry:
                    _emit(f"round {round_num}/{max_rounds}: Lean errors, retrying…")
                    
                    # Parse errors with context
                    from src.formalization.error_parser import (
                        parse_lean_errors, format_errors_for_llm, explain_common_errors
                    )
                    code_lines = full_code.split('\n')
                    errors = parse_lean_errors(stdout, stderr, code_lines)
                    formatted_errors = format_errors_for_llm(errors)
                    
                    # Add explanations for common errors
                    explanations = []
                    for err in errors[:3]:
                        explanation = explain_common_errors(err['message'])
                        if explanation:
                            explanations.append(f"- {err['message'][:80]}: {explanation}")
                    
                    explanation_text = ""
                    if explanations:
                        explanation_text = "\n\nCommon error patterns:\n" + "\n".join(explanations)
                    
                    prompt = (
                        f"The Lean code has compilation errors. Fix them.\n\n"
                        f"{formatted_errors}\n"
                        f"{explanation_text}\n\n"
                        f"Current code:\n```lean\n{full_code}\n```\n\n"
                        f"Rewrite the entire declaration to compile without errors or sorry. "
                        f"Pay attention to the exact line numbers and error messages."
                    )
                    continue

            logger.info(f"Formalization SUCCESS round {round_num} for {block.get('label')}")
            return code

        logger.warning(f"Formalization exhausted {max_rounds} rounds for {block.get('label')}")
        return None

    finally:
        try: target.unlink()
        except: pass


def _build_context_lean(formalized: list[tuple[str, str]]) -> str:
    """Build the context string from previously formalized blocks."""
    if not formalized:
        return ""
    return "\n\n".join(code for _, code in formalized)


# ═══════════════════════════════════════════════════════════════════════════
# Publishability check
# ═══════════════════════════════════════════════════════════════════════════

def _block_blocks_publication(r: dict) -> bool:
    """True if this block prevents the paper from being published.

    Definitions are supporting scaffolding: they are very often already
    known (e.g. `Even` is in Mathlib) and being known must NOT block a
    paper. A definition only blocks publication if it failed to formalize.
    Theorems/lemmas must be genuinely novel.
    """
    novel_verdicts = {
        Verdict.NOVEDAD_ENUNCIADO.value,
        Verdict.NOVEDAD_DEMOSTRACION.value,
    }
    if (r.get("type") or "").lower() == "definition":
        # A known definition is fine; only a formalization failure blocks.
        return r.get("veredicto") == "ERROR" or not r.get("formalized")
    return r.get("veredicto") not in novel_verdicts


def _is_publishable(results: List[dict]) -> bool:
    """A paper is publishable if every theorem/lemma is novel and at least
    one such claim exists. Definitions may be known (see
    _block_blocks_publication) without disqualifying the paper."""
    if not results:
        return False
    if any(_block_blocks_publication(r) for r in results):
        return False
    # Require at least one novel claim — a paper of only definitions is not
    # a result.
    return any((r.get("type") or "").lower() != "definition" for r in results)


# ═══════════════════════════════════════════════════════════════════════════
# Core pipeline
# ═══════════════════════════════════════════════════════════════════════════

def process_tex(
    file_obj: Any,
    api_key_input: str = "",
    progress: gr.Progress = None,
    on_progress = None,
    provider_name: str = "",
    model_name: str = "",
) -> tuple:
    """Full pipeline: .tex → parse → formalize → D2 → D1 → verdicts.

    Returns:
        (summary_dict, results_list, lean_file_path, publication_html)
    """
    if file_obj is None:
        return (
            {"error": "No file uploaded"},
            [],
            None,
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
            None,
            "<p style='color:#d98c95'>Parser error.</p>",
        )

    if not blocks:
        return (
            {"error": "No mathematical blocks found"},
            [],
            None,
            "<p style='color:#9a988f'>No theorems found in file.</p>",
        )

    # ── 2. Topological sort + formalization ────────────────────────────────
    if on_progress: on_progress("sort", "Sorting blocks by dependencies...", 10)
    ordered = topological_sort(blocks)
    logger.info(f"Ordered {len(ordered)} blocks (topological sort)")

    # Resolve provider: the client's own provider+key when supplied (transient,
    # never stored or logged), otherwise the server default (DeepSeek V4 Pro).
    try:
        pname = (provider_name or "").strip().lower()
        if pname in ("claude-code", "claude-cli", "claude-oauth"):
            # Claude Code CLI: agentic, OAuth, server-local — no API key. It
            # formalizes via the orchestrator's agentic path. Requires `claude`
            # on PATH (see run_local_demo.ps1 / deploy notes).
            provider = ClaudeCodeProvider(model=(model_name or None))
            logger.info("Using agentic Claude Code (OAuth) provider")
        elif provider_name and api_key_input.strip():
            provider = build_client_provider(provider_name, api_key_input, model=model_name)
            logger.info(f"Using client provider: {provider_name} model={model_name or '(default)'} ({type(provider).__name__})")
        else:
            provider = resolve_provider()
            logger.info(f"Using server default provider: {type(provider).__name__}")
    except Exception as e:
        logger.warning(f"Provider not available: {e}")
        provider = None
    is_agentic = isinstance(provider, AgenticProvider)
    lean_dir = str(LEAN_PROJECT_DIR) if LEAN_PROJECT_DIR.exists() else None

    results: List[dict] = []
    n = len(ordered)
    errors = 0
    formalized_count = 0
    formalized_context: list[tuple[str, str]] = []  # (label, lean_code)

    # Agentic providers (Claude Code, OpenCode) run their own read-error/retry
    # loop against a Lean project. Instead of the chat-style per-block loop
    # (formalize_block_with_provider, which needs provider.generate()), we
    # delegate the whole paper to the orchestrator once, then map each verified
    # block's Lean back into the per-block novelty pass below.
    agentic_formalized: dict[str, str] = {}
    if FORMALIZATION_ENABLED and is_agentic:
        # Remap the orchestrator's own 0-100 progress into the demo's 12-58%
        # band, so per-block events stream live to the page without the bar
        # jumping around.
        fp_progress = None
        if on_progress:
            on_progress("formalize", "Starting agentic formalization…", 12)

            def fp_progress(step, msg, pct):
                on_progress(step, msg, 12 + int(0.46 * pct))

        # Unique, throwaway project name for this run — deleted in `finally`.
        import uuid as _uuid
        scratch_title = f"Run {_uuid.uuid4().hex[:12]}"
        try:
            fp_summary = formalize_paper(
                tex_path=tex_path,
                paper_title=scratch_title,
                parent_project=str(LEAN_PROJECT_DIR) if LEAN_PROJECT_DIR.exists() else None,
                resume=False,
                # formalize_paper rebuilds the provider from `model`; map the
                # agentic Claude Code provider to the orchestrator's "claude".
                model=("claude" if isinstance(provider, ClaudeCodeProvider) else None),
                on_progress=fp_progress,
            )
            blocks_dir = Path(fp_summary["project_dir"]) / "Blocks"
            for r in fp_summary.get("results", []):
                if "verified" not in (r.get("status") or ""):
                    continue
                bf = blocks_dir / f"{r.get('lean_name', '')}.lean"
                if bf.exists():
                    code = _extract_declarations(bf).strip()
                    if code and r.get("label"):
                        agentic_formalized[r["label"]] = code
            logger.info(
                f"Agentic formalization: {len(agentic_formalized)} verified block(s)"
            )
        except Exception as e:
            logger.exception("Agentic formalization failed")
            if on_progress:
                on_progress("formalize", f"Agentic formalization error: {e}", 12)
        finally:
            # Ephemeral: remove the scratch project so nothing accumulates.
            _wipe_scratch(LEAN_PROJECT_DIR, scratch_title)

    # Progress band for the novelty phase: if we ran up-front agentic
    # formalization (which occupies ~12-58%), novelty lives in 60-95%.
    # Otherwise (API path, which formalizes inline) keep the original band.
    if FORMALIZATION_ENABLED and is_agentic:
        nov_base, nov_span = 60, 35
    else:
        nov_base, nov_span = 10, 75

    for i, block in enumerate(ordered):
        label = block.get("label") or f"block_{i}"
        title = block.get("title") or label
        latex = block.get("content_latex", "")
        pct = nov_base + nov_span * (i / n)
        deps = block.get("references") or []

        # Build context from previously formalized blocks that this one depends on
        context = _build_context_lean(formalized_context)

        # --- Formalization ---
        lean_stmt = None
        formalized = False
        if FORMALIZATION_ENABLED and provider is not None and (latex.strip() or block.get("proof_latex")):
            if is_agentic:
                # Formalized up-front by the orchestrator; pick up the result.
                lean_stmt = agentic_formalized.get(label)
                if on_progress:
                    state = "formalized" if lean_stmt else "not formalized"
                    on_progress("formalize", f"[{i+1}/{n}] {title}: {state} (agentic)", int(pct))
            else:
                if progress:
                    progress(pct / 100.0, desc=f"Formalizing [{i+1}/{n}]: {title}")
                if on_progress:
                    dep_str = f" (depends on: {', '.join(deps)})" if deps else ""
                    on_progress("formalize", f"Formalizing [{i+1}/{n}]: {title}{dep_str}", int(pct))

                lean_stmt = formalize_block_with_provider(
                    block, provider,
                    context_lean=context,
                    lean_project_dir=lean_dir,
                    max_rounds=10,
                    on_progress=on_progress,
                    progress_desc=f"Formalizing [{i+1}/{n}]: {title}",
                    progress_pct=int(pct),
                )

            if lean_stmt is not None:
                formalized = True
                formalized_count += 1
                formalized_context.append((label, lean_stmt))

        # --- D2 + D1 via orchestrator ---
        if on_progress: on_progress("novelty", f"Checking novelty [{i+1}/{n}]: {title}", int(pct)+5)
        try:
            verdict = check_novelty(
                block=block,
                lean_statement=lean_stmt or latex[:2000],
                lean_project_dir=str(LEAN_PROJECT_DIR) if LEAN_PROJECT_DIR.exists() else None,
                use_cache=True,
            )
            mapped = {
                "block_id": i,
                "label": label,
                "title": title,
                "type": block.get("type", ""),
                "content_preview": (block.get("content_latex") or "")[:300],
                "veredicto": verdict.veredicto.value,
                "detail": verdict.razonamiento or "",
                "lean_statement": lean_stmt,
                "formalized": formalized,
                "match_C_F": verdict.d1.match_C_F if verdict.d1 else None,
                "match_C_I": verdict.d1.match_C_I if verdict.d1 else None,
            }
        except Exception as e:
            logger.exception(f"Novelty check failed for {label}")
            mapped = {
                "block_id": i,
                "label": label,
                "title": title,
                "type": block.get("type", ""),
                "content_preview": (block.get("content_latex") or "")[:300],
                "veredicto": "ERROR",
                "detail": str(e),
                "lean_statement": lean_stmt,
                "formalized": formalized,
                "match_C_F": None,
                "match_C_I": None,
            }
            errors += 1

        results.append(mapped)
        logger.info(f"  {label}: {mapped['veredicto']} (formalized={formalized})")

    if progress:
        progress(1.0, desc="Done.")

    # Build downloadable Lean file
    lean_path = _build_lean_file(results, tex_path)

    # Auto-persist the journal's authoritative record IF the paper passed and
    # was verified novel. Personal data stays empty here; the publish form
    # enriches this same record later (by submission_id). We never lose a novel
    # result, even if the author walks away without submitting.
    submission_id = None
    if _is_publishable(results):
        try:
            counts: Dict[str, int] = {}
            for r in results:
                v = r.get("veredicto", "ERROR")
                counts[v] = counts.get(v, 0) + 1
            rec = record_novel_run(
                tex_path=tex_path,
                lean_path=lean_path,
                verdicts={"total": len(results), "counts": counts},
                n_theorems=len(results),
                title=Path(tex_path).stem,
            )
            submission_id = rec["id"]
            logger.info(f"Novel run auto-recorded as {submission_id}")
        except Exception:
            logger.exception("Failed to auto-record novel run")

    summary = _build_summary(results, formalized_count)
    if submission_id:
        summary["submission_id"] = submission_id
    pub_html = _build_publication_section(results, tex_path, submission_id)

    return (summary, results, lean_path, pub_html)


def _build_lean_file(results: List[dict], tex_path: str) -> str | None:
    """Build a clean .lean file from all successfully formalized blocks.

    Cleans up: removes sorry, duplicate imports, incomplete statements.
    Returns the path to the generated file, or None if no blocks were formalized.
    """
    clean_blocks = []
    seen_imports = set()

    for r in results:
        code = r.get("lean_statement", "")
        if not code or not r.get("formalized"):
            continue

        # Extract import lines
        imports = re.findall(r"^import\s+.*$", code, re.MULTILINE)
        for imp in imports:
            seen_imports.add(imp.strip())

        # Remove import lines from body
        body = re.sub(r"^import\s+.*\n?", "", code, flags=re.MULTILINE).strip()

        # Strip `:= sorry`, `:= by sorry`
        body = re.sub(r":=\s*(by\s+)?sorry\b.*", "", body, flags=re.MULTILINE).strip()

        if body:
            clean_blocks.append(body)

    if not clean_blocks:
        return None

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


def _build_publication_section(
    results: List[dict], tex_path: str, submission_id: Optional[str] = None
) -> str:
    """Build interactive publication form HTML.

    `submission_id` links the publish form back to the auto-recorded novel run
    so the author's data enriches that same DB row instead of creating a
    duplicate.
    """
    if not results:
        return ""

    publishable = _is_publishable(results)
    filename = Path(tex_path).name
    sid = submission_id or ""

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
            <button onclick="submitPublication('{filename}', '{sid}')" style="font-family:Inter,sans-serif;font-size:14px;font-weight:500;padding:10px 20px;background:#111110;color:#fff;border:1px solid #111110;cursor:pointer">&#x1F4EC; Submit for Publication</button>
            <button onclick="this.closest('.pub-section').remove()" style="font-family:Inter,sans-serif;font-size:13px;padding:10px 16px;background:transparent;color:#73726c;border:1px solid #cfcec8;cursor:pointer">Not now</button>
          </div>
          <div id="pub-result" style="margin-top:12px;font-family:Inter,sans-serif;font-size:13px"></div>
        </div>
        """
    else:
        failed = [r for r in results if _block_blocks_publication(r)]
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
