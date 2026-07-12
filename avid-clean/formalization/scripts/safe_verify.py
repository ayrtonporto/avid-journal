"""
SafeVerify integration for post-completion proof verification.

SafeVerify (https://github.com/GasStationManager/SafeVerify) performs a robust
kernel-level replay check of submitted Lean proofs against the original target.

Flow:
1. Before the agent runs: snapshot the original .lean file (with sorry) to a
    temp path: this becomes the "target".
2. After the agent finishes: compile both .lean files to .olean, then run the
    safe_verify binary.
"""

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SafeVerifyResult:
    """Result of a SafeVerify check."""
    ran: bool  # Whether SafeVerify was actually executed
    success: bool  # True if safe_verify exited 0
    returncode: int
    output: str  # Combined stdout + stderr from all three commands
    error_message: Optional[str] = None  # Set on unexpected errors


def snapshot_target(src: Path, dest: Path) -> None:
    """
    Copy the original .lean file (with sorry) to dest before the agent modifies it.

    Args:
    - src: The original target .lean file (will be modified by the agent).
    - dest: Where to save the snapshot.
    """
    shutil.copy2(src, dest)


def run_safe_verify(
    target_lean: Path,
    submission_lean: Path,
    safe_verify_bin: Path,
    cwd: Path,
    olean_dir: Optional[Path] = None,
) -> SafeVerifyResult:
    """
    Compile both .lean files and run SafeVerify.

    Runs:
        lake env lean -o <olean_dir>/target.olean    <target_lean>
        lake env lean -o <olean_dir>/submission.olean <submission_lean>
        <safe_verify_bin> <olean_dir>/target.olean <olean_dir>/submission.olean

    Args:
    - target_lean: The original .lean file with sorry (snapshot).
    - submission_lean: The agent's output .lean file.
    - safe_verify_bin: The path to the safe_verify executable.
    - cwd: The project directory (for lake env).
    - olean_dir: The directory for .olean output files. Defaults to a temp dir.

    Returns:
    - SafeVerifyResult: The result of the SafeVerify check.
    """
    output_lines: list[str] = []
    own_tmp = False

    try:
        # Use caller-provided olean_dir or create a temp one
        if olean_dir is None:
            tmp_obj = tempfile.TemporaryDirectory(prefix="numina_sv_")
            olean_dir = Path(tmp_obj.name)
            own_tmp = True

        target_olean = olean_dir / "target.olean"
        submission_olean = olean_dir / "submission.olean"

        cwd_str = str(cwd)

        # Step 1: compile target (with sorry)
        output_lines.append("=== Compiling target (with sorry) ===")
        cmd1 = ["lake", "env", "lean", "-o", str(target_olean), str(target_lean)]
        r1 = subprocess.run(
            cmd1, cwd=cwd_str, capture_output=True, text=True
        )
        output_lines.append(r1.stdout)
        if r1.stderr:
            output_lines.append(r1.stderr)
        if r1.returncode != 0:
            return SafeVerifyResult(
                ran=True,
                success=False,
                returncode=r1.returncode,
                output="\n".join(output_lines),
                error_message=f"Target compilation failed (exit {r1.returncode})",
            )

        # Step 2: compile submission (agent output)
        output_lines.append("=== Compiling submission ===")
        cmd2 = ["lake", "env", "lean", "-o", str(submission_olean), str(submission_lean)]
        r2 = subprocess.run(
            cmd2, cwd=cwd_str, capture_output=True, text=True
        )
        output_lines.append(r2.stdout)
        if r2.stderr:
            output_lines.append(r2.stderr)
        if r2.returncode != 0:
            return SafeVerifyResult(
                ran=True,
                success=False,
                returncode=r2.returncode,
                output="\n".join(output_lines),
                error_message=f"Submission compilation failed (exit {r2.returncode})",
            )

        # Step 3: run safe_verify via `lake env` from the proof project directory.
        # This sets LEAN_PATH so safe_verify can locate Mathlib and other deps.
        # (Running the binary directly fails with "unknown module prefix 'Mathlib'".)
        output_lines.append("=== Running SafeVerify ===")
        cmd3 = ["lake", "env", str(safe_verify_bin), str(target_olean), str(submission_olean)]
        r3 = subprocess.run(
            cmd3, cwd=cwd_str, capture_output=True, text=True
        )
        output_lines.append(r3.stdout)
        if r3.stderr:
            output_lines.append(r3.stderr)

        return SafeVerifyResult(
            ran=True,
            success=(r3.returncode == 0),
            returncode=r3.returncode,
            output="\n".join(output_lines),
        )

    except Exception as e:
        return SafeVerifyResult(
            ran=True,
            success=False,
            returncode=-1,
            output="\n".join(output_lines),
            error_message=str(e),
        )
    finally:
        if own_tmp:
            try:
                tmp_obj.cleanup()
            except Exception:
                pass
