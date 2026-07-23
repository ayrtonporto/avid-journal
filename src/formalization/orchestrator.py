"""
AViD Journal - Formalization Orchestrator (model-agnostic)
==========================================================
Pipeline principal: LaTeX -> (parser) -> bloques -> (topo sort) ->
por cada bloque: classify -> ModelProvider -> verificar ->
append a Paper.lean -> registrar en PAPER_INDEX.md.

La seleccion del modelo se hace por configuracion (variable de entorno
AVID_MODEL_PROVIDER o parametro explicito). El orchestrator no tiene
dependencia en ningun modelo concreto.

Uso:
    from src.formalization.orchestrator import formalize_paper

    # Usa el provider por defecto (Claude Code)
    result = formalize_paper(tex_path="paper.tex", paper_title="My Paper")

    # Usa un provider especifico
    result = formalize_paper(
        tex_path="paper.tex",
        paper_title="My Paper",
        model="deepseek",
    )
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# AViD: force UTF-8 with errors="backslashreplace" para que prints de
# salida con caracteres unicode (∃, ∀, ñ, á...) no rompan la consola
# Windows en cp1252 / cp850.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

# ── Path setup ──────────────────────────────────────────────────
# Necesitamos acceso a:
#   - prompts/ y lean_project/ (repo original)
#   - parser/ (repo local avid-clean/)
_THIS_DIR = Path(__file__).resolve().parent  # avid-clean/formalization/
_STAGING_ROOT = _THIS_DIR.parent  # avid-clean/

# 1) Asegurar que avid-clean/ está en sys.path (para imports locales como parser/)
if str(_STAGING_ROOT) not in sys.path:
    sys.path.insert(0, str(_STAGING_ROOT))

# 2) Buscar el repo original (contiene prompts/, lean_project/, src/)
_candidate = _STAGING_ROOT
_ORIGINAL_REPO: Optional[Path] = None
for _ in range(5):
    if (_candidate / "prompts").exists() and (_candidate / "lean_project").exists():
        _ORIGINAL_REPO = _candidate
        break
    _candidate = _candidate.parent
if _ORIGINAL_REPO is None:
    _ORIGINAL_REPO = _STAGING_ROOT.parents[1]  # fallback
if str(_ORIGINAL_REPO) not in sys.path:
    sys.path.insert(0, str(_ORIGINAL_REPO))

# ruff: noqa: E402
from src.formalization.complexity import (  # noqa: E402
    Mode,
    classify,
    max_rounds_for,
    prompt_file_for,
)
from src.formalization import mathlib_search  # noqa: E402
from src.formalization.lean_project import (  # noqa: E402
    AVID_REPO_ROOT,
    DEFAULT_PARENT_PROJECT,
    LeanProjectManager,
    create_paper_project,
    slugify,
)
from src.formalization.scripts.lean_checker import check_lean_file  # noqa: E402

# ── Parser: desde el paquete local avid-clean/parser/ ──────────
from parser.latex_parser import LaTeXParser  # noqa: E402

# ── Providers: import relativo desde el paquete local ──────────
from .providers import (  # noqa: E402
    ModelProvider,
    FormalizationResult,
    resolve_provider,
)

PROMPTS_DIR = _ORIGINAL_REPO / "prompts"


# ─────────────────────────────────────────────────────────────
# Identificadores Lean a partir de labels LaTeX
# ─────────────────────────────────────────────────────────────

def lean_ident_for(label: Optional[str], fallback: str = "block") -> str:
    """Convierte un label tipo 'thm:lagrange' en un identificador Lean valido.

    >>> lean_ident_for("thm:lagrange")
    'thm_lagrange'
    >>> lean_ident_for(None, fallback="unnamed_block")
    'unnamed_block'
    """
    if not label:
        return fallback
    ident = re.sub(r"[^0-9a-zA-Z_]", "_", label.strip())
    ident = re.sub(r"_+", "_", ident).strip("_")
    if not ident:
        return fallback
    if ident[0].isdigit():
        ident = "b_" + ident
    return ident


# ─────────────────────────────────────────────────────────────
# Ordenamiento topologico por dependencias
# ─────────────────────────────────────────────────────────────

def topological_sort(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ordena bloques segun sus referencias (labels -> dependencias).

    Bloques sin label o sin dependencias mantienen el orden del parser.
    Si hay un ciclo, emite un warning y devuelve el orden original.
    """
    label_to_idx: Dict[str, int] = {}
    for i, b in enumerate(blocks):
        lab = b.get("label")
        if lab:
            label_to_idx[lab] = i

    n = len(blocks)
    indeg = [0] * n
    adj: Dict[int, List[int]] = defaultdict(list)

    for i, b in enumerate(blocks):
        refs = b.get("references") or []
        for r in refs:
            if r in label_to_idx:
                src = label_to_idx[r]
                adj[src].append(i)
                indeg[i] += 1

    # Kahn: priorizamos indices bajos para estabilidad
    ready = deque(sorted(i for i in range(n) if indeg[i] == 0))
    order: List[int] = []

    while ready:
        u = ready.popleft()
        order.append(u)
        for v in sorted(adj[u]):
            indeg[v] -= 1
            if indeg[v] == 0:
                ready.append(v)

    if len(order) != n:
        print(
            f"[avid] [WARN] Dependencias ciclicas detectadas "
            f"({n - len(order)} bloques sin resolver). Se usa orden original."
        )
        return list(blocks)

    return [blocks[i] for i in order]


# ─────────────────────────────────────────────────────────────
# Renderizado de TASK.md y stubs Lean
# ─────────────────────────────────────────────────────────────

def _render_task_md(
    block: Dict[str, Any],
    lean_name: str,
    target_rel: str,
    paper_module: str,
    satisfied_deps: List[Dict[str, Any]],
) -> str:
    """Construye el contenido de TASK.md para el bloque activo."""
    label = block.get("label") or "(sin label)"
    title = block.get("title") or ""
    btype = block.get("type") or "unknown"
    statement = block.get("content_latex") or ""
    proof = block.get("proof_latex")

    deps_lines = []
    for d in satisfied_deps:
        d_label = d.get("label") or "(sin label)"
        d_name = d.get("lean_name", "")
        d_type = d.get("type", "")
        deps_lines.append(f"- `{d_label}` -> Lean name: `{d_name}` (type: {d_type})")
    deps_block = "\n".join(deps_lines) if deps_lines else "(none)"

    proof_section = (
        f"## Informal proof\n\n{proof}\n" if proof else
        "## Informal proof\n\n(no proof provided in paper)\n"
    )

    return (
        f"# Current Block\n\n"
        f"- **Label**: {label}\n"
        f"- **Type**: {btype}\n"
        f"- **Title**: {title}\n"
        f"- **Lean name**: `{lean_name}`\n"
        f"- **Target file (EDIT THIS, AND ONLY THIS)**: `{target_rel}`\n"
        f"- **Paper module imported by the target**: `{paper_module}`\n\n"
        f"## File editing rules (CRITICAL)\n\n"
        f"You MUST follow these rules. Violating them silently drops your work.\n\n"
        f"1. Edit ONLY `{target_rel}`. This is YOUR file for this session.\n"
        f"2. NEVER edit `Paper.lean`. It is read-only context with the blocks\n"
        f"   already proven in this paper. The orchestrator will append your\n"
        f"   declaration to `Paper.lean` automatically AFTER this session.\n"
        f"3. NEVER edit `PAPER_INDEX.md`. The orchestrator updates it.\n"
        f"4. Keep the existing `import {paper_module}` line at the top of the\n"
        f"   target file. That import gives you access to all dependencies\n"
        f"   listed below by their Lean names.\n"
        f"5. The body of `{target_rel}` should be ONE main declaration\n"
        f"   (`{lean_name}`) plus optional helper lemmas above it.\n\n"
        f"## Dependencies you can call (already in `Paper.lean`)\n\n"
        f"{deps_block}\n\n"
        f"## Informal statement\n\n"
        f"{statement}\n\n"
        f"{proof_section}\n"
        f"## Workflow\n\n"
        f"1. (HARD mode only) Read `docs/prompts/avid_common.md` and "
        f"`docs/prompts/avid_sketch_agent.md`.\n"
        f"2. Open `{target_rel}` and add your declaration(s).\n"
        f"3. Verify with the Lean compiler.\n"
        f"4. Iterate until there are no errors and no `sorry`.\n"
        f"5. End your response with `END_REASON:COMPLETE` (success) or "
        f"`END_REASON:LIMIT`.\n"
    )


def _render_stub_lean(
    block: Dict[str, Any],
    paper_module: str,
    lean_name: str,
) -> str:
    """Stub inicial para Blocks/<lean_name>.lean.

    El modelo edita este archivo. El stub contiene solo imports y un comentario
    con metadatos.

    Args:
        paper_module: nombre Lean completo del modulo del paper, p.ej.
                      `Papers.TinyEvensPaper.Paper` (modo compartido) o
                      `TinyEvensPaper.Paper` (modo standalone).
    """
    label = block.get("label") or ""
    btype = block.get("type") or ""
    title = block.get("title") or ""
    return (
        f"-- AViD block stub\n"
        f"-- label: {label}\n"
        f"-- type:  {btype}\n"
        f"-- title: {title}\n"
        f"-- See ../TASK.md for the informal statement and proof.\n"
        f"--\n"
        f"-- Write the formalized Lean declaration(s) below this line.\n"
        f"\n"
        f"import {paper_module}\n"
    )


# ─────────────────────────────────────────────────────────────
# Pre/post-build del modulo Paper (cachea oleans)
# ─────────────────────────────────────────────────────────────

def _lake_build_paper_module(
    parent_project: Path,
    paper_module: str,
    label: str = "(initial)",
) -> bool:
    """Ejecuta `lake build <paper_module>` en el proyecto padre.

    Por que esto importa:
    - Mathlib YA esta precompilado en `<parent_project>/.lake/packages/mathlib/`.
    - Cada vez que `lake env lean Blocks/foo.lean` arranca, lee los oleans
      necesarios. Si Papers.<Slug>.Paper ya tiene su `.olean`, Lean lo usa
      directamente y NO retypechea las declaraciones previas del paper.
    - Si NO esta compilado, Lean intenta typecheckear Paper.lean en cada
      verificacion de un bloque, multiplicando el costo.

    Esta funcion debe llamarse:
    1) Una vez al crear el proyecto (con Paper.lean vacio): pre-calienta
       el FS cache de oleans Mathlib.
    2) Despues de cada bloque verificado: refresca el olean de Paper para
       que el siguiente bloque lo encuentre cacheado.

    Returns:
        True si `lake build` completo sin error.
    """
    import subprocess

    print(f"[avid] lake build {paper_module}  (cachear olean tras: {label})")
    try:
        result = subprocess.run(
            ["lake", "build", paper_module],
            cwd=str(parent_project),
            capture_output=True,
            text=True,
            check=False,
            timeout=900,  # 15 min limite duro
        )
    except FileNotFoundError as e:
        print(f"[avid] [WARN] lake no encontrado: {e}; salto pre-build")
        return False
    except subprocess.TimeoutExpired:
        print(f"[avid] [WARN] lake build timeout; salto pre-build")
        return False

    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").splitlines()[-15:]
        print(f"[avid] [WARN] lake build fallo (rc={result.returncode}):")
        for line in tail:
            print(f"  | {line}")
        return False

    print(f"[avid] [OK] olean actualizado para {paper_module}")
    return True


# ─────────────────────────────────────────────────────────────
# Ejecucion del modelo sobre un bloque
# ─────────────────────────────────────────────────────────────

def _run_model_on_target(
    target_abs: Path,
    cwd: Path,
    prompt_file: Path,
    max_rounds: int,
    provider: ModelProvider,
    task_md_path: Path,
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """Invoca al proveedor de modelo para formalizar el bloque.

    Construye el prompt completo (archivo de prompt + TASK.md) y lo pasa
    al provider. El provider es responsable de ejecutar el modelo y escribir
    el codigo Lean en `target_abs`.

    Args:
        target_abs: path absoluto al archivo .lean que el modelo debe editar.
        cwd: directorio de trabajo (proyecto Lean del paper).
        prompt_file: archivo de prompt especifico del modo (SIMPLE/MEDIUM/HARD).
        max_rounds: presupuesto maximo de rondas.
        provider: instancia de ModelProvider a usar.
        task_md_path: path al archivo TASK.md generado.
        dry_run: si True, no se invoca ningun modelo.

    Returns:
        (success, info) donde success es bool e info es un string descriptivo
        ("COMPLETE", "LIMIT", "RATE_LIMITED", o mensaje de error).
    """
    if dry_run:
        return True, "DRY_RUN"

    # Construir prompt completo: system prompt + TASK.md
    system_prompt = prompt_file.read_text(encoding="utf-8")
    task_content = task_md_path.read_text(encoding="utf-8")
    full_prompt = f"{system_prompt}\n\n---\n\n{task_content}"

    print(f"[avid] Ejecutando modelo ({provider.__class__.__name__})...")
    result = provider.formalize(
        target_path=target_abs,
        prompt=full_prompt,
        max_rounds=max_rounds,
        cwd=cwd,
    )

    if result.info == "RATE_LIMITED":
        return False, "RATE_LIMITED"

    return result.success, result.info


# ─────────────────────────────────────────────────────────────
# Extraccion de codigo formal desde un stub verificado
# ─────────────────────────────────────────────────────────────

def _extract_declarations(target_path: Path) -> str:
    """Extrae las declaraciones Lean del archivo (omitiendo imports/comments banner).

    Estrategia minimalista: elimina lineas `import ...` y el banner inicial
    con `-- AViD block stub` si existe, pero conserva el resto.
    """
    text = target_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: List[str] = []
    skipping_banner = True

    for line in lines:
        stripped = line.strip()
        # Salta lineas de import Lean (ya estan en Paper.lean)
        if stripped.startswith("import "):
            skipping_banner = False
            continue
        # Salta el banner inicial mientras todo sea comentario
        if skipping_banner and (not stripped or stripped.startswith("--")):
            continue
        skipping_banner = False
        out.append(line)

    result = "\n".join(out).strip("\n")
    return result + "\n" if result else ""


# Tipos de bloque LaTeX que se intentan formalizar.
FORMALIZABLE_TYPES = frozenset({
    "definition",
    "theorem",
    "lemma",
    "proposition",
    "corollary",
})


def _parse_blocks_range(spec: str, total: int) -> List[int]:
    """Convierte un spec ("1-13", "5,7-9", "10") en una lista de indices
    1-based dentro de [1, total]. Indices fuera de rango se silencian.
    """
    if not spec or not spec.strip():
        return list(range(1, total + 1))

    selected: set = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, _, b = chunk.partition("-")
            a = a.strip()
            b = b.strip()
            start = int(a) if a else 1
            end = int(b) if b else total
            if start < 1:
                start = 1
            if end > total:
                end = total
            for k in range(start, end + 1):
                selected.add(k)
        else:
            k = int(chunk)
            if 1 <= k <= total:
                selected.add(k)
    return sorted(selected)


# Keywords que abren una declaracion Lean de nivel superior.
_LEAN_DECL_KEYWORDS = (
    "def", "theorem", "lemma", "axiom", "abbrev", "instance",
    "structure", "inductive", "class", "example", "notation",
    "opaque", "constant",
)
_LEAN_DECL_RE = re.compile(
    r"(?m)^\s*(?:noncomputable\s+|protected\s+|private\s+|@\[[^\]]*\]\s*)*"
    r"(?:" + "|".join(_LEAN_DECL_KEYWORDS) + r")\b"
)


def _has_real_declaration(extracted_code: str) -> bool:
    """True si el codigo extraido contiene al menos una declaracion Lean real.

    Filtra el caso en que el modelo no edita el archivo (deja solo banner +
    `import`) pero el verificador de compilacion lo da por bueno trivialmente.
    """
    if not extracted_code or not extracted_code.strip():
        return False
    return bool(_LEAN_DECL_RE.search(extracted_code))


# ─────────────────────────────────────────────────────────────
# Manejo de resultados externos (sin prueba en el paper)
# ─────────────────────────────────────────────────────────────

def _handle_external(
    block: Dict[str, Any],
    lean_name: str,
    manager: LeanProjectManager,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Busca el resultado en Mathlib; si no existe, lo declara como axioma.

    V1: `mathlib_search.lookup` siempre devuelve not_found, por lo que
    siempre se emite axioma con un placeholder de signature y fuente.
    """
    if dry_run:
        return {
            "label": block.get("label"),
            "lean_name": lean_name,
            "status": "⚠️ axiom",
            "mode": Mode.EXTERNAL.value,
            "line": 0,
            "info": "DRY_RUN",
        }

    statement = block.get("content_latex") or ""
    result = mathlib_search.lookup(statement, context={"type": block.get("type")})

    if result.found and result.mathlib_name:
        code = (
            f"-- (external) found in Mathlib as `{result.mathlib_name}`\n"
            f"-- source: Mathlib\n"
            f"abbrev {lean_name} := {result.mathlib_name}\n"
        )
        status = "✅ verified"
        source = "Mathlib"
    else:
        title = block.get("title") or ""
        lean_signature = "True  -- TODO: signature placeholder; refine manually"
        source = title or "external result (paper without proof)"
        code = (
            f"-- source: [{source}]\n"
            f"-- statement (informal): {statement[:160].replace(chr(10), ' ')}\n"
            f"axiom {lean_name} : {lean_signature}\n"
        )
        status = "⚠️ axiom"

    line_number = manager.append_block(code)
    manager.register_block(
        label=block.get("label") or lean_name,
        block_type=block.get("type") or "unknown",
        title=block.get("title"),
        statement=statement,
        status=status,
        lean_line=line_number,
        dependencies=block.get("references"),
        source=source,
    )

    return {
        "label": block.get("label"),
        "lean_name": lean_name,
        "status": status,
        "mode": Mode.EXTERNAL.value,
        "line": line_number,
    }


# ─────────────────────────────────────────────────────────────
# Ejecucion de un bloque con el modelo
# ─────────────────────────────────────────────────────────────

def _run_block(
    block: Dict[str, Any],
    lean_name: str,
    mode: Mode,
    manager: LeanProjectManager,
    provider: ModelProvider,
    processed: List[Dict[str, Any]],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Ejecuta el pipeline para un bloque no-externo usando el provider dado."""
    project_dir = manager.project_dir
    blocks_dir = project_dir / "Blocks"
    blocks_dir.mkdir(parents=True, exist_ok=True)

    target_path = blocks_dir / f"{lean_name}.lean"
    target_rel = f"Blocks/{lean_name}.lean"

    # 1) Stub Lean inicial
    stub = _render_stub_lean(block, manager.lean_module, lean_name)
    target_path.write_text(stub, encoding="utf-8")

    # 2) TASK.md con el contexto
    satisfied_deps = [
        p for p in processed
        if p.get("status") == "✅ verified"
        and block.get("references")
        and p.get("label") in (block.get("references") or [])
    ]
    task_md = _render_task_md(
        block, lean_name, target_rel, manager.lean_module, satisfied_deps,
    )
    task_md_path = project_dir / "TASK.md"
    task_md_path.write_text(task_md, encoding="utf-8")

    # 3) Invocar el modelo
    prompt_file = PROMPTS_DIR / prompt_file_for(mode)
    max_rounds = max_rounds_for(mode)

    if dry_run:
        success, info = True, "DRY_RUN"
    elif not prompt_file.exists():
        print(
            f"[avid] [WARN] No existe el prompt {prompt_file}. "
            f"El bloque {block.get('label')} se marcara como failed."
        )
        success, info = False, f"missing prompt: {prompt_file.name}"
    else:
        success, info = _run_model_on_target(
            target_abs=target_path,
            cwd=project_dir,
            prompt_file=prompt_file,
            max_rounds=max_rounds,
            provider=provider,
            task_md_path=task_md_path,
            dry_run=dry_run,
        )

    # Rate-limit early-exit
    if not success and info == "RATE_LIMITED":
        return {
            "label": block.get("label"),
            "lean_name": lean_name,
            "status": "⏸️ rate_limited",
            "mode": mode.value,
            "line": 0,
            "error": "Model provider rate limit / quota exhausted",
        }

    # 4) Verificar compilacion del archivo objetivo
    extracted_code = ""
    if success and not dry_run:
        has_error, has_sorry, _stdout, _stderr = check_lean_file(target_path)
        if has_error or has_sorry:
            success = False
            info = (
                f"verify failed (has_error={has_error}, has_sorry={has_sorry})"
            )
        else:
            extracted_code = _extract_declarations(target_path)
            if not _has_real_declaration(extracted_code):
                success = False
                info = (
                    "model did not produce a Lean declaration "
                    "(file has only banner/import; likely silent failure)"
                )

    if not success:
        line_number = manager.append_block(
            f"-- FAILED block: {block.get('label')}\n"
            f"-- reason: {info}\n"
            f"-- (no Lean code committed)\n"
        )
        manager.register_block(
            label=block.get("label") or lean_name,
            block_type=block.get("type") or "unknown",
            title=block.get("title"),
            statement=block.get("content_latex") or "",
            status="❌ failed",
            lean_line=line_number,
            dependencies=block.get("references"),
        )
        return {
            "label": block.get("label"),
            "lean_name": lean_name,
            "status": "❌ failed",
            "mode": mode.value,
            "line": line_number,
            "error": info,
        }

    # 5) Extraer codigo y acumular en Paper.lean
    if dry_run:
        return {
            "label": block.get("label"),
            "lean_name": lean_name,
            "status": "✅ verified",
            "mode": mode.value,
            "line": 0,
            "info": "DRY_RUN",
        }

    code = extracted_code
    line_number = manager.append_block(code)
    manager.register_block(
        label=block.get("label") or lean_name,
        block_type=block.get("type") or "unknown",
        title=block.get("title"),
        statement=block.get("content_latex") or "",
        status="✅ verified",
        lean_line=line_number,
        dependencies=block.get("references"),
    )

    # 6) Refrescar olean del modulo Paper
    if not dry_run and manager.parent_project is not None:
        _lake_build_paper_module(
            parent_project=manager.parent_project,
            paper_module=manager.lean_module,
            label=block.get("label") or lean_name,
        )

    return {
        "label": block.get("label"),
        "lean_name": lean_name,
        "status": "✅ verified",
        "mode": mode.value,
        "line": line_number,
    }


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def formalize_paper(
    tex_path: str,
    paper_title: Optional[str] = None,
    base_dir: str = "lean_papers",
    setup_mathlib: bool = False,
    dry_run: bool = False,
    parent_project: Optional[Path | str] = "<default>",
    blocks_range: Optional[str] = None,
    resume: bool = True,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Orquesta la formalizacion de un paper LaTeX completo.

    Args:
        tex_path:       ruta al archivo .tex
        paper_title:    titulo del paper (usado para nombrar el proyecto Lean).
                        Si es None, se deriva del basename del archivo.
        base_dir:       directorio donde se crea el proyecto Lean (modo standalone)
        setup_mathlib:  si True, ejecuta `lake update` + `lake exe cache get`
        dry_run:        si True, NO invoca ningun modelo (util para tests)
        parent_project: directorio del proyecto Lean compartido (con Mathlib
                        pre-compilado). Por defecto usa `<repo>/lean_project`.
                        Pasa `None` explicitamente para forzar modo standalone.
        blocks_range:   filtro opcional sobre los bloques formalizables (1-indexed
                        sobre la lista despues de filtrar tipos no formalizables).
                        Formatos aceptados:
                          - "1-13"     -> primeros 13 bloques (inclusive)
                          - "5-"       -> desde el 5 hasta el final
                          - "10"       -> solo el bloque 10
                          - "1,3,7-9"  -> 1, 3, 7, 8, 9
                          - None       -> todos
        resume:         si True (default), si el paper ya existe en disco se
                        saltan los bloques marcados como verified/axiom en
                        PAPER_INDEX.md.
        model:          nombre del proveedor de modelo a usar
                        ("claude", "deepseek", etc.). Si es None, se resuelve
                        desde la variable de entorno AVID_MODEL_PROVIDER.
                        Default: "claude".

    Returns:
        dict con un resumen: project_dir, results[], summary{verified,axioms,failed}
    """
    tex_abs = Path(tex_path).resolve()
    if not tex_abs.exists():
        raise FileNotFoundError(f"No existe el .tex: {tex_abs}")

    title = paper_title or tex_abs.stem.replace("_", " ").title()

    # Resolver el proveedor de modelo (solo si no es dry-run)
    if dry_run:
        provider = None
        print("[avid] Usando proveedor: (dry-run, ningun modelo)")
    else:
        provider = resolve_provider(model)
        print(f"[avid] Usando proveedor: {provider.__class__.__name__}")

    # Resuelve parent_project (centinela "<default>" -> usar el del repo)
    if parent_project == "<default>":
        parent_project = (
            DEFAULT_PARENT_PROJECT if DEFAULT_PARENT_PROJECT.exists() else None
        )
        if parent_project is None:
            print(
                f"[avid] [WARN] {DEFAULT_PARENT_PROJECT} no existe; "
                f"usando modo standalone con base_dir={base_dir}"
            )

    # 1) Parse
    print(f"[avid] Parseando {tex_abs}...")
    parser = LaTeXParser()
    raw_blocks = parser.parse_file(str(tex_abs))
    print(f"[avid] {len(raw_blocks)} bloques extraidos del .tex.")

    # Filtrar tipos no formalizables
    blocks = []
    skipped_by_type: Dict[str, int] = {}
    for b in raw_blocks:
        t = (b.get("type") or "unknown").lower()
        if t in FORMALIZABLE_TYPES:
            blocks.append(b)
        else:
            skipped_by_type[t] = skipped_by_type.get(t, 0) + 1
    if skipped_by_type:
        skipped_summary = ", ".join(
            f"{n} {t}" for t, n in sorted(skipped_by_type.items(), key=lambda x: -x[1])
        )
        print(f"[avid] {sum(skipped_by_type.values())} bloques no-formalizables omitidos ({skipped_summary}).")
    print(f"[avid] {len(blocks)} bloques formalizables a procesar.")

    # 2) Crear proyecto Lean
    print(f"[avid] Creando proyecto Lean para: {title}")
    manager = create_paper_project(
        paper_title=title,
        base_dir=base_dir,
        setup_mathlib=setup_mathlib,
        parent_project=parent_project,
    )

    # 2b) Pre-build del modulo Paper
    if not dry_run and manager.parent_project is not None:
        print(
            f"[avid] Pre-buildeando {manager.lean_module} (calentando "
            f"cache de Mathlib; primera vez puede tardar ~2 min)..."
        )
        _lake_build_paper_module(
            parent_project=manager.parent_project,
            paper_module=manager.lean_module,
            label="(pre-build inicial)",
        )

    # 3) Topo sort
    ordered = topological_sort(blocks)
    total_in_paper = len(ordered)
    print(f"[avid] Orden topologico: {total_in_paper} bloques.")

    # 3b) Aplicar filtro por rango
    if blocks_range:
        sel = _parse_blocks_range(blocks_range, total_in_paper)
        if not sel:
            print(f"[avid] [WARN] blocks_range={blocks_range!r} no selecciono ningun bloque.")
        ordered_view = [(i, ordered[i - 1]) for i in sel]
        print(f"[avid] Filtro de rango '{blocks_range}': {len(ordered_view)} bloques seleccionados.")
    else:
        ordered_view = list(enumerate(ordered, 1))

    # 3c) Modo resume
    already_processed: Dict[str, Dict[str, str]] = {}
    if resume and not dry_run:
        already_processed = manager.get_processed_blocks()
        if already_processed:
            verified_n = sum(1 for v in already_processed.values() if v["status"] == "verified")
            axiom_n = sum(1 for v in already_processed.values() if v["status"] == "axiom")
            failed_n = sum(1 for v in already_processed.values() if v["status"] == "failed")
            print(
                f"[avid] [RESUME] PAPER_INDEX.md tiene {len(already_processed)} entradas: "
                f"verified={verified_n} axiom={axiom_n} failed={failed_n} "
                f"(los failed se reintentan)."
            )

    # 4) Iterar bloques
    results: List[Dict[str, Any]] = []
    for i, block in ordered_view:
        label = block.get("label") or f"block_{i}"
        lean_name = lean_ident_for(block.get("label"), fallback=f"block_{i}")
        mode = classify(block)

        # Skip si ya esta verified/axiom (modo resume)
        prev = already_processed.get(label)
        if prev and prev["status"] in ("verified", "axiom"):
            print(
                f"\n[avid] ----- Bloque {i}/{total_in_paper} [{label}] "
                f"SKIPPED (already {prev['status']} en PAPER_INDEX.md) -----"
            )
            results.append({
                "label": label,
                "lean_name": lean_name,
                "mode": mode.value,
                "type": block.get("type"),
                "title": block.get("title"),
                "status": prev["raw_status"],
                "info": "skipped: ya estaba en PAPER_INDEX.md",
                "lean_line": int(prev.get("lean_line") or 0),
            })
            continue

        print(
            f"\n[avid] ----- Bloque {i}/{total_in_paper} "
            f"[{label}] type={block.get('type')} mode={mode.value} -----"
        )

        block_meta = dict(block)
        block_meta["lean_name"] = lean_name

        if mode == Mode.EXTERNAL:
            res = _handle_external(block, lean_name, manager, dry_run=dry_run)
        else:
            res = _run_block(
                block=block,
                lean_name=lean_name,
                mode=mode,
                manager=manager,
                provider=provider,
                processed=results,
                dry_run=dry_run,
            )

        res.update({
            "type": block.get("type"),
            "title": block.get("title"),
        })
        results.append(res)

        # Rate-limit: abortar run completo
        if "rate_limited" in (res.get("status") or ""):
            print(
                f"\n[avid] [ABORT] Rate limit detectado en bloque "
                f"{i} ({label}). Abortando el run.\n"
                f"[avid]         Los bloques 1..{i - 1} que se hayan procesado "
                f"quedan persistidos en PAPER_INDEX.md.\n"
                f"[avid]         Volve a correr el mismo comando cuando se "
                f"restablezca la cuota: el modo --resume saltea los ya hechos."
            )
            break

        # Pequeno respiro entre bloques
        if not dry_run:
            time.sleep(0.2)

    # 5) Resumen
    counts = {"verified": 0, "axiom": 0, "failed": 0, "skipped": 0, "rate_limited": 0}
    for r in results:
        s = r.get("status", "")
        info = r.get("info", "") or ""
        if "skipped" in info.lower():
            counts["skipped"] += 1
        elif "verified" in s:
            counts["verified"] += 1
        elif "axiom" in s:
            counts["axiom"] += 1
        elif "rate_limited" in s:
            counts["rate_limited"] += 1
        elif "failed" in s:
            counts["failed"] += 1

    summary = {
        "project_dir": str(manager.project_dir),
        "paper_lean": str(manager.paper_lean),
        "paper_index": str(manager.paper_index),
        "review_md": str(manager.review_md),
        "lean_module": manager.lean_module,
        "total_blocks": len(results),
        "counts": counts,
        "results": results,
        "model_provider": provider.__class__.__name__ if provider else "dry-run",
    }

    print("\n[avid] ============ RESUMEN ============")
    print(f"[avid] Proyecto: {summary['project_dir']}")
    print(f"[avid] Modelo:   {summary['model_provider']}")
    rl_str = f" rate_limited={counts['rate_limited']}" if counts.get("rate_limited") else ""
    print(
        f"[avid] Total: {summary['total_blocks']}  "
        f"verified={counts['verified']} "
        f"axiom={counts['axiom']} "
        f"failed={counts['failed']} "
        f"skipped={counts['skipped']}"
        + rl_str
    )
    print("[avid] =================================\n")

    return summary


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def _main():
    import argparse

    ap = argparse.ArgumentParser(description="AViD formalization orchestrator")
    ap.add_argument("tex", help="Ruta al archivo .tex")
    ap.add_argument("--title", help="Titulo del paper (override)", default=None)
    ap.add_argument("--base-dir", default="lean_papers")
    ap.add_argument("--setup-mathlib", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="No invoca ningun modelo (util para tests)")
    ap.add_argument("--standalone", action="store_true",
                    help="No usar el lean_project compartido; crea un proyecto "
                         "aislado en --base-dir (modo legacy).")
    ap.add_argument("--parent-project", default=None,
                    help="Ruta al proyecto Lean compartido. Por defecto usa "
                         "<repo>/lean_project si existe.")
    ap.add_argument("--blocks-range", default=None,
                    help='Rango 1-based de bloques formalizables a procesar. '
                         'Ejemplos: "1-13", "5-", "10", "1,3,7-9". '
                         'Si se omite, procesa todos.')
    ap.add_argument("--no-resume", action="store_true",
                    help="Desactiva el modo resume: re-procesa bloques que ya "
                         "estaban verified/axiom en PAPER_INDEX.md.")
    ap.add_argument("--model", default=None,
                    help="Proveedor de modelo a usar (claude, deepseek, etc.). "
                         "Default: valor de AVID_MODEL_PROVIDER o 'claude'.")
    ap.add_argument("--json", action="store_true",
                    help="Imprime el resumen final como JSON")
    args = ap.parse_args()

    if args.standalone:
        parent: Optional[Path | str] = None
    elif args.parent_project:
        parent = args.parent_project
    else:
        parent = "<default>"

    summary = formalize_paper(
        tex_path=args.tex,
        paper_title=args.title,
        base_dir=args.base_dir,
        setup_mathlib=args.setup_mathlib,
        dry_run=args.dry_run,
        parent_project=parent,
        blocks_range=args.blocks_range,
        resume=not args.no_resume,
        model=args.model,
    )

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main()
