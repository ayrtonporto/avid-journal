"""
AViD Journal — Claude Code provider.

Implementa ModelProvider usando Claude Code CLI (claude npm package).
Claude Code es un proveedor "agentic": maneja el loop de verificación
internamente mediante herramientas MCP (lean_diagnostic_messages, etc.).

El provider lanza Claude como subprocess, pasando el prompt por stdin
(para evitar el límite de longitud de línea de comandos en Windows).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from .base import AgenticProvider, FormalizationResult

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Match END_REASON:{reason} en una línea
_PAT_REASON = re.compile(
    r"(?m)^\s*END_REASON:(LIMIT|COMPLETE|SELECTED_TARGET_COMPLETE)\s*$", re.I
)

# Detectar mensajes de rate-limit / cuota agotada de Anthropic
_PAT_RATE_LIMIT = re.compile(
    r"\b(hit your limit|hit your session limit|session limit|"
    r"usage limit reached|rate.?limit|out of credit|"
    r"quota exceeded|insufficient credit|credit balance is too low)\b",
    re.IGNORECASE,
)


def _resolve_executable(args: list[str]) -> list[str]:
    """Compatibilidad Windows: resuelve `claude` → path absoluto (.cmd).

    En Windows, subprocess.Popen no consulta PATHEXT para encontrar
    wrappers .cmd/.bat. Sin esta resolución, Popen lanza [WinError 2].
    """
    if not args:
        return args
    cmd = args[0]
    if os.sep in cmd or "/" in cmd:
        return args  # ya es un path
    resolved = shutil.which(cmd)
    if resolved:
        return [resolved] + list(args[1:])
    return args


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class ClaudeCodeProvider(AgenticProvider):
    """Proveedor que usa Claude Code CLI para formalizar."""

    def __init__(
        self,
        binary: str = "claude",
        permission_mode: str = "bypassPermissions",
        sleep_between_rounds: float = 1.0,
        model: Optional[str] = None,
    ):
        """
        Args:
            binary: path o nombre del binario de Claude Code.
            permission_mode: modo de permisos (bypassPermissions por defecto).
            sleep_between_rounds: pausa entre rondas en segundos.
            model: modelo específico a usar (ej. "claude-sonnet-4-20250514").
                   Si es None, usa el default de Claude Code.
        """
        self.binary = binary
        self.permission_mode = permission_mode
        self.sleep_between_rounds = sleep_between_rounds
        self.model = model

    # ------------------------------------------------------------------
    # ModelProvider interface
    # ------------------------------------------------------------------

    def formalize(
        self,
        target_path: Path,
        prompt: str,
        max_rounds: int,
        cwd: Path,
    ) -> FormalizationResult:
        """Ejecuta Claude Code sobre el target y retorna el resultado."""
        return self._run_session(
            target_path=target_path,
            prompt=prompt,
            max_rounds=max_rounds,
            cwd=cwd,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_env(self) -> dict:
        """Construye el entorno para el subprocess de Claude.

        Elimina ANTHROPIC_API_KEY y CLAUDE_API_KEY para forzar el uso
        del flujo de suscripción local de Claude Code (claude auth login).
        Si estas variables se heredan, Claude Code las prioriza y puede
        fallar con errores de crédito de API incluso estando autenticado.
        """
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("CLAUDE_API_KEY", None)
        return env

    def _run_session(
        self,
        target_path: Path,
        prompt: str,
        max_rounds: int,
        cwd: Path,
    ) -> FormalizationResult:
        """Ejecuta una sesión completa de Claude Code con loop de continuación.

        Flujo:
        1. Primer llamado: `claude -p --verbose --output-format stream-json`
           con el prompt completo por stdin.
        2. Si END_REASON=LIMIT: `claude -c -p ... --prompt "continue"`.
        3. Si END_REASON=COMPLETE: fin.
        4. Repite hasta max_rounds.

        Returns:
            FormalizationResult con el estado final.
        """
        import time

        base_cmd = [
            self.binary,
            "-p",
            "--verbose",
            "--output-format",
            "stream-json",
        ]
        if self.permission_mode:
            base_cmd += ["--permission-mode", self.permission_mode]
        if self.model:
            base_cmd += ["--model", self.model]

        env = self._build_env()
        rounds = 0
        reason: Optional[str] = None

        # ── Ronda 1: prompt inicial ──────────────────────────
        rounds += 1
        reason, returncode, claude_result = self._run_claude_once(
            base_cmd, env=env, cwd=cwd, prompt=prompt
        )

        # Rate-limit en ronda 1 → abortar inmediatamente
        if reason == "RATE_LIMITED":
            return FormalizationResult(
                success=False, info="RATE_LIMITED", rounds_used=1
            )

        # ── Rondas siguientes: continuar ─────────────────────
        consecutive_limits = 1 if reason == "LIMIT" else 0

        while reason in (None, "LIMIT", "COMPLETE", "SELECTED_TARGET_COMPLETE"):
            if rounds >= max_rounds:
                break

            if reason == "COMPLETE":
                break  # éxito

            time.sleep(max(0.0, self.sleep_between_rounds))
            rounds += 1

            if reason == "SELECTED_TARGET_COMPLETE":
                continue  # Claude pasó a otro target, seguir

            # Si razón es None o LIMIT, continuar
            if reason is None:
                reason, returncode, claude_result = self._run_claude_once(
                    base_cmd, env=env, cwd=cwd, prompt=prompt
                )
            else:
                # LIMIT: usar --continue
                continue_cmd = [
                    self.binary,
                    "-c",
                    "-p",
                    "--verbose",
                    "--output-format",
                    "stream-json",
                ]
                if self.permission_mode:
                    continue_cmd += ["--permission-mode", self.permission_mode]
                reason, returncode, claude_result = self._run_claude_once(
                    continue_cmd, env=env, cwd=cwd, prompt="continue"
                )

            if reason == "RATE_LIMITED":
                return FormalizationResult(
                    success=False,
                    info="RATE_LIMITED",
                    rounds_used=rounds,
                )

            # Actualizar contador de LIMITs consecutivos
            if reason == "LIMIT":
                consecutive_limits += 1
            else:
                consecutive_limits = 0

            # Si hay 2+ LIMITs consecutivos, reiniciar sesión
            if consecutive_limits >= 2:
                reason, returncode, claude_result = self._run_claude_once(
                    base_cmd, env=env, cwd=cwd, prompt=prompt
                )
                consecutive_limits = 0

        # ── Resultado final ──────────────────────────────────
        success = reason == "COMPLETE"
        info = reason or f"returncode={returncode}"
        return FormalizationResult(
            success=success, info=info, rounds_used=rounds
        )

    def _run_claude_once(
        self,
        args: list[str],
        env: dict,
        cwd: Path,
        prompt: Optional[str] = None,
    ) -> tuple[Optional[str], int, Optional[dict]]:
        """Ejecuta un solo comando `claude` y parsea el stream JSON final.

        Args:
            args: comando base de Claude (sin el prompt).
            env: variables de entorno.
            cwd: directorio de trabajo.
            prompt: prompt a enviar por stdin (None = sin stdin).

        Returns:
            (end_reason, returncode, claude_result_dict)
            end_reason: "COMPLETE" | "LIMIT" | "RATE_LIMITED" | None
        """
        # Archivo temporal para el stream NDJSON
        json_save_path = Path(tempfile.gettempdir()) / f"claude_raw_{uuid.uuid4().hex}.jsonl"
        json_save_path.parent.mkdir(parents=True, exist_ok=True)

        args = _resolve_executable(args)

        stdin_pipe = subprocess.PIPE if prompt is not None else None

        with open(json_save_path, "w", encoding="utf-8") as stdout_target:
            proc = subprocess.Popen(
                args,
                stdin=stdin_pipe,
                stdout=stdout_target,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                env=env or None,
                cwd=str(cwd),
            )
            if prompt is not None:
                try:
                    proc.stdin.write(prompt)
                    proc.stdin.close()
                except (BrokenPipeError, OSError):
                    pass
            proc.wait()

        # Leer última línea del stream (contiene el resultado final)
        last_line = ""
        try:
            with open(json_save_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.strip():
                        last_line = line
        except OSError:
            pass

        claude_result = None
        reason = None
        last_line = last_line.strip()

        if last_line:
            try:
                parsed = json.loads(last_line)
                if parsed.get("type") == "result":
                    claude_result = parsed
                    result_text = parsed.get("result", "")
                    m = _PAT_REASON.search(result_text)
                    reason = m.group(1).upper() if m else None
                    if reason is None and _PAT_RATE_LIMIT.search(result_text):
                        reason = "RATE_LIMITED"
            except json.JSONDecodeError:
                pass

        return reason, proc.returncode, claude_result
