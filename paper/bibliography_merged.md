# AViD Journal — Bibliografía fusionada para el paper

**Generado:** 2026-07-12  
**Propósito:** Fusión del dossier `docs/bibliography_context.md` con las 10 referencias faltantes identificadas en sesión de estrategia. Este documento + el inventario de hallazgos (PARTE 2 del dossier) son las fuentes únicas de citas y cifras para la fase de escritura.  
**IDs marcados `[VERIFICAR]`:** requieren confirmación antes de entrar en la bibliografía final del preprint.

---

# PARTE 1 — Referencias completas

## Grupo A — UW Math AI Lab (competidores directos, citar sí o sí)

### A1. Ilin, Alper, Inchiostro — *TheoremSearch*
- **arXiv:** 2602.05216 (febrero 2026)
- **Mencionado en el repo:** `docs/scout_theoremsearch.md` (como API), `docs/scout_d3_informal.md`, `docs/experiment_run_001_report.md`
- **Qué se afirma:** Corpus de 9.2M enunciados de teoremas de arXiv + 7 fuentes (Open Logic Project, Stacks, etc.). Genera un "slogan" en lenguaje natural por teorema para embeber. Motivado explícitamente por preprints retirados por resultados previos (cita a Rao et al.: ~2.5% de ~14K retiros) y por IA "resolviendo" problemas de Erdős ya resueltos. API pública sin key, endpoint REST, similarity score de coseno directo.
- **Rol en nuestro paper:** **DOBLE — infraestructura usada Y motivación externa directa.** Es la fuente primaria de D1-informal (C_I Stage A). Su motivación documentada (retiros por duplicación) es la misma que nuestro experimento de retirados. Nosotros agregamos la capa de veredicto que ellos no tienen: TheoremSearch encuentra enunciados similares; AViD emite un veredicto de novedad.

### A2. *TheoremGraph + LeanGraph* (mismo lab, UW)
- **arXiv:** 2606.25363 `[VERIFICAR]` (junio 2026)
- **Mencionado en el repo:** No (incorporación nueva).
- **Qué se afirma:** Grafo de dependencias unificado formal-informal. 11.7M entornos tipo-teorema de arXiv, 18.3M dependencias candidatas. LeanGraph: 388,105 nodos y 11.3M aristas tipadas sobre 25 proyectos Lean. Liberan API HTTP y servidor MCP.
- **Rol en nuestro paper:** **Competidor directo en infraestructura de D1/D3.** Si su grafo unificado cubre dependencias formales e informales, compite con nuestra combinación D1 (corpus formal+informal) + D3 (distancias de premisas). Citar para posicionarnos: nosotros emitimos veredictos de novedad sobre su grafo; ellos construyen el grafo sin capa de decisión.

### A3. *COMPOSE* (mismo lab, UW)
- **arXiv:** 2605.30333 `[VERIFICAR]` (mayo 2026)
- **Mencionado en el repo:** No (incorporación nueva).
- **Qué se afirma:** Predicción/composición de teoremas futuros desde estructura de citas + estructura formal.
- **Rol en nuestro paper:** **Competidor cercano en generación.** Si COMPOSE predice qué teoremas vendrán, AViD evalúa si un teorema ya llegó. Direcciones complementarias: ellos generan hacia adelante, nosotros chequeamos hacia atrás.

---

## 1. Competidores directos / baselines de veredicto

### Kasaura et al. — *Discovering New Theorems via LLMs with In-Context Proof Learning in Lean*
- **arXiv:** 2509.14274 (sept 2025)
- **Mencionado en el repo:** `paper/related_work.md:11-12`, `paper/metric_spec.md:22`, `IDEA.md:40`
- **Qué se afirma:** *"Generan teoremas nuevos con un Conjecturing-Proving Loop. Definen novedad como: 'la conjetura no está ya en Mathlib4, ni en la librería generada, ni en la lista del conjeturador'. Es decir, novedad = no-presencia, sin filtro de trivialidad ni distancia estructural."* (`paper/related_work.md:12`)
- **Rol en nuestro paper:** **Baseline que AViD supera.** Es el criterio ingenuo que AViD corrige con D2 (trivialidad) y D3 (distancia estructural).

### Yoo — *The Axiom-Based Atlas*
- **arXiv:** 2504.00063 (abril 2025)
- **Mencionado en el repo:** `paper/related_work.md:63-66,120-121`, `paper/metric_spec.md:82`
- **Qué se afirma:** *"Representa teoremas como proof vectors sobre sistemas de axiomas fundacionales. Compara con similitud coseno, distancia euclidiana o índice de Jaccard."* *"AViD no es 'el Atlas con otro nombre' porque (a) el propósito es novelty-checking activo, no organización, y (b) el alcance del corpus incluye literatura informal vía autoformalización."* (`paper/related_work.md:121`)
- **Rol en nuestro paper:** **Competidor cercano.** Misma herramienta conceptual (Jaccard), propósito distinto.

### Abouzaid et al. — *First Proof*
- **arXiv:** 2602.05192 (febrero 2026)
- **Mencionado en el repo:** `paper/related_work.md:22-25`, `paper/metric_spec.md:22`, `paper/preprint/draft.md:25-27`, `IDEA.md:35-37`
- **Qué se afirma:** *"Once matemáticos de primer nivel lanzaron un examen de matemática para AI con problemas no publicados. 'los LLMs tienen tendencia a encontrar pruebas existentes y olvidadas en lo profundo de la literatura matemática y presentarlas como originales'"* Cita motivante: *"lo que nos falta es una manera sistemática de evaluar si esos lemas pueden ensamblarse en una prueba novedosa"*.
- **Rol en nuestro paper:** **Motivación externa del problema.**

---

## 2. Baselines de mecanismo (Grupo B)

### B1. *LeanConjecturer*
- **Identificador:** arXiv `[VERIFICAR]` (junio 2025)
- **Mencionado en el repo:** No (incorporación nueva).
- **Qué se afirma:** Filtra novedad de conjeturas con `exact?` contra Mathlib y no-trivialidad con `aesop` — exactamente los mecanismos de nuestro D1-formal (fallback) y D2, publicados como filtros estándar.
- **Rol en nuestro paper:** **Baseline directo de mecanismo.** D1 (exact?) y D2 (aesop) no son contribución original nuestra; son filtros estándar que LeanConjecturer ya publicó. Nuestra contribución es: (a) la capa de veredicto integrada (tres dimensiones → un veredicto), (b) D3 (distancia de premisas) que ellos no tienen, (c) D1-informal (arXiv + TheoremSearch) más allá de Mathlib, (d) la evaluación empírica contra ground truth real (retirados). Citar para honestidad.

### B2. *Matlas*
- **Identificador:** `[VERIFICAR]`
- **Mencionado en el repo:** No (incorporación nueva).
- **Qué se afirma:** Búsqueda a nivel teorema sobre 435K papers + 1.9K libros. Extrae enunciados CON sus dependencias y los despliega en orden topológico ("unfolding") para representaciones autocontenidas.
- **Rol en nuestro paper:** **Estado del arte de D1-informal.** Su "unfolding" (despliegue topológico de dependencias) es la solución publicada al problema de "proofs que delegan a lemas" que nosotros documentamos con el flag `proof_delegates_to_lemmas` (batches 002/003). Citar para mostrar que el problema que encontramos ya tiene solución en la literatura — y que AViD podría beneficiarse de integrarla.

### B3. *Pseudo-Formalization / ArxivMathGradingBench*
- **Identificador:** arXiv `[VERIFICAR]` (mayo 2026)
- **Mencionado en el repo:** No (incorporación nueva).
- **Qué se afirma:** Verificación de CORRECCIÓN de papers de arXiv vía formalización.
- **Rol en nuestro paper:** **Vecino exacto — delimita nuestro espacio.** Ellos verifican corrección de papers de arXiv vía formalización; nosotros verificamos novedad. Citar explícitamente: "While ArxivMathGradingBench checks whether arXiv proofs are CORRECT, AViD checks whether they are NEW — orthogonal dimensions that a complete automated review system would combine."

### B4. *MerLean* (expandido)
- **Identificador:** `[VERIFICAR]` — actualmente en el repo sin arXiv ID.
- **Mencionado en el repo:** `README.md:227`, `docs/ARCHITECTURE.md:381-382`
- **Qué se afirma:** *"Inspiration for autoformalization pipeline"* (`README.md:227`). Pipeline paper→Lean que deja la novedad a reviewers humanos. *"MerLean doesn't have novelty detection. We add that layer."* (`docs/ARCHITECTURE.md:382`)
- **Rol en nuestro paper:** **Complemento.** Ellos formalizan sin veredicto de novedad (lo delegan a humanos); nosotros somos la capa de veredicto automatizada que ellos delegan.

---

## 3. Generación sintética / conjecturing con LLMs

### *Synthetic Theorem Generation in Lean*
- **Identificador:** OpenReview EeDSMy5Ruj (sin arXiv ID explícito)
- **Mencionado en:** `paper/related_work.md:14-15`
- **Qué se afirma:** *"Generación sintética de teoremas por forward-reasoning desde estados de prueba existentes."*
- **Rol:** **Referencia conceptual.**

### *Mining Math Conjectures from LLMs: A Pruning Approach*
- **arXiv:** 2412.16177
- **Mencionado en:** `paper/related_work.md:17-18`
- **Qué se afirma:** *"Reportan el problema inverso: redundancia en conjeturas generadas. Atacan con pruning heurístico, no con métrica formal."*
- **Rol:** **Referencia conceptual.**

---

## 4. Novedad bibliométrica

### Uzzi, Mukherjee, Stringer, Jones — *Atypical Combinations and Scientific Impact*
- **Identificador:** Science (2013). Sin arXiv ID.
- **Mencionado en:** `paper/related_work.md:29-30`
- **Qué se afirma:** *"17.9 millones de artículos. Miden novedad como combinaciones atípicas de revistas citadas."*
- **Rol:** **Campo adyacente que no alcanza.** No mira contenido deductivo.

### Wang, Veugelers, Stephan (2017)
- **Identificador:** Sin arXiv ID. `[PENDIENTE completar]`
- **Rol:** **Campo adyacente.**

### Boyack & Klavans (2014)
- **Identificador:** Sin arXiv ID. `[PENDIENTE completar]`
- **Rol:** **Crítica metodológica.**

### *Measuring novelty in science with word embedding* (PLOS ONE, 2026)
- **Identificador:** Sin DOI en el repo. `[PENDIENTE completar]`
- **Rol:** **Campo adyacente.**

---

## 5. Premise selection + genealogía técnica de D3 (Grupo C)

### Sledgehammer (Paulson y Blanchette, línea Isabelle)
- **Identificador:** Sin ref canónica en el repo. `[PENDIENTE completar]`
- **Rol:** **Mecanismo clásico de premise selection.**

### MePo (Meng-Paulson) y MaSh
- **Rol:** **Precedente.** Heurísticas + ML temprano.

### DeepMath (Google, 2016)
- **Rol:** **Precedente.** Primer deep learning para premise selection.

### Mikuła, Jiang, Wenda Li et al. — *Magnushammer*
- **Identificador:** ICLR 2024. Sin arXiv ID. `[PENDIENTE completar]`
- **Mencionado en:** `paper/related_work.md:49-50`, `paper/metric_spec.md:69`, `paper/decisions.md:112`
- **Qué se afirma:** *"59.5% contra 38.3% en PISA, 34.0% contra 20.9% en miniF2F. Wenda Li es coautor."*
- **Rol:** **Infraestructura usada / precedente.** AViD usa premise selection en dirección inversa.

### Piotrowski et al. — *Machine-Learned Premise Selection for Lean*
- **arXiv:** 2304.00994
- **Mencionado en:** `paper/related_work.md:52-53`, `paper/metric_spec.md:69,71`
- **Qué se afirma:** *"Math filter que preserva solo lemas de naturaleza claramente matemática, usando nombres de teoremas de mathlib como whitelist."*
- **Rol:** **Infraestructura usada.** La receta AViD de math filter sigue exactamente este paper.

### Piotrowski & Urban — *Stateful premise selection*
- **Identificador:** Sin ref en el repo. `[PENDIENTE completar]`
- **Rol:** **Precedente.**

### ReProver / LeanDojo (Yang et al.)
- **Identificador:** Sin arXiv ID en el repo. `[PENDIENTE completar]`
- **Rol:** **Infraestructura usada.** Retrieval-augmented proving. AViD usa LeanDojo v1 para D3.

### C1. Kaliszyk & Urban — línea MaSh / k-NN premise selection
- **Identificador:** `[VERIFICAR]` — referencias canónicas: *"MaSh: Machine Learning for Sledgehammer"* y *"Learning-Assisted Automated Reasoning with Flyspeck"*, ~2013-2015.
- **Mencionado en el repo:** No por nombre (incorporación nueva). La línea se cita indirectamente vía Piotrowski y Magnushammer.
- **Qué se afirma:** Premise selection con features ponderadas por rareza (IDF). El k-NN sobre conjuntos de premisas con pesos IDF es una técnica establecida en la literatura de ATP.
- **Rol en nuestro paper:** **GENEALOGÍA de D3 — obligatorio para honestidad intelectual.** El Jaccard (ponderado) sobre conjuntos de premisas no lo inventamos nosotros; viene de la literatura de premise selection. Nuestro aporte es **reposicionarlo como medida de novedad de demostración** (en lugar de como input para construir pruebas). Sin esta cita, D3 parece TF-IDF redescubierto. Con ella, es la aplicación legítima de una técnica establecida a un problema nuevo.

### C2. *The Network Structure of Mathlib*
- **arXiv:** 2604.24797 `[VERIFICAR]`
- **Mencionado en el repo:** No (incorporación nueva).
- **Qué se afirma:** Grafo multicapa de 308,129 declaraciones y 8.4M aristas. Hallazgo: la centralidad de red captura infraestructura del lenguaje (tipo `Nat`, `Eq`, `List`) más que relevancia matemática.
- **Rol en nuestro paper:** **Justificación publicada de nuestro Filtro 1 (blacklist de namespaces de infraestructura antes del Jaccard).** Cuando AViD filtra `Init.Prelude`, `Lean`, `Std` antes de calcular Jaccard, no es una heurística ad-hoc — está respaldado por el hallazgo empírico de que esos nodos dominan las métricas de red por razones de infraestructura, no por contenido matemático. Citar para blindar D3.

---

## 6. Estructura de pruebas, grafos de dependencia y similitud

### Aspinall et al. — *Towards Formal Proof Metrics* (Springer)
- **Rol:** **Referencia conceptual.**

### Huch — *Structure in Theorem Proving*
- **arXiv:** 2209.13305
- **Mencionado en:** `paper/related_work.md:71-72`, `paper/metric_spec.md:81`, `paper/limitations.md:17`
- **Qué se afirma:** *"Distribución scale-free del grado de entrada en AFP."*
- **Rol:** **Referencia conceptual.** Útil para IDF.

### *Dependency Graphs for ITP* — `[PENDIENTE completar]`
### *Supporting Maintenance of Formal Mathematics with Similarity Search* (Springer 2024)
### *Metrics for Graph Comparison: A Practitioner's Guide* (PLOS One)

---

## 7. Autoformalización

### Wu et al. — *Autoformalization with Large Language Models* (NeurIPS 2022)
### ProofFlow (Huawei AI4Math) — arXiv:2510.15981
### Aria — arXiv:2510.04520
### *Conjecturing: An Overlooked Step* — arXiv:2510.11986
### Patel — *A New Approach Towards Autoformalization* — arXiv:2310.07957

*(Contenido preservado del dossier original para todas las anteriores.)*

---

## 8. Herramientas e infraestructura

### TheoremSearch (API)
- **Nota:** La entrada canónica con arXiv ID está en **Grupo A1**. Esta sección preserva la información operacional de uso.

### WithdrarXiv (Rao, Young, Dietterich, Callison-Burch)
- **arXiv:** 2412.03775
- **Mencionado en:** `docs/retracted_dataset_report.md:13-20`
- **Qué se afirma:** *"~14,000 preprints retirados con taxonomía de 10 categorías."*
- **Rol:** **Dataset de referencia.** Fuente del experimento de retirados (AViD usó Plan B: arXiv API directa por gating).

### LeanDojo v1 / v2 (Yang et al.)
- **Rol:** **Infraestructura usada.** D3 vía LeanDojo v1 o ExtractData standalone.

### Leandex (aka LeanExplore)
- **Rol:** **Infraestructura usada.** Backend de D1 sobre C_F.

### Grupo D — Buscadores de Mathlib como trabajos académicos

#### D1. Loogle
- **Identificador:** `[VERIFICAR si tiene paper/publicación asociada]`
- **Mencionado en:** `vendor/numina-lean-agent/skills/search/reference-loogle.md`
- **Rol:** Búsqueda por patrón en Mathlib. Parte del "campo saturado" de D1-formal.

#### D2. LeanSearch
- **Identificador:** `[VERIFICAR arXiv/paper]`
- **Mencionado en:** `vendor/numina-lean-agent/skills/search/reference-leansearch.md`
- **Rol:** Búsqueda NL + Lean terms.

#### D3. LeanExplore (Leandex)
- **Identificador:** `[VERIFICAR si tiene paper independiente del API]`
- **Rol:** Backend principal de D1-formal.

#### D4. Lean Finder / LeanStateSearch
- **Identificador:** `[VERIFICAR]`
- **Rol:** Búsqueda semántica y por estado de prueba en Mathlib.

**Nota colectiva para Related Work:** El espacio de buscadores de Mathlib está saturado (Loogle, LeanSearch, LeanExplore, Lean Finder, LeanStateSearch). AViD no compite en búsqueda — consume estas herramientas como infraestructura y agrega la capa de veredicto. Una frase en Related Work con las citas que existan.

### Numina-Lean-Agent
- **Rol:** **Infraestructura usada / inspiración.** AViD hereda patrón coordinator/blueprint/sketch.

### Semantic Scholar API
- **Rol:** **Infraestructura usada.** Fuente de D1 C_I Stage A.

### ExtractData.lean
- **Rol:** **Herramienta propia.** Extractor standalone de premisas para D3 (515 líneas).

### DeepSeek V4 Flash / Pro (vía OpenCode Go)
- **Rol:** **Infraestructura usada.** LLM Judge (Flash) y formalización (Pro).

---

## 9. Filosofía y teoría (para el paper)

*(Contenido preservado del dossier original.)*

- Tao — *Machine-Assisted Proof* (Notices AMS, 2025)
- Boden — *The Creative Mind* (2004)
- Thurston — *On Proof and Progress in Mathematics* (1994)
- Lakatos — *Proofs and Refutations* (1976)
- Došen — *Identity of Proofs* (Bull. Symbolic Logic, 2003)
- Granville — *Accepted Proofs* (arXiv:2305.02115)
- Detlefsen & Arana — *Purity of Methods* (2011)
- Rav — *Why Do We Prove Theorems?* (1999)
- Zahar (1973)
- Kuhn

---

## 10. Comunidad Mathlib / ITP

*(Contenido preservado del dossier original. Incluye: van Doorn-Ebner-Lewis CICM 2020, Condensed Mathematics 2024, Sieg arXiv:1403.0641, Hilbert's 24th / Thiele 2003, Best et al. CICM 2023, TacMiner OOPSLA 2025, Brown & Pelletier arXiv:2603.13680.)*

---

# Resumen de referencias con flags

## `[VERIFICAR]` — requieren confirmación antes de la bibliografía final

| # | Referencia | Flag | Prioridad |
|---|---|---|---|
| A2 | TheoremGraph + LeanGraph | arXiv 2606.25363 `[VERIFICAR]` | ALTA — competidor directo |
| A3 | COMPOSE | arXiv 2605.30333 `[VERIFICAR]` | ALTA — competidor cercano |
| B1 | LeanConjecturer | arXiv `[VERIFICAR]` | ALTA — baseline de mecanismo |
| B2 | Matlas | ID `[VERIFICAR]` | MEDIA — estado del arte D1-informal |
| B3 | Pseudo-Formalization / ArxivMathGradingBench | arXiv `[VERIFICAR]` | MEDIA — vecino exacto |
| B4 | MerLean | ID `[VERIFICAR]` | MEDIA — ya en el repo sin ID |
| C1 | Kaliszyk & Urban (MaSh/Flyspeck) | Ref canónica `[VERIFICAR]` | ALTA — genealogía de D3 |
| C2 | Network Structure of Mathlib | arXiv 2604.24797 `[VERIFICAR]` | ALTA — justifica Filtro 1 |
| D1-D4 | Loogle, LeanSearch, LeanExplore, Lean Finder/StateSearch | `[VERIFICAR]` papers asociados | BAJA — cita colectiva |

## `[PENDIENTE completar]` — sin identificador suficiente

*(Heredadas del dossier original: 16 referencias sin arXiv ID, DOI o journal. Ver sección 10 del dossier `docs/bibliography_context.md`.)*

---

# PARTE 2 — Inventario de hallazgos y números

**→ Ver `docs/bibliography_context.md`, PARTE 2 (líneas 366–510).**  
Todo el inventario de hallazgos se mantiene en ese documento como fuente única de cifras. Este archivo (`bibliography_merged.md`) cubre solo las referencias. Para números, dirigirse al dossier.

**Correcciones aplicadas al inventario (2026-07-12):**
1. **Modelo batch 002:** Corregida la contradicción. Ambos batches (002 y 003) usaron deepseek-v4-PRO. Header de `docs/batch_run_002.md` fue el erróneo → corregido.
2. **0% formalización:** Anotado "medido con DeepSeek V4 Pro (45 llamadas); pendiente re-medición opcional con Qwen 3.7-max (ganador del benchmark de enunciados)."
