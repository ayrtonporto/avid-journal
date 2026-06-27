"""AViD Journal — Novelty v2.

Implementación de la métrica de novedad según paper/metric_spec.md.

Tres dimensiones independientes:
  D1 — No-existencia previa  (dimensions/d1_existence.py)
  D2 — No-trivialidad        (dimensions/d2_triviality.py)
  D3 — Distancia estructural (dimensions/d3_premises.py)

Árbol de decisión combinado y cinco veredictos finales definidos en
types.py y orchestrator.py.

Relación con src/novelty/ (v1):
  src/novelty/ NO se modifica. Este módulo la importa como dependencia
  externa para reutilizar:
    - mathlib_checker.check_in_mathlib()   → D1 sobre C_F
    - arxiv_search.search_semantic_scholar/arxiv()  → D1 sobre C_I etapa A
    - block_comparator (MiniLM)            → D1 sobre C_I etapa A (similitud)
    - llm_judge.judge_theorem_pair()       → D1 sobre C_I etapa B
    - _cache.cache_or_fetch()              → caching compartido
"""

from src.novelty_v2.orchestrator import check_novelty
from src.novelty_v2.types import (
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
