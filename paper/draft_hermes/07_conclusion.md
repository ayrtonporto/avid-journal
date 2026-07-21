# Conclusión

Este artículo presentó AViD Journal: un pipeline que recibe un artículo en LaTeX, lo formaliza en Lean 4, y aplica un árbol de decisión en tres dimensiones para emitir un veredicto de novedad con grounding formal. La contribución central es la estructura del sistema, no la magnitud de los resultados experimentales. Ambos se reportan con el mismo nivel de detalle.

<!-- fuente: paper/PAPER_BRIEF.md (tesis del paper) -->

## 7.1 Lo construido

El pipeline integra cinco componentes que, combinados, cubren el recorrido completo desde el fuente LaTeX hasta el veredicto:

1. **Parser de LaTeX** que extrae bloques matemáticos (teoremas, lemas, definiciones) y construye un grafo de dependencias para determinar el orden de formalización.

2. **Capa de formalización multi-modelo** con ocho backends (Claude Code, Anthropic, OpenAI, DeepSeek, OpenRouter, Mistral, Gemini, y OpenCode Go como default), criterio de éxito exigente (sin errores, sin `sorry`, con declaración sustantiva), y proyecto Lean 4 compartido con Mathlib v4.29.0 (8,247 archivos `.olean`).

3. **Tres corpus de referencia**: Mathlib v4.29.0 vía Leandex (formal), arXiv + Semantic Scholar + TheoremSearch con LLM judge (informal), y el corpus propio del paper vía `PAPER_INDEX.md`.

4. **Tres dimensiones de novedad**: D1 (no-existencia previa, ramas formal e informal con cortocircuito), D2 (no-trivialidad, 6 tácticas con presupuestos y blacklist para `norm_num`), D3 (distancia de Jaccard sobre premisas con dos filtros, umbral theta = 0.5).

5. **Árbol de decisión** que compone las tres dimensiones en ocho veredictos, recorriendo las evaluaciones en orden de costo creciente: D2 (local, segundos), D1 C_F (API rápida), D1 C_I (múltiples APIs + LLM judge), D3 (extracción de premisas + Jaccard).

<!-- fuente: docs/PROJECT_STATE.md §1, docs/section3_facts.md §3-5 -->

El sistema corre sobre Windows 10 nativo. Toda la infraestructura de extracción de premisas (D3) funciona sin requerir WSL ni Docker. El código está disponible en `github.com/ayrtonporto/avid-journal`.

<!-- fuente: docs/PROJECT_STATE.md entorno, paper/PAPER_BRIEF.md §7 artefacto público -->

## 7.2 Lo medido

Los experimentos, reportados como preliminares en todos los casos, produjeron tres tipos de evidencia:

**Evidencia de funcionamiento.** El pipeline corre de extremo a extremo. Formalizó 7 de 10 papers en el estudio profundo (Run 002). Sobre los 4 retirados con formalización fiel, el pipeline detectó la no-novedad en 1 caso (Paper 2, vía D1 C_I) y produjo 3 falsos negativos (Papers 1, 3, 4), atribuibles al punto ciego temporal del corpus (L14). Los 3 controles evaluados tuvieron formalizaciones no fieles, por lo que el experimento no aporta evidencia sobre falsos positivos. D2 acertó en 22 de 24 teoremas del eval set (91.7%), excluyendo 2 casos con expectativa ambigua (T19 y T22). D1 C_F encontró los 18 teoremas no triviales que alcanzaron esa etapa, aunque esta cobertura está determinada por la composición del eval set (dominado por teoremas clásicos ya en Mathlib) y por la ausencia de umbral en Leandex v2. D3 produjo distancias consistentes con el juicio humano en 2 de los 3 pares calibrados (T08 y T09), con T07 como punto degenerado (unión = 2 premisas).

**Evidencia de límites.** El wide study v2 (37 papers evaluables) no encontró diferencia estadísticamente significativa entre papers retirados y controles en la similitud semántica de enunciados (Mann-Whitney p = 0.854). El punto ciego temporal del corpus impide encontrar duplicadores anteriores a 1991 (caso Hardy & Littlewood). La rama D1 informal, en su configuración actual con threshold MiniLM de 0.40, no se activa para ningún teorema del eval set. La auditoría de fidelidad de formalización reveló una asimetría preocupante: 4/4 papers retirados resultaron fieles contra 0/3 controles.

**Evidencia metodológica.** La construcción del dataset de 26 papers retirados viables (de 33 candidatos), con 52 controles emparejados por categoría y año, establece un benchmark reusable. La comparación de cuatro modelos de formalización (Qwen 3.7-max 5/5, GLM-5.2 3/5, DeepSeek Pro 0/5, DeepSeek Flash 0/5) cuantifica la viabilidad relativa de distintos backends. Los defectos metodológicos del wide study v1 (self-matches por falta de auto-exclusión, 38/52 papers sin scores) quedan documentados como advertencia para trabajos futuros que usen TheoremSearch como fuente.

<!-- fuente: docs/wide_study_v2_closeout.md, docs/run_002_verdicts.md, results/experiment_run_002.csv, results/d3_validation.csv, docs/model_comparison_001c.md -->

## 7.3 Lo pendiente

El trabajo futuro se organiza en tres frentes:

**Mejoras de la métrica.**
- **F1:** Premisas ponderadas por IDF usando la distribución scale-free del AFP (Huch, arXiv:2209.13305).
- **F2:** Distancia sobre grafos de dependencia completos, no solo conjuntos de premisas.
- **F3:** `isDefEq` para D1 nivel 1 (equivalencia definicional, más allá de la igualdad sintáctica actual).

**Expansión experimental.**
- **F4:** Corrida del pipeline completo (D1+D2+D3) sobre Mathlib completo (~1.9 millones de líneas).
- **F5:** Benchmark sobre un corpus arXiv autoformalizado, análogo al enfoque de ArxivMathGradingBench.
- **F6:** Re-ejecución del wide study con el dataset ampliado a los 26 retirados viables y exploración de thresholds alternativos para MiniLM con medición propia de recall y precisión.

**Infraestructura.**
- **F7:** Múltiples modelos de autoformalización en paralelo (Numina, Axiom, Kimina, ProofFlow) para reducir la dependencia de un solo proveedor.
- **F8:** Demo web (Gradio + Hugging Face Spaces) con pipeline D1+D2 en tiempo real y D3 a pedido.
- **F9:** Integración con TheoremGraph + LeanGraph (arXiv:2606.25363 [VERIFICAR]) para heredar su grafo unificado formal-informal como corpus de D1 y D3.
- **F10:** Publicación del dataset de papers retirados como benchmark comunitario para verificación de novedad.
- **F11:** Integración de Matlas (arXiv:2604.17484) como segundo proveedor de C_I, cerrando el punto ciego temporal anterior a 1991 (L14). Su corpus de 8.07 millones de enunciados de revistas peer-reviewed (1826-2025) complementa el horizonte arXiv de TheoremSearch.

<!-- fuente: paper/PAPER_BRIEF.md §7 (future work), paper/bibliography_merged.md, docs/PROJECT_STATE.md pendientes -->

## 7.4 Cierre

AViD Journal no es un sistema que resuelva el problema de la novedad automática. Es un sistema que lo plantea de manera operacional, lo implementa, lo mide, y documenta exactamente dónde falla. Esa documentación de los límites (las 17 limitaciones de la sección 6, el resultado negativo del wide study, la asimetría de fidelidad en Run 002) es tan parte de la contribución como el pipeline mismo.

La tesis del paper es que la pregunta "¿se puede arbitrar novedad automáticamente?" no se responde con un diseño de métrica ni con un argumento de arquitectura. Se responde construyendo el sistema, corriéndolo contra ground truth real, y reportando qué funcionó y qué no. Eso es lo que este artículo hace.

<!-- fuente: paper/PAPER_BRIEF.md (espina narrativa, tesis del paper) -->
