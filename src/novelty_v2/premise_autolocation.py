"""Auto-localización de teoremas en archivos .lean (lado A y lado B).

Provee localización automática de teoremas sin depender del mapa manual
(d3_extraction_map.yaml). El mapa manual queda como override/fallback.

Lado A: lee PAPER_INDEX.md o busca en directorios Papers/Blocks/.
Lado B: busca en fuentes de Mathlib vía ripgrep.

Rangos de línea EXACTOS: el fin del teorema se determina buscando la
siguiente declaración (theorem/lemma/def/instance/example/end) después
del encabezado.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Keywords that start a new declaration (end the previous theorem)
_DECLARATION_KW = re.compile(
    r"^[ \t]*(?:theorem|lemma|def|instance|example|axiom|class|structure|inductive|"
    r"coinductive|opaque|abbrev|end)\s",
    re.MULTILINE,
)

# Regex to find a specific theorem/lemma/def header
def _header_pattern(name: str) -> re.Pattern:
    """Pattern to match 'theorem <name>|lemma <name>|def <name>' with word boundary.
    Uses [ \\t]* instead of \\s* to avoid matching newlines."""
    return re.compile(
        rf"^[ \t]*(?:theorem|lemma|def)\s+{re.escape(name)}\b",
        re.MULTILINE,
    )


# ---------------------------------------------------------------------------
# Core: locate a theorem within a known .lean file (exact line range)
# ---------------------------------------------------------------------------

def locate_theorem_in_file(
    file_path: str | Path,
    theorem_name: str,
) -> Optional[Tuple[int, int]]:
    """Find the exact line range of a theorem within a .lean file.

    Args:
        file_path: path to the .lean file.
        theorem_name: the Lean identifier (e.g., "irrational_sqrt_two").

    Returns:
        (start_line, end_line) 1-indexed inclusive, or None if not found.
    """
    path = Path(file_path)
    if not path.exists():
        logger.debug("locate_theorem_in_file: file not found: %s", path)
        return None

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Find the theorem header
    pattern = _header_pattern(theorem_name)
    match = pattern.search(content)
    if not match:
        logger.debug("locate_theorem_in_file: '%s' not found in %s",
                     theorem_name, path.name)
        return None

    start_line = content[:match.start()].count("\n") + 1  # 1-indexed

    # Find the next declaration after the match
    search_start = match.end()
    next_decl = _DECLARATION_KW.search(content, search_start)

    if next_decl:
        end_line = content[:next_decl.start()].count("\n") + 1 - 1  # line before
    else:
        end_line = len(lines)  # end of file

    # Trim trailing blank and comment-only lines
    while end_line > start_line:
        line_text = lines[end_line - 1].strip() if end_line <= len(lines) else ""
        if line_text == "" or line_text.startswith("--"):
            end_line -= 1
        else:
            break

    # Sanity check
    if end_line < start_line:
        end_line = start_line

    logger.debug(
        "locate_theorem_in_file: %s → %s:%d-%d",
        theorem_name, path.name, start_line, end_line,
    )
    return (start_line, end_line)


# ---------------------------------------------------------------------------
# Side B: locate a Mathlib theorem by fullName
# ---------------------------------------------------------------------------

def locate_mathlib_source(
    full_name: str,
    mathlib_root: str | Path,
) -> Optional[Tuple[Path, int, int]]:
    """Locate a Mathlib theorem's source file and line range.

    Uses ripgrep to search Mathlib sources for the theorem header.
    Then calls locate_theorem_in_file for the exact line range.

    Args:
        full_name: fully qualified Lean name (e.g., "irrational_sqrt_two").
        mathlib_root: path to Mathlib source tree
                      (e.g., lean_project/.lake/packages/mathlib/).

    Returns:
        (file_path, start_line, end_line) or None if not found.
    """
    root = Path(mathlib_root)
    if not root.exists():
        logger.debug("locate_mathlib_source: mathlib_root not found: %s", root)
        return None

    # Search for the theorem header using ripgrep
    try:
        proc = subprocess.run(
            [
                "rg", "--no-heading", "-n",
                rf"^[ \t]*(?:theorem|lemma|def)\s+{re.escape(full_name)}\b",
                str(root),
                "--max-count=1",
            ],
            capture_output=True, text=True, timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("locate_mathlib_source: rg failed: %s", exc)
        return None

    if proc.returncode != 0 or not proc.stdout.strip():
        logger.debug("locate_mathlib_source: '%s' not found in Mathlib", full_name)
        return None

    # Parse output: "path:line:content" — handle Windows drive letters
    for line in proc.stdout.strip().split("\n"):
        # rg on Windows outputs "D:\path\to\file.lean:line:content"
        # Split on ":" but handle "D:" drive prefix
        parts = line.split(":", 2)
        if len(parts) >= 3 and len(parts[0]) == 1 and parts[1].startswith("\\"):
            # Windows drive letter: "D:\path..." split as ["D", "\path...", "line:content"]
            file_part = parts[0] + ":" + parts[1]
            rest = parts[2]
        elif len(parts) >= 2:
            file_part = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
        else:
            continue

        if file_part.endswith(".lean"):
            file_path = Path(file_part)
            if file_path.exists():
                break
    else:
        logger.debug("locate_mathlib_source: '%s' not found in Mathlib", full_name)
        return None

    # Now get exact line range
    line_range = locate_theorem_in_file(file_path, full_name)
    if line_range is None:
        return None

    start_line, end_line = line_range
    logger.info(
        "locate_mathlib_source: %s → %s:%d-%d",
        full_name, file_path.name, start_line, end_line,
    )
    return (file_path, start_line, end_line)


# ---------------------------------------------------------------------------
# Side A: locate a candidate proof from PAPER_INDEX.md or directory scan
# ---------------------------------------------------------------------------

def _parse_paper_index(index_path: Path) -> List[dict]:
    """Parse PAPER_INDEX.md into a list of entry dicts.

    Each entry: {label, type, status, file, line, depends_on, statement}
    """
    if not index_path.exists():
        return []

    content = index_path.read_text(encoding="utf-8")
    entries = []
    current = None

    for line in content.splitlines():
        # New entry: "## label — title"
        m = re.match(r"^##\s+(\S+)\s", line)
        if m:
            if current:
                entries.append(current)
            current = {"label": m.group(1)}
            continue
        if current is None:
            continue
        # Key: Value
        m = re.match(r"^(Type|Status|File|Depends on|Statement):\s*(.*)", line)
        if m:
            key = m.group(1).lower().replace(" ", "_")
            val = m.group(2)
            if key == "file":
                # "Paper.lean:42" → file="Paper.lean", line=42
                parts = val.rsplit(":", 1)
                current["file"] = parts[0]
                current["line"] = int(parts[1]) if len(parts) > 1 else 0
            elif key == "depends_on":
                current["depends_on"] = val
            elif key == "statement":
                current["statement"] = val
            elif key == "type":
                current["type"] = val
            elif key == "status":
                current["status"] = val

    if current:
        entries.append(current)

    return entries


def locate_candidate_from_index(
    lean_name: str,
    paper_dir: str | Path,
) -> Optional[Tuple[Path, int, int]]:
    """Locate a candidate proof using PAPER_INDEX.md metadata.

    Args:
        lean_name: the Lean identifier (e.g., "t08a_parity").
        paper_dir: directory containing PAPER_INDEX.md and .lean files.

    Returns:
        (file_path, start_line, end_line) or None if not found.
    """
    pdir = Path(paper_dir)
    index_path = pdir / "PAPER_INDEX.md"

    entries = _parse_paper_index(index_path)

    # Try exact label match first
    for entry in entries:
        label = entry.get("label", "")
        # Labels are like "thm:four_evens" — extract the name part
        name_part = label.split(":", 1)[-1] if ":" in label else label
        if name_part == lean_name:
            file_name = entry.get("file", "Paper.lean")
            start_line = entry.get("line", 0)
            if start_line <= 0:
                return None

            file_path = pdir / file_name
            if not file_path.exists():
                logger.debug("locate_candidate: file from index not found: %s", file_path)
                return None

            # Get exact end line
            line_range = locate_theorem_in_file(file_path, lean_name)
            if line_range is None:
                # Fall back to approximate: start_line + 500 or EOF
                content = file_path.read_text(encoding="utf-8")
                total = content.count("\n") + 1
                end_line = min(start_line + 500, total)
                return (file_path, start_line, end_line)

            return (file_path, line_range[0], line_range[1])

    return None


def locate_candidate_by_scan(
    lean_name: str,
    search_dirs: List[str | Path],
) -> Optional[Tuple[Path, int, int]]:
    """Locate a candidate proof by scanning .lean files in search directories.

    Searches for 'theorem <lean_name>' in all .lean files under each directory.

    Args:
        lean_name: the Lean identifier.
        search_dirs: list of directories to search recursively.

    Returns:
        (file_path, start_line, end_line) or None if not found.
    """
    pattern = _header_pattern(lean_name)

    for sdir in search_dirs:
        sd = Path(sdir)
        if not sd.exists():
            continue
        for fp in sd.rglob("*.lean"):
            try:
                content = fp.read_text(encoding="utf-8")
            except OSError:
                continue
            if pattern.search(content):
                line_range = locate_theorem_in_file(fp, lean_name)
                if line_range:
                    logger.info(
                        "locate_candidate_scan: %s → %s:%d-%d",
                        lean_name, fp.name, line_range[0], line_range[1],
                    )
                    return (fp, line_range[0], line_range[1])

    return None


def locate_candidate_source(
    lean_name: str,
    project_dir: str | Path,
) -> Optional[Tuple[Path, int, int]]:
    """Full candidate auto-location pipeline.

    Priority:
      1. PAPER_INDEX.md in known paper directories
      2. Scan Papers/ and Blocks/ directories

    Args:
        lean_name: the Lean identifier.
        project_dir: root of the Lean project (lean_project/).

    Returns:
        (file_path, start_line, end_line) or None if not found.
    """
    proj = Path(project_dir)

    # 1) Try PAPER_INDEX.md in known paper directories
    papers_dir = proj / "Papers"
    if papers_dir.exists():
        for paper_dir in sorted(papers_dir.iterdir()):
            if not paper_dir.is_dir():
                continue
            result = locate_candidate_from_index(lean_name, paper_dir)
            if result:
                return result

    # 2) Scan Papers/ and Blocks/
    search_dirs = []
    if papers_dir.exists():
        search_dirs.append(papers_dir)
    blocks_dir = proj / "Blocks"
    if blocks_dir.exists():
        search_dirs.append(blocks_dir)

    return locate_candidate_by_scan(lean_name, search_dirs)


# ---------------------------------------------------------------------------
# Helper: resolve ast.json path for a .lean file (handles Mathlib packages)
# ---------------------------------------------------------------------------

def resolve_ast_json_path(
    lean_file_path: str | Path,
    lean_project_dir: str | Path,
) -> Optional[Path]:
    """Resolve the ast.json path that ExtractData generates for a given .lean file.

    Handles two cases:
      1. Files in the lean_project tree → .lake/build/ir/<rel>/<name>.ast.json
      2. Files in a package (e.g., Mathlib) → .lake/packages/<pkg>/.lake/build/ir/<rel>/<name>.ast.json
    """
    file_path = Path(lean_file_path).resolve()
    proj = Path(lean_project_dir).resolve()

    try:
        rel = file_path.relative_to(proj)
    except ValueError:
        rel = file_path

    rel_str = str(rel).replace("\\", "/")

    # Case 1: File inside a .lake/packages/<pkg> directory
    packages_dir = proj / ".lake" / "packages"
    try:
        rel_to_packages = file_path.relative_to(packages_dir)
        # e.g., mathlib/Mathlib/NumberTheory/Real/Irrational.lean
        parts = rel_to_packages.parts
        if len(parts) >= 1:
            pkg_name = parts[0]  # "mathlib"
            rest = Path(*parts[1:])  # Mathlib/NumberTheory/Real/Irrational.lean
            rest_no_ext = rest.with_suffix("")
            ast = packages_dir / pkg_name / ".lake" / "build" / "ir" / rest_no_ext
            ast = Path(str(ast) + ".ast.json")
            if ast.exists():
                return ast
    except ValueError:
        pass

    # Case 2: File in the lean_project tree
    ast = proj / ".lake" / "build" / "ir" / rel_str
    ast = ast.with_suffix("").with_suffix(".ast.json")
    if ast.exists():
        return ast

    # Case 3: Try without .lean extension change
    alt = Path(str(ast).replace(".lean.ast.json", ".ast.json"))
    if alt.exists():
        return alt

    return None
