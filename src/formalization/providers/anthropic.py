"""
AViD Journal — Anthropic API provider.

Uses Anthropic's OpenAI-compatible endpoint.
Base URL: https://api.anthropic.com/v1
Auth: x-api-key header (NOT Bearer)
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

import requests

from .base import APIProvider


class AnthropicProvider(APIProvider):
    """Provider for Anthropic's OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY no está configurada. "
                "Configurala con: export ANTHROPIC_API_KEY=sk-ant-..."
            )
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        self.temperature = temperature
        self.max_tokens = max_tokens

    # ------------------------------------------------------------------
    # APIProvider interface
    # ------------------------------------------------------------------

    def generate(self, messages: list[dict]) -> str:
        """Send a chat completion request via Anthropic's OpenAI-compatible API."""
        url = "https://api.anthropic.com/v1/chat/completions"

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                resp = requests.post(url, json=body, headers=headers, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]

                try:
                    error_msg = resp.json().get("error", {}).get("message", str(resp.text))
                except Exception:
                    error_msg = resp.text[:200]

                if resp.status_code == 429:
                    wait = 2 ** attempt
                    print(f"[anthropic] Rate limited (429), retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                elif resp.status_code >= 500:
                    wait = 2 ** attempt
                    print(f"[anthropic] Server error ({resp.status_code}), retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                else:
                    raise RuntimeError(f"Anthropic API error {resp.status_code}: {error_msg}")

            except requests.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"[anthropic] Error: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                raise

        raise RuntimeError(f"Anthropic API call failed after {max_retries} attempts: {last_error}")

    def __repr__(self) -> str:
        return f"AnthropicProvider(model={self.model!r})"
