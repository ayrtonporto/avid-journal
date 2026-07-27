"""
AViD Journal — Model-agnostic verification loop.

Para proveedores API (OpenAI, DeepSeek, Leanstral, etc.) que no tienen
un loop interno de leer-errores-corregir. Este módulo implementa ese loop
de forma genérica: funciona con cualquier APIProvider.

Flujo:
  1. Enviar prompt al modelo → recibir respuesta
  2. Extraer código Lean de la respuesta
  3. Escribir código en target_path
  4. Compilar con lake env lean
  5. Si hay errores o sorry: construir nuevo prompt con errores + código
  6. Repetir hasta éxito o max_rounds
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from ..providers.base import APIProvider, FormalizationResult

logger = logging.getLogger(__name__)


def verification_loop(
    provider: APIProvider,
    target_path: Path,
    prompt: str,
    max_rounds: int,
    cwd: Path,
) -> FormalizationResult:
    """Loop de verificación agnóstico al modelo.

    Args:
        provider: instancia de APIProvider (implementa generate()).
        target_path: archivo .lean a editar.
        prompt: prompt inicial completo.
        max_rounds: máximo de rondas de envío→compilación→corrección.
        cwd: directorio del proyecto Lean.

    Returns:
        FormalizationResult con éxito/fallo.
    """
    from .lean_checker import check_lean_file

    messages: list[dict] = [{"role": "user", "content": prompt}]
    last_code = ""
    seen_hashes: set[str] = set()
    repeat_count = 0

    for round_num in range(1, max_rounds + 1):
        # 1. Llamar al modelo
        response = provider.generate(messages)

        # 2. Extraer código Lean de la respuesta
        code = _extract_lean_code(response)
        if not code.strip():
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": (
                    "No Lean code found in your response. "
                    "Please provide the complete Lean 4 code between "
                    "```lean and ``` markers."
                ),
            })
            continue

        # 2b. Detectar código idéntico repetido (modelo estancado)
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if code_hash in seen_hashes:
            repeat_count += 1
            logger.warning(
                "Round %d: identical code repeated (hash=%s, repeat #%d)",
                round_num, code_hash[:12], repeat_count,
            )
            if repeat_count >= 2:
                logger.error(
                    "Model stuck: same output %d times. Aborting.",
                    repeat_count + 1,
                )
                return FormalizationResult(
                    success=False,
                    info="STUCK",
                    rounds_used=round_num,
                    extracted_code=code,
                )
        else:
            repeat_count = 0
            seen_hashes.add(code_hash)

        # 3. Escribir código en el archivo target
        target_path.write_text(code, encoding="utf-8")

        # 4. Compilar
        has_error, has_sorry, stdout, stderr = check_lean_file(target_path)

        # 5. Evaluar resultado
        if not has_error and not has_sorry:
            return FormalizationResult(
                success=True,
                info="COMPLETE",
                rounds_used=round_num,
                extracted_code=code,
            )

        # Construir feedback para la próxima ronda
        feedback = _build_error_feedback(
            has_error, has_sorry, stdout, stderr, code,
        )
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": feedback})
        last_code = code

    # Se agotaron las rondas
    return FormalizationResult(
        success=False,
        info="LIMIT",
        rounds_used=max_rounds,
        extracted_code=last_code,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_lean_code(response: str) -> str:
    """Extrae código Lean de una respuesta del modelo.

    Busca bloques de código marcados con ```lean ... ```.
    Si no encuentra, devuelve la respuesta completa (best-effort).
    """
    import re

    # Buscar bloque ```lean ... ```
    pattern = re.compile(r"```(?:lean4?|Lean)\s*\n(.*?)```", re.DOTALL)
    matches = pattern.findall(response)
    if matches:
        return "\n\n".join(m.strip() for m in matches)

    # Buscar cualquier bloque de código ```
    pattern = re.compile(r"```\s*\n(.*?)```", re.DOTALL)
    matches = pattern.findall(response)
    if matches:
        return "\n\n".join(m.strip() for m in matches)

    # Sin bloques: devolver la respuesta tal cual
    return response.strip()


def _build_error_feedback(
    has_error: bool,
    has_sorry: bool,
    stdout: str,
    stderr: str,
    code: str = "",
) -> str:
    """Construye un mensaje de feedback para el modelo con los errores.

    Incluye el código que falló y la salida de error de Lean para que
    el modelo pueda corregir con contexto completo.
    """
    parts: list[str] = []

    if has_error:
        parts.append("## ❌ Compilation failed\n")

        # Show actual error output first (most important)
        error_text = ""
        if stderr.strip():
            stderr_lines = stderr.strip().splitlines()
            error_text = "\n".join(stderr_lines[-40:])
        if stdout.strip():
            stdout_lines = stdout.strip().splitlines()
            if error_text:
                error_text += "\n" + "\n".join(stdout_lines[-20:])
            else:
                error_text = "\n".join(stdout_lines[-40:])

        if error_text.strip():
            parts.append("```\n" + error_text.strip() + "\n```\n")
        else:
            parts.append(
                "(Lean exited with non-zero status but produced no error output. "
                "Check for syntax errors, duplicate definitions, or missing imports.)\n\n"
            )

    if has_sorry:
        parts.append("## ❌ Unresolved `sorry`\n")
        parts.append(
            "The code contains `sorry` placeholders. "
            "Replace each `sorry` with an actual proof.\n\n"
        )

    # Include the failing code for context
    if code.strip():
        parts.append("## Your code that failed\n")
        # Truncate if very long
        code_display = code.strip()
        if len(code_display) > 3000:
            code_display = code_display[:1500] + "\n\n... (truncated) ...\n\n" + code_display[-1500:]
        parts.append("```lean\n" + code_display + "\n```\n")

    parts.append(
        "## Instructions\n"
        "Fix ALL errors in the code above. "
        "Return ONLY the corrected Lean 4 code between ```lean and ``` markers. "
        "Do NOT repeat definitions that are already imported or defined elsewhere — "
        "only output the NEW declaration(s) needed for this block."
    )

    return "\n".join(parts)
