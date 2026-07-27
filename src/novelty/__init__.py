"""AViD Journal — Novelty Check Module.

Implementación de la métrica de novedad.

Tres dimensiones independientes:
  D1 — No-existencia previa  (dimensions/d1_existence.py)
  D2 — No-trivialidad        (dimensions/d2_triviality.py)
  D3 — Distancia estructural (dimensions/d3_premises.py)

Árbol de decisión combinado y siete veredictos finales definidos en
types.py y orchestrator.py.
"""

from src.novelty.orchestrator import check_novelty
from src.novelty.types import (
    NoveltyVerdict,
    Verdict,
    D1Result,
    D2Result,
    D3Result,
)

__all__ = [
    "check_novelty",
    "NoveltyVerdict",
    "Verdict",
    "D1Result",
    "D2Result",
    "D3Result",
]
