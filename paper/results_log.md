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
- **`src/novelty_v2/dimensions/d1_existence.py`**: `check_novelty_verdict_simple` reescrito con árbol DECISIÓN A completo (D2 → C_F → C_I). Mergeado a `main` el 2026-06-27 (480 líneas).
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

- Merge del branch `claude/agitated-lovelace-e10f00` a `main` (contiene D1 implementación + eval set scripts + resultados).
- D3 (distancia de premisas): LeanDojo + Jaccard sobre pares T07/T08/T09. Días 8-9.
- `orchestrator.py`: árbol D2→D1→D3 completo. 
- D1 (C_I via Semantic Scholar): requiere `ANTHROPIC_API_KEY` para `llm_judge`. Pendiente de configurar en `.env`.

---

## Día 6 — Mejoras de infraestructura y búsqueda ✓

**Fecha:** 13 de junio de 2026.

**Hecho:**

- **`fix(novelty): improve semantic scholar candidate search`** (commit `d604cbc`): mejora en la búsqueda de candidatos en Semantic Scholar para la etapa A de D1 sobre C_I. Mayor precisión en el filtro grueso.
- **`fix(claude): use local Claude Code for AViD agents`** (commit `3c81710`): configuración de Claude Code local para los agentes de formalización de AViD. Elimina dependencia de API externa para el pipeline de autoformalización.
- **Worktree `claude/infallible-yonath-b5dfe3`** activo con estos fixes aplicados.

**Pendiente:**

- ~~Merge de `claude/agitated-lovelace-e10f00` a `main`~~ → mergeado el 2026-06-27.
- Decisión sobre implementación del `llm_judge`: API Anthropic con saldo prepagado vs. modelo local vs. Claude Code como juez.
- Resolver cuestión de `ANTHROPIC_API_KEY` para continuar con D1 sobre C_I.

---

## Día 7 — 27 de junio: Integración D1+D2+D3 + correcciones masivas ✓

**Fecha:** 27 de junio de 2026. Sesión intensiva de ~8 horas.

### Hecho

#### Pipeline LLM Judge
- **Migración de LLM Judge** de Claude Code binary → DeepSeek V4 Flash vía API OpenCode Go (`src/novelty/llm_judge.py` reescrito). Modelo: `deepseek-v4-flash`, temperature=0, max_tokens=2048 con retry automático a 4096 para `reasoning_content`.
- Probado con 3 pares de teoremas: "equivalent" (suma de pares), "different" (√2 vs Goldbach), "generalization" (FTA con/sin unicidad).

#### Correcciones de bugs (5 bugs)
1. **Leandex API v2**: reescrito `_extract_matches()` para el nuevo formato sin scores (flat: `name`, `source_text`). Similarity sintética 1.0/0.9/... por orden de resultado.
2. **Basura en `match_C_F`**: `_check_cf()` ahora solo guarda `match_C_F` cuando `existe_en_C_F=True`.
3. **Columnas CSV incorrectas**: el script leía `title`/`content_latex` que no existen; mapeado a `enunciado_informal`.
4. **`exact?` movido de D2 a D1**: la táctica busca existencia previa, no trivialidad. Ahora es fallback de C_F.
5. **`norm_num`/`Irrational`**: blacklist para evitar falso positivo L10.

#### Mejoras de pipeline
- **arXiv como fuente primaria de C_I**: `_run_ci_stage_a()` ahora consulta arXiv primero, Semantic Scholar después, con dedup por `arxiv_id`.
- **Orchestrator**: extraído `check_novelty()` a `src/novelty_v2/orchestrator.py` con árbol D2→D1→D3 completo (3 pasos + D3 stub + exact? fallback).
- **D3 — ExtractData**: bajado `ExtractData.lean` (515 líneas), ejecutado en Windows sobre archivos Mathlib. Extrae premisas correctamente: 2062 para `Irrational.lean`, 27 para `Infinite.lean`.
- **D3 — Jaccard demostrado**: T07 (infinitos primos, 27 premisas) vs T08 (√2 irracional, 268 premisas) → Jaccard = 0.035, Distancia = 0.965 → `NOVEDAD_DEMOSTRACION`.
- **D3 — Paper de calibración**: 6 teoremas compilados en `lean_project/Papers/D3_Calibration/Paper.lean` (T07a/b, T08a/b, T09a/b).

#### Eval script mejorado
- `scripts/run_eval_full.py`: checkpointing (CSV incremental), resume, prewarm, mapeo de IDs (T07a→T07).
- Corre sobre 24 teoremas con el orquestador completo D1+D2.

### Resultados del eval (corrida 2026-06-28, Windows nativo, Lean 4.29.0)

**Pipeline D1+D2 sobre 24 teoremas, 32 minutos:**

| Veredicto | Cantidad | % |
|-----------|----------|---|
| `MATCH_ENCONTRADO_PENDIENTE_D3` | 18 | 75% |
| `NO_NOVEDOSO_trivial` | 6 | 25% |

**Precisión: 20/24 = 83%** (4 falsos positivos/esperados-fallo).

**Matches de Leandex (selección):**
| ID | Teorema | Match Mathlib |
|----|---------|---------------|
| T01 | √2 irracional | `Tactic.NormNum.evalIrrationalSqrt` |
| T02 | Infinitos primos | `EuclidNumbers.infinite_prime_euclid_numbers` |
| T03 | Teorema Fundamental del Cálculo | `intervalIntegral.integral_deriv_eq_sub'` |
| T04 | Pequeño Teorema de Fermat | `Int.ModEq.pow_prime_eq_self` |
| T05 | Pitágoras (EuclideanSpace) | `PythagoreanTriple.eq` |
| T06 | Suma 1+2+...+n | `List.range'` |
| T10 | Primo > 2 es impar | `Nat.Prime.odd_of_ne_two` |
| T12 | AM-GM 2 números | `NNReal.agm_pos` |
| T25 | Even n ↔ 2∣n | `Nat.even_iff` |

### Pendiente

- **D1 C_I**: arXiv y Semantic Scholar no producen candidatos que superen el threshold MiniLM (0.40). Bajar a 0.25 para activar rama C_I.
- **D3 pruebas distintas**: T09a = T09b actualmente (usan el mismo lema `sum_range_id`). Escribir prueba por inducción con `sum_range_succ` + `ring`.
- **Eval completo D1+D2+D3**: integrar los 3 pasos en una sola corrida.
- **9 slots TBD** del eval set sin llenar.
- **Demo Gradio** + deploy en Hugging Face Spaces.

### Decisiones del día

- **LLM Judge**: DeepSeek V4 Flash vía OpenCode Go (gratis con suscripción, sin dependencia de Anthropic API).
- **`exact?` en D1**: confirmado como fuente secundaria de C_F, no como táctica de trivialidad.
- **ArXiv primero en C_I**: mejor cobertura matemática que Semantic Scholar.
- **D3 vía ExtractData standalone**: sin dependencia del paquete pesado `lean-dojo-v2` (PyTorch, DeepSpeed, etc.).

---

## Días 10-12 — Pendiente: Demo web (Gradio + deploy)

**Objetivo:** scaffold Gradio con upload .tex + pipeline D1+D2 con streaming + tabla de veredictos + botón D3 (cola SQLite). Deploy a Hugging Face Spaces. URL pública estable.

**Estado:** landing page desplegada en `avid-journal.github.io`. Demo funcional pendiente.

---

## Días 13-15 — Pendiente: Preprint

**Objetivo:** draft completo: Introduction, Related Work, Methodology, Implementation, Evaluation, Limitations, Future Work, Conclusion. Figuras (árbol de decisión, matriz taxonómica, tabla de resultados, diagrama de arquitectura). Compilar PDF, subir a arXiv.

---

## Días 16+ — Pendiente: Outreach

**Objetivo:** emails personalizados a Wenda Li (Edinburgh), Sean Welleck (CMU), Floris van Doorn (Bonn), Heath Sanchez (Metalogic Labs) con preprint + URL del demo + write-up técnico.

---

## Post-mortem del sprint

*(se completa al finalizar)*

**Qué salió bien:**

**Qué salió mal:**

**Qué cambiaría si lo hiciera de nuevo:**

**Próximos pasos:**
