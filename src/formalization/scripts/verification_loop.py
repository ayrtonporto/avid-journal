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

from pathlib import Path

from ..providers.base import APIProvider, FormalizationResult


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
        feedback = _build_error_feedback(has_error, has_sorry, stdout, stderr)
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
) -> str:
    """Construye un mensaje de feedback para el modelo con los errores."""
    parts = ["The Lean code has the following issues:\n"]

    if has_error:
        parts.append("## Compilation Errors\n")
        if stdout.strip():
            # Mostrar últimas 50 líneas (lo más relevante suele estar al final)
            stdout_lines = stdout.strip().splitlines()
            relevant = stdout_lines[-50:]
            parts.append("```\n" + "\n".join(relevant) + "\n```\n")
        if stderr.strip():
            stderr_lines = stderr.strip().splitlines()
            relevant = stderr_lines[-20:]
            parts.append("```\n" + "\n".join(relevant) + "\n```\n")

    if has_sorry:
        parts.append(
            "## Unresolved `sorry`\n"
            "The code contains `sorry` placeholders. "
            "Replace each `sorry` with an actual proof.\n"
        )

    parts.append(
        "\nPlease fix ALL errors and remove ALL `sorry` placeholders. "
        "Return the complete corrected Lean code between ```lean and ``` markers."
    )

    return "\n".join(parts)
