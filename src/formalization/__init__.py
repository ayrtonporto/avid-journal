"""
AViD Journal — Autoformalization module (model-agnostic).

Public API:
    formalize_paper(tex_path, ...)  → dict con resultados
    ModelProvider                   → interfaz abstracta de proveedor
    resolve_provider(name)          → factory de proveedores
"""

from .orchestrator import formalize_paper, topological_sort, lean_ident_for
from .providers import ModelProvider, FormalizationResult, resolve_provider

__all__ = [
    "formalize_paper",
    "topological_sort",
    "lean_ident_for",
    "ModelProvider",
    "FormalizationResult",
    "resolve_provider",
]
