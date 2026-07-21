# 2. Trabajo relacionado

El problema de determinar si un teorema es nuevo toca cuatro frentes de investigación que rara vez se cruzan. Esta sección los recorre en orden, desde la infraestructura de búsqueda hasta la novedad bibliométrica, y cierra con una tabla de posicionamiento.

<!-- fuente: paper/PAPER_BRIEF.md §2 (4 frentes), paper/bibliography_merged.md (referencias) -->

## 2.1 Buscadores e infraestructura de teoremas

El frente más concurrido es el de los motores de búsqueda de teoremas. **TheoremSearch** (Ilin, Alper, Inchiostro, arXiv:2602.05216) indexa 9.2 millones de enunciados extraídos de arXiv y siete fuentes adicionales. Genera un "slogan" en lenguaje natural por teorema para embeber y expone una API pública sin autenticación. Su motivación documentada (retiros por duplicación en arXiv) es exactamente la misma que motiva nuestro experimento con papers retirados. TheoremSearch encuentra enunciados similares; AViD agrega la capa de veredicto.

<!-- fuente: paper/bibliography_merged.md A1 (TheoremSearch, 9.2M, API pública) -->

**TheoremGraph + LeanGraph** (arXiv:2606.25363 [VERIFICAR]) construye un grafo unificado formal-informal con 11.7 millones de entornos tipo-teorema de arXiv y 18.3 millones de dependencias candidatas. Su componente LeanGraph abarca 388,105 nodos y 11.3 millones de aristas tipadas sobre 25 proyectos Lean. Es el competidor más cercano en infraestructura: ellos construyen el grafo; nosotros emitimos veredictos de novedad sobre él.

<!-- fuente: paper/bibliography_merged.md A2 (TheoremGraph + LeanGraph) -->

**COMPOSE** (arXiv:2605.30333 [VERIFICAR]) predice teoremas futuros a partir de la estructura de citas y la estructura formal. La dirección es complementaria: COMPOSE genera hacia adelante; AViD verifica hacia atrás.

<!-- fuente: paper/bibliography_merged.md A3 (COMPOSE) -->

El espacio de buscadores de Mathlib está saturado. **Loogle** [VERIFICAR], **LeanSearch** [VERIFICAR], **LeanExplore** (backend de Leandex) [VERIFICAR], y **Lean Finder / LeanStateSearch** [VERIFICAR] ofrecen búsqueda por patrón, por lenguaje natural, y por estado de prueba. AViD no compite en este espacio: consume estas herramientas como infraestructura (Leandex es el backend de D1 C_F) y agrega la capa de decisión automatizada que ninguna de ellas ofrece.

<!-- fuente: paper/bibliography_merged.md D1-D4 (buscadores de Mathlib) -->

**Matlas** (arXiv:2604.17484) extrae 8.07 millones de enunciados de 435,000 artículos revisados por pares que abarcan de 1826 a 2025, provenientes de 180 revistas seleccionadas por criterio de citación ICM, más 1,900 libros de texto. Su motivación explícita, construir un motor de búsqueda de teoremas sobre fuentes con verificación editorial, es complementaria a la de AViD: donde TheoremSearch cubre arXiv (desde 1991), Matlas cubre revistas peer-reviewed hasta 1826. Un survey reciente sobre IA matemática (arXiv:2601.13209) cita a ambos como infraestructura para determinar si un resultado ya es conocido, posicionando el problema de AViD como reconocido por el campo.

<!-- fuente: paper/bibliography_merged.md B2 (Matlas) -->

## 2.2 Generación de conjeturas con filtros de novedad

**Kasaura et al.** (arXiv:2509.14274) definen novedad como ausencia en Mathlib, en la librería generada durante la sesión, y en una lista manual del conjeturador. Es el baseline ingenuo que AViD corrige: sin filtro de trivialidad (D2), un teorema como "la suma de cuatro pares es par" se marcaría como nuevo; sin distancia estructural (D3), dos pruebas distintas del mismo enunciado serían indistinguibles.

<!-- fuente: paper/bibliography_merged.md §1 (Kasaura et al.), paper/PAPER_BRIEF.md §1 (baseline ingenuo) -->

**LeanConjecturer** (arXiv:2506.22005) filtra novedad con `exact?` contra Mathlib y no-trivialidad con `aesop`. El sistema generó 12,289 conjeturas desde 40 archivos semilla de Mathlib, de las cuales 3,776 resultaron sintácticamente válidas y no triviales (donde "no trivial" significa que `aesop` no las cierra). Estos son exactamente los mecanismos que AViD implementa como D1 (exact? como fallback de C_F) y D2 (aesop en el conjunto T_AUTO). La contribución de AViD no es inventar estos filtros sino integrarlos en un árbol de decisión de tres dimensiones que emite un veredicto, agregar D3 (distancia de premisas) y D1 informal (arXiv + TheoremSearch), y evaluar contra ground truth real.

<!-- fuente: paper/bibliography_merged.md B1 (LeanConjecturer) -->

**Mining Math Conjectures** (arXiv:2412.16177) ataca el problema inverso (redundancia en conjeturas generadas por LLMs) con pruning heurístico, sin métrica formal. **Synthetic Theorem Generation** (OpenReview EeDSMy5Ruj) genera teoremas por forward-reasoning desde estados de prueba existentes. Ambos son referencias conceptuales que ilustran la necesidad de filtros de novedad en pipelines de generación.

<!-- fuente: paper/bibliography_merged.md §3 (generación sintética) -->

## 2.3 Identidad y similitud de demostraciones

La distancia de Jaccard sobre conjuntos de premisas que AViD usa en D3 tiene una genealogía precisa en la literatura de premise selection. **Kaliszyk y Urban** (línea MaSh/Flyspeck, circa 2013-2015 [VERIFICAR]) usaron k-NN con features ponderadas por IDF para seleccionar premisas relevantes durante la demostración automática. AViD toma esa misma herramienta y la reposiciona: en lugar de usarla como input para construir pruebas, la usa como huella para comparar pruebas ya construidas. Sin esta cita, D3 parece TF-IDF redescubierto; con ella, es la aplicación legítima de una técnica establecida a un problema nuevo.

<!-- fuente: paper/bibliography_merged.md C1 (Kaliszyk & Urban, genealogy of D3) -->

**Magnushammer** (Mikuła, Jiang, Li et al., ICLR 2024 [PENDIENTE completar]) aplica premise selection con transformers, alcanzando 59.5% de precisión en PISA contra 38.3% de Sledgehammer. **Piotrowski et al.** (arXiv:2304.00994) introducen un "math filter" que preserva solo lemas de naturaleza claramente matemática usando nombres de teoremas de Mathlib como whitelist. AViD sigue exactamente esa receta en sus filtros previos al Jaccard.

<!-- fuente: paper/bibliography_merged.md §5 (premise selection) -->

**The Network Structure of Mathlib** (arXiv:2604.24797 [VERIFICAR]) analiza el grafo de 308,129 declaraciones y 8.4 millones de aristas de Mathlib. Su hallazgo principal es que la centralidad de red captura infraestructura del lenguaje (tipo `Nat`, `Eq`, `List`) más que relevancia matemática. Este hallazgo justifica el Filtro 1 de D3: cuando AViD elimina premisas de los namespaces `Init.` y `Lean.` antes de calcular Jaccard, no aplica una heurística ad-hoc sino un filtro respaldado por evidencia publicada.

<!-- fuente: paper/bibliography_merged.md C2 (Network Structure of Mathlib) -->

**Yoo** (Axiom-Based Atlas, arXiv:2504.00063) representa teoremas como proof vectors sobre sistemas de axiomas y los compara con similitud coseno, distancia euclidiana o Jaccard. Es el trabajo más cercano en herramienta conceptual, pero con propósito opuesto: el Atlas organiza teoremas por similitud estructural; AViD usa esa similitud para decidir si una prueba es redundante.

<!-- fuente: paper/bibliography_merged.md §1 (Yoo / Atlas) -->

**Huch** (arXiv:2209.13305) documenta la distribución scale-free del grado de entrada en el AFP, relevante para trabajo futuro con premisas ponderadas por IDF.

<!-- fuente: paper/bibliography_merged.md §6 (Huch) -->

## 2.4 Novedad bibliométrica y verificación

**Pseudo-Formalization / ArxivMathGradingBench** [VERIFICAR] verifica la corrección de pruebas de arXiv mediante formalización. Es el vecino exacto de AViD en el espacio de diseño: ellos verifican corrección; nosotros verificamos novedad. Un sistema completo de revisión automatizada requeriría ambas dimensiones.

<!-- fuente: paper/bibliography_merged.md B3 (Pseudo-Formalization) -->

**MerLean** [VERIFICAR] es un pipeline paper-to-Lean que deja la verificación de novedad a revisores humanos. AViD es explícitamente la capa que MerLean delega.

<!-- fuente: paper/bibliography_merged.md B4 (MerLean) -->

**First Proof** (Abouzaid et al., arXiv:2602.05192) documenta el modo de falla que motiva este trabajo: once matemáticos diseñaron un examen con problemas no publicados, y los LLMs "tienen tendencia a encontrar pruebas existentes y olvidadas en lo profundo de la literatura matemática y presentarlas como originales". Su diagnóstico ("lo que nos falta es una manera sistemática de evaluar si esos lemas pueden ensamblarse en una prueba novedosa") es la pregunta que AViD intenta responder.

<!-- fuente: paper/bibliography_merged.md §1 (First Proof) -->

En el frente bibliométrico, **Uzzi et al.** (Science, 2013) miden novedad como combinaciones atípicas de revistas citadas sobre 17.9 millones de artículos. **Wang, Veugelers y Stephan** (2017) [PENDIENTE completar] y **Boyack y Klavans** (2014) [PENDIENTE completar] refinan la metodología. Estos trabajos operan a nivel de paper completo y no miran contenido deductivo; son el campo adyacente que AViD no alcanza pero señala como complementario.

<!-- fuente: paper/bibliography_merged.md §4 (novedad bibliométrica) -->

## 2.5 Tabla de posicionamiento

| Sistema | ¿Chequea existencia? | ¿Filtra trivialidad? | ¿Mide distancia de prueba? | ¿Corpus informal? | ¿Emite veredicto? |
|---|---|---|---|---|---|
| Kasaura et al. | ✅ (solo Mathlib) | ❌ | ❌ | ❌ | ❌ (sí/no) |
| LeanConjecturer [VERIFICAR] | ✅ (exact?) | ✅ (aesop) | ❌ | ❌ | ❌ |
| TheoremSearch | ✅ (9.2M) | ❌ | ❌ | ✅ | ❌ |
| Atlas (Yoo) | ❌ | ❌ | ✅ (Jaccard) | ❌ | ❌ |
| COMPOSE [VERIFICAR] | Predice forward | ❌ | ❌ | ✅ | ❌ |
| **AViD** | ✅ (Mathlib + arXiv + TheoremSearch) | ✅ (6 tácticas + blacklist) | ✅ (Jaccard + 2 filtros) | ✅ | ✅ (8 veredictos) |

<!-- fuente: paper/PAPER_BRIEF.md §2 (tabla de posicionamiento), paper/bibliography_merged.md -->

La diferencia no está en ninguna celda individual sino en la columna completa: los trabajos previos construyen piezas de infraestructura (búsqueda, formalización, similitud); AViD las ensambla en un pipeline que recibe un paper en LaTeX y devuelve un veredicto de novedad con grounding formal.

<!-- fuente: paper/PAPER_BRIEF.md (tesis del paper) -->
