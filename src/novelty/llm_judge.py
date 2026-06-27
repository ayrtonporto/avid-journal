"""Stage 3 (y 5, no usado en v1): juez LLM para comparar enunciados/pruebas.

Recibe pares de bloques marcados como similares por Stage 2 y emite un
veredicto:
  - equivalent       : enuncian el mismo resultado
  - generalization   : el bloque NUEVO generaliza al candidato
  - specialization   : el bloque NUEVO es un caso particular del candidato
  - different        : enuncian resultados distintos

`judge_proof_method` queda definido para Stage 5 (no llamado en v1).

LLM backend: DeepSeek V4 Flash via OpenCode Go API (OpenAI-compatible).
Modelo configurable mediante variable de entorno DEEPSEEK_MODEL o
parámetro `model` en las funciones públicas.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from src.novelty import _cache

# Cargar .env del proyecto y del sistema Hermes (para OPENCODE_GO_API_KEY).
load_dotenv()
_hermes_env = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / ".env"
if _hermes_env.exists():
    load_dotenv(_hermes_env, override=True)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
THEOREM_VERDICTS = {"equivalent", "generalization", "specialization", "different"}
METHOD_VERDICTS = {"same_method", "different_method", "unknown"}
_REPO_ROOT = Path(__file__).resolve().parents[2]

OPENCODE_GO_API_KEY = os.getenv("OPENCODE_GO_API_KEY", "")
OPENCODE_GO_BASE_URL = os.getenv(
    "OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1"
).rstrip("/")


@dataclass
class JudgeVerdict:
    verdict: str
    confidence: float
    reasoning: str


@dataclass
class MethodVerdict:
    verdict: str
    reasoning: str


THEOREM_PROMPT = """You are a careful mathematician comparing two theorem statements
extracted from research papers. Decide the relation between them.

Reply with a JSON object on a single line, no extra prose, with keys:
  verdict     : one of "equivalent", "generalization", "specialization", "different"
  confidence  : float in [0, 1]
  reasoning   : short explanation (<= 2 sentences)

Definitions:
  - equivalent     : up to renaming and routine reformulation, both statements
                     assert the same mathematical fact under the same hypotheses.
  - generalization : statement A logically implies statement B and is strictly
                     stronger (weaker hypotheses or stronger conclusion).
  - specialization : statement A is a strict particular case of statement B.
  - different      : neither implies the other, or they concern different objects.

Statement A (NEW paper):
Title: {title_new}
{statement_new}

Statement B (CANDIDATE paper):
Title: {title_candidate}
{statement_candidate}

JSON:"""


METHOD_PROMPT = """You are a careful mathematician comparing two informal proofs of
(presumably) the same theorem. Decide whether they use the same proof METHOD.

Reply with a JSON object on a single line, no extra prose, with keys:
  verdict   : one of "same_method", "different_method", "unknown"
  reasoning : short explanation (<= 2 sentences)

Proof A (NEW paper):
{proof_new}

Proof B (CANDIDATE paper):
{proof_candidate}

JSON:"""


# ---------------------------------------------------------------------------
# DeepSeek V4 Flash via OpenCode Go (OpenAI-compatible API)
# ---------------------------------------------------------------------------

def _call_deepseek(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 2048,
    timeout: int = 120,
    temperature: float = 0.0,
) -> str:
    """Llama a DeepSeek V4 Flash via la API OpenAI-compatible de OpenCode Go.

    DeepSeek V4 es un modelo con razonamiento interno (reasoning_content).
    Usamos max_tokens=2048 para dar espacio al razonamiento + respuesta JSON.
    Si content vuelve vacío (todos los tokens se fueron en razonamiento),
    se reintenta con el doble de max_tokens, una sola vez.
    """
    if not OPENCODE_GO_API_KEY:
        raise RuntimeError(
            "OPENCODE_GO_API_KEY no está configurada. "
            "Configurala en ~/AppData/Local/hermes/.env"
        )

    url = f"{OPENCODE_GO_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENCODE_GO_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(2):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.exceptions.Timeout:
            raise RuntimeError(f"DeepSeek API timeout after {timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(f"DeepSeek API connection error: {e}")

        if r.status_code != 200:
            detail = r.text[:300]
            raise RuntimeError(
                f"DeepSeek API returned {r.status_code}: {detail}"
            )

        try:
            body = r.json()
        except ValueError:
            raise RuntimeError(f"DeepSeek API returned non-JSON: {r.text[:200]}")

        choices = body.get("choices", [])
        if not choices:
            raise RuntimeError("DeepSeek API returned no choices")

        message = choices[0].get("message", {})
        content = (message.get("content") or "").strip()

        if content:
            return content

        # Content vacío: los tokens se fueron en razonamiento interno.
        # Reintentar con el doble de tokens (solo el primer intento).
        if attempt == 0:
            reasoning_len = len(message.get("reasoning_content") or "")
            logger.info(
                "DeepSeek content empty (%d reasoning chars), "
                "retrying with max_tokens=%d",
                reasoning_len,
                max_tokens * 2,
            )
            payload["max_tokens"] = max_tokens * 2
        else:
            reasoning_len = len(message.get("reasoning_content") or "")
            raise RuntimeError(
                f"DeepSeek returned empty content after retry "
                f"({reasoning_len} reasoning chars). Increase max_tokens."
            )

    raise RuntimeError("DeepSeek unexpected: no content after retries")


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json_blob(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    # Eliminar fences de código si los hay.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_RE.search(text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def _truncate(text: Optional[str], limit: int = 4000) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + " [truncated]"


def judge_theorem_pair(
    block_new: Dict[str, Any],
    block_candidate: Dict[str, Any],
    model: str = DEFAULT_MODEL,
    use_cache: bool = True,
) -> JudgeVerdict:
    prompt = THEOREM_PROMPT.format(
        title_new=block_new.get("title") or "(no title)",
        statement_new=_truncate(block_new.get("content_latex")),
        title_candidate=block_candidate.get("title") or "(no title)",
        statement_candidate=_truncate(block_candidate.get("content_latex")),
    )

    def _do() -> Dict[str, Any]:
        try:
            text = _call_deepseek(prompt, model=model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("DeepSeek call failed: %s", exc)
            return {
                "verdict": "different",
                "confidence": 0.0,
                "reasoning": f"LLM call failed: {exc}",
            }
        parsed = _parse_json_blob(text)
        if not parsed:
            return {
                "verdict": "different",
                "confidence": 0.0,
                "reasoning": f"could not parse LLM response: {text[:200]}",
            }
        verdict = str(parsed.get("verdict", "different")).strip().lower()
        if verdict not in THEOREM_VERDICTS:
            verdict = "different"
        try:
            confidence = float(parsed.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        return {
            "verdict": verdict,
            "confidence": max(0.0, min(1.0, confidence)),
            "reasoning": str(parsed.get("reasoning", "")),
        }

    payload = _cache.cache_or_fetch(
        namespace="judge_theorem",
        key=prompt,
        fetch_fn=_do,
        use_cache=use_cache,
    )
    return JudgeVerdict(
        verdict=payload["verdict"],
        confidence=float(payload.get("confidence", 0.0)),
        reasoning=payload.get("reasoning", ""),
    )


def judge_proof_method(
    proof_new: str,
    proof_candidate: str,
    model: str = DEFAULT_MODEL,
    use_cache: bool = True,
) -> MethodVerdict:
    """Comparacion de metodos de prueba. Reservado para Stage 5 (no usado en v1)."""
    prompt = METHOD_PROMPT.format(
        proof_new=_truncate(proof_new),
        proof_candidate=_truncate(proof_candidate),
    )

    def _do() -> Dict[str, Any]:
        try:
            text = _call_deepseek(prompt, model=model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("DeepSeek call failed: %s", exc)
            return {"verdict": "unknown", "reasoning": f"LLM call failed: {exc}"}
        parsed = _parse_json_blob(text)
        if not parsed:
            return {
                "verdict": "unknown",
                "reasoning": f"could not parse LLM response: {text[:200]}",
            }
        verdict = str(parsed.get("verdict", "unknown")).strip().lower()
        if verdict not in METHOD_VERDICTS:
            verdict = "unknown"
        return {"verdict": verdict, "reasoning": str(parsed.get("reasoning", ""))}

    payload = _cache.cache_or_fetch(
        namespace="judge_method",
        key=prompt,
        fetch_fn=_do,
        use_cache=use_cache,
    )
    return MethodVerdict(
        verdict=payload["verdict"], reasoning=payload.get("reasoning", "")
    )
