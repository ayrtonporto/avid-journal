"""
AViD Journal — Model providers package.

Provee la abstracción ModelProvider y el registry de proveedores.

Providers disponibles:
    opencode    — OpenCode Go (DeepSeek V4 Pro/Flash, default)
    claude      — Claude Code CLI (agentic, requiere claude auth login)
    openai      — OpenAI (GPT-4o, etc.)
    deepseek    — DeepSeek directo (Chat V3)
    openrouter  — OpenRouter (cualquier modelo)
    mistral     — Mistral AI (Large)
    gemini      — Google Gemini (2.5 Pro)

Uso:
    export OPENCODE_GO_API_KEY=sk-...
    export AVID_MODEL_PROVIDER=opencode   # o pasarlo como parámetro
"""

from .base import ModelProvider, AgenticProvider, APIProvider, FormalizationResult
from .config import resolve_provider, PROVIDER_REGISTRY
from .openai_compatible import OpenAIChatProvider
from .anthropic import AnthropicProvider

__all__ = [
    "ModelProvider",
    "AgenticProvider",
    "APIProvider",
    "FormalizationResult",
    "OpenAIChatProvider",
    "AnthropicProvider",
    "resolve_provider",
    "PROVIDER_REGISTRY",
]
