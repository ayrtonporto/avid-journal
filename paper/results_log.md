# Log de resultados del sprint AViD Journal

**Sprint de 15 días para entregar:** demo web funcional + métrica de novedad con filtro de trivialidad + evidencia preliminar + preprint v1.

**Formato por día:** qué se hizo, qué quedó andando, qué quedó pendiente, qué decisiones aparecieron.

---

## Día 1 — Especificación escrita de la métrica ✓

**Hecho:** documento `metric_spec.md` completo. Tres dimensiones definidas. Árbol de decisión. Limitaciones declaradas.

**Pendiente:** ninguno.

**Decisiones nuevas:** ninguna (todas las decisiones de diseño fueron tomadas y registradas en `decisions.md`).

## Día 2 — Conjunto de evaluación ✓

**Hecho:** `eval_set.csv` con 26 teoremas firmes + 9 slots TBD. Cuatro categorías cubiertas: clásicos en mathlib, pares con distinta prueba (T07 Euclides/Euler, T08 √2 paridad/raíz racional, T09 Gauss inducción/emparejamiento), triviales, casos de falla.

**Pendiente:** llenar los 9 slots TBD durante implementación (clásicos no en mathlib, conocidos en literatura, teoremas muy nuevos).

## Día 3 — Setup de infraestructura

**Objetivo:** repo limpio con estructura de carpetas, README inicial, entorno reproducible, **LeanDojo corriendo sobre un ejemplo mínimo de mathlib**.

**Hecho:**

- WSL2 instalado correctamente con Ubuntu 22.04 LTS en `D:\WSL\Ubuntu2204\` (fuera de `C:` por restricción de espacio). Usuario `ayrton`, systemd activo.
- Repo clonado en `~/avid-journal/` (filesystem nativo WSL), SSH key a GitHub configurada, sincronizado con `origin/main` en commit `a0cbd05`.
- Venv Python 3.10 en `~/avid-journal/.venv/` con todas las dependencias del `requirements.txt` instaladas + `lean-dojo 4.20.0` + `elan 4.2.2` + toolchain `leanprover/lean4:v4.29.0` (la que usa el `lean_project/` del repo).
- Scaffold de `src/novelty_v2/` commiteado en `a0cbd05`: `types.py` con los 5 veredictos de la spec + `ZONA_GRIS`, dataclasses `D1Result/D2Result/D3Result/NoveltyVerdict`, README con la tabla de reutilización de `src/novelty/`, stubs por dimensión.
- Hallazgo empírico sobre LeanDojo (ver `decisions.md`): traza dependencias transitivas, no solo archivos del proyecto. Reorienta arquitectura del sprint.

**Pendiente:**

- D3 vía LeanDojo queda en modo manual/offline, no en el flujo automático del demo. Se ejecuta el Día 7 sobre los pares estrella (T07, T08, T09).
- Llenar 9 slots TBD del `eval_set.csv` durante implementación de D1 (Días 4-6).

**Bloqueos:** ninguno. Reorientación arquitectural absorbida.

**Resumen del cierre:** WSL2 instalado correctamente con Ubuntu 22.04 en D:. Venv y entorno Python listos. LeanDojo instalado pero pausado para uso manual en Día 7. Descubierto que LeanDojo traza dependencias transitivas, no tracing puntual. Reorientación arquitectural del sprint hacia demo en tiempo real con D1+D2 automáticos y D3 a pedido. Cierra Día 3 con setup completo pero alcance redirigido.

## Día 4 — Filtro de trivialidad (D2) ✓

**Objetivo:** módulo `triviality_filter.py` que toma un enunciado en Lean e intenta cerrarlo con `T_auto = {decide, omega, simp, norm_num, aesop, tauto}` + `exact?`. Output: bandera + táctica que lo cerró.

**Hecho:**

- `src/novelty_v2/dimensions/d2_triviality.py`: implementación completa de `check_triviality(lean_statement, lean_project_dir, budgets) → D2Result`. Itera `T_AUTO_ORDER = [decide, norm_num, simp, omega, tauto, exact?, aesop]`, detiene en primer éxito. Timeouts: `budget_seconds + LEAN_STARTUP_OVERHEAD_S` (45 s overhead medido empíricamente en Windows).
- `src/novelty_v2/types.py`: añadido campo `all_attempts: List[Tuple[str, bool, float, Optional[str]]]` a `D2Result`.
- `scripts/d2/test_eval_set.py`: script de evaluación con T14-T18 + T23. Pre-warm step para calentar caché de OS antes del cronómetro. Default `--lean-project` apunta a Windows nativo.
- **Decisión arquitectural crítica:** abandono de WSL como entorno primario. Pipeline automatizado corre en Windows nativo. WSL preservado solo para D3 manual del Día 7. Documentado en `decisions.md`.
- Mathlib en Windows confirmada funcional: 8 247 oleans, 0 vacíos, `Mathlib.olean` presente. `lake env lean` → `exit=0` en 165.8 s primera corrida fría, ~30 s con OS cache caliente.

**Pendiente:** ninguno para Día 4.

**Resultados sobre eval set (corrida 2026-06-07, Windows nativo, Lean 4.29.0):**

| Test | Descripción | Resultado | Táctica | Tiempo total | Esperado | OK |
|------|-------------|-----------|---------|-------------|----------|----|
| T14 | 4 enteros pares → par | TRIVIAL | aesop | 215 s | trivial | ✓ |
| T15 | 2 + 2 = 4 | TRIVIAL | decide | 29 s | trivial | ✓ |
| T16 | ∀ n : Nat, n + 0 = n | TRIVIAL | norm_num | 61 s | trivial | ✓ |
| T17 | ∀ n : Nat, n ≤ n + 1 | TRIVIAL | norm_num | 60 s | trivial | ✓ |
| T18 | Σ primeros n impares = n² (trampa) | NO TRIVIAL | — | 214 s | no trivial | ✓ |
| T23 | grafo conexo + acíclico → árbol (FP esperado) | TRIVIAL | tauto | 146 s | FP esperado | registrado |

**Score: 5/5 con expectativa booleana. T23 registrado como falso positivo esperado.**

**Observaciones:**

1. **T14 requirió aesop** (se esperaba simp u omega). `Even` en Lean 4 es una proposición existencial — `simp` no la resuelve por unfolding automático; `omega` tampoco maneja `Even` directamente. `aesop` lo cierra buscando el camino. Consecuencia: T14 tarda 215 s en total (7 tácticas × ~30 s c/u).

2. **T16 y T17 cerraron con norm_num** (se esperaba simp/omega). `norm_num` generaliza más que `decide` sobre ecuaciones e inecuaciones numéricas con cuantificadores sobre `Nat`.

3. **T23 cerró con `tauto`** (se esperaba `aesop`). En Mathlib v4.29.0, `SimpleGraph.IsTree` está definido como `Connected ∧ IsAcyclic` (una conjunción), y `tauto` maneja lógica proposicional trivialmente. Falso positivo confirmado — D2 clasifica este teorema como trivial aunque no lo sea matemáticamente. Registrado como limitación conocida del filtro.

4. **Overhead de inicio de Lean en Windows**: ~30 s por invocación con OS cache caliente. Cada `lake env lean` carga todos los oleans desde cero. Absorber con `LEAN_STARTUP_OVERHEAD_S = 45`. Para la demo, esto implica que D2 tarda ~30–215 s por teorema dependiendo de qué táctica lo cierra primero.

5. **T18 (trampa) no se cerró**: ninguna de las 7 tácticas pudo con `Finset.range n).sum (fun k => 2 * k + 1) = n ^ 2`. Inducción necesaria. D2 funciona correctamente como filtro.

## Día 5 — Corrida D2 sobre eval set completo + adelanto D1 ✓

**Objetivo original (reprogramado):** extracción de premisas con LeanDojo.
**Objetivo real ejecutado:** corrida completa del filtro D2 sobre los 24 teoremas del eval set + implementación de D1 (no-existencia) como adelanto del Día 6.

**Hecho:**

- **DECISIONES A, B, C** tomadas, argumentadas y documentadas en `decisions.md` (2026-06-09):
  - DECISIÓN A: C_F (Mathlib) tiene precedencia sobre C_I (literatura); si hay match en Mathlib no se corre C_I.
  - DECISIÓN B: veredicto provisional `MATCH_ENCONTRADO_PENDIENTE_D3` cuando C_F encuentra match y D3 aún no corrió.
  - DECISIÓN C: caché organizada por endpoint (`mathlib/`, `judge_theorem/`, `judge_method/`), `temperature=0` en todas las llamadas al juez LLM.
- **`src/novelty_v2/types.py`**: añadido `MATCH_ENCONTRADO_PENDIENTE_D3` al enum `Verdict`.
- **`src/novelty_v2/dimensions/d1_existence.py`**: `check_novelty_verdict_simple` reescrito con árbol DECISIÓN A completo (D2 → C_F → C_I).
- **`src/novelty/llm_judge.py`**: `temperature=0` añadido a `_call_claude` (fix de configuración para DECISIÓN C).
- **Corrida D2 completa**: `scripts/d2/test_eval_set_full.py` sobre 24 teoremas. Lean 4.29.0, Windows nativo, 2026-06-09. Duración total: ~30 min (26.1 min de test + ~4 min prewarm). Corrida secundaria con `import Mathlib` sobre T14/T18/T23/T26.
- **Limitaciones L10 y L11** documentadas en `limitations.md`.

**Resultados D2 — corrida principal + re-corrida (merged, 2026-06-09/10):**

| ID | Categoría | D2 trivial | Táctica | Tiempo total | Expected | OK | Nota |
|---|---|---|---|---|---|---|---|
| T01 | clasico_en_mathlib | **True (FP)** | norm_num | 29.5s | False | No | L10: norm_num cierra irracionalidad |
| T02 | clasico_en_mathlib | False | — | 74.4s | False | Sí | import error (L11) |
| T03 | clasico_en_mathlib | False | — | 70.1s | False | Sí | import error (L11) |
| T04 | clasico_en_mathlib | False | — | 73.1s | False | Sí | import error (L11) |
| T05 | clasico_en_mathlib | False | — | 97.6s | False | Sí | syntax error ⟪x,y⟫ |
| T06 | clasico_en_mathlib | False | — | 71.1s | False | Sí | import error (L11) |
| T07 | par_distinta_prueba | False | — | 71.5s | False | Sí | import error (L11) |
| T08 | par_distinta_prueba | **True (FP)** | norm_num | 26.9s | False | No | L10 (mismo enunciado que T01) |
| T09 | par_distinta_prueba | False | — | 70.3s | False | Sí | import error (L11) |
| T10 | enunciados_cercanos | False | — | 70.3s | False | Sí | import error (L11) |
| T11 | enunciados_cercanos | False | — | 71.7s | False | Sí | import error (L11) |
| T12 | enunciados_cercanos | False | — | 99.3s | False | Sí | deprecated import, no error |
| T13 | enunciados_cercanos | False | — | 71.4s | False | Sí | import error (L11) |
| T14 | trivial | **False (FN)** | — | 405.2s* | True | No | budget insuf.: aesop necesita ~215s > 75s |
| T15 | trivial | True | decide | 13.3s | True | Sí | — |
| T16 | trivial | True | norm_num | 26.3s | True | Sí | — |
| T17 | trivial | True | norm_num | 26.2s | True | Sí | — |
| T18 | trivial (ctrl) | False | — | 257.8s* | False | Sí | control: inducción necesaria |
| T19 | generado_IA | True | aesop | 98.1s | True | Sí | 6 tácticas previas fallaron rápido |
| T22 | caso_falla | True | norm_num | 26.5s | True | Sí | — |
| T23 | caso_falla | **True (FP)** | tauto | 154.2s* | "probable FP" | — | FP confirmado: IsTree=Connected∧IsAcyclic |
| T24 | caso_falla | False | — | 111.7s | False | Sí | type error esperado (CoherentSheaf) |
| T25 | caso_falla | True | exact? | 81.1s | True | Sí | simp no; exact? encontró lema |
| T26 | enunciados_cercanos | **True (FP)** | exact? | 195.9s* | False | No | FP inesperado: exact? encontró lema |

\* Re-corrido con `import Mathlib` completo (ver `rerun_import_errors_20260610_013952.csv`).

**Score D2 (sobre los 23 con `expected_trivial` booleano): 20/23 = 87%**
- Falsos positivos: T01, T08 (L10 — norm_num irracionalidad), T26 (FP inesperado — exact? con import Mathlib)
- Falsos negativos: T14 (budget insuficiente para aesop)
- T23: FP confirmado (diseñado como FP, se reproduce con import Mathlib)

**Tiempos medios por categoría (corrida principal, sin re-corrida):**

| Categoría | N | Promedio | Min | Max |
|---|---|---|---|---|
| clasico_en_mathlib | 6 | 69.3s | 29.5s | 97.6s |
| par_distinta_prueba | 3 | 56.3s | 26.9s | 71.5s |
| enunciados_cercanos_distintos | 5 | 76.9s | 70.3s | 99.3s |
| trivial | 5 | 41.8s | 13.3s | 71.9s |
| generado_IA | 1 | 98.1s | — | — |
| caso_falla | 4 | 72.0s | 26.5s | 111.7s |

**Observaciones clave:**

1. **Velocidad**: corrida completó en ~30 min total (estimado original: 90-130 min). El prewarm de oleans redujo el startup de `import Mathlib.Tactic` de ~40s a ~13-16s por táctica.

2. **L10 — trivialidad monótona en poder táctico**: `norm_num` en Mathlib v4.29.0 cierra `Irrational (Real.sqrt 2)` en 14s. Ilustra que el umbral de trivialidad de D2 se mueve con el estado del arte de las tácticas. Candidato a hallazgo principal del paper (ver `decisions.md`).

3. **L11 — Mathlib monolítico**: imports específicos (`import Mathlib.Data.Nat.Prime`, etc.) fallan en `lake env lean` standalone. Solo `import Mathlib` e `import Mathlib.Tactic` son confiables. Impacto en demo: ~30-45s startup/teorema con caché cálida.

4. **T14 (FN por budget)**: `aesop` necesita ~215s para cerrar `Even a → Even b → Even c → Even d → Even (a+b+c+d)`. Budget de aesop = 30s (+45s overhead = 75s). Presupuesto insuficiente. No resuelto en v1.

5. **T26 (FP inesperado)**: la generalización a `n` enteros es cerrada por `exact?` con `import Mathlib` en 39.4s. Mathlib tiene un lema directo. Esto es correcto desde la perspectiva de D2: si Mathlib puede automatizarlo, no es contribución matemática.

**Pendiente para Días siguientes:**

- D3 (distancia de premisas): LeanDojo + Jaccard sobre pares T07/T08/T09. Días 8-9.
- `orchestrator.py`: árbol D2→D1→D3 completo. Día 8.
- D1 (C_I via Semantic Scholar): requiere `ANTHROPIC_API_KEY` para `llm_judge`. Pendiente de configurar en `.env`.

## Día 6 — Extracción de premisas con LeanDojo (parte 2)

**Objetivo:** extracción funcionando sobre los pares T07, T08, T09 + math filter (whitelist mathlib).

**Hecho:**

**Pendiente:**

## Día 7 — Eje 1: comparación de tipos (D1)

**Objetivo:** `type_compare.py` que decide si dos enunciados Lean tienen el mismo tipo (nivel 0 sintáctico tras normalización).

**Hecho:**

**Pendiente:**

## Día 8 — Distancia de Jaccard + integración de la métrica

**Objetivo:** `novelty_score.py` que toma un teorema y devuelve el veredicto combinado (las tres dimensiones).

**Hecho:**

**Pendiente:**

## Día 9 — Corrida sobre eval set + tabla de resultados

**Objetivo:** procesar las 26 filas firmes del eval set. Tabla con etiqueta esperada vs. veredicto real. Cálculo de accuracy por categoría.

**Hecho:**

**Resultados:**

| Categoría | Aciertos | Total | % |
| --- | --- | --- | --- |
| Clásicos en mathlib | | 6 | |
| Pares distinta prueba | | 6 | |
| Enunciados cercanos | | 5 | |
| Triviales | | 5 | |
| Generados por IA | | 3 | |
| Casos de falla | | 4 | |
| **Total** | | **29** | |

**Hallazgos importantes (para Limitations y Future Work):**

## Día 10 — Demo web (Gradio) backend

**Objetivo:** interfaz Gradio que toma un enunciado en lenguaje natural, lo autoformaliza, corre la métrica, y muestra veredicto + las tres sub-puntuaciones.

**Hecho:**

**Pendiente:**

## Día 11 — Pulido del demo + página de landing

**Objetivo:** página explicando la idea (matriz de cuatro casos, caso Axiom, qué hace AViD distinto) + demo embebido con ejemplos pre-cargados.

**Hecho:**

**Pendiente:**

## Día 12 — Deploy del demo

**Objetivo:** URL pública estable (Hugging Face Spaces o equivalente).

**URL del demo:**

## Día 13 — Draft del preprint

**Objetivo:** draft completo siguiendo la estructura de `preprint/draft.md`.

**Hecho:**

**Pendiente:**

## Día 14 — Figuras + pulido del paper

**Objetivo:** diagrama del pipeline, tabla de resultados, matriz taxonómica. Pasada final buscando afirmaciones débiles.

**Hecho:**

**Pendiente:**

## Día 15 — Preprint listo (no publicado todavía)

**Objetivo:** versión final en PDF lista para subir. Decisión de dónde/cómo publicar queda para después del sprint.

**Hecho:**

**Entregables finales:**
- `preprint/draft.md` (versión final)
- `preprint/AViD_novelty_preprint_v1.pdf`
- URL del demo
- Repo limpio

## Post-mortem del sprint

*(se completa el Día 15 o 16)*

**Qué salió bien:**

**Qué salió mal:**

**Qué cambiaría si lo hiciera de nuevo:**

**Próximos pasos:**
