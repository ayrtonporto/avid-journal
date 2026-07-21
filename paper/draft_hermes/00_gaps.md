# Gaps pendientes de completar por el autor

Este archivo recopila lo unico que queda pendiente tras cerrar todos los gaps de datos con los CSVs de evaluacion (julio 2026). Ya no hay gaps 2-9: todos fueron resueltos.

---

## Gap unico: Threshold de C_I (0.40 vs 0.25)

**Archivo:** `paper/draft_hermes/03_pipeline.md`, linea 93

**Marcador textual:** `[FALTA: confirmar si el threshold de C_I es 0.40 (valor en codigo) o 0.25 (valor mencionado en PAPER_BRIEF.md). La discrepancia esta documentada en docs/section3_facts.md:266-268.]`

**Contexto:** Seccion 3.4.1, rama C_I. El codigo en `src/novelty_v2/dimensions/d1_existence.py:45` tiene `CI_SIMILARITY_THRESHOLD_A = 0.40`. El PAPER_BRIEF menciona que se bajo a 0.25. La discrepancia esta documentada pero no resuelta.

**Que debe hacer Ayrton:** Decidir cual es el valor que va en el paper y, si es 0.25, aplicar el cambio en el codigo para que coincida.

---

## Referencias por verificar

Las siguientes referencias aparecen en `paper/bibliography_merged.md` marcadas `[VERIFICAR]` y se usan en `paper/draft_hermes/02_related_work.md`. Requieren confirmacion de arXiv ID antes de la version final:

- TheoremGraph + LeanGraph (arXiv:2606.25363)
- COMPOSE (arXiv:2605.30333)
- LeanConjecturer (arXiv pendiente)
- Matlas (ID pendiente)
- Pseudo-Formalization / ArxivMathGradingBench (arXiv pendiente)
- MerLean (ID pendiente)
- Network Structure of Mathlib (arXiv:2604.24797)
- Kaliszyk & Urban MaSh/Flyspeck (refs canonicas pendientes)
- Loogle, LeanSearch, LeanExplore, Lean Finder (papers asociados pendientes)

---

## Gaps cerrados en esta sesion

| Gap | Tema | Resolucion |
|---|---|---|
| 2 | Numero de tests | 167 passed, 1 skipped (pytest, julio 2026) |
| 4 | Tabla D2 completa | Construida con 24 filas desde eval_full_20260628_143702.csv |
| 5 | T26: exact? en D1 o D2 | D1 C_F: match via Leandex (Nat.even_add). No paso por D2. |
| 6 | Por que 24 y no 26 | T20 y T21 no formalizados en esta corrida |
| 7 | Los 6 sin match en C_F | Son los 6 triviales detenidos en D2 (T14-T17, T19, T22) |
| 8 | C_I: threshold o no ejecucion | No se ejecuto: la condicion de entrada nunca se cumplio |
| 9 | Precision D2 solo | 22/24 = 91.7% (2 casos con expectativa ambigua) |
| T09 | Tabla D3 desactualizada | Corregida con datos de pair_judgments.json y d3_validation.csv |
