"""
AViD Journal — Model Provider abstraction.
==========================================================================

Interfaz uniforme para cualquier modelo que formalice código Lean 4.
Cada proveedor (Claude Code, DeepSeek, Leanstral, OpenRouter, etc.)
implementa esta interfaz. El orchestrator solo depende de esta abstracción,
nunca de un modelo concreto.

Dos familias de proveedores:

1. AgenticProvider — el modelo maneja el loop de verificación internamente
   (Claude Code, OpenCode). El provider solo invoca y espera el resultado.

2. APIProvider — el modelo es una API de chat. El sistema ejecuta un loop
   de verificación agnóstico: enviar prompt → recibir código → compilar →
   si hay errores, realimentar → repetir.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FormalizationResult:
    """Resultado estructurado de una tarea de formalización.

    Attributes:
        success: True si el código compila sin errores ni sorry.
        info: "COMPLETE", "LIMIT", "RATE_LIMITED", o mensaje de error.
        rounds_used: cantidad de rondas consumidas.
        extracted_code: código Lean extraído (sin imports/banner), si existe.
    """

    success: bool
    info: str
    rounds_used: int = 0
    extracted_code: str = ""


# ---------------------------------------------------------------------------
# Provider base
# ---------------------------------------------------------------------------


class ModelProvider(ABC):
    """Interfaz abstracta para un proveedor de modelo.

    Cada implementación concreta debe proveer `formalize()`.
    """

    @abstractmethod
    def formalize(
        self,
        target_path: Path,
        prompt: str,
        max_rounds: int,
        cwd: Path,
    ) -> FormalizationResult:
        """Ejecuta el modelo sobre una tarea de formalización.

        El modelo debe escribir el código Lean resultante en `target_path`.
        El caller (orchestrator) luego verifica la compilación con
        `check_lean_file()` y extrae las declaraciones.

        Args:
            target_path: archivo .lean que el modelo debe editar.
            prompt: contenido completo del prompt (TASK.md + system prompt).
            max_rounds: presupuesto máximo de rondas/iteraciones.
            cwd: directorio de trabajo (raíz del proyecto Lean del paper).

        Returns:
            FormalizationResult con éxito/fallo y metadata.
        """
        ...


class AgenticProvider(ModelProvider):
    """Proveedor que maneja el loop de verificación internamente.

    Claude Code, OpenCode y similares tienen su propio ciclo de
    leer-errores-corregir-reintentar. El provider solo lanza el proceso
    y recoge el resultado final.
    """

    pass


class APIProvider(ModelProvider):
    """Proveedor basado en API de chat (sin loop interno).

    OpenAI, DeepSeek, Leanstral, etc. no tienen loop de verificación.
    El sistema ejecuta `verification_loop()` que orquesta:
    enviar prompt → recibir código → compilar → errores → realimentar.

    Las subclases solo deben implementar `generate(messages) -> str`.
    """

    @abstractmethod
    def generate(self, messages: list[dict]) -> str:
        """Envía una lista de mensajes al modelo y retorna la respuesta.

        Args:
            messages: lista de dicts {"role": "...", "content": "..."}
                      en formato OpenAI Chat Completions.

        Returns:
            Texto de la respuesta del modelo.
        """
        ...

    def formalize(
        self,
        target_path: Path,
        prompt: str,
        max_rounds: int,
        cwd: Path,
    ) -> FormalizationResult:
        """Implementación por defecto: delega en verification_loop."""
        from ..scripts.verification_loop import verification_loop

        return verification_loop(self, target_path, prompt, max_rounds, cwd)
