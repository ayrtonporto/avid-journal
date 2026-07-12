# AViD Journal — Dossier bibliográfico y de hallazgos

**Generado:** 2026-07-12  
**Propósito:** Compilación de lectura de todo trabajo previo mencionado en el repositorio e inventario de hallazgos con fuente interna, para la fase de escritura del paper.  
**Regla:** Solo lectura. Cero interpretación nueva. Todo lo que sigue está extraído de los archivos del repo con su ubicación exacta.

---

# PARTE 1 — Barrido de referencias

## 1. Competidores directos / baselines

### Kasaura et al. — *Discovering New Theorems via LLMs with In-Context Proof Learning in Lean*
- **arXiv:** 2509.14274 (sept 2025)
- **Mencionado en:** `paper/related_work.md:11-12`, `paper/metric_spec.md:22`, `IDEA.md:40`, `paper/CLAUDE_CODE_BRIEFING.md` (implícito vía baseline)
- **Qué se afirma:** *"Generan teoremas nuevos con un Conjecturing-Proving Loop. Definen novedad como: 'la conjetura no está ya en Mathlib4, ni en la librería generada, ni en la lista del conjeturador'. Es decir, novedad = no-presencia, sin filtro de trivialidad ni distancia estructural."* (`paper/related_work.md:12`)
- **Rol en nuestro paper:** **Competidor directo / baseline que AViD supera.** Es el baseline ingenuo que AViD corrige con D2 (trivialidad) y D3 (distancia estructural).

### Yoo — *The Axiom-Based Atlas*
- **arXiv:** 2504.00063 (abril 2025)
- **Mencionado en:** `paper/related_work.md:63-66,120-121`, `paper/metric_spec.md:82`
- **Qué se afirma:** *"Competidor más cercano a vigilar. Representa teoremas como proof vectors sobre sistemas de axiomas fundacionales. [...] Compara con similitud coseno, distancia euclidiana o índice de Jaccard."* (`paper/related_work.md:64`). *"AViD no es 'el Atlas con otro nombre' porque (a) el propósito es novelty-checking activo, no organización, y (b) el alcance del corpus incluye literatura informal vía autoformalización."* (`paper/related_work.md:121`)
- **Rol en nuestro paper:** **Competidor cercano.** Misma herramienta conceptual (Jaccard sobre vectores de axiomas/premisas), propósito distinto. Hay que posicionarse explícitamente.

### Abouzaid et al. — *First Proof*
- **arXiv:** 2602.05192 (febrero 2026)
- **Mencionado en:** `paper/related_work.md:22-25`, `paper/metric_spec.md:22`, `paper/preprint/draft.md:25-27`, `IDEA.md:35-37`
- **Qué se afirma:** *"Once matemáticos de primer nivel [...] lanzaron un examen de matemática para AI con problemas no publicados. [...] 'los LLMs tienen tendencia a encontrar pruebas existentes y olvidadas en lo profundo de la literatura matemática y presentarlas como originales'"* (`paper/related_work.md:23`). *"First Proof testea sus preguntas en LLMs para asegurar que ninguna respuesta exista en datos de entrenamiento."* Cita motivante: *"lo que nos falta es una manera sistemática de evaluar si esos lemas pueden ensamblarse en una prueba novedosa"* (`paper/related_work.md:25`).
- **Rol en nuestro paper:** **Motivación externa del problema.** Documenta que el modo de falla existe y es urgente. La cita de SecZine es casi la definición de AViD.

## 2. Generación sintética / conjecturing con LLMs

### *Synthetic Theorem Generation in Lean*
- **Identificador:** OpenReview EeDSMy5Ruj (sin arXiv ID explícito en el repo)
- **Mencionado en:** `paper/related_work.md:14-15`
- **Qué se afirma:** *"Generación sintética de teoremas por forward-reasoning desde estados de prueba existentes."*
- **Rol:** **Referencia conceptual.** Trabajo relacionado en generación sintética.

### *Mining Math Conjectures from LLMs: A Pruning Approach*
- **arXiv:** 2412.16177
- **Mencionado en:** `paper/related_work.md:17-18`
- **Qué se afirma:** *"Reportan el problema inverso: redundancia en conjeturas generadas, 'GPT-4 usualmente produce el mismo tipo de lemas genéricos cada vez'. Atacan con pruning heurístico, no con métrica formal."*
- **Rol:** **Referencia conceptual.** Documenta el problema de redundancia que AViD ataca con métrica formal.

## 3. Novedad bibliométrica

### Uzzi, Mukherjee, Stringer, Jones — *Atypical Combinations and Scientific Impact*
- **Identificador:** Science (2013). Sin arXiv ID en el repo.
- **Mencionado en:** `paper/related_work.md:29-30`
- **Qué se afirma:** *"17.9 millones de artículos analizados. [...] Miden novedad como combinaciones atípicas de revistas citadas."*
- **Rol:** **Referencia conceptual — campo adyacente que no alcanza.** Mide novedad externamente (citaciones), nunca mira contenido deductivo.

### Wang, Veugelers, Stephan (2017)
- **Identificador:** Sin arXiv ID en el repo. [PENDIENTE completar]
- **Mencionado en:** `paper/related_work.md:32`
- **Qué se afirma:** *"Novedad como primera aparición de una combinación de conocimientos en Web of Science."*
- **Rol:** **Referencia conceptual — campo adyacente.**

### Boyack & Klavans (2014)
- **Identificador:** Sin arXiv ID en el repo. [PENDIENTE completar]
- **Mencionado en:** `paper/related_work.md:34`
- **Qué se afirma:** *"Crítica: los indicadores de Uzzi están confundidos por efectos disciplinarios."*
- **Rol:** **Referencia de crítica metodológica.**

### *Measuring novelty in science with word embedding*
- **Identificador:** PLOS ONE (corrección 2026). Sin arXiv ID en el repo.
- **Mencionado en:** `paper/related_work.md:36-37`
- **Qué se afirma:** *"Validación de medidas bibliométricas de novedad con embeddings de título/abstract/keyword."*
- **Rol:** **Referencia conceptual — campo adyacente.**

## 4. Premise selection

### Sledgehammer (Paulson y Blanchette, línea Isabelle)
- **Identificador:** Sin identificador específico en el repo. Mecanismo clásico.
- **Mencionado en:** `paper/related_work.md:43`
- **Rol:** **Infraestructura de referencia.** Mecanismo clásico de premise selection.

### MePo (Meng-Paulson) y MaSh
- **Identificador:** Sin identificadores específicos en el repo.
- **Mencionado en:** `paper/related_work.md:45`
- **Rol:** **Precedente.** Heurísticas y ML temprano para premise selection.

### DeepMath (Google, 2016)
- **Identificador:** Sin identificador específico en el repo.
- **Mencionado en:** `paper/related_work.md:47`
- **Rol:** **Precedente.** Primer uso serio de deep learning para premise selection.

### Mikuła, Jiang, Wenda Li et al. — *Magnushammer*
- **Identificador:** ICLR 2024. Sin arXiv ID en el repo.
- **Mencionado en:** `paper/related_work.md:49-50`, `paper/metric_spec.md:69`, `paper/decisions.md:112`, `paper/future_work.md:238` (Q1)
- **Qué se afirma:** *"Premise selection con entrenamiento contrastivo y transformers que supera a Sledgehammer, logrando 59.5% contra 38.3% en PISA y 34.0% contra 20.9% en miniF2F. Wenda Li es coautor — citarlo bien es hablar su idioma."* (`paper/related_work.md:50`)
- **Rol:** **Infraestructura usada / precedente.** AViD usa premise selection en dirección inversa (extraer premisas como huella, no para construir pruebas). Conexión directa con Wenda Li (supervisor PhD target).

### Piotrowski et al. — *Machine-Learned Premise Selection for Lean*
- **arXiv:** 2304.00994
- **Mencionado en:** `paper/related_work.md:52-53`, `paper/metric_spec.md:69,71`, `paper/decisions.md:112`
- **Qué se afirma:** *"Crítico para implementación de AViD. Muestra cómo 'tomar una prueba en Lean como string y listar las premisas que aparecen ahí' e introduce un math filter que 'preserva solo lemas de naturaleza claramente matemática, descartando los básicos y técnicos, usando los nombres de teoremas y definiciones de mathlib como whitelist'."* (`paper/related_work.md:53`)
- **Rol:** **Infraestructura usada.** La receta de math filter de AViD sigue exactamente este paper.

### Piotrowski & Urban — *Stateful premise selection*
- **Identificador:** Sin identificador específico en el repo. [PENDIENTE completar]
- **Mencionado en:** `paper/related_work.md:55`
- **Rol:** **Precedente.** Iteración sobre estado de prueba.

### ReProver / LeanDojo (Yang et al.)
- **Identificador:** Sin identificador específico en el repo (el paper de LeanDojo).
- **Mencionado en:** `paper/related_work.md:57`, `paper/decisions.md:101-114`
- **Rol:** **Infraestructura usada.** Retrieval-augmented theorem proving. AViD usa LeanDojo v1 para extracción de premisas en D3.

## 5. Estructura de pruebas, grafos de dependencia y similitud

### Aspinall et al. — *Towards Formal Proof Metrics*
- **Identificador:** Springer. Sin DOI/ISBN en el repo.
- **Mencionado en:** `paper/related_work.md:68-69`
- **Rol:** **Referencia conceptual.** Métricas de prueba por analogía con métricas de software.

### Huch — *Structure in Theorem Proving*
- **arXiv:** 2209.13305
- **Mencionado en:** `paper/related_work.md:71-72`, `paper/metric_spec.md:81`, `paper/limitations.md:17` (L2)
- **Qué se afirma:** *"Analiza el grafo de dependencias del Archive of Formal Proofs. Encuentra distribución scale-free del grado de entrada."*
- **Rol:** **Referencia conceptual.** Útil para pesar premisas por rareza (IDF). Trabajo futuro.

### *Dependency Graphs for Interactive Theorem Provers*
- **Identificador:** Sin identificador específico en el repo. [PENDIENTE completar]
- **Mencionado en:** `paper/related_work.md:74`
- **Rol:** **Referencia conceptual.**

### *Supporting Maintenance of Formal Mathematics with Similarity Search*
- **Identificador:** Springer 2024. Sin DOI/ISBN en el repo.
- **Mencionado en:** `paper/related_work.md:76-77`
- **Rol:** **Referencia conceptual.** Detección de clones en pruebas formales.

### *Metrics for Graph Comparison: A Practitioner's Guide*
- **Identificador:** PLOS One. Sin DOI en el repo.
- **Mencionado en:** `paper/related_work.md:79-80`, `paper/metric_spec.md:81`, `paper/future_work.md:15` (F2)
- **Rol:** **Referencia conceptual.** Menú de distancias entre grafos para ir más allá de Jaccard.

## 6. Autoformalización

### Wu et al. — *Autoformalization with Large Language Models*
- **Identificador:** NeurIPS 2022. Sin arXiv ID en el repo.
- **Mencionado en:** `paper/related_work.md:84`
- **Qué se afirma:** *"Paper fundacional."*
- **Rol:** **Precedente fundacional.**

### ProofFlow (Huawei AI4Math)
- **arXiv:** 2510.15981
- **Mencionado en:** `paper/related_work.md:86-87`, `paper/metric_spec.md:51`
- **Qué se afirma:** *"Enfoque de grafo de dependencias con lemas intermedios para preservar la estructura lógica. Introduce PROOFSCORE, métrica compuesta para evaluar corrección sintáctica, fidelidad semántica y fidelidad estructural."*
- **Rol:** **Precedente / punto débil.** La autoformalización es el eslabón frágil de AViD; ProofFlow muestra que la comunidad ya reconoce el problema.

### Aria
- **arXiv:** 2510.04520
- **Mencionado en:** `paper/related_work.md:89-90`, `paper/metric_spec.md:51`
- **Qué se afirma:** *"Los LLMs generan código inválido con funciones inexistentes en Mathlib o incompatibles con toolchains que evolucionan rápido."*
- **Rol:** **Precedente.** Documenta la fragilidad de la autoformalización — riesgo del paso de traducción de AViD.

### *Conjecturing: An Overlooked Step in Formal Mathematical Reasoning*
- **arXiv:** 2510.11986
- **Mencionado en:** `paper/related_work.md:92-93`
- **Qué se afirma:** *"'El desempeño de autoformalización está sustancialmente sobreestimado cuando se tiene en cuenta la conjetura'. Tratar el conjeturar como tarea independiente."*
- **Rol:** **Referencia conceptual.**

### Patel — *A New Approach Towards Autoformalization*
- **arXiv:** 2310.07957
- **Mencionado en:** `paper/related_work.md:95`
- **Rol:** **Precedente.** LLMs para formalización con few-shot.

## 7. Herramientas e infraestructura

### TheoremSearch
- **Identificador:** API pública en `https://api.theoremsearch.com/search`. Dataset HuggingFace: `uw-math-ai/TheoremSearch`.
- **Mencionado en:** `docs/scout_theoremsearch.md` (completo), `docs/scout_d3_informal.md`, `docs/experiment_run_001_report.md`, `docs/run_001_review.md`, `docs/selection_dossier.md`
- **Qué se afirma:** *"9.2M teoremas"* (implícito vía dataset size en `docs/scout_theoremsearch.md:151`). API sin key, endpoint REST. Similarity score directo. Fuente de D1-informal (C_I Stage A). *"TheoremSearch no siempre devuelve un paper_id con formato arXiv."* (`docs/scout_theoremsearch.md:93`)
- **Rol:** **Infraestructura usada.** Fuente terciaria de C_I.

### WithdrarXiv (Rao, Young, Dietterich, Callison-Burch)
- **arXiv:** 2412.03775
- **Mencionado en:** `docs/retracted_dataset_report.md:13-20`
- **Qué se afirma:** *"~14,000 preprints retirados de arXiv con taxonomía de 10 categorías de motivos de retiro. Disponible en HuggingFace como darpa-scify/withdrarxiv (17.2 MB, Apache 2.0) pero es gated."* (`docs/retracted_dataset_report.md:13-16`)
- **Rol:** **Dataset de referencia.** Fuente original del experimento de papers retirados (aunque AViD usó Plan B: arXiv API directa por el gating).

### LeanDojo v1 / v2 (Yang et al.)
- **Identificador:** `lean-dojo` (PyPI, v1), `lean-dojo-v2` (PyPI, v2). Paper asociado sin arXiv ID en el repo.
- **Mencionado en:** `paper/decisions.md:101-114`, `paper/metric_spec.md:71`, `CLAUDE.md`, `docs/scout_d3*.md`, `paper/results_log.md` (Día 3, Día 7)
- **Qué se afirma:** *"LeanDojo v1 y LeanDojo-v2 NO son versiones de la misma herramienta — son herramientas con propósitos completamente distintos."* (`paper/decisions.md:105`). *"LeanDojo traza dependencias transitivas, no solo archivos del proyecto."* (`paper/decisions.md:129-130`). v1 para extracción de premisas (D3), v2 para agentes de prueba (future work).
- **Rol:** **Infraestructura usada.** D3 usa LeanDojo v1 (o ExtractData standalone como alternativa Windows).

### Leandex (aka LeanExplore)
- **Identificador:** API HTTP. Variable `LEAN_LEANDEX_API_KEY`.
- **Mencionado en:** `vendor/numina-lean-agent/skills/search/reference-leanexplore.md`, `paper/results_log.md:197`, `src/novelty/mathlib_checker.py` (CLAUDE.md referencia), `IDEA.md:58`
- **Qué se afirma:** *"API v2 sin scores. Similarity sintética 1.0/0.9/... por orden de resultado."* (`paper/results_log.md:197`). *"Leandex API v2: reescrito _extract_matches() para el nuevo formato sin scores."* (`paper/results_log.md:197`)
- **Rol:** **Infraestructura usada.** Backend de D1 sobre C_F (búsqueda en Mathlib).

### Loogle
- **Identificador:** Herramienta CLI en Numina-Lean-Agent.
- **Mencionado en:** `vendor/numina-lean-agent/skills/search/reference-loogle.md`
- **Rol:** **Herramienta auxiliar.** Búsqueda por patrón en Mathlib (no usada directamente por AViD, presente en el vendor).

### LeanSearch
- **Identificador:** Herramienta CLI en Numina-Lean-Agent.
- **Mencionado en:** `vendor/numina-lean-agent/skills/search/reference-leansearch.md`
- **Rol:** **Herramienta auxiliar.** Búsqueda NL + Lean terms.

### LeanFinder
- **Identificador:** Herramienta CLI en Numina-Lean-Agent.
- **Mencionado en:** `vendor/numina-lean-agent/skills/search/reference-leanfinder.md`
- **Rol:** **Herramienta auxiliar.** Búsqueda semántica en Mathlib.

### Numina-Lean-Agent
- **Identificador:** Vendored en `vendor/numina-lean-agent/`. Repo externo.
- **Mencionado en:** `docs/CONTEXT.md:15`, `docs/PROGRESS.md:58,70`, `CLAUDE.md:16`
- **Qué se afirma:** *"Unlike Numina-Lean-Agent, AViD uses one agent (the Sketch Agent) that formalizes statement and proof together."* (`docs/CONTEXT.md:15`)
- **Rol:** **Infraestructura usada / inspiración.** AViD hereda el patrón coordinator/blueprint/sketch pero con un solo agente. Runtime scripts vendored.

### MerLean
- **Identificador:** Sin arXiv ID ni URL en el repo.
- **Mencionado en:** `README.md:227`, `docs/ARCHITECTURE.md:381-382`
- **Qué se afirma:** *"Inspiration for autoformalization pipeline"* (`README.md:227`). *"MerLean doesn't have novelty detection. We add that layer."* (`docs/ARCHITECTURE.md:382`)
- **Rol:** **Inspiración.** No es competidor — AViD agrega la capa de novedad.

### Semantic Scholar API
- **Identificador:** API pública (`api.semanticscholar.org`).
- **Mencionado en:** `paper/results_log.md:175`, `src/novelty/arxiv_search.py` (vía CLAUDE.md), `IDEA.md:62`
- **Rol:** **Infraestructura usada.** Fuente de D1 sobre C_I (Stage A, búsqueda de candidatos).

### ExtractData.lean
- **Identificador:** Archivo custom de 515 líneas en `lean_project/ExtractData.lean`.
- **Mencionado en:** `CLAUDE.md`, `paper/results_log.md:206`, `docs/scout_autoextract.md` (completo), `docs/scout_d3.md`
- **Qué se afirma:** *"Extrae premisas correctamente: 2062 para Irrational.lean, 27 para Infinite.lean. Funciona en Windows con 'lake env lean --run ExtractData.lean <archivo>'."* (`paper/results_log.md:206`)
- **Rol:** **Herramienta propia.** Extractor de premisas standalone para D3, sin dependencia de LeanDojo.

### DeepSeek V4 Flash / Pro (vía OpenCode Go)
- **Identificador:** Modelo LLM, provider `opencode-go`. API key `OPENCODE_GO_API_KEY`.
- **Mencionado en:** `CLAUDE.md`, `paper/results_log.md:193,248`, `IDEA.md` (sección cuestión técnica), `docs/batch_run_002.md`, `docs/batch_run_003.md`
- **Rol:** **Infraestructura usada.** LLM Judge para D1 (DeepSeek V4 Flash) y modelo de formalización (DeepSeek V4 Pro).

## 8. Filosofía y teoría (para el paper)

### Tao — *Machine-Assisted Proof*
- **Identificador:** Notices of the AMS 72(1), 2025.
- **Mencionado en:** `paper/AViD_dosis_filosofica_paper.md:16-19,93`
- **Qué se afirma:** *"Es el gancho. 'Matemática a escala → hace falta filtrar novedad automáticamente' es justo lo que Tao articula. Legitima la existencia de AViD ante el campo."* (`paper/AViD_dosis_filosofica_paper.md:17`)
- **Rol en el paper:** **Referencia filosófica — Introducción/Motivación.** Núcleo no negociable.

### Boden — *The Creative Mind: Myths and Mechanisms*
- **Identificador:** 2ª ed., Routledge, 2004.
- **Mencionado en:** `paper/AViD_dosis_filosofica_paper.md:21-24,94`
- **Qué se afirma:** *"En una línea te da la distinción nuevo-para-el-agente vs. nuevo-para-la-comunidad, que es exactamente lo que mide D1. Convierte D1 de 'heurística ad hoc' en 'operacionalización de una noción establecida'."* (`paper/AViD_dosis_filosofica_paper.md:23`)
- **Rol en el paper:** **Referencia filosófica — ancla de D1.** Núcleo no negociable.

### Thurston — *On Proof and Progress in Mathematics*
- **Identificador:** Bull. AMS 30(2):161–177, 1994.
- **Mencionado en:** `paper/AViD_dosis_filosofica_paper.md:26-29,95`
- **Qué se afirma:** *"Justifica en una oración por qué medís novedad de prueba (D3) y no solo de enunciado. Muy citado, nadie te la discute."* (`paper/AViD_dosis_filosofica_paper.md:28`)
- **Rol en el paper:** **Referencia filosófica — justifica D3.** Núcleo no negociable.

### Lakatos — *Proofs and Refutations*
- **Identificador:** Cambridge University Press, 1976.
- **Mencionado en:** `paper/AViD_dosis_filosofica_paper.md:34-36,96`
- **Qué se afirma:** *"Reconoce lo que AViD no captura — la novedad conceptual/transformacional (definiciones nuevas, reformulación de la conjetura) que ocurre antes de que el enunciado/proof term se congele."* (`paper/AViD_dosis_filosofica_paper.md:35`)
- **Rol en el paper:** **Referencia filosófica — Limitaciones.** Núcleo no negociable.

### Došen — *Identity of Proofs Based on Normalization and Generality*
- **Identificador:** Bulletin of Symbolic Logic 9(4), 477–503, 2003. Marcado `[VERIF páginas]` en el repo.
- **Mencionado en:** `paper/AViD_dosis_filosofica_paper.md:37-39,97`, `paper/mathlib_convergence_finding.md:54`
- **Qué se afirma:** *"Declara que tu Jaccard sobre premisas es una aproximación computable a un problema genuinamente difícil (posiblemente indecidible). Esto es honestidad operacional, no debilidad — sube el techo intelectual del paper."* (`paper/AViD_dosis_filosofica_paper.md:38`). *"Two proofs are identical if they have the same normal form."* (`paper/mathlib_convergence_finding.md:54`)
- **Rol en el paper:** **Referencia filosófica — Limitaciones (D3).** Núcleo no negociable.

### Granville — *Accepted Proofs: Objective Truth, or Culturally Robust?*
- **Identificador:** Annals of Math. and Philosophy 2, 2023. arXiv:2305.02115.
- **Mencionado en:** `paper/AViD_dosis_filosofica_paper.md:49-51,100`
- **Qué se afirma:** *"El costado 'qué cambia cuando las pruebas se mecanizan' / 'aceptar una prueba es un pacto social' → matiza que D1 ('existir en el corpus') es un hecho social, no ontológico."*
- **Rol en el paper:** **Referencia filosófica — opcional.** "En la medida de lo posible."

### Detlefsen & Arana — *Purity of Methods*
- **Identificador:** Philosophers' Imprint 11(2), 2011.
- **Mencionado en:** `paper/AViD_dosis_filosofica_paper.md:53-55,101`
- **Qué se afirma:** *"Fundamenta técnicamente que tu Jaccard sobre premisas es esencialmente una medida de (im)pureza."*
- **Rol en el paper:** **Referencia filosófica — opcional.** Solo si se quiere dar densidad a D3.

### Rav — *Why Do We Prove Theorems?*
- **Identificador:** Philosophia Mathematica 7(1), 5–41, 1999.
- **Mencionado en:** `paper/AViD_dosis_filosofica_paper.md:57-59,102`
- **Qué se afirma:** *"Refuerza D2/D3 (la prueba porta el método/conocimiento) y aporta la cautela sobre formalización."*
- **Rol en el paper:** **Referencia filosófica — opcional (baja prioridad).**

### Zahar (1973) — *Why did Einstein's Programme Supersede Lorentz's?*
- **Identificador:** BJPS 24, 1973. Marcado `[VERIF]` en el repo.
- **Mencionado en:** `paper/AViD_dosis_filosofica_paper.md:61-63,103`
- **Qué se afirma:** *"Distingue 'no estaba antes' (temporal) de 'no aporta contenido' (uso)."*
- **Rol en el paper:** **Referencia filosófica — opcional (baja prioridad).** Candidato natural para nota aparte.

### Kuhn
- **Identificador:** Sin referencia específica en el repo.
- **Mencionado en:** `paper/AViD_dosis_filosofica_paper.md:65-67`
- **Qué se afirma:** *"Enunciado no cerrable por automatización ≈ anomalía que resiste el paradigma vigente. Riesgo: la analogía gotea. Recomendación: dejarlo para la nota aparte."*
- **Rol en el paper:** **Fuera del paper.** Va a nota aparte.

## 9. Comunidad Mathlib / ITP

### van Doorn, Ebner, Lewis — *Maintaining a Library of Formal Mathematics*
- **Identificador:** CICM 2020. DOI: 10.1007/978-3-030-53518-6_16.
- **Mencionado en:** `paper/mathlib_convergence_finding.md:33-34,123`
- **Qué se afirma:** *"'Mathlib is a cohesive library of formalized mathematics. [...] The library is designed to be a single coherent body of mathematics, not a collection of independent formalizations.'"* (`paper/mathlib_convergence_finding.md:33`)
- **Rol:** **Referencia conceptual.** Documenta la filosofía de Mathlib que causa el "convergence finding" — la mayoría de teoremas clásicos tienen una sola prueba canónica.

### *Categorical Foundations of Formalized Condensed Mathematics*
- **Identificador:** 2024. Mathlib community effort. Sin DOI en el repo.
- **Mencionado en:** `paper/mathlib_convergence_finding.md:36-37,125`
- **Rol:** **Referencia conceptual.** Refuerza la cohesión de Mathlib.

### Sieg — *Proof Identity for Mere Mortals*
- **Identificador:** arXiv:1403.0641 (2014).
- **Mencionado en:** `paper/mathlib_convergence_finding.md:56,129`
- **Qué se afirma:** *"Argues for a pragmatic, human-centered notion of proof identity based on the inferential structure."*
- **Rol:** **Referencia conceptual.**

### Hilbert's 24th Problem
- **Identificador:** Hilbert (1900), discutido en Thiele, R. (2003). *"Hilbert's Twenty-Fourth Problem."* American Mathematical Monthly, 110(1), 1-24.
- **Mencionado en:** `paper/mathlib_convergence_finding.md:45,131`
- **Rol:** **Referencia conceptual.** Contexto histórico del problema de identidad de pruebas.

### Best et al. — *Doob's Martingale Convergence Theorems in Mathlib*
- **Identificador:** CICM 2023. Sin DOI en el repo.
- **Mencionado en:** `paper/mathlib_convergence_finding.md:133`
- **Rol:** **Referencia conceptual.**

### TacMiner
- **Identificador:** OOPSLA 2025. Sin DOI en el repo.
- **Mencionado en:** `paper/mathlib_convergence_finding.md:80,135`
- **Qué se afirma:** *"Found that 'syntactically different proofs can share the same Tactic Dependency Graph (TDG).'"*
- **Rol:** **Referencia conceptual.** Dual de nuestro hallazgo de convergencia.

### Brown & Pelletier — *A Correspondence Problem for Mathematical Proof*
- **Identificador:** arXiv:2603.13680 (2026).
- **Mencionado en:** `paper/mathlib_convergence_finding.md:82,137`
- **Qué se afirma:** *"Formalization confirms derivability but not strategy validity. A formal proof in one system may not correspond to the 'same proof' in another."*
- **Rol:** **Referencia conceptual.**

## 10. Referencias sin arXiv ID (requieren completar)

Las siguientes referencias se mencionan en el repo **sin identificador completo** (sin arXiv ID, DOI, o referencia de journal). Habrá que completarlas para la bibliografía del paper:

| Referencia | Mencionada en | Qué se dice |
|---|---|---|
| Synthetic Theorem Generation in Lean (OpenReview EeDSMy5Ruj) | `paper/related_work.md:14` | OpenReview ID, falta mapear a autores/arXiv |
| Uzzi et al. (Science 2013) | `paper/related_work.md:29` | Journal + año, falta DOI |
| Wang, Veugelers, Stephan (2017) | `paper/related_work.md:32` | Solo autores + año |
| Boyack & Klavans (2014) | `paper/related_work.md:34` | Solo autores + año |
| Measuring novelty with word embedding (PLOS ONE 2026) | `paper/related_work.md:36` | Journal + año, falta DOI |
| Sledgehammer (Paulson-Blanchette) | `paper/related_work.md:43` | Línea de trabajo, falta ref canónica |
| DeepMath (Google 2016) | `paper/related_work.md:47` | Solo mención, falta ref |
| Magnushammer (ICLR 2024) | `paper/related_work.md:49` | Conferencia + año, falta arXiv/DOI |
| Piotrowski & Urban — Stateful premise selection | `paper/related_work.md:55` | Solo autores |
| ReProver/LeanDojo (Yang et al.) | `paper/related_work.md:57` | Solo mención, falta ref |
| Aspinall et al. — Formal Proof Metrics (Springer) | `paper/related_work.md:68` | Solo editorial + autores |
| Dependency Graphs for ITP | `paper/related_work.md:74` | Sin datos |
| Supporting Maintenance... Similarity Search (Springer 2024) | `paper/related_work.md:76` | Sin datos |
| Metrics for Graph Comparison (PLOS One) | `paper/related_work.md:79` | Solo journal |
| Wu et al. — Autoformalization (NeurIPS 2022) | `paper/related_work.md:84` | Conferencia + año, falta arXiv |
| MerLean | `README.md:227` | Sin arXiv/URL |

---

# PARTE 2 — Inventario de hallazgos y números

Cada hallazgo con su fuente interna exacta y una línea de contexto.

## Dataset de evaluación (eval set)

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **26 teoremas firmes + 9 slots TBD** | `paper/results_log.md:19`, `paper/decisions.md:69`, `IDEA.md:147` | Eval set curado a mano en `paper/eval_set.csv`. 4 categorías: clásicos en mathlib, pares con distinta prueba, triviales, casos de falla. |
| **24 teoremas únicos para D2** (deduplicados) | `paper/eval_set_lean_statements.md:13-14` | T07a=T07b mismo tipo, T08a=T08b mismo tipo, T09a=T09b mismo tipo → 26 − 3 + 1 (T19) = 24. |
| **6 categorías**: clasico_en_mathlib, par_distinta_prueba, enunciados_cercanos_distintos, trivial, generado_IA, caso_falla | `paper/eval_set_lean_statements.md` (estructura), `IDEA.md:150-155` | Cubren todos los caminos del árbol de decisión. |

## Dataset de papers retirados

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **2600 papers escaneados** de arXiv (math) | `docs/retracted_dataset_report.md:28` | Búsqueda `cat:math.* AND co:withdrawn` sobre API arXiv. |
| **23 patrones de duplicación** (regex) | `docs/retracted_dataset_report.md:33-34` | Para filtrar retiros por "resultado ya conocido" vs. errores/gaps. |
| **33 candidatos identificados** | `docs/retracted_dataset_report.md:45` | De los 2600, 33 contienen withdrawal por duplicación. |
| **26 viables** (fuente LaTeX + ≥1 teorema) | `docs/retracted_dataset_report.md:46` | Los 7 no viables usan AMS-TeX o nombres abreviados de entornos. |
| **52 controles** (2 por retirado) | `docs/retracted_dataset_report.md:167` | Misma categoría, año ±1, fuente LaTeX verificada. |
| **382 controles chequeados**, 332 viables (87%) | `docs/retracted_dataset_report.md:169-170` | Backoff exponencial implementado (5 reintentos). |
| **12/26 citan explícitamente el duplicador**, 14 usan frases genéricas | `docs/retracted_dataset_report.md:215-217` | Los que citan son más valiosos (ground truth verificable). |
| **17 categorías matemáticas** representadas | `docs/retracted_dataset_report.md:53-71` | El fenómeno de retiro por duplicación es transversal. |
| **7 papers "no viables" son falsos negativos** del contador | `docs/retracted_dataset_report.md:140-156` | Con contador expandido, viables reales ~31-32/33. Formatos: AMS-TeX, `\newtheorem{thm}`, `\begin{inizio}`, etc. |

## Run 001 — Smoke test (5 papers retirados)

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **5/5 papers** formalizados (compilaron) | `docs/experiment_run_001_report.md:9-15` | Todos con veredicto `MATCH_ENCONTRADO_PENDIENTE_D3`. |
| **4 defectos encontrados** en el pipeline: | `docs/run_001_review.md:350-357` | (1) Generated Lean code not saved (temp file deletion). (2) Leandex scores all 1.0 (sospechoso — formalización probablemente trivial). (3) Withdrawal comments not in experiment YAML. (4) Implícito: formalization fidelity issues en papers 2, 4, 5. |
| **Caso Fillmore (1207.0631v1)** | `docs/run_001_review.md:74-135` | Known duplicator: Fillmore, 1969. Match de Leandex: `Matrix.scalar_apply` (lema trivial sobre matrices escalares, NO es el teorema de Fillmore). **Posición 1** en D1 informal top-5: "Filmor Theorem for integers" [1704.08037] (score 0.754). |
| **Candidato prior art 1404.0187** | `docs/experiment_run_001_report.md:30`, `docs/run_001_review.md:63` | Paper 1609.02090v1 (Waring/Z_n), D1 top-5 resultado #3: "Representing Integers as the Sum of Two Squares in the Ring Z_n" [1404.0187] (score 0.637). El duplicador conocido es Hardy & Littlewood (no encontrado en D1). |

## Resultado negativo del puente informal (formalización de matches)

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **Tasa de formalización: 0%** (0/2 papers) | `docs/batch_run_002.md:49-56`, `docs/batch_run_003.md:50-58` | Batch 002 (deepseek-v4-flash, 3 rondas): 0/2, 9 API calls. Batch 003 (deepseek-v4-pro, 6 rondas): 0/2, 36 API calls. Total acumulado: **45 API calls, 0 éxitos**. |
| **Causa: capacidad del modelo**, no presupuesto de rondas | `docs/batch_run_003.md:75-76,80-81` | *"Duplicar las rondas no cambió el resultado. El problema es de capacidad de razonamiento matemático del modelo, no de presupuesto de rondas."* |
| **Proof por delegación (1607.03618) correctamente saltado** en 002 | `docs/batch_run_002.md:38-43` | *"The delegation skip correctly avoided wasting API calls on an unformalizable proof pointer."* |
| **PoC de descarga arXiv + extracción de proof: ✅ funciona** | `docs/scout_d3_informal.md:209` | *"Descarga arXiv + extracción de proof: ✅ Funciona. < 5s total."* |
| **PoC de formalización vía API: ❌ no confiable** | `docs/scout_d3_informal.md:213` | Timeout a 120s con prompt de ~2KB. |

## D2 — Filtro de trivialidad

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **Accuracy D2: 20/23 = 87%** (eval set completo, 24 teoremas) | `paper/results_log.md:131-134` | Falsos positivos: T01, T08 (L10: norm_num cierra irracionalidad), T26 (exact? con import Mathlib). Falso negativo: T14 (budget insuficiente para aesop). |
| **8 cierres por D2:** T01 (norm_num, FP), T08 (norm_num, FP), T15 (decide), T16/T17/T22 (norm_num), T19 (aesop), T25 (exact?) | `IDEA.md:175-177` | — |
| **T23 cierra con `tauto`** (no `aesop` como se esperaba) | `paper/results_log.md:77-78` | `IsTree = Connected ∧ IsAcyclic` → conjunción proposicional. Falso positivo documentado. |
| **Tiempo total D2: ~30 min** para 24 teoremas | `paper/results_log.md:97` | Con prewarm de oleans. Startup ~30s/invocación en Windows con cache caliente. |
| **L10 — Relatividad de D2:** `norm_num` cierra `Irrational (Real.sqrt 2)` en Mathlib v4.29.0 | `paper/results_log.md:151`, `paper/limitations.md:72-84` | Hallazgo principal del paper: la trivialidad operacional es relativa al par (T_auto, Mathlib_version). |
| **L11 — Mathlib monolítico:** solo `import Mathlib` e `import Mathlib.Tactic` funcionan standalone | `paper/results_log.md:153`, `paper/limitations.md:88-108` | 13/24 teoremas afectados en corrida inicial. Con `import Mathlib`: startup 15-25s con cache caliente, ~6-10 min primera invocación fría. |
| **T14 (FN por budget):** aesop necesita ~215s, budget era 75s | `paper/results_log.md:156` | Presupuesto insuficiente. No resuelto en v1. |
| **T26 (FP inesperado):** `exact?` cierra suma de n enteros pares con `import Mathlib` | `paper/results_log.md:157` | Mathlib tiene lema directo. Correcto desde perspectiva D2. |

## D1 — No-existencia

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **Leandex encuentra 18/24 teoremas** en Mathlib (75%) | `paper/results_log.md:218-237` | Matches incluyen: T01 `Tactic.NormNum.evalIrrationalSqrt`, T02 `EuclidNumbers.infinite_prime_euclid_numbers`, T03 `intervalIntegral.integral_deriv_eq_sub'`, T04 `Int.ModEq.pow_prime_eq_self`, T09 vacío (requiere escribir prueba custom). |
| **D1 C_I no produce candidatos** — threshold MiniLM (0.40) muy alto | `paper/results_log.md:240` | Recomendación: bajar a 0.25 para activar rama C_I. |
| **`exact?` movido de D2 a D1** (2026-06-27) | `paper/results_log.md:200,249` | *"La táctica busca existencia previa, no trivialidad."* Ahora es fallback secundario de C_F. |
| **`norm_num` blacklist para `Irrational`** | `paper/results_log.md:201` | Evita falso positivo L10. |
| **arXiv como fuente primaria de C_I** | `paper/results_log.md:204,250` | *"Mejor cobertura matemática que Semantic Scholar."* Dedup por `arxiv_id`. |

## D3 — Distancia estructural

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **ExtractData: 2062 premisas** para `Irrational.lean`, **27 premisas** para `Infinite.lean` | `paper/results_log.md:206` | Ejecutado en Windows con `lake env lean --run ExtractData.lean`. |
| **Jaccard T07 vs T08 = 0.035, Distancia = 0.965 → NOVEDAD_DEMOSTRACION** | `paper/results_log.md:207` | T07 (infinitos primos, 27 premisas) vs T08 (√2 irracional, 268 premisas). |
| **T09a = T09b actualmente** (mismo lema `sum_range_id`) | `paper/results_log.md:241` | Pendiente: escribir prueba por inducción con `sum_range_succ` + `ring`. |
| **Premisas son DIRECTAS, no transitivas** | `docs/scout_d3.md:12-13` | ExtractData extrae solo constantes resueltas por el elaborador del archivo actual. Confirmado con evidencia de T08a (28 premisas) vs T08b (33 premisas). |
| **Identidad canónica de premisas: `(defPath, defPos)`** | `docs/scout_d3.md:104-105` | Deduplicación necesaria: `Nat` aparece 75 veces con distintos `(pos, endPos)`. |
| **Tiempo de extracción: 4-5 min** para Paper.lean (6 teoremas, `import Mathlib`) | `docs/scout_autoextract.md:77-78` | Con oleans cacheados. Sin cache: 6-10 min (frío). |
| **Extracción de archivos Mathlib individuales: 30-60s** | `docs/scout_d3_autolocation.md:79` | Ej: `Irrational.lean` → 36.6s, ast.json ~2.5 MB. |
| **Convergence finding:** Mathlib tiene una sola prueba canónica por teorema clásico | `paper/mathlib_convergence_finding.md:25-39` | Causa estructural: filosofía de biblioteca cohesiva. Consecuencia: D3 es relativo al corpus formal, no a la "realidad matemática". |
| **T07 rescatado:** prueba alternativa vía divergencia de ∑ 1/p en Archive (`Real.tendsto_sum_one_div_prime_atTop`) | `scripts/d3/notes/mathlib_investigation.md:54-77` | Completamente distinta de `Nat.exists_infinite_primes` (factorial). Sin factorial, sin minFac. |

## Pipeline y orquestador

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **Pipeline D1+D2 sobre 24 teoremas: 32 minutos** | `paper/results_log.md:216` | Windows nativo, Lean 4.29.0. |
| **Precisión D1+D2: 20/24 = 83%** | `paper/results_log.md:222` | 18 `MATCH_ENCONTRADO_PENDIENTE_D3` + 6 `NO_NOVEDOSO_trivial`. |
| **88/88 tests pasando** | `CLAUDE.md:27` | — |
| **7 veredictos** en `types.py`: `NOVEDAD_ENUNCIADO`, `NOVEDAD_DEMOSTRACION`, `CONOCIDO_LITERATURA`, `NO_NOVEDOSO_redundante`, `NO_NOVEDOSO_trivial`, `ZONA_GRIS`, `MATCH_ENCONTRADO_PENDIENTE_D3` | `CLAUDE.md:17`, `src/novelty_v2/types.py` | — |
| **LLM Judge migrado** de Claude Code → DeepSeek V4 Flash vía OpenCode Go | `paper/results_log.md:193,248` | temperature=0, retry automático a 4096 tokens. |
| **Checkpointing** en `run_eval_full.py`: CSV incremental, resume | `paper/results_log.md:211` | — |
| **D3 calibration paper**: 6 teoremas compilados en `lean_project/Papers/D3_Calibration/Paper.lean` | `paper/results_log.md:208` | T07a/b, T08a/b, T09a/b. |

## Distancia Jaccard D3 — valor 0.7222

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **Jaccard T08a vs T08b = 0.7222** (paridad vs. valuación) | `results/d3_validation.csv:2`, `tests/test_d3_orchestrator_integration.py:91-92`, `tests/test_premise_extraction.py:336` | Distancia de Jaccard entre las dos pruebas de √2 irracional (T08a: paridad, 28 premisas; T08b: valuación p-ádica, 33 premisas). `genuinely_different`, 0.7222 > θ = 0.5 → pruebas estructuralmente distantes. Validado por tests de integración. |

## Punto ciego temporal (L10 — relatividad de D2)

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **D2 es relativo al par (T_auto, Mathlib_version)** | `paper/limitations.md:72-84`, `paper/decisions.md:239-253` | Un teorema puede ser no-trivial hoy y trivial mañana si las tácticas mejoran. `norm_num` cierra `Irrational (Real.sqrt 2)` en v4.29.0 — en 1870 requería ~5 páginas. No es limitación del diseño, es propiedad arquitectural correcta. |
| **Riesgo de no-reproducibilidad cross-version** | `paper/limitations.md:78-79` | *"Reproducciones del eval set en versiones futuras de Mathlib pueden dar resultados parcialmente distintos."* Mitigado reportando `(T_auto, Mathlib_version)` exactos. |

## Tasas de formalización

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **Autoformalización de papers reales: 0% (0/2)** | `docs/batch_run_002.md:49-56`, `docs/batch_run_003.md:50-58` | DeepSeek no logra formalizar pruebas no triviales de LaTeX a Lean 4, incluso con 6 rondas de feedback. |
| **Pipeline de formalización con agentes:** 2 ejemplos funcionando (TinyEvens, AyrtonPortoTesis) | `docs/PROGRESS.md:28` | Con Claude Code agentic, funciona para pruebas simples. Sin medición de tasa sobre corpus grande. |
| **Formalización vía API no confiable** para C_I Stage B | `docs/scout_d3_informal.md:209-218` | Timeout a 120s. *"La formalización es el cuello de botella. Sin un provider confiable y rápido, el pipeline informal → D3 no es práctico en tiempo real."* |

## Corpus con `sorry`

| Hallazgo | Fuente | Contexto |
|---|---|---|
| **Mathlib contiene teoremas con `sorry`** | `docs/run_001_review.md:175-176` (Paper 3: `not_congruentNumber_1`), `docs/run_001_review.md:244-248` (Paper 4: `green_85`) | `not_congruentNumber_1`: `sorry` en la prueba. `green_85`: teorema abierto (Green's conjecture), con `answer(sorry)`. Mathlib no es 100% fully-verified. |

## Contradicciones detectadas entre documentos

| Contradicción | Doc 1 | Doc 2 | Detalle |
|---|---|---|---|
| **Modelo usado en batch 002** | `docs/batch_run_002.md:2` dice provider `opencode (deepseek-v4-flash)` | `docs/batch_run_003.md:68` dice que 002 usaba modelo `pro` (implícito) | Batch 002 header dice "deepseek-v4-flash" pero la tabla de comparación en 003 dice "Modelo: pro (implícito)". El header de 002 probablemente es el correcto (flash), y la tabla de 003 tiene un error al caracterizar 002 retroactivamente. |
| **Número de oleans en Windows** | `paper/CLAUDE_CODE_BRIEFING.md:88` dice "7871 oleans" | `paper/results_log.md:50` dice "8247 oleans" | `results_log.md` (Día 4, 2026-06-07) reporta 8247. `CLAUDE_CODE_BRIEFING.md` (2026-06-08) dice 7871. Posiblemente Mathlib se actualizó entre días o uno de los dos números es un error de conteo. El número más reciente y medido es 8247. |
| **Overhead de startup en Windows** | `paper/results_log.md:51` dice "~30 s con OS cache caliente" | `paper/CLAUDE_CODE_BRIEFING.md:46` dice "D2 tarda ~30s por invocación" | Consistente. `paper/decisions.md:176` dice "Overhead de inicio fijo: ~30s/invocación". |

---

# Resumen de gaps de referencia

Las siguientes referencias esperables del encargo **no aparecen en ningún .md del repositorio**:

- **TheoremGraph / LeanGraph** — No mencionado.
- **Matlas** — No mencionado.
- **LeanConjecturer** — No mencionado.
- **Pseudo-Formalization** — No mencionado.
- **Moogle** — No mencionado (Loogle sí, en vendor/numina).
- **LeanSearch** — Mencionado solo como tool CLI en vendor/numina (no como paper/trabajo académico).
- **Kaliszyk-Urban** — No mencionados por nombre. La línea de premise selection se cita vía Piotrowski y Magnushammer.
- **Network Structure of Mathlib** — No mencionado con ese título. El paper de van Doorn-Ebner-Lewis (CICM 2020) y Huch (arXiv:2209.13305) cubren temas relacionados.

Si estas referencias deben aparecer en el paper, habrá que incorporarlas manualmente con sus identificadores completos.
