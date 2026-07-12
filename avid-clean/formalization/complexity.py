"""
AViD Journal - Block Complexity Classifier
==========================================
Dado un bloque extraido por el parser LaTeX, decide que modo de
formalizacion usar (que prompt lanzar con Claude Code).
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Dict, Optional


class Mode(str, Enum):
    """Modo de formalizacion para un bloque."""

    SIMPLE = "simple"      # prompt_avid.txt
    MEDIUM = "medium"      # prompt_medium_mode_avid.txt
    HARD = "hard"          # prompt_hard_mode_avid.txt
    EXTERNAL = "external"  # no lanza Claude; ruta Mathlib-search -> axioma


# Tipos que llevan prueba
PROVING_TYPES = {"theorem", "lemma", "proposition", "corollary"}

# Umbral de longitud para considerar la prueba "larga"
MEDIUM_PROOF_LEN_THRESHOLD = 800

# Senales de complejidad dentro de proof_latex
COMPLEXITY_SIGNALS = [
    r"\bcase(s)?\b",            # case analysis
    r"\binduction\b",            # inductive proofs
    r"\binducci[oó]n\b",         # spanish
    r"\bWLOG\b",
    r"\bcontradict\b",
    r"\bcontrapositive\b",
    r"\blemma\b",                # inline aux lemma reference
    r"\\begin\{cases\}",         # LaTeX case environment
]


def _count_steps(proof_latex: str) -> int:
    """Heuristica: cuenta 'pasos distintos' en la prueba informal.

    Usa como senal enumerate/itemize, separadores tipo "Step", "Paso",
    "First", "Next", "Finally", etc.
    """
    if not proof_latex:
        return 0

    lower = proof_latex.lower()
    count = 0

    # enumeraciones explicitas
    count += len(re.findall(r"\\begin\{enumerate\}", lower))
    count += len(re.findall(r"\\begin\{itemize\}", lower))

    # marcadores de paso
    step_markers = [
        r"\bstep\s+\d+",
        r"\bpaso\s+\d+",
        r"\bfirst[,\s]",
        r"\bsecond[,\s]",
        r"\bthird[,\s]",
        r"\bfinally[,\s]",
        r"\bnext[,\s]",
        r"\bprimero[,\s]",
        r"\bsegundo[,\s]",
        r"\btercero[,\s]",
        r"\bfinalmente[,\s]",
    ]
    for pat in step_markers:
        count += len(re.findall(pat, lower))

    return count


def _has_complexity_signals(proof_latex: str) -> bool:
    """True si la prueba exhibe al menos una senal de complejidad."""
    if not proof_latex:
        return False
    for pat in COMPLEXITY_SIGNALS:
        if re.search(pat, proof_latex, re.IGNORECASE):
            return True
    return False


def classify(block: Dict[str, Optional[str]]) -> Mode:
    """Clasifica un bloque del parser en un modo de formalizacion.

    Args:
        block: dict con las claves 'type', 'content_latex', 'proof_latex'
               (tal como devuelve LaTeXParser.parse_text).

    Returns:
        Mode correspondiente.
    """
    btype = (block.get("type") or "").lower()
    proof = block.get("proof_latex")
    content = block.get("content_latex") or ""

    # Definiciones: siempre modo simple (no tienen prueba)
    if btype == "definition":
        return Mode.SIMPLE

    # Tipos probatorios
    if btype in PROVING_TYPES:
        # Sin prueba explicita -> resultado externo (Mathlib o axioma)
        if not proof or not proof.strip():
            return Mode.EXTERNAL

        # Con prueba: decidir medium vs hard
        proof_len = len(proof)
        steps = _count_steps(proof)
        complex_signals = _has_complexity_signals(proof)

        is_hard = (
            proof_len >= MEDIUM_PROOF_LEN_THRESHOLD
            or steps >= 3
            or (proof_len >= 400 and complex_signals)
        )
        return Mode.HARD if is_hard else Mode.MEDIUM

    # Tipos desconocidos: trata como SIMPLE (best effort)
    return Mode.SIMPLE


def prompt_file_for(mode: Mode) -> str:
    """Mapea un Mode al nombre del archivo de prompt correspondiente.

    Las rutas son relativas a la carpeta `prompts/` del repo.
    """
    return {
        Mode.SIMPLE: "prompt_avid.txt",
        Mode.MEDIUM: "prompt_medium_mode_avid.txt",
        Mode.HARD: "prompt_hard_mode_avid.txt",
    }[mode]


def max_rounds_for(mode: Mode) -> int:
    """Presupuesto de rondas por modo (pasado a run_claude)."""
    return {
        Mode.SIMPLE: 5,
        Mode.MEDIUM: 15,
        Mode.HARD: 30,
    }[mode]


# ------------------------------------------------------------------
# Demo rapida
# ------------------------------------------------------------------

if __name__ == "__main__":
    samples = [
        {"type": "definition", "content_latex": "A group is a set...", "proof_latex": None},
        {"type": "lemma", "content_latex": "Even+Even=Even", "proof_latex": "Straightforward."},
        {
            "type": "theorem",
            "content_latex": "FLT",
            "proof_latex": "First, we use induction on n. Step 1: base case. Step 2: hypothesis. "
                           "Step 3: inductive step. By WLOG we reduce to primes...",
        },
        {"type": "theorem", "content_latex": "External fact", "proof_latex": None},
    ]

    for i, b in enumerate(samples, 1):
        m = classify(b)
        print(f"Sample {i} ({b['type']}): mode={m.value}")
