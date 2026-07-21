# El pipeline AViD

El sistema recibe un archivo `.tex`, extrae sus bloques matemáticos, los formaliza en Lean 4, y aplica un árbol de decisión en tres dimensiones para emitir un veredicto de novedad. Esta sección describe cada etapa con el detalle necesario para su reproducción conceptual.

<!-- fuente: docs/CONTEXT.md, docs/section3_facts.md -->

## 3.1 Ingesta y parseo del LaTeX

El parser extrae entornos matemáticos del fuente LaTeX: `theorem`, `lemma`, `proposition`, `corollary`, `definition`, y sus variantes en español (`teorema`, `lema`, `proposición`, `definición`, `corolario`). También reconoce variantes abreviadas (`thm`, `lem`, `prop`, `cor`, `defn`) y entornos definidos por el usuario mediante `\newtheorem` y `\theoremstyle`.

<!-- fuente: docs/section3_facts.md:24-30 (entornos base + variantes), :29-30 (auto-detección) -->

El parser extrae las dependencias entre bloques a partir de referencias cruzadas `\ref{}` y `\cite{}`. Con esas dependencias construye un grafo dirigido acíclico y aplica un ordenamiento topológico (algoritmo de Kahn) para determinar la secuencia de formalización: los bloques sin dependencias se procesan primero; los que dependen de otros, después.

<!-- fuente: docs/section3_facts.md:39-41 (topological_sort), :41 (extract_references) -->

No todos los entornos detectados pasan a la etapa siguiente. El orquestador solo formaliza tipos considerados "formalizables": `theorem`, `lemma`, `proposition`, `corollary` y sus variantes. Entornos como `remark`, `example`, `proof` y `definition` (cuando no es requerida como dependencia) se extraen pero no se formalizan.

<!-- fuente: docs/section3_facts.md:33-35 (FORMALIZABLE_TYPES), :34 (entornos que se pierden) -->

**Limitación conocida.** El parser opera por expresión regular compilada con una lista fija de nombres de entorno. Los papers que usan AMS-TeX (`\documentstyle{amsppt}`) o definen entornos con nombres idiosincráticos (`\begin{inizio}`, `\begin{numero}`) no son parseables por esta versión. De los 33 candidatos del dataset de retirados, 7 resultaron no viables por este motivo.

<!-- fuente: docs/retracted_dataset_report.md:130-138 (formatos no estándar), docs/section3_facts.md:33 (regex compilado) -->

## 3.2 Formalización a Lean 4

### 3.2.1 Abstracción multi-modelo

La formalización de cada bloque (enunciado y demostración) se delega a un modelo de lenguaje a través de una interfaz abstracta `ModelProvider`. La implementación actual (`avid-clean/`) soporta ocho backends: Claude Code (modo agéntico, vía CLI), Anthropic API (Claude Sonnet 4), OpenAI (GPT-4o), DeepSeek (Chat V3), OpenRouter (cualquier modelo), Mistral (Large), Gemini (2.5 Pro), y OpenCode Go (DeepSeek V4 Pro, el default).

<!-- fuente: docs/section3_facts.md:51-66 (ModelProvider, registry, resolve_provider) -->

La arquitectura distingue dos familias de proveedores. Los "agénticos" (Claude Code) manejan su propio ciclo de verificación: el modelo recibe el prompt, genera código Lean, intenta compilar, y corrige iterativamente. Los "API" (todos los demás) usan un ciclo de verificación externo: el sistema envía el prompt, recibe la respuesta, extrae el código Lean, compila con `lake env lean`, y reenvía errores como feedback para la siguiente iteración.

<!-- fuente: docs/section3_facts.md:54-56 (AgenticProvider vs APIProvider), :83-91 (verification_loop) -->

Cada bloque se clasifica en uno de cuatro modos según su complejidad estimada: `SIMPLE` (5 rondas máximas de corrección), `MEDIUM` (15 rondas), `HARD` (30 rondas), y `EXTERNAL` (sin modelo; se emite un axioma con referencia a la fuente).

<!-- fuente: docs/section3_facts.md:94-97 (modos de formalización) -->

### 3.2.2 Proyecto Lean compartido

Todos los papers comparten un único proyecto Lean 4 (v4.29.0) con una compilación de Mathlib (8247 archivos `.olean`). Cada paper se aloja como submódulo en `Papers/<Slug>/`. Los bloques formalizados se acumulan incrementalmente en un archivo `Paper.lean` y se registran en un índice `PAPER_INDEX.md` que el orquestador consulta antes de buscar en Mathlib.

<!-- fuente: docs/PROJECT_STATE.md:34-36 (proyecto Lean compartido, PAPER_INDEX), docs/CONTEXT.md:16 (PAPER_INDEX como BD local de teoremas) -->

El criterio de éxito de formalización es exigente: el archivo debe compilar sin errores (`returncode == 0`), sin `sorry` en ninguna declaración, y debe contener al menos una declaración sustantiva (keyword `theorem`, `lemma`, `def`, etc.). Los archivos vacíos o con únicamente imports se rechazan.

<!-- fuente: docs/section3_facts.md:108-113 (criterio de éxito, guardia anti-vacío) -->

### 3.2.3 Modo statement-only

Para experimentos donde solo se requiere el enunciado (no la demostración), el sistema puede operar en modo "statement-only": el modelo genera el enunciado en Lean con `:= by sorry` y el criterio de éxito se relaja para aceptar `has_sorry=True` siempre que no haya errores de compilación. Este modo no es una capacidad nativa del código base sino una configuración experimental de los prompts y del criterio de aceptación.

<!-- fuente: docs/section3_facts.md:99-105 (statement-only como prompt, no como modo de código) -->

## 3.3 Corpus de referencia

El sistema compara cada enunciado contra tres corpus:

**C_F (corpus formal).** Mathlib v4.29.0, accedido a través de la API de Leandex. Leandex indexa los enunciados de teoremas de Mathlib y devuelve matches con su estatus de prueba (`proof_status`). La versión actual de la API (v2) no proporciona scores de similitud; el sistema usa el ordenamiento provisto por la API y filtra resultados cuyo `proof_status` es `"statement_only"`.

<!-- fuente: docs/dimensions_facts.md:44-49 (Leandex v2 sin scores, proof_status), docs/PROJECT_STATE.md:32 (18/24 encontrados en Mathlib) -->

**C_I (corpus informal).** Dos fuentes encadenadas. La etapa A consulta TheoremSearch (9.2 millones de enunciados extraídos de arXiv y 7 fuentes adicionales; API pública sin autenticación) más Semantic Scholar y arXiv directamente. Los candidatos se filtran con embeddings MiniLM: solo aquellos con similitud de coseno >= 0.40 pasan a la etapa B. En la etapa B, un juez LLM (DeepSeek V4 Flash, temperature=0) compara el enunciado candidato con cada resultado y emite uno de cuatro veredictos: `equivalent`, `generalization`, `specialization`, `different`.

<!-- fuente: docs/dimensions_facts.md:51-66 (C_I, threshold 0.40, bandas de decisión), docs/PROJECT_STATE.md:36-38 (TheoremSearch + arXiv + Semantic Scholar), docs/bibliography_merged.md:16-17 (TheoremSearch 9.2M) -->

**Corpus propio.** A medida que el orquestador formaliza bloques de un paper, los acumula en `PAPER_INDEX.md`. Los bloques ya procesados dentro del mismo paper se consultan antes de buscar en Mathlib, evitando que el sistema marque como "ya existente" un teorema que el propio paper acaba de introducir.

<!-- fuente: docs/section3_facts.md:201-209 (PAPER_INDEX, modo resume, incrementalidad) -->

## 3.4 Las tres dimensiones

### 3.4.1 D1: No-existencia previa

D1 verifica si el enunciado ya aparece en el corpus formal (C_F) o informal (C_I). La evaluación sigue un orden fijo con cortocircuito: si C_F encuentra match, C_I no se ejecuta.

<!-- fuente: docs/dimensions_facts.md:13-20 (orden de evaluación) -->

**Rama C_F.** Se consulta la API de Leandex con el enunciado en lenguaje natural. Si Leandex devuelve al menos un resultado con `proof_status != "statement_only"`, se considera que el teorema existe en Mathlib. No hay umbral de similitud aplicado: Leandex v2 no proporciona scores.

<!-- fuente: docs/dimensions_facts.md:46-49 (sin threshold en C_F) -->

**Fallback `exact?`.** Si Leandex no encuentra match, el sistema ejecuta `example : τ := by exact?` con un presupuesto de 15 segundos. `exact?` busca teoremas en el entorno Lean cargado (Mathlib completo). Si encuentra uno que cierra el goal, se trata como match en C_F con similitud sintética de 0.95. Esta táctica se clasifica como D1 (búsqueda de existencia), no como D2 (trivialidad), porque su función es encontrar un teorema ya demostrado, no cerrar el goal por automatización.

<!-- fuente: docs/dimensions_facts.md:29-40 (exact? ubicación y semántica), :39 (similarity=0.95) -->

**Rama C_I.** Solo se activa si C_F (Leandex + `exact?`) no encontró match. La etapa A (filtro grueso) consulta TheoremSearch, Semantic Scholar y arXiv. El threshold de embeddings MiniLM es 0.40: candidatos con score inferior se descartan. La etapa B (LLM judge, DeepSeek V4 Flash) recibe los candidatos supervivientes y los compara con el enunciado original.

<!-- fuente: docs/dimensions_facts.md:51-66 (threshold 0.40, bandas C_I) -->

### 3.4.2 D2: No-trivialidad

D2 verifica si el enunciado puede ser demostrado exclusivamente con tácticas automáticas estándar de Lean. Si alguna táctica cierra `example : τ := by T`, el teorema es trivial.

**Tácticas, orden y presupuestos.** El conjunto `T_AUTO` se ejecuta en este orden: `decide`, `norm_num`, `simp`, `omega`, `tauto`, `aesop`. Las primeras cinco tienen un presupuesto de 10 segundos cada una; `aesop` dispone de 30 segundos. El orden prioriza tácticas baratas y específicas; `aesop`, que realiza búsqueda más exhaustiva, va al final. La ejecución se detiene en la primera táctica que cierra el goal.

<!-- fuente: docs/dimensions_facts.md:74-87 (T_AUTO_ORDER), :89-100 (presupuestos) -->

Cada invocación de táctica incurre en un overhead de inicio de `lake env lean`, medido empíricamente en 45 segundos en Windows. El presupuesto total por táctica es, por tanto, `budget + 45s`.

<!-- fuente: docs/dimensions_facts.md:101 (LEAN_STARTUP_OVERHEAD_S=45) -->

**Blacklist de `norm_num`.** La táctica `norm_num` en Mathlib v4.29.0 incluye un atajo hardcodeado que cierra `Irrational (Real.sqrt 2)`. Para evitar este falso positivo, `norm_num` se excluye cuando el enunciado contiene la palabra `Irrational`.

<!-- fuente: docs/dimensions_facts.md:112-126 (blacklist, rationale) -->

**`exact?` no está en D2.** La táctica `exact?` fue removida de D2 y reubicada en D1 como fallback de C_F (sección 3.4.1). La razón es semántica: `exact?` busca un teorema existente en el entorno, lo cual es verificación de existencia previa, no de trivialidad.

<!-- fuente: docs/dimensions_facts.md:37-39 (exact? movido a D1) -->

**Caso de falla conocido.** T14 ("la suma de cuatro números pares es par") es sensible al enunciado Lean concreto generado por el formalizador. En corridas con enunciados que expanden la definición de paridad, `aesop` puede cerrarlo en ~14s (ver sección 4.2). En corridas con enunciados que usan cuantificadores anidados sobre listas, `aesop` requiere ~215s y excede el presupuesto de 30s. Esta variabilidad ilustra que el resultado de D2 no es una propiedad fija del teorema sino del par (enunciado formalizado, táctica, presupuesto).

<!-- fuente: docs/PROJECT_STATE.md:25-26 (bug T14), docs/dimensions_facts.md:74 -->

### 3.4.3 D3: Distancia estructural de premisas

D3 mide cuán diferente es la demostración propuesta de una demostración existente en Mathlib. La métrica es la distancia de Jaccard sobre los conjuntos de premisas (lemas, teoremas, definiciones) usados en cada prueba.

<!-- fuente: docs/dimensions_facts.md:145-232 -->

**Extracción de premisas.** Las premisas se extraen con `ExtractData.lean` (515 líneas), una herramienta standalone que recorre el `InfoTree` de Lean y recolecta, para cada nodo `TermInfo`, la constante referenciada (vía `constName?`), su ubicación de definición (`defPath`, `defPos`), y el módulo que la contiene (`modName`). Se excluyen las referencias que ocurren en el sitio mismo de definición de la constante, para evitar que un teorema se registre a sí mismo como premisa.

<!-- fuente: docs/dimensions_facts.md:148-167 (ExtractData, visitTermInfo, filtro de definición) -->

El extractor funciona en Windows nativo (no requiere WSL ni LeanDojo). Un wrapper en Python (`premise_extraction.py`) gestiona la ejecución y mantiene un caché por SHA256 del archivo fuente.

<!-- fuente: docs/dimensions_facts.md:150-151 (Windows nativo), :177 (caché SHA256) -->

**Pipeline de filtrado.** Antes de calcular Jaccard, las premisas pasan por dos filtros:

1. **Filtro 1 (namespace blacklist).** Se eliminan premisas cuyo `modName` comienza con `Init.` o `Lean.`. Estos namespaces contienen constructores de tipo del núcleo, instancias de typeclasses e internals de tácticas que el elaborador resuelve automáticamente; no reflejan contenido matemático y dominarían artificialmente la intersección.

<!-- fuente: docs/dimensions_facts.md:177-188 (Filtro 1, YAML, rationale) -->

2. **Filtro 2 (premisas del enunciado).** Se eliminan premisas cuya posición en el archivo fuente cae dentro del rango de líneas del enunciado del teorema. Las constantes que aparecen en el enunciado (hipótesis, tipos, definiciones locales) son parte de la firma, no de la prueba; comparar pruebas por las premisas del enunciado infla artificialmente la similitud.

<!-- fuente: docs/dimensions_facts.md:190-194 (Filtro 2, rationale) -->

**Identidad canónica y deduplicación.** Dos premisas con el mismo `(defPath, defPos)` representan el mismo objeto lógico, aunque aparezcan en posiciones distintas de la prueba (por ejemplo, una función invocada dos veces). Antes de cualquier filtro, las premisas se deduplican por esta identidad canónica.

<!-- fuente: docs/dimensions_facts.md:203-222 (identidad canónica, rationale) -->

**Cálculo de Jaccard.** Sean `P(A)` y `P(B)` los conjuntos de premisas (post-filtros, deduplicados). La distancia de Jaccard se define como:

$$d_J(A, B) = 1 - \frac{|P(A) \cap P(B)|}{|P(A) \cup P(B)|}$$

El umbral de decisión es $\theta = 0.5$: si la distancia supera 0.5, las pruebas se consideran estructuralmente distintas (`pruebas_distantes = True`). Si no lo supera, se consideran cercanas. Si alguno de los conjuntos queda vacío tras los filtros, no se emite distancia y el veredicto es `INCONCLUSIVE`.

<!-- fuente: docs/dimensions_facts.md:226-237 (fórmula Jaccard, casos extremos), :252-258 (umbral θ=0.5) -->

**Estado de calibración.** El umbral $\theta = 0.5$ es el valor inicial de diseño y no ha sido calibrado contra un conjunto amplio de pares. El único punto de datos calibrado es el par T08 (pruebas de irracionalidad de $\sqrt{2}$ por paridad vs. valuación 2-ádica), que arroja Jaccard = 0.7222 y es correctamente clasificado como "pruebas distintas" con $\theta = 0.5$.

<!-- fuente: docs/dimensions_facts.md:239-242 (regresión T08 = 0.7222), :262-266 (no calibrado) -->

## 3.5 Árbol de veredictos

El orquestador (`src/novelty_v2/orchestrator.py`) implementa el árbol de decisión completo, que se recorre en orden de costo creciente:

<!-- fuente: docs/dimensions_facts.md:228-242 (árbol de decisión), docs/section3_facts.md:229-242 (ídem) -->

```
D2 (trivialidad): ¿alguna táctica de T_AUTO cierra τ?
  ├── SÍ → NO_NOVEDOSO_trivial                         (FIN)
  └── NO → D1 C_F (Leandex)
            ├── match → D3 (si hay premisas)
            │           ├── distantes  → NOVEDAD_DEMOSTRACION
            │           ├── cercanas   → NO_NOVEDOSO_redundante
            │           ├── vacías     → INCONCLUSIVE
            │           └── no disponible → MATCH_ENCONTRADO_PENDIENTE_D3
            └── sin match → exact? (fallback)
                            ├── match → mismo camino que C_F
                            └── sin match → D1 C_I (arXiv/SS + LLM judge)
                                            ├── equivalent → CONOCIDO_LITERATURA
                                            ├── generalization/specialization → ZONA_GRIS
                                            └── different/sin candidatos → NOVEDAD_ENUNCIADO
```

<!-- fuente: docs/section3_facts.md:229-242 (8 veredictos y árbol) -->

**Lógica de cortocircuito.** D2 es la primera evaluación porque es local y barata (segundos por táctica). Si el teorema es trivial, el árbol termina sin consultar APIs externas. D1 C_F (Leandex) es la segunda porque es una consulta HTTP rápida. D1 C_I es la tercera porque involucra múltiples APIs (TheoremSearch, Semantic Scholar, arXiv) y una llamada al LLM judge. D3 es la más cara (extracción de premisas + Jaccard) y solo se ejecuta cuando hay un match en C_F que requiere dirimir si la prueba es novedosa o redundante.

<!-- fuente: docs/dimensions_facts.md:244-247 (orden por costo) -->

**Los ocho veredictos.** El sistema emite uno de ocho veredictos, cada uno con una interpretación operacional precisa:

1. `NOVEDAD_ENUNCIADO`: sin match en C_F ni C_I.
2. `NOVEDAD_DEMOSTRACION`: match en C_F, D3 indica pruebas distantes.
3. `CONOCIDO_LITERATURA`: match en C_I (literatura informal), sin match en C_F.
4. `NO_NOVEDOSO_redundante`: match en C_F, D3 indica misma prueba.
5. `NO_NOVEDOSO_trivial`: D2 cierra con táctica estándar.
6. `ZONA_GRIS`: el LLM judge clasifica el match como generalización o especialización (requiere revisión humana).
7. `MATCH_ENCONTRADO_PENDIENTE_D3`: match en C_F, D3 no disponible (sin premisas extraídas o sin par de comparación).
8. `INCONCLUSIVE`: D3 ejecutado pero los conjuntos de premisas quedaron vacíos tras los filtros.

<!-- fuente: docs/section3_facts.md:219-227 (8 veredictos con definiciones) -->

## 3.6 Implementación y estado actual

El sistema está implementado en Python 3.11+ y corre sobre Windows 10 nativo. La base de código se organiza en dos módulos: `src/` contiene el parser original, el orquestador de novedad (`src/novelty_v2/`) y las tres dimensiones (D1, D2, D3); `avid-clean/` contiene una copia del parser y un orquestador de formalización reescrito con abstracción multi-modelo. El árbol de veredictos se ejecuta desde `src/novelty_v2/` y es idéntico independientemente de qué orquestador haya formalizado el paper.

<!-- fuente: docs/section3_facts.md:250-263 (tabla de diferencias avid-clean vs src) -->

El proyecto completo cuenta con 167 pruebas superadas y 1 saltada (julio 2026), un dataset de evaluación de 24 teoremas evaluados (de 26 planificados, más 9 slots pendientes), y un dataset de 33 papers retirados por duplicación con 52 controles emparejados.

<!-- fuente: docs/PROJECT_STATE.md:102-105 (tests, eval set, dataset) -->
