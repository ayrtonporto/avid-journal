"""
AViD Journal — Provider registry and configuration.

Resuelve qué proveedor de modelo usar desde:
1. Parámetro explícito (pasado a formalize_paper)
2. Variable de entorno AVID_MODEL_PROVIDER
3. Default: "opencode" (OpenCode Go)

Providers disponibles y sus variables de entorno:

    opencode    OPENCODE_GO_API_KEY     (default, usa DeepSeek V4 Pro)
    claude      —                       (Claude Code CLI, requiere claude auth login)
    anthropic   ANTHROPIC_API_KEY       (Claude Sonnet 4 vía API directa)
    openai      OPENAI_API_KEY          (GPT-4o, etc.)
    deepseek    DEEPSEEK_API_KEY        (DeepSeek Chat V3)
    openrouter  OPENROUTER_API_KEY      (cualquier modelo via OpenRouter)
    mistral     MISTRAL_API_KEY         (Mistral Large)
    gemini      GEMINI_API_KEY          (Gemini 2.5 Pro)

Todos los providers API (menos claude) usan el mismo OpenAIChatProvider
con distintos base_url y model. El registry mapea nombres a factories.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

from .base import ModelProvider
from .claude_code import ClaudeCodeProvider
from .openai_compatible import OpenAIChatProvider
from .anthropic import AnthropicProvider


# ---------------------------------------------------------------------------
# Factory functions — cada una lee su propia variable de entorno
# ---------------------------------------------------------------------------

def _make_opencode() -> ModelProvider:
    api_key = os.environ.get("OPENCODE_GO_API_KEY", "")
    if not api_key:
        raise ValueError(
            "OPENCODE_GO_API_KEY no está configurada. "
            "Configurala con: export OPENCODE_GO_API_KEY=sk-..."
        )
    model = os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-pro")
    return OpenAIChatProvider(
        api_key=api_key,
        base_url="https://opencode.ai/zen/go/v1",
        model=model,
    )


def _make_openai() -> ModelProvider:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY no está configurada.")
    return OpenAIChatProvider(
        api_key=api_key,
        base_url="https://api.openai.com/v1",
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
    )


def _make_deepseek() -> ModelProvider:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY no está configurada.")
    return OpenAIChatProvider(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
    )


def _make_openrouter() -> ModelProvider:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY no está configurada.")
    return OpenAIChatProvider(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model=os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4"),
    )


def _make_mistral() -> ModelProvider:
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY no está configurada.")
    return OpenAIChatProvider(
        api_key=api_key,
        base_url="https://api.mistral.ai/v1",
        model=os.environ.get("MISTRAL_MODEL", "mistral-large-latest"),
    )


def _make_gemini() -> ModelProvider:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no está configurada.")
    return OpenAIChatProvider(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        model=os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"),
    )


def _make_anthropic() -> ModelProvider:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY no está configurada.")
    return AnthropicProvider(
        api_key=api_key,
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
    )


def _make_claude() -> ModelProvider:
    return ClaudeCodeProvider()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ProviderFactory = Callable[[], ModelProvider]

PROVIDER_REGISTRY: dict[str, ProviderFactory] = {
    "opencode":   _make_opencode,
    "anthropic":  _make_anthropic,
    "openai":     _make_openai,
    "deepseek":   _make_deepseek,
    "openrouter": _make_openrouter,
    "mistral":    _make_mistral,
    "gemini":     _make_gemini,
    "claude":     _make_claude,
}


def resolve_provider(model_spec: Optional[str] = None) -> ModelProvider:
    """Resuelve el proveedor de modelo desde configuración.

    Prioridad:
    1. Parámetro explícito `model_spec`
    2. Variable de entorno `AVID_MODEL_PROVIDER`
    3. Default: "opencode"

    Args:
        model_spec: nombre del provider.
                    None → usa AVID_MODEL_PROVIDER o default "opencode".

    Returns:
        Instancia de ModelProvider lista para usar.

    Raises:
        ValueError: si el provider no está en el registry o le falta API key.
    """
    name = model_spec or os.environ.get("AVID_MODEL_PROVIDER", "opencode")
    name = name.lower().strip()

    if name not in PROVIDER_REGISTRY:
        available = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(
            f"Provider desconocido: '{name}'. "
            f"Providers disponibles: {available}"
        )

    factory = PROVIDER_REGISTRY[name]
    return factory()
