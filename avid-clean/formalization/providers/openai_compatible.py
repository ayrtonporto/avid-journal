"""
AViD Journal — OpenAI-compatible API provider.

Generic provider for any LLM that exposes an OpenAI-compatible
chat completions endpoint. Works with:
- OpenAI (gpt-4o, gpt-4.1, etc.)
- DeepSeek (deepseek-chat, deepseek-reasoner) via api.deepseek.com
- OpenRouter (any model) via openrouter.ai
- OpenCode Go (deepseek-v4-pro, deepseek-v4-flash) via opencode.ai
- Together AI, Groq, Fireworks, etc.
- Local models via vLLM / Ollama with OpenAI-compatible servers

Configuration via environment variables:
    AVID_MODEL_API_KEY       — API key (required)
    AVID_MODEL_BASE_URL      — Base URL (default: https://api.openai.com/v1)
    AVID_MODEL_NAME          — Model name (default: gpt-4o)
    AVID_MODEL_TEMPERATURE   — Temperature (default: 0.0)
    AVID_MODEL_MAX_TOKENS    — Max tokens (default: 4096)
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

import requests

from .base import APIProvider


class OpenAIChatProvider(APIProvider):
    """Provider for any OpenAI-compatible chat completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or os.environ.get("AVID_MODEL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set AVID_MODEL_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.base_url = (
            base_url
            or os.environ.get("AVID_MODEL_BASE_URL")
            or "https://api.openai.com/v1"
        )
        self.model = model or os.environ.get("AVID_MODEL_NAME") or "gpt-4o"
        self.temperature = temperature
        self.max_tokens = max_tokens

    # ------------------------------------------------------------------
    # APIProvider interface
    # ------------------------------------------------------------------

    def generate(self, messages: list[dict]) -> str:
        """Send a chat completion request and return the response text."""
        url = f"{self.base_url.rstrip('/')}/chat/completions"

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    msg = data["choices"][0]["message"]
                    content = msg.get("content", "") or ""
                    # DeepSeek v4 models return all output in reasoning_content
                    if not content.strip():
                        reasoning = msg.get("reasoning_content", "") or ""
                        if reasoning.strip():
                            content = reasoning
                    if not content.strip():
                        raise RuntimeError(
                            "API returned empty response "
                            "(both content and reasoning_content are empty)"
                        )
                    return content

                # Error handling
                try:
                    error_msg = resp.json().get("error", {}).get("message", str(resp.text))
                except Exception:
                    error_msg = resp.text[:200]

                if resp.status_code == 429:
                    wait = 2 ** attempt
                    print(f"[api] Rate limited (429), retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                elif resp.status_code >= 500:
                    wait = 2 ** attempt
                    print(f"[api] Server error ({resp.status_code}), retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                else:
                    raise RuntimeError(
                        f"API error {resp.status_code}: {error_msg}"
                    )
            except requests.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"[api] Error: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                raise

        raise RuntimeError(f"API call failed after {max_retries} attempts: {last_error}")

    def __repr__(self) -> str:
        return (
            f"OpenAIChatProvider(model={self.model!r}, "
            f"base_url={self.base_url!r})"
        )


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def deepseek_provider(
    api_key: Optional[str] = None,
    model: str = "deepseek-chat",
) -> OpenAIChatProvider:
    """Create a provider configured for DeepSeek API."""
    return OpenAIChatProvider(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        model=model,
    )


def openrouter_provider(
    api_key: Optional[str] = None,
    model: str = "anthropic/claude-sonnet-4",
) -> OpenAIChatProvider:
    """Create a provider configured for OpenRouter API."""
    return OpenAIChatProvider(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model=model,
    )
