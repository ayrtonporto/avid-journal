"""D3 — Distancia estructural de pruebas.

Compara las premisas de dos pruebas Lean usando distancia de Jaccard.
Única implementación canónica; todo el cómputo de Jaccard pasa por aquí.

Pipeline interno (orden fijo e inamovible):
  1. Extraer premisas (recibe listas de dicts PremiseTrace).
  2. Deduplicar por identidad canónica (defPath, defPos).
  3. FILTRO 1: eliminar premisas de infraestructura (namespace blacklist).
  4. FILTRO 2: eliminar premisas del enunciado (por rango de líneas).
  5. Calcular Jaccard sobre lo que queda.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from src.novelty.types import D3Result

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical identity
# ---------------------------------------------------------------------------

def _canonical_id(premise: dict) -> str:
    """Identidad canónica de una premisa: fullName.

    Usamos el nombre Lean completo en vez de (defPath, defPos) para
    que premisas idénticas usadas en distintos archivos (ej. custom
    PaperEven.lean vs Mathlib Even.lean) sean consideradas la misma
    cuando comparten el mismo nombre lógico.
    """
    return premise.get("fullName", "")


def _deduplicate(premises: List[dict]) -> List[dict]:
    """Deduplica premisas por identidad canónica (fullName).

    Mantiene la primera ocurrencia de cada premisa.
    """
    seen: Set[str] = set()
    result: List[dict] = []
    for p in premises:
        cid = _canonical_id(p)
        if cid not in seen:
            seen.add(cid)
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# Filter 1 — Namespace blacklist
# ---------------------------------------------------------------------------

def _load_blacklist(config_path: Optional[str] = None) -> List[str]:
    """Carga la lista negra de prefijos de namespace desde archivo YAML.

    Si no se provee ruta, busca en config/d3_filter_blacklist.yaml
    relativo a la raíz del repo.
    """
    if config_path is None:
        # Default: config/ relative to repo root
        repo_root = Path(__file__).resolve().parents[3]
        config_path = str(repo_root / "src" / "novelty" / "d3_filter_blacklist.yaml")

    path = Path(config_path)
    if not path.exists():
        logger.warning("D3 filter config not found at %s; using hardcoded defaults", path)
        return ["Init.", "Lean."]

    with open(path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    prefixes = config.get("blacklist_prefixes", [])
    if not prefixes:
        logger.warning("D3 filter config at %s has empty blacklist_prefixes", path)
        return ["Init.", "Lean."]

    return prefixes


def _filter1_blacklist(
    premises: List[dict],
    blacklist_prefixes: List[str],
) -> List[dict]:
    """Elimina premisas cuyo modName empieza con alguno de los prefijos.

    Matching por prefijo EXACTO: "Init." matchea "Init.Prelude" pero NO "InitPrelude".
    """
    result = []
    for p in premises:
        mod = p.get("modName", "")
        if any(mod.startswith(prefix) for prefix in blacklist_prefixes):
            continue
        result.append(p)
    return result


# ---------------------------------------------------------------------------
# Filter 2 — Statement premises
# ---------------------------------------------------------------------------

def _filter2_statement(
    premises: List[dict],
    statement_line_range: Optional[Tuple[int, int]] = None,
) -> List[dict]:
    """Elimina premisas cuyo pos.line cae dentro del rango del enunciado.

    Args:
        premises: lista de premisas (cada una con campo 'pos' opcional).
        statement_line_range: (start_line, end_line) inclusivo del enunciado.
            Si es None, no se filtra nada.

    Returns:
        Premisas que NO están en el enunciado (i.e., las de la prueba).
    """
    if statement_line_range is None:
        return premises

    start, end = statement_line_range
    result = []
    for p in premises:
        pos = p.get("pos")
        if pos is not None and start <= pos.get("line", 0) <= end:
            continue  # En el enunciado → eliminar
        result.append(p)
    return result


# ---------------------------------------------------------------------------
# Jaccard computation
# ---------------------------------------------------------------------------

def _compute_jaccard_distance(
    premises_a: List[dict],
    premises_b: List[dict],
) -> Tuple[Optional[float], int, int, Set[str], Set[str], List[str]]:
    """Calcula la distancia de Jaccard entre dos conjuntos de premisas.

    Args:
        premises_a: premisas de la prueba A (ya deduplicadas y filtradas).
        premises_b: premisas de la prueba B (ya deduplicadas y filtradas).

    Returns:
        Tuple de (distancia, intersection_size, union_size, set_a_ids, set_b_ids, flags).
        distancia es None si ambos conjuntos están vacíos (no se divide por cero).
    """
    ids_a = {_canonical_id(p) for p in premises_a}
    ids_b = {_canonical_id(p) for p in premises_b}

    intersection = ids_a & ids_b
    union = ids_a | ids_b

    intersection_size = len(intersection)
    union_size = len(union)

    flags: List[str] = []

    # Spec: "si uno o ambos conjuntos quedan VACÍOS después de los filtros,
    # la función NO divide por cero. Devuelve distancia None y un flag explicativo."
    if union_size == 0:
        # Ambos vacíos → división por cero
        flags.append("empty_after_filters")
        return None, 0, 0, ids_a, ids_b, flags

    if len(ids_a) == 0:
        flags.append("empty_a_after_filters")
        return None, 0, union_size, ids_a, ids_b, flags

    if len(ids_b) == 0:
        flags.append("empty_b_after_filters")
        return None, intersection_size, union_size, ids_a, ids_b, flags

    jaccard_similarity = intersection_size / union_size
    distancia = 1.0 - jaccard_similarity
    return distancia, intersection_size, union_size, ids_a, ids_b, flags


# ---------------------------------------------------------------------------
# Public API — compute_d3
# ---------------------------------------------------------------------------

def compute_d3(
    premises_a: List[dict],
    premises_b: List[dict],
    *,
    statement_lines_a: Optional[Tuple[int, int]] = None,
    statement_lines_b: Optional[Tuple[int, int]] = None,
    blacklist_config_path: Optional[str] = None,
) -> D3Result:
    """ÚNICO punto de cómputo de distancia de Jaccard en el repo.

    Orden fijo e inamovible:
      1. Deduplicar por identidad canónica (fullName).
      2. FILTRO 1: eliminar infraestructura (namespace blacklist).
      3. FILTRO 2: eliminar premisas del enunciado.
      4. Calcular Jaccard sobre lo que queda.

    Args:
        premises_a: lista de dicts PremiseTrace para la prueba A.
        premises_b: lista de dicts PremiseTrace para la prueba B.
        statement_lines_a: (start, end) del enunciado de A. None = sin filtro.
        statement_lines_b: (start, end) del enunciado de B. None = sin filtro.
        blacklist_config_path: ruta al YAML de filtro 1. None = default.

    Returns:
        D3Result con distancia, intersection_size, union_size, premises after
        filters, y flags. Si uno o ambos conjuntos quedan vacíos después de
        filtros, distancia es None y hay un flag explicativo (nunca excepción).
    """
    # ── Paso 1: Deduplicación ──────────────────────────────────────────
    dedup_a = _deduplicate(premises_a)
    dedup_b = _deduplicate(premises_b)

    # ── Paso 2: Filtro 1 — blacklist de infraestructura ─────────────────
    blacklist = _load_blacklist(blacklist_config_path)
    after_f1_a = _filter1_blacklist(dedup_a, blacklist)
    after_f1_b = _filter1_blacklist(dedup_b, blacklist)

    # ── Paso 3: Filtro 2 — premisas del enunciado ──────────────────────
    after_f2_a = _filter2_statement(after_f1_a, statement_lines_a)
    after_f2_b = _filter2_statement(after_f1_b, statement_lines_b)

    # ── Paso 4: Jaccard ─────────────────────────────────────────────────
    distancia, inter_size, union_size, ids_a, ids_b, flags = _compute_jaccard_distance(
        after_f2_a, after_f2_b
    )

    return D3Result(
        activa=True,
        jaccard=distancia,
        intersection_size=inter_size,
        union_size=union_size,
        premises_a_after_filters=sorted(ids_a),
        premises_b_after_filters=sorted(ids_b),
        flags=flags,
        pruebas_distantes=(
            None if distancia is None else distancia > 0.5
        ),
    )


# ---------------------------------------------------------------------------
# Extraction helper — read premises from ExtractData JSON output
# ---------------------------------------------------------------------------

def load_premises_from_ast(
    ast_json_path: str | Path,
    theorem_line_start: int,
    theorem_line_end: int,
) -> List[dict]:
    """Carga las premisas de un teorema específico desde un archivo ast.json.

    Args:
        ast_json_path: ruta al archivo ast.json producido por ExtractData.
        theorem_line_start: primera línea del teorema (inclusivo).
        theorem_line_end: última línea del teorema (inclusivo).

    Returns:
        Lista de dicts PremiseTrace cuyas posiciones caen dentro del rango.
    """
    path = Path(ast_json_path)
    if not path.exists():
        raise FileNotFoundError(f"AST JSON not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    all_premises = data.get("premises", [])
    result = []
    for p in all_premises:
        pos = p.get("pos")
        if pos is not None:
            line = pos.get("line", 0)
            if theorem_line_start <= line <= theorem_line_end:
                result.append(p)

    return result


def load_tactic_spans_from_ast(
    ast_json_path: str | Path,
) -> List[dict]:
    """Carga los spans de tácticas desde un archivo ast.json.

    Returns:
        Lista de dicts TacticTrace con pos/endPos en byteIdx.
    """
    path = Path(ast_json_path)
    if not path.exists():
        raise FileNotFoundError(f"AST JSON not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    return data.get("tactics", [])



