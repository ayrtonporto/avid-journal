# 5. Experimentos

Esta sección reporta tres bloques de evaluación, todos de carácter preliminar. El primero describe cómo se construyó el dataset de papers retirados que sirve de ground truth para los experimentos. El segundo presenta un estudio profundo sobre 10 papers con el pipeline D1+D2 completo, incluyendo una auditoría manual de fidelidad de formalización. El tercero presenta un estudio ancho sobre 52 papers usando similitud semántica de enunciados. Los tres bloques comparten una misma metodología: comparar papers retirados de arXiv por duplicación de resultados previos contra papers de control emparejados por categoría y año.

<!-- fuente: paper/PAPER_BRIEF.md §5 -->

## 5.1 Construcción del dataset de retirados

### 5.1.1 Búsqueda y filtrado

Se consultó la API pública de arXiv (`export.arxiv.org`) con la query `cat:math.* AND co:withdrawn`, que devolvió 2600 papers retirados en categorías de matemática. Sobre el texto del withdrawal comment de cada paper, se aplicaron 23 patrones de expresión regular diseñados para identificar retiros por duplicación de resultados previos y excluir retiros por errores, gaps o problemas administrativos.

<!-- fuente: docs/retracted_dataset_report.md:23-35 (2600 papers, 23 patrones) -->

Los patrones más frecuentes fueron: "result was/is already known" (5 ocurrencias), "had already been proved by [autor]" (4), "results are not new/original" (4), "subsumed by" (4), y "previously proved/proven by" (3).

<!-- fuente: docs/retracted_dataset_report.md:79-89 (patrones más frecuentes) -->

El resultado fueron 33 candidatos. De ellos, 26 resultaron viables (fuente LaTeX descargable desde arXiv, al menos un entorno de teorema detectable), y 7 no viables: sus fuentes usan formatos no estándar como AMS-TeX (`\documentstyle{amsppt}`) o nombres abreviados de entornos (`\begin{thm}` en lugar de `\begin{theorem}`) que el parser actual no reconoce.

<!-- fuente: docs/retracted_dataset_report.md:42-47 (33 candidatos, 26 viables), :130-138 (formatos no estándar) -->

Los 26 papers viables cubren 17 categorías de matemática, con concentración en Combinatorics (math.CO, 4) y Algebraic Geometry (math.AG, 3), y un rango de años de 2001 a 2026 con mayor densidad en 2007–2016.

<!-- fuente: docs/retracted_dataset_report.md:51-76 (distribución por categoría y rango de años) -->

### 5.1.2 Controles emparejados

Para cada uno de los 26 papers retirados se seleccionaron 2 controles de arXiv con los siguientes criterios: misma categoría, año de publicación ±1, no retirados, y fuente LaTeX verificable con al menos un entorno de teorema. El emparejamiento se realizó mediante búsqueda programática sobre la API de arXiv con cortesía de red (delay de 3 segundos entre requests, backoff exponencial ante HTTP 429). Se verificaron 382 candidatos para obtener 52 controles (2 por cada retirado).

<!-- fuente: docs/retracted_dataset_report.md:161-174 (estrategia de emparejamiento), :166 (382 chequedos, 332 viables) -->

El dataset completo para experimentos consta de 26 pares retirado + 2 controles cada uno (78 papers en total).

<!-- fuente: docs/retracted_dataset_report.md:194-196 -->

### 5.1.3 Calidad del ground truth

De los 26 papers retirados viables, 12 (46%) citan explícitamente el trabajo previo que duplica su resultado, proporcionando autores, arXiv IDs o referencias a journals. Los 14 restantes usan frases genéricas ("already known", "not new") sin especificar la fuente. Para el experimento, el withdrawal comment del autor se toma como proxy de ground truth de duplicación, con la salvedad de que es un indicador imperfecto: el autor puede equivocarse sobre qué resultado exactamente ya existía, o puede retirar por motivos que no impliquen duplicación literal de enunciados.

<!-- fuente: docs/retracted_dataset_report.md:92-95 (12 citan explícitamente), :212-222 (¿los comentarios citan?) -->

## 5.2 Selección de modelo de formalización

Antes de ejecutar el experimento principal, se compararon cuatro modelos de lenguaje en la tarea de formalización statement-only (enunciado sin demostración) sobre los 5 papers retirados del smoke test. Los modelos y sus resultados:

| Modelo | 1609.02090v1 | 1207.0631v1 | 1212.0196v1 | 1004.3381v1 | math/0604362v1 | Éxito |
|---|---|---|---|---|---|---|
| deepseek-v4-pro | ❌ | ❌ | ⚠️ placeholder | ❌ | ❌ | **0/5** |
| deepseek-v4-flash | ❌ | ❌ | ❌ | ❌ | ❌ | **0/5** |
| **qwen3.7-max** | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5** |
| glm-5.2 | ✅ | ✅ | ❌ | ✅ | ⏳ timeout | **3/5** |

<!-- fuente: docs/model_comparison_001c.md:12-17 (tabla de resultados) -->

**Ganador: Qwen 3.7-max (5/5).** Fue el único modelo que formalizó correctamente los 5 enunciados con definiciones matemáticamente sustantivas. Los modelos DeepSeek fallaron en todos los casos, principalmente por errores de síntesis y tokens inesperados. GLM-5.2 es un segundo fuerte (3/5, con errores reparables). Todos los experimentos subsiguientes usan Qwen 3.7-max como modelo de formalización, accedido a través de la API de OpenCode Go.

<!-- fuente: docs/model_comparison_001c.md:21-52 (winner, detalles), docs/decisions.md:314 (Qwen como modelo seleccionado) -->

## 5.3 Estudio profundo: Run 002

### 5.3.1 Diseño

Run 002 evaluó 10 papers (5 retirados + 5 controles emparejados) con el pipeline completo: formalización statement-only del enunciado en Lean 4, filtro de trivialidad D2, búsqueda en Mathlib D1 C_F (Leandex), y búsqueda en literatura informal D1 C_I (TheoremSearch + Semantic Scholar + LLM judge). Los 5 retirados se seleccionaron manualmente como casos claros de duplicación entre los 26 viables. Los 5 controles son los pares emparejados correspondientes.

<!-- fuente: docs/decisions.md:307-317 (Run 002: diseño, resultados), docs/run_002_verdicts.md -->

### 5.3.2 Resultados de formalización

De los 10 papers, 7 fueron formalizados exitosamente y 3 fallaron: uno por error de compilación (`IsIrreducible` duplicado, `Complex.abs` no encontrado) y dos por timeout de API (enunciados con 4 niveles de casos anidados que exceden el límite de Qwen 3.7-max).

<!-- fuente: docs/run_002_verdicts.md:52-55 (fallos), results/experiment_run_002.csv (datos completos) -->

### 5.3.3 Veredictos del pipeline

Sobre los 7 papers formalizados, el pipeline emitió:

- **6 `NOVEDAD_ENUNCIADO`**: el enunciado no fue encontrado en Mathlib ni en la literatura informal.
- **1 `CONOCIDO_LITERATURA`**: Paper 2 (1207.0631v1, teorema de Fillmore sobre matrices). D1 C_I encontró arXiv:1804.02140 (2018) que trata el mismo teorema. El LLM judge emitió `equivalent` con confianza 0.95. El veredicto es correcto: el teorema de Fillmore es conocido en la literatura desde al menos 1969.

<!-- fuente: results/experiment_run_002.csv:2-3 (veredictos), docs/run_002_verdicts.md:12-19 (Paper 1), :17-21 (Paper 2) -->

### 5.3.4 Auditoría de fidelidad del autor

El primer autor revisó manualmente cada una de las 7 formalizaciones exitosas, comparando el código Lean generado contra el enunciado LaTeX original, y asignó una clasificación de fidelidad:

| Paper | ID | Rol | Fidelidad |
|---|---|---|---|
| 1 | 1609.02090v1 | retirado | ✅ Fiel |
| 2 | 1207.0631v1 | retirado | ✅ Fiel |
| 3 | 1212.0196v1 | retirado | ✅ Fiel |
| 4 | 1004.3381v1 | retirado | ✅ Fiel |
| 8 | 1101.3720v1 | control | ❌ Incorrecto |
| 9 | 0904.1783v3 | control | ⚠️ Aproximación |
| 10 | math/0504586v2 | control | ❌ Incorrecto |

<!-- fuente: docs/run_002_verdicts.md:57-70 (tabla de fidelidad), docs/decisions.md:317 (anotación de fidelidad) -->

**Hallazgos de la auditoría:**

- **4/4 retirados resultaron fieles.** Los enunciados formalizados capturan correctamente los teoremas originales.
- **0/3 controles resultaron fieles.** Los tres controles presentan problemas graves: Paper 8 usa `theta m := sorry` (placeholder) en la definición central; Paper 9 solo formaliza una dirección de una equivalencia (⇒ en lugar de ⇔); Paper 10 define `PercolationEvent = {ω | True}` y `probMeasure` como medida de Dirac en lugar de Bernoulli(p), trivializando completamente el teorema.

<!-- fuente: docs/run_002_verdicts.md:32-50 (papers con problemas), docs/run_002_verdicts.md:57-70 (tabla resumen) -->

**Asimetría retirados/controles.** La tasa de fidelidad es 4/4 para retirados y 0/3 para controles. Una posible explicación es un sesgo de selección: los controles, emparejados por categoría y año pero no por complejidad de enunciado, tienden a tener enunciados más largos y con más casos anidados, lo que aumenta la dificultad de formalización. Los dos controles que fallaron por timeout de API (Papers 6 y 7) refuerzan esta hipótesis.

<!-- fuente: docs/decisions.md:317 (asimetría retirados/controles) -->

### 5.3.5 Caso de prior art: 1404.0187

El Paper 1 (1609.02090v1, problema de Waring sobre Z_n) es un caso ilustrativo de los límites de D1. El paper fue retirado porque su resultado principal (γ(4) = 15) ya había sido probado por Hardy y Littlewood. Sin embargo, D1 informal no encontró a Hardy y Littlewood en el top 5 de TheoremSearch. Lo que sí encontró fue arXiv:1404.0187 ("Representing Integers as the Sum of Two Squares in the Ring Z_n"), un paper de 2014 sobre exactamente el mismo problema, con score 0.637. El duplicador canónico (Hardy & Littlewood, circa 1920) no aparece porque TheoremSearch indexa arXiv, no la literatura anterior a 1991.

<!-- fuente: docs/prior_art_1404.md:1-36 (verificación de prior art), docs/run_002_verdicts.md:12-15 (Paper 1) -->

Este caso ilustra el punto ciego temporal de D1: el corpus informal cubre arXiv, no la literatura matemática completa. Resultados anteriores a la era de los preprints electrónicos son invisibles para el sistema.

<!-- fuente: paper/PAPER_BRIEF.md:192-198 (caso 1404.0187) -->

## 5.4 Estudio ancho: Wide Study v2

### 5.4.1 Diseño original y defectos metodológicos (v1)

El objetivo del wide study era evaluar, a escala, si una métrica simple de similitud semántica de enunciados basta para distinguir papers retirados de controles. La primera versión (v1) corrió sobre los 52 papers del dataset (26 retirados + 26 controles), consultando TheoremSearch con el texto del primer teorema de cada paper (truncado a 1000 caracteres) y registrando el top-10 de matches.

<!-- fuente: docs/wide_study_audit.md:1-5, docs/wide_study_audit.md:53-62 (diseño) -->

La v1 reportó 12 strong matches (papers con al menos un resultado de score ≥ 0.75), todos controles. Este resultado parecía prometedor pero resultó ser un artefacto de dos defectos metodológicos:

1. **Auto-exclusión ausente.** El script no excluía el propio paper de los resultados de TheoremSearch. De los 12 strong matches, 11 eran self-matches: el paper se encontró a sí mismo en el índice de TheoremSearch. Solo 1 match (math/0504586v2 vs. 0901.4760, "A survey on dynamical percolation") era genuinamente cruzado.

2. **38 de 52 papers sin texto de teorema.** El script no pudo extraer enunciados para 38 papers. Las causas: arXiv retiró los fuentes de los papers retirados (el endpoint `arxiv.org/src/{id}` devuelve 404), y varios controles no estaban en el caché local. El resultado fue que 0 de 26 retirados tenían scores, haciendo imposible cualquier comparación.

<!-- fuente: docs/wide_study_audit.md:48-49 (38 sin scores), :120-144 (11/12 self-matches), :148-160 (retirados sin scores) -->

### 5.4.2 Correcciones (v2)

La versión 2 corrigió ambos defectos:

- **Auto-exclusión.** Se pasó el parámetro `exclude_arxiv_ids` a la función `search_theoremsearch()`, filtrando el propio paper de los resultados.
- **Cache lookup.** Se agregó búsqueda en el caché de la v1 (`cache/retracted_dataset/`) para papers cuyas fuentes de arXiv ya no están disponibles.
- **Explicit skip.** Los papers sin texto de teorema extraíble se marcan explícitamente como `skip` en lugar de generar scores falsos.

<!-- fuente: git log commit 75b9773 "fix(wide): v2, auto-exclusion + v1 cache lookup + skip explicito" -->

### 5.4.3 Resultados (v2)

La v2 se ejecutó sobre los 52 papers originales. Tras filtrado, 37 resultaron evaluables (tenían texto de teorema extraíble y generaron resultados de TheoremSearch distintos de self-match). Los resultados:

- **7 strong matches** (score ≥ 0.75): 5 retirados y 2 controles.
- **Mann-Whitney U test** sobre la distribución de similarity scores entre retirados y controles: **p = 0.854**.

<!-- fuente: docs/wide_study_v2_closeout.md -->

### 5.4.4 Interpretación

El valor p = 0.854 indica que no hay diferencia estadísticamente significativa entre las distribuciones de scores de similitud de papers retirados y controles. Dicho de otra forma: la similitud semántica de enunciados, medida como embedding coseno contra el índice de TheoremSearch, no permite distinguir un paper que duplica resultados previos de uno que no.

Este es el resultado principal del wide study y es un **resultado negativo**: con la métrica actual y el corpus disponible, el sistema no puede separar retirados de controles a escala. Las razones posibles son múltiples: (a) el withdrawal comment es un proxy ruidoso de ground truth (un paper puede ser retirado por duplicación sin que su enunciado principal sea textualmente cercano al original duplicado); (b) TheoremSearch indexa enunciados modernos de arXiv, no la literatura clásica donde están los duplicadores originales; (c) el texto del primer teorema de un paper no necesariamente es el enunciado duplicado.

<!-- fuente: paper/PAPER_BRIEF.md (interpretación preliminar) -->

## 5.5 Resumen de hallazgos experimentales

| Experimento | n | Resultado principal | Carácter |
|---|---|---|---|
| Comparación de modelos | 5 papers × 4 modelos | Qwen 3.7-max 5/5; DeepSeek Pro 0/5 | Selección de herramienta |
| Run 002 (estudio profundo) | 10 papers | 7/10 formalizados; 1 acierto D1; asimetría de fidelidad (4/4 vs 0/3) | Evidencia de funcionamiento + límites |
| Wide Study v2 (estudio ancho) | 37 papers evaluables | p = 0.854; indistinguibles | Resultado negativo |

<!-- fuente: compilación de secciones 5.2–5.4 -->

**Tres conclusiones preliminares:**

1. El pipeline corre de extremo a extremo sobre papers reales, con una tasa de formalización del 70% (7/10) en el estudio profundo, pero esa tasa es engañosamente alta porque los papers fueron seleccionados manualmente entre los más formalizables del dataset.

2. Allí donde el pipeline corre, D1 encuentra matches relevantes en la literatura informal (Paper 2) y no produce falsos positivos (los 4 retirados fieles fueron correctamente clasificados como `NOVEDAD_ENUNCIADO` porque Mathlib no contiene sus enunciados). Pero el punto ciego temporal impide encontrar duplicadores canónicos anteriores a arXiv (caso Hardy & Littlewood).

3. A escala, la señal de novedad se diluye. El wide study no encuentra diferencia entre retirados y controles. Esto puede reflejar una limitación del corpus, una limitación de la métrica de similitud semántica como proxy de novedad, o una combinación de ambas.

<!-- fuente: paper/PAPER_BRIEF.md §5 (espina narrativa de experimentos), docs/PROJECT_STATE.md:122-140 (pendientes) -->
