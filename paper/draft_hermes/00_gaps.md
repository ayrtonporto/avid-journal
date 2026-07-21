# Gaps pendientes de completar por el autor

**Estado:** Gap 1 cerrado (2026-07-20). LeanConjecturer y Matlas verificados. Quedan ~7 refs por verificar.

---

## Gaps cerrados

| Gap | Tema | Resolucion | Fecha |
|---|---|---|---|
| 1 | Threshold C_I 0.40 vs 0.25 | 0.40. Regla del proyecto: gana el codigo (`d1_existence.py:45`). PAPER_BRIEF corregido. | 2026-07-20 |
| 2 | Numero de tests | 167 passed, 1 skipped (pytest, julio 2026) | 2026-07-20 |
| 3 | Veredicto humano T09 | genuinely_different, etiqueta firmada por Ayrton Porto (pair_judgments.json, 2026-07-12) | 2026-07-20 |
| 4 | Tabla D2 completa | Construida con 24 filas desde eval_full_20260628_143702.csv | 2026-07-20 |
| 5 | T26: exact? en D1 o D2 | D1 C_F: match via Leandex (Nat.even_add). No paso por D2. | 2026-07-20 |
| 6 | Por que 24 y no 26 | T20 y T21 no formalizados en esta corrida | 2026-07-20 |
| 7 | Los 6 sin match en C_F | Son los 6 triviales detenidos en D2 (T14-T17, T19, T22) | 2026-07-20 |
| 8 | C_I: threshold o no ejecucion | No se ejecuto: la condicion de entrada nunca se cumplio | 2026-07-20 |
| 9 | Precision D2 solo | 22/24 = 91.7% (2 casos con expectativa ambigua) | 2026-07-20 |
| T09 | Tabla D3 desactualizada | Corregida con pair_judgments.json y d3_validation.csv | 2026-07-20 |

---

## IDs verificados

- **LeanConjecturer** → arXiv:2506.22005 (Onda et al., junio 2025)
- **Matlas** → arXiv:2604.17484 (abril 2026). 8.07M enunciados, 1826-2025.
- **Survey IA matematica** → arXiv:2601.13209. Cita TheoremSearch y Matlas como infraestructura para determinar si un resultado ya es conocido.

---

## Referencias pendientes de verificacion

- TheoremGraph + LeanGraph (arXiv:2606.25363)
- COMPOSE (arXiv:2605.30333)
- Pseudo-Formalization / ArxivMathGradingBench (arXiv pendiente)
- MerLean (ID pendiente)
- Network Structure of Mathlib (arXiv:2604.24797)
- Kaliszyk & Urban MaSh/Flyspeck (refs canonicas pendientes)
- Loogle, LeanSearch, LeanExplore, Lean Finder (papers asociados pendientes)
