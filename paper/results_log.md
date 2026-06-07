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

## Día 5 — Extracción de premisas con LeanDojo (parte 1)

**Objetivo:** función `get_premises(theorem) -> set[str]` corriendo sobre teoremas básicos.

**Hecho:**

**Pendiente:**

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
