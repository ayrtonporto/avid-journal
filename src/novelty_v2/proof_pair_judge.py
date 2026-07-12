"""Judge LLM de distintividad de pruebas (proof pair judge).

Compara dos pruebas Lean del mismo teorema y emite un veredicto:
  - genuinely_different: ideas matemáticas centrales distintas
  - same_disguised:   misma idea con cambios cosméticos
  - statement_mismatch: los enunciados NO coinciden (sin llamar al LLM)
  - error: falló la llamada al LLM o el parseo

El veredicto es OPINIÓN del juez LLM. Se registra junto al campo
user_label (que llena el usuario). Nunca se usa como etiqueta final
sin firma del usuario.

Usa la misma infraestructura que llm_judge.py: DeepSeek V4 Flash,
temperature=0, via OpenCode Go API (OpenAI-compatible).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.novelty.llm_judge import _call_deepseek, _parse_json_blob

logger = logging.getLogger(__name__)


def _truncate_text(text: str, limit: int = 2500) -> str:
    """Truncate text to limit chars, adding marker if truncated."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n-- [truncated]"

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

PAIR_VERDICTS = {"genuinely_different", "same_disguised"}


@dataclass
class ProofPairJudgment:
    """Resultado completo del juez de pares de pruebas."""

    pair_id: str
    """Identificador del par (ej. 'T08a_vs_T08b')."""

    statement_match: bool
    """True si los enunciados coinciden (mismo tipo Lean)."""

    statement_a: str = ""
    """Enunciado extraído de la prueba A (tipo Lean)."""

    statement_b: str = ""
    """Enunciado extraído de la prueba B (tipo Lean)."""

    idea_a: str = ""
    """Idea matemática central de la prueba A (1 frase, del LLM)."""

    idea_b: str = ""
    """Idea matemática central de la prueba B (1 frase, del LLM)."""

    verdict: str = ""
    """Veredicto del juez LLM: 'genuinely_different' | 'same_disguised' |
    'statement_mismatch' | 'error'."""

    justification: str = ""
    """Justificación del veredicto (2-3 oraciones, del LLM)."""

    user_label: str = ""
    """Etiqueta final firmada por el usuario (vacía hasta que el usuario la llene)."""

    raw_response: str = ""
    """Respuesta cruda del LLM (para debugging)."""

    def to_dict(self) -> dict:
        return {
            "pair_id": self.pair_id,
            "statement_match": self.statement_match,
            "statement_a": self.statement_a,
            "statement_b": self.statement_b,
            "idea_a": self.idea_a,
            "idea_b": self.idea_b,
            "verdict": self.verdict,
            "justification": self.justification,
            "user_label": self.user_label,
        }


# ---------------------------------------------------------------------------
# Mechanical check — statement extraction
# ---------------------------------------------------------------------------

_STMT_RE = re.compile(
    r"^\s*theorem\s+\S+.*?:\s*(.+?)\s*:=\s*",
    re.DOTALL | re.MULTILINE,
)


def _extract_statement(lean_text: str) -> Optional[str]:
    """Extrae el enunciado (tipo) de un teorema Lean.

    Busca el texto entre 'theorem name ... :' y ':='.
    Retorna el tipo normalizado (whitespace colapsado) o None.
    """
    # Quitar comentarios de línea
    clean_lines = []
    for line in lean_text.split("\n"):
        # Quitar comentarios (-- ...)
        stripped = re.sub(r"--.*$", "", line)
        clean_lines.append(stripped)
    clean = "\n".join(clean_lines)

    match = _STMT_RE.search(clean)
    if not match:
        return None

    stmt = match.group(1).strip()
    # Colapsar whitespace para comparación robusta
    stmt = re.sub(r"\s+", " ", stmt)
    return stmt


def _statements_match(text_a: str, text_b: str) -> tuple[bool, str, str]:
    """Compara mecánicamente los enunciados de dos pruebas Lean.

    Returns:
        (match, stmt_a, stmt_b) donde match es True si los enunciados
        son sintácticamente idénticos después de normalización.
    """
    stmt_a = _extract_statement(text_a) or ""
    stmt_b = _extract_statement(text_b) or ""

    if not stmt_a or not stmt_b:
        return False, stmt_a, stmt_b

    return stmt_a == stmt_b, stmt_a, stmt_b


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

PAIR_JUDGE_PROMPT = """You are a careful mathematician comparing two formal proofs
written in Lean 4. Both proofs establish the SAME theorem statement.
Your job: decide whether the two proofs are GENUINELY DIFFERENT
or the SAME proof in disguise (cosmetic changes only).

Reply with a JSON object on a single line, no extra prose, with keys:
  idea_a        : one-sentence description of the CENTRAL mathematical idea
                  behind proof A (the core insight or technique)
  idea_b        : one-sentence description of the CENTRAL mathematical idea
                  behind proof B
  verdict       : "genuinely_different" or "same_disguised"
  justification : 2-3 sentences explaining WHY the proofs are genuinely
                  different or merely the same in disguise. Reference
                  specific tactics, lemmas, or reasoning structures.

Definitions:
  - genuinely_different: the two proofs rely on fundamentally different
    mathematical insights, techniques, or lemmas (e.g., parity argument
    vs. valuation theory; induction vs. combinatorial pairing).
  - same_disguised: the two proofs use the same core reasoning with
    superficial differences (renamed variables, reordered steps,
    slightly different but equivalent lemma calls).

Proof A:
```lean
{proof_a}
```

Proof B:
```lean
{proof_b}
```

JSON:"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def judge_proof_pair(
    proof_a_text: str,
    proof_b_text: str,
    *,
    pair_id: str = "",
) -> ProofPairJudgment:
    """Evalúa si dos pruebas Lean del mismo teorema son genuinamente distintas.

    Pipeline:
      1. Mechanical check: extraer enunciados → comparar tipos.
         Si difieren → statement_mismatch (sin llamar al LLM).
      2. LLM call (DeepSeek V4 Flash, temperature=0):
         describir idea central de cada prueba + veredicto + justificación.
      3. Parsear JSON → ProofPairJudgment.

    Args:
        proof_a_text: texto completo de la prueba A (Lean 4).
        proof_b_text: texto completo de la prueba B (Lean 4).
        pair_id: identificador opcional del par.

    Returns:
        ProofPairJudgment con todos los campos poblados.
    """
    result = ProofPairJudgment(pair_id=pair_id, statement_match=False)

    # ── Step 1: Mechanical statement check ─────────────────────────────
    match, stmt_a, stmt_b = _statements_match(proof_a_text, proof_b_text)
    result.statement_match = match
    result.statement_a = stmt_a
    result.statement_b = stmt_b

    if not match:
        result.verdict = "statement_mismatch"
        result.justification = (
            "Los enunciados no coinciden sintácticamente. "
            f"A: '{stmt_a[:100]}...' vs B: '{stmt_b[:100]}...'"
        )
        return result

    # ── Step 2: LLM call ──────────────────────────────────────────────
    # Truncate long proofs to keep prompt manageable for the LLM
    # (DeepSeek V4 Flash needs token budget for reasoning + response)
    _TRUNC_LIMIT = 2500  # chars per proof; enough to see the core structure
    proof_a_trimmed = _truncate_text(proof_a_text, _TRUNC_LIMIT)
    proof_b_trimmed = _truncate_text(proof_b_text, _TRUNC_LIMIT)

    prompt = PAIR_JUDGE_PROMPT.format(
        proof_a=proof_a_trimmed,
        proof_b=proof_b_trimmed,
    )

    try:
        # Use higher max_tokens: 4096 base, retry auto-doubles to 8192
        raw = _call_deepseek(prompt, temperature=0.0, max_tokens=4096)
        result.raw_response = raw
    except Exception as exc:
        logger.warning("Proof pair judge: LLM call failed for %s: %s", pair_id, exc)
        result.verdict = "error"
        result.justification = f"LLM call failed: {exc}"
        return result

    # ── Step 3: Parse JSON ────────────────────────────────────────────
    parsed = _parse_json_blob(raw)
    if not parsed:
        result.verdict = "error"
        result.justification = f"Could not parse LLM response: {raw[:200]}"
        return result

    result.idea_a = str(parsed.get("idea_a", ""))
    result.idea_b = str(parsed.get("idea_b", ""))
    result.justification = str(parsed.get("justification", ""))

    verdict_raw = str(parsed.get("verdict", "")).strip().lower()
    if verdict_raw in PAIR_VERDICTS:
        result.verdict = verdict_raw
    else:
        logger.warning(
            "Proof pair judge: unexpected verdict '%s' for %s, defaulting to error",
            verdict_raw, pair_id,
        )
        result.verdict = "error"
        result.justification = (
            f"Unexpected verdict '{verdict_raw}'. "
            f"Justification: {result.justification}"
        )

    return result


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def judge_pairs(
    pairs: list[dict],
) -> list[ProofPairJudgment]:
    """Ejecuta el juez sobre una lista de pares.

    Cada dict debe tener:
      - pair_id: str
      - proof_a: str (texto Lean completo)
      - proof_b: str (texto Lean completo)

    Returns:
        Lista de ProofPairJudgment en el mismo orden.
    """
    results = []
    for pair in pairs:
        pid = pair.get("pair_id", "unknown")
        logger.info("Judging pair: %s", pid)
        judgment = judge_proof_pair(
            proof_a_text=pair["proof_a"],
            proof_b_text=pair["proof_b"],
            pair_id=pid,
        )
        results.append(judgment)
    return results
