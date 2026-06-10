"""Tipos de datos para la métrica de novedad v2.

Los cinco veredictos finales siguen exactamente la spec (metric_spec.md §6).
El Caso 5 ("zona gris") se expone vía revision_humana=True en NoveltyVerdict.

Mapeo desde veredictos del llm_judge de v1 (src/novelty/llm_judge.py):
  "equivalent"     → existe_en_C_I = True  (contribuye a NO_NOVEDOSO_redundante
                      o CONOCIDO_LITERATURA según si hay match en C_F)
  "generalization" → revision_humana = True, veredicto = ZONA_GRIS
  "specialization" → revision_humana = True, veredicto = ZONA_GRIS
  "different"      → no hay match → continúa en el árbol
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Verdict(str, Enum):
    """Cinco veredictos finales de la spec + zona gris (Caso 5)."""

    NOVEDAD_ENUNCIADO = "NOVEDAD_ENUNCIADO"
    """D1 no encontró match en C_F ni en C_I. Enunciado genuinamente nuevo."""

    NOVEDAD_DEMOSTRACION = "NOVEDAD_DEMOSTRACION"
    """D1 encontró match de tipo pero D3 indica pruebas estructuralmente distantes."""

    CONOCIDO_LITERATURA = "CONOCIDO_LITERATURA"
    """D1 encontró match en C_I pero no en C_F. La formalización puede ser aporte
    de ingeniería, pero no es contribución matemática nueva."""

    NO_NOVEDOSO_redundante = "NO_NOVEDOSO_redundante"
    """D1 encontró match de tipo en C_F y D3 indica pruebas cercanas (misma prueba)."""

    NO_NOVEDOSO_trivial = "NO_NOVEDOSO_trivial"
    """D2 cerró el enunciado con una táctica estándar. Trivial sin ideas."""

    ZONA_GRIS = "ZONA_GRIS"
    """Caso 5: tipos relacionados pero no iguales (generalization / specialization
    según el juez LLM). No se fuerza etiqueta; se recomienda revisión humana."""

    MATCH_ENCONTRADO_PENDIENTE_D3 = "MATCH_ENCONTRADO_PENDIENTE_D3"
    """D1 encontró match de tipo en C_F (Mathlib), pero D3 aún no se ejecutó.
    Veredicto provisional: enunciado conocido, novedad de prueba por determinar.
    Cuando D3 corra, se reemplaza por NOVEDAD_DEMOSTRACION o NO_NOVEDOSO_redundante."""


@dataclass
class D1Result:
    """Resultado de la Dimensión 1 — No-existencia previa."""

    existe_en_C_F: bool = False
    """¿Se encontró match de tipo en mathlib (corpus formal)?"""

    existe_en_C_I: bool = False
    """¿Se encontró match en literatura informal (arXiv / Semantic Scholar)?"""

    match_C_F: Optional[Dict[str, Any]] = None
    """Mejor match en C_F: {lean_name, statement, similarity, url}."""

    match_C_I: Optional[Dict[str, Any]] = None
    """Mejor match en C_I: {paper_id, title, block_title, similarity}."""

    traduccion_incierta: bool = False
    """True si la clasificación depende de una autoformalización con baja confianza.
    Cuando es True, el veredicto final debe marcarse como requiriendo revisión."""

    llm_judge_verdict: Optional[str] = None
    """Veredicto crudo del llm_judge: 'equivalent'|'generalization'|'specialization'|'different'."""


@dataclass
class D2Result:
    """Resultado de la Dimensión 2 — No-trivialidad."""

    trivial: bool = False
    """¿Alguna táctica de T_auto cerró el enunciado?"""

    tactica: Optional[str] = None
    """Táctica que lo cerró ('decide'|'omega'|'simp'|'norm_num'|'aesop'|'tauto'|'exact?')."""

    tiempo_segundos: Optional[float] = None
    """Tiempo que tardó la táctica ganadora en cerrar el goal."""

    all_attempts: List[Tuple[str, bool, float, Optional[str]]] = field(default_factory=list)
    """Lista de intentos: (tactic_name, success, elapsed_seconds, output_or_error).
    Incluye todas las tácticas intentadas, en orden, hasta y con la ganadora."""


@dataclass
class D3Result:
    """Resultado de la Dimensión 3 — Distancia estructural de pruebas."""

    activa: bool = False
    """D3 solo se activa si D1 encontró match de tipo (existe_en_C_F=True)."""

    premisas_candidato: List[str] = field(default_factory=list)
    """Premisas de la prueba existente en C_F (extraídas con LeanDojo)."""

    premisas_nueva: List[str] = field(default_factory=list)
    """Premisas de la prueba candidata (extraídas con LeanDojo)."""

    jaccard: Optional[float] = None
    """Distancia de Jaccard: 1 - |P1 ∩ P2| / |P1 ∪ P2|. None si no se pudo calcular."""

    umbral_theta: float = 0.5
    """Umbral de decisión. Valor inicial 0.5; calibrar con pares T07/T08/T09."""

    pruebas_distantes: Optional[bool] = None
    """True si jaccard > umbral_theta (prueba alternativa)."""


@dataclass
class NoveltyVerdict:
    """Veredicto final completo de la métrica de novedad v2."""

    veredicto: Verdict
    """Uno de los cinco veredictos de la spec, o ZONA_GRIS (Caso 5)."""

    d1: D1Result = field(default_factory=D1Result)
    d2: D2Result = field(default_factory=D2Result)
    d3: D3Result = field(default_factory=D3Result)

    revision_humana: bool = False
    """True cuando el veredicto depende de traducción incierta o es ZONA_GRIS."""

    razonamiento: str = ""
    """Explicación en lenguaje natural del camino recorrido en el árbol de decisión."""

    stage_detenido: int = -1
    """
    En qué paso del árbol se tomó la decisión final:
      2 → D2 (trivialidad)
      1f → D1 sobre C_F
      1i → D1 sobre C_I
      3 → D3 (distancia de premisas)
    """

    def to_dict(self) -> Dict[str, Any]:
        return {
            "veredicto": self.veredicto.value,
            "revision_humana": self.revision_humana,
            "razonamiento": self.razonamiento,
            "stage_detenido": self.stage_detenido,
            "d1": {
                "existe_en_C_F": self.d1.existe_en_C_F,
                "existe_en_C_I": self.d1.existe_en_C_I,
                "match_C_F": self.d1.match_C_F,
                "match_C_I": self.d1.match_C_I,
                "traduccion_incierta": self.d1.traduccion_incierta,
                "llm_judge_verdict": self.d1.llm_judge_verdict,
            },
            "d2": {
                "trivial": self.d2.trivial,
                "tactica": self.d2.tactica,
                "tiempo_segundos": self.d2.tiempo_segundos,
                "all_attempts": [
                    {"tactic": t, "success": s, "runtime": r, "output": o}
                    for t, s, r, o in self.d2.all_attempts
                ],
            },
            "d3": {
                "activa": self.d3.activa,
                "jaccard": self.d3.jaccard,
                "umbral_theta": self.d3.umbral_theta,
                "pruebas_distantes": self.d3.pruebas_distantes,
                "n_premisas_candidato": len(self.d3.premisas_candidato),
                "n_premisas_nueva": len(self.d3.premisas_nueva),
            },
        }
