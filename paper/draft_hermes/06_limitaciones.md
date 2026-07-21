# 6. Limitaciones

Las limitaciones de AViD v1 se agrupan en tres categorías: las del framework conceptual (qué mide la métrica y qué no), las de la implementación (qué hace el sistema actual y qué no), y las del diseño experimental (qué nos dicen realmente los números reportados).

<!-- fuente: paper/limitations.md -->

## 6.1 Limitaciones del framework conceptual

**L1. Métrica teorema-a-teorema, no artículo-completo.** AViD evalúa cada teorema individualmente contra el corpus. Un paper que reorganiza teoremas conocidos de forma novedosa (la combinación es lo nuevo, no las partes) no sería detectado. Esta es una decisión de scope para v1; una capa de agregación sobre teoremas queda como trabajo futuro.

<!-- fuente: paper/limitations.md L1 -->

**L2. Jaccard ignora el peso de cada premisa.** Una premisa rara y específica (por ejemplo, un lema profundo de teoría algebraica de números) cuenta igual que una premisa ubicua (por ejemplo, `Nat.add_comm`). La ponderación por IDF usando la distribución scale-free del AFP documentada por Huch (arXiv:2209.13305) es trabajo futuro.

<!-- fuente: paper/limitations.md L2, paper/bibliography_merged.md §6 (Huch) -->

**L3. Solo opera sobre `Prop` (proof irrelevance).** La distancia de Jaccard sobre conjuntos de premisas asume proof irrelevance: dos pruebas de la misma proposición son intercambiables. Para teoremas en `Type` (donde la identidad de la prueba importa), la noción correcta sería homotópica, no de premisas. Extender D3 a un fragmento univalente es trabajo futuro de largo plazo.

<!-- fuente: paper/limitations.md L3 -->

**Lakatos (1976).** AViD mide novedad sobre enunciados y pruebas congelados en un corpus formal. No captura novedad conceptual: una definición nueva que reformula un problema, o una demostración que introduce un método transferible a otros dominios. Esta limitación no es de implementación sino del marco mismo: la novedad transformacional es cualitativamente distinta de la novedad de enunciado y requiere criterios que exceden la comparación de premisas.

<!-- fuente: paper/PAPER_BRIEF.md §6 (Lakatos 1976), paper/bibliography_merged.md §9 (Lakatos) -->

**Došen (2003).** La identidad de pruebas es un problema indecidible en general. Jaccard sobre premisas es una aproximación computable que expone al sistema a dos tipos de error: falsos positivos (pruebas normalización-equivalentes que usan premisas superficialmente distintas) y falsos negativos (estrategias distintas que comparten lemas del núcleo). La elección de Jaccard es una decisión de ingeniería, no una solución al problema filosófico.

<!-- fuente: paper/limitations.md (Došen 2003), paper/bibliography_merged.md §9 (Došen) -->

## 6.2 Limitaciones de la implementación v1

**L4. Equivalencia de tipos solo sintáctica (D1 nivel 0).** D1 compara enunciados por igualdad sintáctica tras normalización. No implementa `isDefEq` (equivalencia definicional vía kernel de Lean). Dos enunciados lógicamente equivalentes con sintaxis distinta (por ejemplo, `Even n` vs. `2 \mid n`) pueden producir un falso negativo. Documentado con los casos T22 y T25 del eval set. `isDefEq` está diferido por ser no prioritario para v1.

<!-- fuente: paper/limitations.md L4, docs/PROJECT_STATE.md decisión out-of-scope isDefEq -->

**L5. D2 sobre-aproxima la trivialidad.** Las tácticas de `T_AUTO`, en particular `aesop`, pueden cerrar teoremas que un matemático no consideraría triviales. El caso documentado es T23 (`IsTree = Connected ∧ IsAcyclic`), que en corridas con una definición conjuntiva fue cerrado por `tauto`, aunque en la corrida de evaluación reportada (sección 4.2) el enunciado Lean usado no activó ese camino. El sesgo es conservador hacia "no novedoso", que es el error seguro: es preferible marcar como trivial un teorema que no lo es que declarar novedoso uno que un estudiante puede probar en tres líneas.

**L5b. Sensibilidad de D2 al enunciado formalizado.** T14 (suma de cuatro pares es par) ilustra que el resultado de D2 no es una propiedad fija del teorema sino del par (enunciado formalizado, táctica, presupuesto). En la corrida de evaluación, `aesop` lo cerró en 13.6s; en corridas anteriores con un enunciado Lean más complejo, la misma táctica requirió ~215s y excedió el presupuesto de 30s. Esta variabilidad no es un bug sino una consecuencia de que D2 opera sobre el producto de la autoformalización, no sobre el enunciado platónico.

<!-- fuente: paper/limitations.md L5, docs/dimensions_facts.md T14 budget -->

**L6. Autoformalización de pruebas ajenas es frágil.** La rama D1 C_I requiere traducir enunciados de papers de arXiv para compararlos con el enunciado candidato. La tasa de éxito de formalización de pruebas ajenas, medida con DeepSeek V4 Pro en 45 llamadas, fue de 0%. Pendiente remedición con Qwen 3.7-max, que mostró mejor desempeño en formalización de enunciados (5/5 en el benchmark de modelos).

<!-- fuente: paper/limitations.md L6, paper/bibliography_merged.md PARTE 2 correcciones (0%), docs/model_comparison_001c.md (Qwen 5/5) -->

**L7. Eval set pequeño y curado a mano.** El eval set actual tiene 26 teoremas firmes más 9 slots sin poblar, de los cuales 24 fueron evaluados en la corrida reportada (sección 4.2). La precisión de D2 aislado es de 22/24 = 91.7%, con 2 casos de expectativa ambigua (T19 y T22). Estos números son evidencia preliminar, no validación a escala. Una corrida sobre Mathlib completo (~1.9 millones de líneas) o sobre un corpus arXiv mayor es trabajo futuro.

<!-- fuente: paper/limitations.md L7, docs/PROJECT_STATE.md eval set 26+9 -->

**L8. La medición depende del proceso de formalización.** AViD evalúa la prueba formalizada, no la prueba platónica. Dos formalizaciones distintas del mismo argumento informal podrían dar distancias de Jaccard diferentes. El math filter sobre premisas (Filtro 1 + Filtro 2) reduce este ruido pero no lo elimina.

<!-- fuente: paper/limitations.md L8 -->

**L9. D3 fuera del pipeline en tiempo real.** La extracción de premisas con `ExtractData.lean` requiere ejecutar `lake env lean` sobre archivos que posiblemente importen Mathlib completo. Aunque funciona en Windows nativo (sin requerir WSL), el tiempo de extracción no es compatible con un demo interactivo. En la arquitectura actual, D3 se ofrece como análisis a pedido, no como parte del flujo automático.

<!-- fuente: paper/limitations.md L9, docs/PROJECT_STATE.md decisión D3 offline -->

**L10. D2 es relativo al par (T_AUTO, Mathlib_version).** Esto no es una limitación sino una propiedad del diseño: la trivialidad operacional depende de qué tácticas están disponibles y de qué tan potentes son. `norm_num` en Mathlib v4.29.0 cierra `Irrational (Real.sqrt 2)` en 14 segundos; en 1870, esa demostración requería aproximadamente 5 páginas de análisis real. El paper reporta `T_AUTO` y la versión exacta de Mathlib (v4.29.0, commit 8a178386) para permitir reproducción fiel. Reproducciones en versiones futuras pueden dar resultados distintos, y eso es esperable.

<!-- fuente: paper/limitations.md L10, docs/decisions.md 2026-06-10 relatividad D2 -->

**L11. Mathlib compila monolíticamente.** Los imports específicos de módulos (`import Mathlib.Data.Nat.Prime`, etc.) fallan al ejecutar `lake env lean` sobre archivos temporales. Solo `import Mathlib` e `import Mathlib.Tactic` funcionan como puntos de entrada. Esto obliga a que cada invocación de D2 cargue Mathlib completo, con un overhead de 45 segundos por proceso (medido en Windows). El precalentamiento de oleans al iniciar el demo amortiza este costo.

<!-- fuente: paper/limitations.md L11, docs/dimensions_facts.md overhead -->

## 6.3 Limitaciones del diseño experimental

**L12. n pequeño en el estudio profundo.** Run 002 evaluó solo 10 papers (5 retirados + 5 controles), seleccionados manualmente entre los 26 viables del dataset. Los resultados (7/10 formalizados, 1 acierto en D1 informal) son ilustrativos pero no generalizables. Un experimento con los 26 retirados completos + sus 52 controles requeriría resolver el cuello de botella de formalización (tasa actual: 70% en selección manual, probablemente menor en el dataset completo).

<!-- fuente: docs/PROJECT_STATE.md Run 002, paper/decisions.md Run 002 congelada -->

**L13. Sesgo de formalizabilidad en el dataset.** Los 26 papers viables del dataset de retirados son aquellos cuya fuente LaTeX era parseable y cuyos enunciados eran formalizables. Los 7 excluidos (AMS-TeX, nombres abreviados de entornos) y los 2 controles que fallaron por timeout en Run 002 (enunciados demasiado largos) introducen un sesgo de accesibilidad técnica. No sabemos si los papers excluidos son sistemáticamente más o menos "duplicables" que los incluidos.

<!-- fuente: paper/PAPER_BRIEF.md §6 (sesgo de formalizabilidad), docs/retracted_dataset_report.md 7 no viables -->

**L14. Punto ciego temporal del corpus.** D1 informal indexa arXiv (desde 1991) y TheoremSearch (arXiv + 7 fuentes adicionales). La literatura matemática anterior a la era de los preprints electrónicos es invisible para el sistema. El caso documentado es el Paper 1 de Run 002 (1609.02090v1): el duplicador real es Hardy y Littlewood (circa 1920), pero D1 informal encontró arXiv:1404.0187 (2014) en su lugar. Este no es un bug sino una limitación del corpus: AViD encuentra "lo que está en arXiv con embeddings similares", no necesariamente "el paper que el autor cita como fuente de la duplicación".

<!-- fuente: docs/prior_art_1404.md, paper/PAPER_BRIEF.md caso 1404.0187 -->

**L15. θ = 0.5 sin calibrar.** El umbral de Jaccard para decidir entre `NOVEDAD_DEMOSTRACION` y `NO_NOVEDOSO_redundante` es el valor inicial de diseño (0.5). Fue propuesto para ser calibrado contra los pares T07, T08 y T09, pero la calibración está bloqueada: T07 está exactamente en la frontera (distancia = 0.50), T08 es correctamente clasificado (0.7222), y T09 tiene intersección vacía por un fallo de extracción. Las distancias se reportan crudas donde es posible; donde no, el veredicto es `INCONCLUSIVE`.

<!-- fuente: docs/PROJECT_STATE.md decisión θ=0.5 sin calibrar, docs/dimensions_facts.md θ=0.5 -->

**L16. D3 informal es experimental.** El puente "match en C_I, descargar fuente del paper, formalizar su prueba, extraer premisas, comparar con D3" se implementó como prueba de concepto en `src/novelty_v2/informal_match.py` pero no tiene tasa de éxito medida. La formalización de pruebas ajenas, necesaria para este camino, tuvo 0% de éxito en el PoC actual con DeepSeek V4 Pro. Reportamos esta capacidad como dirección de investigación, no como resultado.

<!-- fuente: docs/PROJECT_STATE.md D3 sobre C_I es PoC, paper/PAPER_BRIEF.md D3 informal experimental -->

**L17. El withdrawal comment como ground truth es un proxy imperfecto.** El experimento con papers retirados asume que el comentario de retiro del autor es evidencia confiable de duplicación. La auditoría de Run 002 encontró que 3 de 5 papers de control tenían problemas de fidelidad de formalización (definiciones placeholder, equivalencias truncadas a una dirección, teoremas trivializados). Esto sugiere que la calidad del ground truth no es uniforme incluso entre papers no retirados. Para los retirados, 12 de 26 citan explícitamente el trabajo previo que los duplica; los 14 restantes usan frases genéricas ("already known") sin especificar la fuente.

<!-- fuente: docs/retracted_dataset_report.md 12 citan explícitamente, docs/run_002_verdicts.md problemas de fidelidad -->

## 6.4 Síntesis

Las limitaciones de AViD v1 trazan un perímetro claro. El sistema funciona sobre el subconjunto de teoremas que (a) son expresables en el fragmento `Prop` de Lean 4, (b) tienen un enunciado parseable por el extractor de LaTeX, (c) son formalizables por al menos uno de los modelos del backend, y (d) tienen premisas extraíbles por `ExtractData.lean`. Dentro de ese perímetro, el árbol de decisión D2-D1-D3 produce veredictos con grounding verificable. Fuera de él, el sistema es explícitamente incompleto. La sección 7 detalla qué queda por construir para expandir ese perímetro.

<!-- fuente: paper/limitations.md (compilación) -->
