"""
Lean file checking utilities.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Tuple
from multiprocessing import Pool, cpu_count


# Regex que matchea el formato real de un error de Lean:
#   <path>:<line>:<col>: error: ...
# o variantes con `error[unsolvedGoals]:`, etc.
# No matchea sustrings como "Errors", "error_handling", o palabras
# en docstrings/comentarios. Tampoco matchea "warning:" (que NO es error).
_LEAN_ERROR_RE = re.compile(
    r"^[^\n]*?:\s*\d+:\s*\d+:\s*error\b",
    re.MULTILINE,
)

# Sorry warning real de Lean:
#   <path>:<line>:<col>: warning: declaration uses 'sorry'
# o    declaration uses 'sorry'
# Tambien capturamos `:warning:` con texto sobre sorry, para no perdernos
# axiom-checks.
_LEAN_SORRY_RE = re.compile(
    r"declaration uses ['`\"]?sorry['`\"]?",
    re.IGNORECASE,
)


def find_lean_files(folder_path: str | Path) -> List[Path]:
    """
    Recursively find all .lean files in a folder.

    Args:
        folder_path: Path to the folder to search

    Returns:
        Sorted list of .lean file paths
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")

    if not folder.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {folder_path}")

    lean_files = []
    for file_path in folder.rglob("*.lean"):
        if file_path.is_file():
            lean_files.append(file_path)

    return sorted(lean_files)


def find_lean_project_root(file_path: Path) -> Path:
    """
    Find the Lean project root (directory containing lean-toolchain).

    Args:
        file_path: Path to a file or directory

    Returns:
        Project root path, or the file's parent if not found
    """
    current = file_path.parent if file_path.is_file() else file_path
    while current != current.parent:  # Until reaching root
        lean_toolchain = current / "lean-toolchain"
        if lean_toolchain.exists():
            return current
        current = current.parent
    # If not found, return file's parent directory
    return file_path.parent if file_path.is_file() else file_path


def check_lean_file(file_path: Path) -> Tuple[bool, bool, str, str]:
    """
    Check a single .lean file for real errors and sorry warnings.

    AViD-tightened version (2026-04): the upstream Numina version used
    substring matching on the words "error" / "sorry", which produced
    false positives whenever lake's build output mentioned a module name
    like "Mathlib.Algebra.Errors" or a path that happened to contain
    those substrings. We now check:

      - returncode (the authoritative signal from `lean`),
      - the standard Lean diagnostic format `path:line:col: error:`,
      - the standard sorry warning `declaration uses 'sorry'`.

    Args:
        file_path: Path to the .lean file

    Returns:
        (has_error, has_sorry_warning, stdout, stderr)
    """
    try:
        project_root = find_lean_project_root(file_path)

        result = subprocess.run(
            ["lake", "env", "lean", str(file_path)],
            capture_output=True,
            timeout=180,  # generoso porque rebuild dependencias puede tardar
            cwd=str(project_root),
        )

        # Decodificamos manualmente con utf-8 (Lean emite UTF-8 siempre)
        stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
        stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""

        combined = stdout + "\n" + stderr

        # Errores reales: returncode no-cero, o un diagnostico Lean.
        has_error = (
            result.returncode != 0
            or bool(_LEAN_ERROR_RE.search(combined))
        )

        has_sorry_warning = bool(_LEAN_SORRY_RE.search(combined))

        return has_error, has_sorry_warning, stdout, stderr

    except subprocess.TimeoutExpired:
        return True, False, "", "Check timed out (180s)"
    except Exception as e:
        return True, False, "", f"Execution error: {str(e)}"


def _check_wrapper(file_path: Path) -> Tuple[Path, bool, bool, str, str]:
    """
    Wrapper function for multiprocessing.

    Returns:
        (file_path, has_error, has_sorry_warning, stdout, stderr)
    """
    has_error, has_sorry_warning, stdout, stderr = check_lean_file(file_path)
    return (file_path, has_error, has_sorry_warning, stdout, stderr)


def check_lean_files_parallel(
    lean_files: List[Path], num_proc: int = None
) -> List[Tuple[Path, bool, bool, str, str]]:
    """
    Check multiple .lean files in parallel.

    Args:
        lean_files: List of .lean file paths
        num_proc: Number of parallel processes (default: CPU count)

    Returns:
        List of (file_path, has_error, has_sorry_warning, stdout, stderr)
    """
    if num_proc is None:
        num_proc = cpu_count()

    with Pool(processes=num_proc) as pool:
        results = pool.map(_check_wrapper, lean_files)

    return results


def check_folder(
    folder_path: str | Path, num_proc: int = None
) -> Tuple[bool, List[Path], List[Path]]:
    """
    Check all .lean files in a folder.

    Args:
        folder_path: Path to the folder
        num_proc: Number of parallel processes

    Returns:
        (all_passed, error_files, sorry_files)
    """
    lean_files = find_lean_files(folder_path)
    if not lean_files:
        return True, [], []

    results = check_lean_files_parallel(lean_files, num_proc)

    error_files = []
    sorry_files = []

    for file_path, has_error, has_sorry_warning, _, _ in results:
        if has_error:
            error_files.append(file_path)
        elif has_sorry_warning:
            sorry_files.append(file_path)

    all_passed = len(error_files) == 0 and len(sorry_files) == 0
    return all_passed, error_files, sorry_files
