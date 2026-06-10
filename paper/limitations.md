# Limitaciones de AViD Journal v1

**Propósito:** esta lista se va llenando durante el sprint a medida que aparecen casos de falla. Al Día 13 se reformatea para la sección "Limitations" del preprint. Cada limitación debe corresponder a (a) una decisión consciente de scope o (b) un caso documentado del eval set.

---

## Limitaciones del framework conceptual

### L1 — La métrica mide novedad teorema-a-teorema, no artículo-completo
**Status:** decisión de scope para v1.
**Impacto:** un paper que reordena teoremas conocidos sin contribución nueva podría no ser detectado si cada teorema individual ya estaba en el corpus pero su combinación es lo nuevo.
**Trabajo futuro:** capa de agregación sobre teoremas.

### L2 — La distancia de Jaccard ignora el peso de cada premisa
**Status:** decisión consciente para v1.
**Impacto:** una premisa rara y específica (que aporta mucho) cuenta igual que una premisa ubicua (que aporta poco).
**Trabajo futuro:** Jaccard ponderado por IDF; uso de la distribución scale-free del AFP (Huch arXiv:2209.13305).

### L3 — La métrica solo opera sobre teoremas en `Prop`
**Status:** decisión técnica (proof irrelevance).
**Impacto:** para teoremas en `Type` (con relevancia de pruebas) la noción correcta sería homotópica, no de premisas.
**Trabajo futuro:** extensión a HoTT / fragmento univalente.

## Limitaciones de la implementación v1

### L4 — Equivalencia de tipos solo sintáctica (D1 nivel 0)
**Status:** v1 usa igualdad sintáctica tras normalización. Implementación de `isDefEq` (nivel 1) queda pendiente.
**Caso del eval set que lo documenta:** T22 (n + 0 = n vs. n = n), T25 (Even n vs. 2 ∣ n).
**Impacto:** falsos negativos esperables en enunciados lógicamente equivalentes con sintaxis distinta.

### L5 — Filtro de trivialidad sobre-aproxima
**Status:** `T_auto` puede cerrar teoremas no triviales (especialmente `aesop`).
**Caso del eval set que lo documenta:** T23 (definición de árbol).
**Impacto:** falsos positivos de trivialidad. Sesgo conservador hacia "no novedoso" — error seguro.

### L6 — Autoformalización del corpus informal es frágil
**Status:** punto débil reconocido. Acotado por estado del arte de autoformalización (cf. ProofFlow, Aria).
**Caso del eval set que lo documenta:** T24 (esquemas/haces — vocabulario fuera de mathlib).
**Impacto:** la rama C_I del árbol de decisión es solo tan confiable como la traducción del rival. Se reporta cuándo la clasificación depende de traducción incierta.

### L7 — Eval set pequeño y curado a mano
**Status:** 29 teoremas + 9 TBD. Limitado por el sprint.
**Impacto:** los números reportados son evidencia preliminar, no validación a escala.
**Trabajo futuro:** corrida sobre mathlib completa y/o sobre un corpus arXiv mayor.

### L8 — La medición depende del proceso de formalización
**Status:** decisión consciente — AViD evalúa la prueba *formalizada*, no la prueba *platónica*.
**Impacto:** dos formalizaciones distintas del mismo argumento podrían dar veredictos distintos en D3.
**Mitigación parcial:** math filter sobre premisas reduce ruido de formalización.

---

## Limitaciones descubiertas durante implementación

### L9 — D3 ejecutado offline manualmente, no en el pipeline en tiempo real

**Status:** decisión de scope para v1 (registrada en `decisions.md`, 2026-06-01).

**Origen del hallazgo:** durante el Día 3 se descubrió empíricamente que LeanDojo v1 traza dependencias transitivas de todos los imports al procesar un proyecto Lean, no solo los archivos del proyecto. El smoke test sobre `yangky11/lean4-example` (proyecto trivial sin Mathlib) inició procesamiento de 1518 archivos de stdlib.

**Impacto en el demo:**
- D1 (no-existencia) y D2 (trivialidad) corren automáticamente sobre cada teorema en tiempo real cuando el usuario sube un paper.
- D3 (distancia de premisas) NO corre automáticamente. Para los teoremas marcados por D1 como "enunciado similar encontrado", el demo expone un botón **"solicitar análisis fino"** que encola el pedido en una cola SQLite.
- D3 se procesa offline en máquina local con WSL+LeanDojo y se devuelve al usuario asincrónicamente.

**Impacto en la evidencia del paper:**
- La sección de resultados del preprint reporta D3 ejecutado manualmente sobre los pares estrella del eval set (T07, T08, T09), no sobre todos los 29 teoremas.
- Las distancias de Jaccard reportadas son válidas; el alcance es menor de lo planificado pre-sprint.

**Mitigación futura:** F2 / F7 del `future_work.md` (premisas ponderadas y arquitectura modular) habilitan reemplazar LeanDojo por un extractor más liviano en versiones futuras.

### L10 — norm_num cierra teoremas de irracionalidad algebraica (falsos positivos de D2)

**Status:** comportamiento emergente de Mathlib v4.29.0, no corregible sin cambiar T_auto o agregarle un filtro.

**Origen del hallazgo:** corrida del eval set Día 5 (2026-06-09). T01 (`Irrational (Real.sqrt 2)`) y T08 (mismo enunciado) fueron cerrados por `norm_num` en ~14s con `import Mathlib.Tactic`. El módulo `Mathlib.Data.Real.Irrational` está marcado como deprecado; `norm_num` en Mathlib v4.29.0 incorpora una extensión de decisión algebraica para irracionalidad de raíces cuadradas de enteros libres de cuadrados.

**Impacto:** D2 devuelve `trivial=True` para teoremas del tipo `Irrational (Real.sqrt p)` con `p` libre de cuadrados. Desde la perspectiva del filtro D2 esto es **correcto por definición** — si `norm_num` lo cierra, el resultado es automáticamente verificable. El enunciado deja de requerir idea matemática en el sentido de D2. La etiqueta `expected_trivial=False` en el eval set refleja la intuición pre-sprint (√2 irracional es "clásico"), no la definición operacional de D2.

**Consecuencia para el paper:** este caso ilustra que **D2 es monótono creciente en poder táctico**: a medida que `T_auto` crece, más teoremas cruzan el umbral de trivialidad. Este es el comportamiento diseñado, no un bug. Se sugiere incluirlo como ejemplo positivo en la sección de Propiedades de D2.

**Casos del eval set:** T01, T08.

---

### L11 — Mathlib v4.29.0 compila monolíticamente; imports específicos de módulos fallan en `lake env lean`

**Status:** limitación de infraestructura de Lean 4 / Lake. Sin mitigación en v1.

**Origen del hallazgo:** corrida del eval set Día 5 (2026-06-09). Los imports específicos (`import Mathlib.Data.Nat.Prime`, `import Mathlib.Data.Int.Parity`, `import Mathlib.Algebra.BigOperators.Group.Finset`, etc.) producen errores de tipo "object file '...' could not resolve HEAD" al ejecutar `lake env lean` sobre un archivo `.lean` temporal. Solo `import Mathlib` e `import Mathlib.Tactic` funcionan como entry-points confiables.

**Causa técnica:** Mathlib se compila como un árbol de oleans interdependientes. Al usar `lake env lean` con un archivo temporal fuera del proyecto Mathlib, Lake no puede resolver el árbol de dependencias de un módulo interior sin compilar todo lo que está por encima de él en el grafo. `import Mathlib` y `import Mathlib.Tactic` son los únicos módulos cuya compilación completa ya está cacheada en `.lake/`.

**Impacto cuantitativo:** 13 de 24 teoremas del eval set (T02-T07, T09-T11, T13-T14, T18, T23, T26) recibieron el error. Para los 12 no-triviales esto no afecta la corrección del resultado (all tactics fail → trivial=False, correcto). Para T14 (trivial esperado) produjo un falso negativo. Para T18 (trampa de control) y T23 (FP esperado) impidió la verificación experimental.

**Impacto en el demo en producción:** cada invocación de D2 debe usar `import Mathlib`, lo que implica ~30-45s de startup por teorema (con caché de OS cálida). Para un paper de 10 teoremas: ~5-8 minutos de cómputo D2. Manejable para el pipeline offline; subóptimo para el demo en tiempo real.

**Mitigación futura:** (a) precalentamiento de oleans al arrancar el servidor del demo; (b) caché de resultados D2 keyed por `hash(lean_statement)`; (c) en versiones futuras de Mathlib/Lake que expongan importación selectiva.

**Casos del eval set:** T02-T07, T09-T11, T13-T14, T18, T23, T26.
