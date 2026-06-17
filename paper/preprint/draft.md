# AViD Journal: Measuring Novelty in Formalized Mathematics through Three Independent Dimensions

**Authors:** Ayrton Porto, [TBD coauthors]
**Affiliation:** Universidad Nacional del Centro de la Provincia de Buenos Aires (UNICEN)
**Draft v0 — fecha:** [a llenar al Día 13]
**Estado:** esqueleto inicial. Cada sección incluye notas sobre qué va adentro.

---

## Abstract

*[Llenar el Día 14, después de tener resultados. Versión preliminar:]*

We introduce AViD Journal, a system for automatically assessing the novelty of mathematical theorems by decomposing it into three independent dimensions: non-existence in a corpus combining formal libraries and informal literature, non-triviality under standard proof automation, and structural distance from existing proofs measured via premise sets. We argue and show empirically that the naive criterion of "absence from the formal corpus", widely used by recent LLM-based theorem generators, conflates triviality and informal existence with genuine novelty — a failure mode publicly documented in industrial AI mathematics systems. AViD's three-dimensional decomposition corrects this conflation. We present a preliminary evaluation over 29 hand-curated theorems and release a functional web demo at [URL].

*Cap: 200 palabras.*

---

## 1. Introduction

### 1.1 Motivación — el modo de falla actual

*[Notas para llenar:]*
- Abrir con el caso Axiom Math / conjetura de Fel (cf. First Proof, Scientific American febrero 2026).
- LLMs presentan resultados viejos como nuevos porque no chequean novedad estructuralmente.
- Cita motivante de First Proof: "what we lack is a systematic way to gauge whether those lemmas can be stitched into a novel proof".
- Tesis central del paper: la novedad matemática NO es una sola cosa; descomponerla en tres dimensiones independientes resuelve el problema.

### 1.2 Por qué correctness ≠ novelty

*[Notas para llenar:]*
- Axiom, Harmonic, DeepSeek-Prover, Kimina: todos miden correctness.
- AViD mide ortogonalmente: ¿es nuevo?
- Una prueba puede ser correcta y vieja, o novedosa y mal. Son ejes independientes.

### 1.3 Por qué ausencia del corpus ≠ novedad

*[Notas para llenar:]*
- Caso testigo: "suma de cuatro pares es par" — no está en mathlib, omega lo cierra.
- Falla por trivialidad y falla por existencia informal.
- Baseline de Kasaura et al. (arXiv:2509.14274) cae en este error.

### 1.4 Contribuciones

*[Llenar al final con la lista final:]*
1. Una taxonomía de la novedad matemática como cruce de dos ejes (mismo tipo, premisas cercanas/distantes) que produce cuatro casos.
2. Una métrica operacional implementada como conjunción de tres dimensiones: no-existencia, no-trivialidad, distancia estructural.
3. Una implementación funcional con demo público en [URL].
4. Evaluación preliminar sobre 29 teoremas hand-curated cubriendo casos canónicos y casos de falla.

---

## 2. Related Work

*[Importar de `related_work.md` adaptado a tono académico. Siete subsecciones:]*

### 2.1 Novelty detection in LLM-generated mathematics
### 2.2 Bibliometric novelty
### 2.3 Premise selection
### 2.4 Proof structure and dependency graphs
### 2.5 Autoformalization
### 2.6 Theoretical notions of novelty
### 2.7 Positioning of AViD

---

## 3. The Three Dimensions of Novelty

*[Adaptar `metric_spec.md` Sección 4. Mantener la rigurosidad técnica.]*

### 3.1 Dimension 1 — Prior existence
### 3.2 Dimension 2 — Non-triviality

<!-- TODO DÍA 18: SUBSECCIÓN "Operational triviality is relative"
     Desarrollar aquí que D2 se calibra al par (T_auto, Mathlib_version) en el
     momento de la evaluación. El veredicto "trivial" es relativo, no absoluto.
     Usar T01/T08 (Irrational sqrt 2 cerrado por norm_num en v4.29.0) como
     ejemplo canónico. Citar DECISIÓN D de decisions.md.
     Contrastar con la noción estática de trivialidad (rechazada en esa decisión).
     Ver también L10 en limitations.md para la formulación completa.
-->
### 3.3 Dimension 3 — Structural distance via premises
### 3.4 The taxonomic matrix
### 3.5 Combined decision rule

---

## 4. Why premises and not homotopy: a note on type theory

*[Sección breve pero crítica para la credibilidad técnica. Mostrar que entendemos proof irrelevance en Prop. Anticipa la pregunta del reviewer.]*

---

## 5. Implementation

### 5.1 Architecture overview
*[Diagrama: pipeline de dos etapas para C_I, árbol de decisión, conexión con Numina/Axiom como módulos de autoformalización futuros.]*

### 5.2 Triviality filter (D2)
### 5.3 Type comparison (D1, C_F branch)
### 5.4 Literature search (D1, C_I branch, two-stage)
### 5.5 Premise extraction with LeanDojo
### 5.6 Jaccard distance (D3)
### 5.7 The web demo

---

## 6. Evaluation

### 6.1 Evaluation set
*[Adaptar `eval_set.csv` a tabla narrativa. Explicar las ocho categorías y el principio "cada teorema testea una rama".]*

### 6.2 Two-layer evaluation methodology
*[Capa 1: ¿el formalizador tradujo bien? Capa 2: dada la traducción, ¿la métrica clasificó bien? Separar errores de traducción de errores de métrica.]*

### 6.3 Results
*[Tabla principal del paper, llenada el Día 9. Aciertos por categoría.]*

### 6.4 The triviality bug, fixed
*[Mostrar concretamente el caso "suma de 4 pares" antes y después de D2.]*

### 6.5 Proof-alternative detection
*[Mostrar los pares T07/T08/T09. Distancias de Jaccard reales. Calibración del umbral θ.]*

---

## 7. Limitations

*[Adaptar de `limitations.md`. Honestidad total — las limitaciones bien declaradas suben la credibilidad, no la bajan.]*

---

## 8. Future Work

*[Adaptar de `future_work.md`. Selección de los items más relevantes para el lector académico.]*

---

## 9. Conclusion

*[Volver a la matriz taxonómica. Resumir las tres dimensiones. Cerrar con la cita motivante de First Proof transformada: "AViD provee la manera sistemática de chequear si una prueba propuesta es genuinamente nueva."]*

---

## References

*[Compilar de `related_work.md`. Mantener formato consistente. Apuntar a ~30-40 referencias.]*

---

## Appendix A — Detailed evaluation table

*[Exportar `eval_set.csv` enriquecido con resultados.]*

## Appendix B — Reproducibility

*[Link al repo. Instrucciones de instalación. Versión exacta de mathlib usada. URL del demo.]*
