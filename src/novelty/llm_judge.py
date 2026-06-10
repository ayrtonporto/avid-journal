"""Stage 3 (y 5, no usado en v1): juez LLM para comparar enunciados/pruebas.

Recibe pares de bloques marcados como similares por Stage 2 y emite un
veredicto:
  - equivalent       : enuncian el mismo resultado
  - generalization   : el bloque NUEVO generaliza al candidato
  - specialization   : el bloque NUEVO es un caso particular del candidato
  - different        : enuncian resultados distintos

`judge_proof_method` queda definido para Stage 5 (no llamado en v1).
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from src.novelty import _cache

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-5"
THEOREM_VERDICTS = {"equivalent", "generalization", "specialization", "different"}
METHOD_VERDICTS = {"same_method", "different_method", "unknown"}


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
# Cliente Anthropic (lazy)
# ---------------------------------------------------------------------------

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _call_claude(prompt: str, model: str, max_tokens: int = 400) -> str:
    client = _get_client()
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = []
    for block in message.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts).strip()


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json_blob(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    # Eliminar fences de codigo si los hay.
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
# API publica
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
            text = _call_claude(prompt, model=model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Anthropic call failed: %s", exc)
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
            text = _call_claude(prompt, model=model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Anthropic call failed: %s", exc)
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
    return MethodVerdict(verdict=payload["verdict"], reasoning=payload.get("reasoning", ""))
