"""
AViD Journal - External Result Lookup (stub v1)
================================================
Para bloques sin prueba (resultados externos citados por el paper),
intenta encontrarlos en Mathlib antes de declararlos como axioma.

V1 stub: devuelve siempre `not_found`, forzando la ruta de axioma.
La implementacion real llamara a `lean_leandex` / `lean_loogle` via MCP.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    """Resultado de buscar un enunciado externo en Mathlib."""

    found: bool
    mathlib_name: Optional[str] = None   # ej. "Nat.factorial_pos"
    import_line: Optional[str] = None    # ej. "import Mathlib.Data.Nat.Factorial.Basic"
    confidence: float = 0.0              # [0.0, 1.0], 1.0 = exact match

    @property
    def not_found(self) -> bool:
        return not self.found


def lookup(statement_latex: str, context: Optional[dict] = None) -> SearchResult:
    """Busca un enunciado informal (LaTeX) en Mathlib.

    V1: stub. Siempre devuelve `found=False`, lo que senala al orchestrator
    que debe declarar el bloque como `axiom`.

    Args:
        statement_latex: enunciado informal en LaTeX.
        context: dict opcional con metadatos (ej. tipo del bloque, titulo).

    Returns:
        SearchResult describiendo el match encontrado (o su ausencia).
    """
    # TODO(v2): invocar lean_leandex via MCP sobre un proyecto de referencia.
    # TODO(v3): si la descripcion del tipo es clara (ej. regex sobre content_latex
    #           detecta "is prime" / "divides"), intentar loogle con patron de tipo.
    _ = statement_latex, context
    return SearchResult(found=False)


def format_axiom(
    lean_name: str,
    lean_signature: str,
    source: str,
    title: Optional[str] = None,
) -> str:
    """Formatea un bloque como declaracion `axiom` con comentario de fuente.

    Args:
        lean_name:      identificador Lean (ej. "ext_stone_duality")
        lean_signature: firma del tipo (ej. "forall B : BooleanAlgebra, ...")
        source:         referencia bibliografica (ej. "Stone, 1936")
        title:          titulo opcional del bloque

    Returns:
        Codigo Lean listo para append a Paper.lean.
    """
    title_str = f" -- {title}" if title else ""
    return (
        f"-- source: [{source}]{title_str}\n"
        f"axiom {lean_name} : {lean_signature}\n"
    )


if __name__ == "__main__":
    r = lookup("Every Boolean algebra is isomorphic to a field of sets.")
    print(f"found={r.found}, not_found={r.not_found}")

    print(format_axiom(
        lean_name="ext_stone_duality",
        lean_signature="forall B : BooleanAlgebra, exists X : Type, Nonempty (B equiv FieldOfSets X)",
        source="Stone, 1936",
        title="Stone Representation Theorem",
    ))
