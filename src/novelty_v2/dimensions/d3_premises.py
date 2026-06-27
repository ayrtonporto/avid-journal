"""D3 — Distancia estructural de pruebas.

Compara las premisas de la prueba candidata con las de la prueba
existente en Mathlib usando distancia de Jaccard.

IMPLEMENTACIÓN PENDIENTE:
  Requiere LeanDojo 4.20.0+ en WSL2 para extraer premisas de archivos .lean.
  La calibración del umbral θ se hará con pares T07/T08/T09 del eval set.

  Mientras tanto, check_premise_distance() devuelve D3Result(activa=False).

  Estado actual:
    - WSL2 en D:/WSL/Ubuntu2204/ (usuario ayrton)
    - Mathlib cache corrupta → requiere rebuild
    - Solo se ejecutará manualmente (no automatizado en el pipeline)
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.novelty_v2.types import D3Result

logger = logging.getLogger(__name__)


def check_premise_distance(
    lean_name_nuevo: str,
    lean_name_existente: str,
    lean_project_dir: Optional[str] = None,
    umbral_theta: float = 0.5,
) -> D3Result:
    """Compara las premisas de dos pruebas Lean usando distancia de Jaccard.

    STUB — no implementado aún. Requiere LeanDojo en WSL2.

    Args:
        lean_name_nuevo: nombre completo Lean de la declaración nueva.
        lean_name_existente: nombre completo Lean de la declaración en Mathlib.
        lean_project_dir: ruta al proyecto Lean con Mathlib compilado.
        umbral_theta: umbral para decidir si las pruebas son distantes.

    Returns:
        D3Result con activa=False (stub).
    """
    logger.warning(
        "D3.check_premise_distance es un stub — no implementado. "
        "Requiere LeanDojo en WSL2 para extraer premisas. "
        "Comparación solicitada: '%s' vs '%s'",
        lean_name_nuevo,
        lean_name_existente,
    )

    return D3Result(
        activa=False,
        premisas_candidato=[],
        premisas_nueva=[],
        jaccard=None,
        umbral_theta=umbral_theta,
        pruebas_distantes=None,
    )


# ---------------------------------------------------------------------------
# Placeholder para la implementación real (futuro)
# ---------------------------------------------------------------------------

def _extract_premises_lean(
    lean_name: str,
    lean_project_dir: str,
) -> List[str]:
    """Extrae las premisas de una declaración Lean usando LeanDojo.

    IMPLEMENTACIÓN FUTURA — requiere WSL2 con LeanDojo 4.20.0+:
      1. Activar entorno WSL2: wsl -d Ubuntu2204
      2. cd al lean_project/
      3. Ejecutar script de extracción via LeanDojo
      4. Devolver lista de nombres completos de premisas

    Returns:
        Lista de strings con nombres completos de premisas (e.g.
        ['Nat.add_comm', 'Nat.succ_eq_add_one', ...])
    """
    raise NotImplementedError(
        "Extracción de premisas con LeanDojo no implementada. "
        "Requiere WSL2 con LeanDojo 4.20.0+."
    )
