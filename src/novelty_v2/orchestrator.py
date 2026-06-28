"""Orquestador de la métrica de novedad v2.

Ejecuta el árbol de decisión D2 → D1 → D3 siguiendo la spec
(paper/metric_spec.md §6) y devuelve NoveltyVerdict con los 7 veredictos.

Árbol completo:
  1. D2 (trivialidad):
     Si trivial → NO_NOVEDOSO_trivial, FIN.
  2. D1 C_F (Mathlib via Leandex):
     Si match → evaluar D3:
       - D3 no disponible → MATCH_ENCONTRADO_PENDIENTE_D3
       - D3 disponible ∧ jaccard > θ → NOVEDAD_DEMOSTRACION
       - D3 disponible ∧ jaccard ≤ θ → NO_NOVEDOSO_redundante
  3. D1 C_I (Semantic Scholar + LLM judge), solo si C_F no dio match:
     - equivalent → CONOCIDO_LITERATURA
     - generalization / specialization → ZONA_GRIS
     - different / vacío → NOVEDAD_ENUNCIADO

D3 (distancia de premisas) está en desarrollo. Actualmente es un stub que
devuelve D3Result con activa=False. La implementación requiere LeanDojo
en WSL2 y se ejecuta manualmente (ver §D3 más abajo).

Uso:
  from src.novelty_v2.orchestrator import check_novelty

  result = check_novelty(
      block={"title": "...", "content_latex": "..."},
      lean_statement="Irrational (Real.sqrt 2)",
      lean_imports="import Mathlib.Tactic",
  )
  print(result.veredicto.value)  # e.g. NOVEDAD_ENUNCIADO
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from src.novelty_v2.dimensions.d1_existence import (
    check_d1,
    _check_cf,
    _run_ci_stage_a,
    _run_ci_stage_b,
    CI_SIMILARITY_THRESHOLD_A,
)
from src.novelty_v2.dimensions.d2_triviality import check_triviality, _run_tactic, LEAN_STARTUP_OVERHEAD_S
from src.novelty_v2.dimensions.d3_premises import check_premise_distance
from src.novelty_v2.types import (
    D1Result,
    D2Result,
    D3Result,
    NoveltyVerdict,
    Verdict,
)

logger = logging.getLogger(__name__)


def check_novelty(
    block: Dict[str, Any],
    lean_statement: str,
    lean_project_dir: Optional[str | Path] = None,
    lean_imports: str = "import Mathlib",
    use_cache: bool = True,
    ci_top_k: int = 3,
    ci_threshold: float = CI_SIMILARITY_THRESHOLD_A,
    d3_star_pairs: Optional[Dict[str, str]] = None,
) -> NoveltyVerdict:
    """Evalúa la novedad de un teorema usando el árbol D2 → D1 → D3.

    Args:
        block: dict con "title" y "content_latex" (enunciado informal).
        lean_statement: enunciado Lean 4 del teorema (para D2).
        lean_project_dir: ruta al lean_project/ con Mathlib compilado.
        lean_imports: imports para el archivo Lean de D2.
        use_cache: compartido con los módulos de src/novelty/.
        ci_top_k: candidatos Semantic Scholar que pasan a llm_judge.
        ci_threshold: umbral de similitud MiniLM para C_I etapa A.
        d3_star_pairs: pares de teoremas para evaluación D3 manual.
            Formato: {"lean_name_nuevo": "lean_name_existente", ...}
            Si se provee, D3 se ejecuta sobre estos pares en vez de
            sobre el match de C_F. Útil para evaluación offline.

    Returns:
        NoveltyVerdict con veredicto, razonamiento y resultados de las 3 dimensiones.
    """
    d2 = D2Result()
    d1 = D1Result()
    d3 = D3Result()

    # ── Paso 1: D2 (trivialidad) ────────────────────────────────────────────
    d2 = check_triviality(
        lean_statement,
        lean_project_dir=lean_project_dir,
        lean_imports=lean_imports,
    )

    if d2.trivial:
        return NoveltyVerdict(
            veredicto=Verdict.NO_NOVEDOSO_trivial,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=False,
            razonamiento=(
                f"D2: táctica '{d2.tactica}' cerró el enunciado "
                f"en {d2.tiempo_segundos:.1f}s. No requiere idea matemática."
            ),
            stage_detenido=2,
        )

    # ── Paso 2: D1 C_F (Mathlib/Leandex) ────────────────────────────────────
    d1 = _check_cf(block, use_cache)

    if d1.existe_en_C_F:
        # ── Paso 2a: D3 (distancia de premisas) ──────────────────────────
        lean_name_existente = (d1.match_C_F or {}).get("lean_name", "?")
        d3 = _run_d3_if_possible(
            lean_statement=lean_statement,
            lean_name_existente=lean_name_existente,
            d3_star_pairs=d3_star_pairs,
        )

        if d3.pruebas_distantes is True:
            return NoveltyVerdict(
                veredicto=Verdict.NOVEDAD_DEMOSTRACION,
                d1=d1,
                d2=d2,
                d3=d3,
                revision_humana=False,
                razonamiento=(
                    f"D1 C_F: match en Mathlib — '{lean_name_existente}'. "
                    f"D3: distancia Jaccard = {d3.jaccard:.2f} > "
                    f"umbral θ = {d3.umbral_theta} → pruebas estructuralmente "
                    f"distantes. Mismo enunciado, prueba nueva."
                ),
                stage_detenido=3,
            )

        if d3.pruebas_distantes is False:
            return NoveltyVerdict(
                veredicto=Verdict.NO_NOVEDOSO_redundante,
                d1=d1,
                d2=d2,
                d3=d3,
                revision_humana=False,
                razonamiento=(
                    f"D1 C_F: match en Mathlib — '{lean_name_existente}'. "
                    f"D3: distancia Jaccard = {d3.jaccard:.2f} ≤ "
                    f"umbral θ = {d3.umbral_theta} → misma prueba. "
                    f"Enunciado y demostración conocidos."
                ),
                stage_detenido=3,
            )

        # D3 no disponible → veredicto provisional
        sim = (d1.match_C_F or {}).get("similarity", 0.0)
        return NoveltyVerdict(
            veredicto=Verdict.MATCH_ENCONTRADO_PENDIENTE_D3,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=False,
            razonamiento=(
                f"D1 C_F: match en Mathlib — '{lean_name_existente}' "
                f"(sim={sim:.2f}). Enunciado conocido. "
                f"Novedad de prueba pendiente de D3 (análisis offline "
                f"con LeanDojo)."
            ),
            stage_detenido=1,
        )

    # ── Fallback C_F: exact? (si Leandex no encontró match) ─────────────
    # exact? busca en el entorno Lean cargado. Si encuentra un teorema
    # existente, lo tratamos como match en C_F. Esto captura teoremas que
    # Leandex podría no encontrar por diferencia de idioma o formato.
    if lean_project_dir and lean_statement:
        try:
            success, elapsed, output = _run_tactic(
                lean_statement,
                "exact?",
                lean_project_dir,
                budget_seconds=15,
                lean_imports=lean_imports,
            )
            if success and output:
                # Extraer el nombre del lema que exact? sugirió
                import re
                exact_match = re.search(r"Try this:\s*([^\s]+)", output)
                if not exact_match:
                    exact_match = re.search(r"exact\s+([^\s]+)", output)
                lean_name = exact_match.group(1) if exact_match else "exact?_match"
                d1.existe_en_C_F = True
                d1.match_C_F = {
                    "lean_name": lean_name,
                    "statement": f"exact? closed in {elapsed:.1f}s",
                    "similarity": 0.95,  # exact match, slightly below 1.0 to distinguish from Leandex
                    "url": "",
                }
                # Emitir MATCH_ENCONTRADO_PENDIENTE_D3 igual que si Leandex lo hubiera encontrado
                return NoveltyVerdict(
                    veredicto=Verdict.MATCH_ENCONTRADO_PENDIENTE_D3,
                    d1=d1,
                    d2=d2,
                    d3=d3,
                    revision_humana=False,
                    razonamiento=(
                        f"D1 C_F (exact?): '{lean_name}' cerró el enunciado "
                        f"en {elapsed:.1f}s. Enunciado conocido en Mathlib (vía exact?). "
                        f"Novedad de prueba pendiente de D3."
                    ),
                    stage_detenido=1,
                )
        except Exception as exc:
            logger.debug("exact? fallback failed: %s", exc)

    # ── Paso 3: D1 C_I (solo si C_F no dio match) ───────────────────────────
    ci_candidates = _run_ci_stage_a(block, use_cache, ci_top_k, ci_threshold)
    if ci_candidates:
        ci_result = _run_ci_stage_b(block, ci_candidates, use_cache)
        d1.existe_en_C_I = ci_result.existe_en_C_I
        d1.match_C_I = ci_result.match_C_I
        d1.llm_judge_verdict = ci_result.llm_judge_verdict
        if ci_result.traduccion_incierta:
            d1.traduccion_incierta = True

    llm_v = d1.llm_judge_verdict or "different"

    if llm_v in ("generalization", "specialization"):
        return NoveltyVerdict(
            veredicto=Verdict.ZONA_GRIS,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=True,
            razonamiento=(
                f"D1 C_I: juez LLM marcó '{llm_v}' con candidato "
                f"'{(d1.match_C_I or {}).get('title', '?')}'. "
                f"Tipos relacionados pero no iguales — revisión humana."
            ),
            stage_detenido=1,
        )

    if d1.existe_en_C_I:
        return NoveltyVerdict(
            veredicto=Verdict.CONOCIDO_LITERATURA,
            d1=d1,
            d2=d2,
            d3=d3,
            revision_humana=d1.traduccion_incierta,
            razonamiento=(
                f"D1 C_I: match en literatura informal — "
                f"'{(d1.match_C_I or {}).get('title', '?')}'. "
                f"Sin match en Mathlib. Formalización puede ser aporte "
                f"de ingeniería."
            ),
            stage_detenido=1,
        )

    # ── Sin match en C_F ni C_I → enunciado genuinamente nuevo ─────────────
    return NoveltyVerdict(
        veredicto=Verdict.NOVEDAD_ENUNCIADO,
        d1=d1,
        d2=d2,
        d3=d3,
        revision_humana=d1.traduccion_incierta,
        razonamiento=(
            "D1: sin match en C_F (Mathlib) ni en C_I (arXiv/SS). "
            "Enunciado genuinamente nuevo."
            + (" [traducción incierta — revisar]" if d1.traduccion_incierta else "")
        ),
        stage_detenido=1,
    )


# ---------------------------------------------------------------------------
# D3 — Distancia de premisas (stub + integración futura)
# ---------------------------------------------------------------------------

def _run_d3_if_possible(
    lean_statement: str,
    lean_name_existente: str,
    d3_star_pairs: Optional[Dict[str, str]] = None,
) -> D3Result:
    """Intenta ejecutar D3. Actualmente es un stub.

    D3 requiere:
      - LeanDojo 4.20.0+ instalado en WSL2
      - Mathlib cache funcional en WSL2
      - Extracción manual de premisas de la prueba existente en C_F
      - Calibración de umbral θ con pares T07/T08/T09

    Si d3_star_pairs contiene un mapeo del par actual, se usa ese
    resultado precomputado.
    """
    logger.info(
        "D3 stub: match en C_F='%s'. D3 requiere LeanDojo en WSL2 "
        "(no automatizado aún).",
        lean_name_existente,
    )

    # Si hay pares precomputados (evaluación offline), usarlos
    if d3_star_pairs and lean_name_existente in d3_star_pairs:
        logger.info(
            "D3: usando par precomputado para '%s'", lean_name_existente
        )
        # TODO: cargar resultados desde archivo de calibración
        # Por ahora devolvemos D3Result con activa=False como stub

    return D3Result(activa=False)


# ---------------------------------------------------------------------------
# Demo mínima
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

    def _demo(label: str, block: dict, lean_stmt: str, imports: str = "import Mathlib.Tactic"):
        print(f"\n{'='*64}")
        print(f"Demo: {label}")
        print("=" * 64)
        v = check_novelty(
            block=block,
            lean_statement=lean_stmt,
            lean_imports=imports,
        )
        print(f"Veredicto:       {v.veredicto.value}")
        print(f"Stage detenido:  {v.stage_detenido}")
        print(f"Revisión humana: {v.revision_humana}")
        print(f"Razonamiento:    {v.razonamiento}")
        print(f"D2 trivial:      {v.d2.trivial}, táctica: {v.d2.tactica}")
        print(f"D1 C_F match:    {v.d1.existe_en_C_F} | C_I match: {v.d1.existe_en_C_I}")
        if v.d1.match_C_F:
            m = v.d1.match_C_F
            print(f"  C_F: {m.get('lean_name')} (sim={m.get('similarity', 0):.2f})")
        if v.d1.match_C_I:
            m = v.d1.match_C_I
            print(f"  C_I: {m.get('title', '?')} (sim={m.get('similarity', 0):.2f})")
        return v

    # Caso 1: trivial
    _demo(
        "T15 — trivial: (2:Nat)+2=4",
        block={"title": "2 + 2 = 4", "content_latex": "2 + 2 = 4"},
        lean_stmt="(2 : Nat) + 2 = 4",
        imports="import Mathlib.Tactic",
    )

    # Caso 2: clásico en Mathlib
    _IMP_REAL = (
        "import Mathlib.Tactic\n"
        "import Mathlib.Analysis.SpecialFunctions.Pow.Real\n"
        "import Mathlib.Data.Real.Irrational"
    )
    _demo(
        "T01 — en Mathlib: Irrational (sqrt 2)",
        block={
            "title": "Irrationality of sqrt(2)",
            "content_latex": r"$\sqrt{2}$ is irrational",
        },
        lean_stmt="Irrational (Real.sqrt 2)",
        imports=_IMP_REAL,
    )

    # Caso 3: potencial novedad
    _IMP_PARITY = (
        "import Mathlib.Tactic\n"
        "import Mathlib.Data.Int.Parity\n"
        "import Mathlib.Algebra.BigOperators.Group.Finset"
    )
    _demo(
        "T26 — suma de n pares es par",
        block={
            "title": "Sum of n even integers is even",
            "content_latex": r"If $f(i)$ is even for all $i$, then $\sum_{i} f(i)$ is even",
        },
        lean_stmt="∀ (n : ℕ) (f : Fin n → ℤ), (∀ i, Even (f i)) → Even (∑ i, f i)",
        imports=_IMP_PARITY,
    )
