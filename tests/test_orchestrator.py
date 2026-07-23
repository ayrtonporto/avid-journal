"""
Tests para el orchestrator (mayoritariamente en modo dry-run).

El test e2e real requiere Claude Code CLI + Mathlib cache y debe correrse
manualmente con:

    python tests/test_orchestrator.py --real

Por defecto (sin --real) corre en dry-run:
    python tests/test_orchestrator.py

y verifica:
- Parser extrae 3 bloques (1 definition, 1 lemma, 1 theorem).
- classify() asigna correctamente SIMPLE/MEDIUM/HARD/EXTERNAL.
- topological_sort respeta: def:even < lem:even_sum < thm:four_evens.
- formalize_paper en dry-run crea el proyecto, TASK.md y stubs;
  NO escribe entradas por bloque en PAPER_INDEX.md ni textos simulados en
  Paper.lean (evita confundir el modo resume).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Anadir repo root a sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ruff: noqa: E402
from src.formalization.complexity import Mode, classify
from src.formalization.orchestrator import (
    formalize_paper,
    lean_ident_for,
    topological_sort,
)
from src.parser.latex_parser import LaTeXParser


FIXTURE = REPO_ROOT / "tests" / "fixtures" / "sample_paper.tex"


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"{msg}: expected={expected!r} actual={actual!r}")


def test_parser_extracts_three_blocks():
    parser = LaTeXParser()
    blocks = parser.parse_file(str(FIXTURE))
    assert_eq(len(blocks), 3, "parser block count")

    labels = [b.get("label") for b in blocks]
    assert_eq(
        sorted(labels),
        sorted(["def:even", "lem:even_sum", "thm:four_evens"]),
        "parser labels",
    )

    types = {b["label"]: b["type"] for b in blocks}
    assert_eq(types["def:even"], "definition", "def:even type")
    assert_eq(types["lem:even_sum"], "lemma", "lem:even_sum type")
    assert_eq(types["thm:four_evens"], "theorem", "thm:four_evens type")

    print("[PASS] test_parser_extracts_three_blocks")


def test_classify_modes():
    parser = LaTeXParser()
    blocks = parser.parse_file(str(FIXTURE))
    by_label = {b["label"]: b for b in blocks}

    assert_eq(classify(by_label["def:even"]), Mode.SIMPLE, "def:even mode")
    # Short proofs should be MEDIUM (not HARD)
    assert_eq(classify(by_label["lem:even_sum"]), Mode.MEDIUM, "lem:even_sum mode")
    assert_eq(classify(by_label["thm:four_evens"]), Mode.MEDIUM, "thm:four_evens mode")

    print("[PASS] test_classify_modes")


def test_topological_sort_order():
    parser = LaTeXParser()
    blocks = parser.parse_file(str(FIXTURE))
    ordered = topological_sort(blocks)
    labels = [b.get("label") for b in ordered]

    # def:even debe ir antes que lem:even_sum
    assert labels.index("def:even") < labels.index("lem:even_sum"), \
        f"def:even must come before lem:even_sum: {labels}"
    # lem:even_sum antes que thm:four_evens
    assert labels.index("lem:even_sum") < labels.index("thm:four_evens"), \
        f"lem:even_sum must come before thm:four_evens: {labels}"

    print(f"[PASS] test_topological_sort_order  order={labels}")


def test_lean_ident_for():
    assert_eq(lean_ident_for("thm:four_evens"), "thm_four_evens", "thm label")
    assert_eq(lean_ident_for("lem:even_sum"), "lem_even_sum", "lem label")
    assert_eq(lean_ident_for("def:even"), "def_even", "def label")
    assert_eq(lean_ident_for(None, fallback="unnamed"), "unnamed", "None label")
    assert_eq(lean_ident_for("42:foo", fallback="x"), "b_42_foo", "starts-with-digit")

    print("[PASS] test_lean_ident_for")


def test_formalize_paper_dry_run():
    """Test e2e en dry-run STANDALONE: no se invoca Claude y no contamina
    el lean_project compartido."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "lean_papers"
        summary = formalize_paper(
            tex_path=str(FIXTURE),
            paper_title="Tiny Evens Paper",
            base_dir=str(base),
            setup_mathlib=False,
            dry_run=True,
            parent_project=None,  # standalone para no tocar lean_project/
        )

        # 3 bloques procesados
        assert_eq(summary["total_blocks"], 3, "total_blocks")

        project = Path(summary["project_dir"])
        assert project.exists(), f"project dir missing: {project}"
        assert (project / "lakefile.toml").exists(), "lakefile.toml missing"
        assert (project / "lean-toolchain").exists(), "lean-toolchain missing"
        assert (project / "PAPER_INDEX.md").exists(), "PAPER_INDEX.md missing"
        assert (project / "REVIEW.md").exists(), "REVIEW.md missing"
        assert (project / "docs" / "prompts" / "avid_common.md").exists(), \
            "avid_common.md missing in project"
        assert (project / "docs" / "prompts" / "avid_sketch_agent.md").exists(), \
            "avid_sketch_agent.md missing in project"

        # Blocks dir con 3 stubs
        blocks_dir = project / "Blocks"
        stubs = list(blocks_dir.glob("*.lean"))
        assert_eq(len(stubs), 3, "stub count")

        # Dry-run no registra bloques en PAPER_INDEX (solo cabecera inicial).
        idx_text = (project / "PAPER_INDEX.md").read_text(encoding="utf-8")
        for lab in ["def:even", "lem:even_sum", "thm:four_evens"]:
            assert f"## {lab}" not in idx_text, f"dry-run no debe escribir ## {lab}"

        # Paper.lean en modo standalone: project_dir/<ModuleName>/Paper.lean
        paper_path = Path(summary["paper_lean"])
        assert paper_path.exists(), f"missing {paper_path}"
        paper_text = paper_path.read_text(encoding="utf-8")
        assert "(dry-run)" not in paper_text.lower()

        # El resumen cuenta bloques como verified en memoria (sin persistir indice).
        counts = summary["counts"]
        assert counts["verified"] == 3, f"expected 3 verified, got {counts}"

        print(f"[PASS] test_formalize_paper_dry_run  counts={counts}")


def test_formalize_paper_dry_run_shared():
    """Igual que el anterior, pero usando el lean_project compartido.

    Verifica que la estructura `lean_project/Papers/<Slug>/` se crea bien y
    que el lakefile padre tiene el lean_lib `Papers` registrado. Limpia el
    sub-directorio del paper al terminar.
    """
    from src.formalization.lean_project import (
        DEFAULT_PARENT_PROJECT,
        ensure_papers_lib_in_lakefile,
    )

    if not DEFAULT_PARENT_PROJECT.exists():
        print("[SKIP] test_formalize_paper_dry_run_shared (no lean_project/)")
        return

    paper_subdir = DEFAULT_PARENT_PROJECT / "Papers" / "TinyEvensPaperShared"
    if paper_subdir.exists():
        shutil.rmtree(paper_subdir)

    try:
        summary = formalize_paper(
            tex_path=str(FIXTURE),
            paper_title="Tiny Evens Paper Shared",
            dry_run=True,
            # parent_project default => DEFAULT_PARENT_PROJECT
        )

        assert_eq(summary["lean_module"], "Papers.TinyEvensPaperShared.Paper",
                  "lean_module")

        project = Path(summary["project_dir"])
        assert project == paper_subdir, f"unexpected project dir: {project}"
        assert (project / "Paper.lean").exists(), "Paper.lean missing"
        assert (project / "PAPER_INDEX.md").exists(), "PAPER_INDEX.md missing"
        assert (project / "REVIEW.md").exists(), "REVIEW.md missing"
        assert not (project / "lakefile.toml").exists(), \
            "no debe haber lakefile en sub-proyecto"
        assert not (project / "lean-toolchain").exists(), \
            "no debe haber lean-toolchain en sub-proyecto"

        # Lakefile padre debe contener [[lean_lib]] name = "Papers"
        lakefile = (DEFAULT_PARENT_PROJECT / "lakefile.toml").read_text(encoding="utf-8")
        assert 'name = "Papers"' in lakefile, "Papers lib no registrado en lakefile"

        # Idempotencia
        modified = ensure_papers_lib_in_lakefile(DEFAULT_PARENT_PROJECT)
        assert modified is False, "ensure_papers_lib_in_lakefile no es idempotente"

        # Stubs deben importar el modulo del paper compartido
        stub_text = next((project / "Blocks").glob("*.lean")).read_text(encoding="utf-8")
        assert "import Papers.TinyEvensPaperShared.Paper" in stub_text, \
            f"stub no importa el modulo correcto:\n{stub_text}"

        print(f"[PASS] test_formalize_paper_dry_run_shared  project={project}")
    finally:
        if paper_subdir.exists():
            shutil.rmtree(paper_subdir, ignore_errors=True)


@pytest.mark.skipif(
    not os.environ.get("AVID_RUN_REAL_E2E"),
    reason=(
        "E2E con Claude real: establece AVID_RUN_REAL_E2E=1 para pytest, "
        "o ejecuta: python tests/test_orchestrator.py --real"
    ),
)
def test_formalize_paper_real():
    """Test e2e real. Requiere:
    - claude CLI en PATH
    - lean 4 (v4.29) via elan
    - Mathlib descargado en lean_project/.lake/

    Corre con pytest y variable de entorno:

        AVID_RUN_REAL_E2E=1 pytest tests/test_orchestrator.py::test_formalize_paper_real

    O como script:

        python tests/test_orchestrator.py --real
    """
    print("[info] Corriendo e2e real contra Claude Code. Esto puede tardar...")
    summary = formalize_paper(
        tex_path=str(FIXTURE),
        paper_title="Tiny Evens Paper Real",
        # Modo compartido por defecto (Mathlib pre-compilado en lean_project)
        dry_run=False,
    )

    counts = summary["counts"]
    print(f"[PASS?] test_formalize_paper_real  counts={counts}")

    # Criterio de exito: todos verificados
    if counts["verified"] != summary["total_blocks"]:
        raise AssertionError(f"Esperados {summary['total_blocks']} verified, got {counts}")


def main():
    real = "--real" in sys.argv

    test_parser_extracts_three_blocks()
    test_classify_modes()
    test_topological_sort_order()
    test_lean_ident_for()
    test_formalize_paper_dry_run()
    test_formalize_paper_dry_run_shared()

    if real:
        test_formalize_paper_real()
    else:
        print("\n[info] Tests dry-run completos.")
        print("[info] Para el e2e real, usa: python tests/test_orchestrator.py --real")


if __name__ == "__main__":
    main()
