# Dosis filosófica para el paper de AViD — qué entra y dónde

> Guía de colocación, no de contenido. El mapa filosófico completo (`AViD_mapa_filosofico_novedad.md`) es andamiaje privado / insumo para una **nota aparte** y para los *research statements* de las aplicaciones a PhD. **En el paper de sistema entra muy poco.**

## Regla de oro
Cada cita filosófica tiene que hacer un trabajo **operacional**: o vuelve *defendible* una definición, o vuelve *honesta* una limitación. Si no hace ninguna de las dos, no entra. Los revisores de este mundo (autoformalización / ML-for-proof) leen el exceso de filosofía como hand-waving que tapa falta de rigor empírico.

- **Presupuesto total:** 4–7 referencias filosóficas, cada una citada 1–2 veces.
- **Concentración:** casi todo en *Introducción/Motivación* y *Limitaciones/Discusión*. Nada (o casi) en Related Work y Methods.
- Las oraciones modelo están en inglés y son *paste-ready*; ajustá a tu estilo.

---

## ✅ SÍ O SÍ (el núcleo no negociable)

### 1. Tao — *Introducción / motivación*
- **Cita:** Tao, "Machine-Assisted Proof", *Notices of the AMS* 72(1), 2025.
- **Trabajo que hace:** es el gancho. "Matemática a escala → hace falta filtrar novedad automáticamente" es justo lo que Tao articula. Legitima la *existencia* de AViD ante el campo.
- **Oración modelo:** *"As machine-generated formal mathematics scales [Tao 2025], distinguishing genuinely new contributions from restatements of known results becomes a bottleneck that manual review cannot absorb."*

### 2. Boden — *Definición del problema* (ancla de D1)
- **Cita:** Boden, *The Creative Mind: Myths and Mechanisms*, 2.ª ed., 2004 (P-creatividad vs H-creatividad).
- **Trabajo que hace:** en **una línea** te da la distinción nuevo-para-el-agente vs. nuevo-para-la-comunidad, que es *exactamente* lo que mide D1. Convierte D1 de "heurística ad hoc" en "operacionalización de una noción establecida".
- **Oración modelo:** *"We operationalize novelty in the sense of Boden's H-creativity [Boden 2004]: a contribution counts as novel when it is new relative to the recorded body of mathematics, not merely new to the agent that produced it."*

### 3. Thurston — *Definición del problema* (justifica medir D3)
- **Cita:** Thurston, "On Proof and Progress in Mathematics", *Bull. AMS* 30(2):161–177, 1994.
- **Trabajo que hace:** justifica en una oración por qué medís novedad de *prueba* (D3) y no solo de enunciado. Es la elección segura: muy citado, nadie te la discute.
- **Oración modelo:** *"Because distinct proofs of the same statement can carry different mathematical understanding [Thurston 1994], we treat proof structure as a dimension of novelty in its own right, independent of statement-level novelty."*

### 4. Párrafo de Limitaciones — Lakatos + identidad de pruebas
> Este es el único lugar donde la filosofía *paga de verdad*. Un solo párrafo, dos citas. Acá los revisores premian la sofisticación.

- **Cita A:** Lakatos, *Proofs and Refutations*, 1976.
  - **Trabajo:** reconoce lo que AViD **no** captura — la novedad conceptual/transformacional (definiciones nuevas, reformulación de la conjetura) que ocurre *antes* de que el enunciado/proof term se congele.
  - **Oración modelo:** *"AViD measures novelty over fixed, formalized statements and proof terms; it therefore does not capture conceptual or transformational novelty — the introduction of new definitions or the reframing of a problem that, in Lakatos's sense [Lakatos 1976], drives much mathematical discovery before any statement is fixed."*
- **Cita B:** Došen, "Identity of Proofs Based on Normalization and Generality", *Bull. Symbolic Logic* 9, 2003. `[VERIF páginas exactas]`
  - **Trabajo:** declara que tu Jaccard sobre premisas es una *aproximación computable* a un problema genuinamente difícil (posiblemente indecidible). Esto es honestidad operacional, no debilidad — sube el techo intelectual del paper.
  - **Oración modelo:** *"Our premise-set Jaccard is a computable proxy for proof similarity; deciding when two proofs are 'the same' is, in general, undecidable [Došen 2003]. D3 is thus an approximation, exposed to both false positives (normalization-equivalent proofs with differing surface premises) and false negatives (distinct strategies that share core library lemmas)."*

> **Bonus del párrafo (gratis, sin cita extra):** agregá la observación de que **D2 es relativa a la herramienta** — lo "no cerrable por automatización" depende del estado actual de las tácticas y de mathlib, y puede volverse trivial mañana. Versioná (qué mathlib, qué tácticas, qué fecha). No necesita cita; es la limitación más concreta y verificable de las tres.

---

## 🔶 EN LA MEDIDA DE LO POSIBLE (si hay espacio / si querés flexionar)

Orden de prioridad. Agregá de arriba hacia abajo según presupuesto de páginas.

1. **Granville**, "Accepted Proofs: Objective Truth, or Culturally Robust?", *Annals of Math. and Philosophy* 2, 2023 (arXiv:2305.02115).
   - *Dónde:* intro (junto a Tao) o limitaciones. *Una* cita.
   - *Trabajo:* el costado "qué cambia cuando las pruebas se mecanizan" / "aceptar una prueba es un pacto social" → matiza que D1 ("existir en el corpus") es un hecho social, no ontológico.

2. **Detlefsen & Arana**, "Purity of Methods", *Philosophers' Imprint* 11(2), 2011.
   - *Dónde:* sección de D3 (methods) o limitaciones. *Una* cita.
   - *Trabajo:* fundamenta técnicamente que tu Jaccard sobre premisas es esencialmente una medida de (im)pureza. Solo si querés dar densidad a la justificación de D3.

3. **Rav**, "Why Do We Prove Theorems?", *Philosophia Mathematica* 7, 1999.
   - *Dónde:* se *funde* en el párrafo de limitaciones (no abre párrafo propio).
   - *Trabajo:* refuerza D2/D3 (la prueba porta el método/conocimiento) y aporta la cautela sobre formalización. Útil pero prescindible si ya tenés Thurston + Lakatos.

4. **Lakatos–Zahar (novedad temporal vs. de uso)** — solo si decidís *desarrollar* la ambigüedad de D1.
   - *Cita:* Zahar (1973) reformulando a Lakatos. `[VERIF: BJPS 1973]`
   - *Trabajo:* distingue "no estaba antes" (temporal) de "no aporta contenido" (uso). Es fino y bueno, pero abre una discusión que quizás no quieras en un paper de sistema. Candidato natural para la **nota aparte**.

5. **Kuhn** (anomalía / ciencia normal) para enmarcar D2 — **con cuidado.**
   - *Trabajo:* "enunciado no cerrable por automatización ≈ anomalía que resiste el paradigma vigente".
   - *Riesgo:* la analogía gotea (la ciencia normal kuhniana también incluye puzzles durísimos). Si lo usás, declará que es analogía, no equivalencia. **Recomendación: dejalo para la nota aparte**, no para el paper.

---

## ❌ FUERA DEL PAPER (va a la nota aparte, no al preprint)

Para protegerte del scope creep. Todo esto es valioso pero **no pertenece a un paper de sistema/benchmark**:

- **Metafísica de la novedad:** Bergson, Whitehead, Deleuze. → nota aparte, sección "por qué la novedad resiste la captura formal".
- **Background histórico de filosofía de la matemática:** Poincaré, Pólya, Hersh–Davis, Cellucci. → nota aparte / research statement.
- **Filosofía de la ciencia general:** Popper, Laudan, Feyerabend. Demasiado general para aportar algo operacional acá.
- **El debate "¿recombina o crea?"** (Poincaré + Boden + stochastic parrots). → nota aparte; era el corazón del "segundo paper" descartado, así que su lugar natural es la nota.
- **Prehistoria computacional:** Lenat (AM/EURISKO), Colton, Ritchie & Hanna. → si acaso, una línea en *future work* o en la nota; no en la fundamentación.

---

## 🚫 Dónde NO poner filosofía dentro del paper
- **Related Work:** son tus vecinos *técnicos* (autoformalización, premise selection, búsqueda en Mathlib/Leandex, deduplicación, embeddings de teoremas). A lo sumo dos oraciones que conecten con Tao/Granville.
- **Methods / arquitectura del pipeline:** cero filosofía. Definiciones operacionales, métricas, implementación.
- **Resultados:** cero.

---

## Referencias completas (núcleo + opcionales)

**Sí o sí**
- Tao, T. (2025). *Machine-Assisted Proof.* Notices of the AMS 72(1), 6–13.
- Boden, M. (2004). *The Creative Mind: Myths and Mechanisms* (2nd ed.). Routledge.
- Thurston, W. (1994). *On Proof and Progress in Mathematics.* Bulletin of the AMS 30(2), 161–177.
- Lakatos, I. (1976). *Proofs and Refutations.* Cambridge University Press.
- Došen, K. (2003). *Identity of Proofs Based on Normalization and Generality.* Bulletin of Symbolic Logic 9(4), 477–503. `[VERIF páginas]`

**Opcionales**
- Granville, A. (2023). *Accepted Proofs: Objective Truth, or Culturally Robust?* Annals of Mathematics and Philosophy 2. arXiv:2305.02115.
- Detlefsen, M. & Arana, A. (2011). *Purity of Methods.* Philosophers' Imprint 11(2).
- Rav, Y. (1999). *Why Do We Prove Theorems?* Philosophia Mathematica 7(1), 5–41.
- Zahar, E. (1973). *Why did Einstein's Programme Supersede Lorentz's?* BJPS 24. `[VERIF]`

> Verificá las marcas `[VERIF]` (sobre todo las páginas de Došen y los datos de Zahar) antes de que entren a la bibliografía.
