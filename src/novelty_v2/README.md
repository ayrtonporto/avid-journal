# src/novelty_v2/ — Métrica de novedad según metric_spec.md

Implementación de la métrica de novedad de AViD Journal conforme a
`paper/metric_spec.md` (documento de diseño v1).

## Relación con src/novelty/ (v1)

`src/novelty/` **no se modifica**. Es la implementación previa de stages
0–3 (Leandex + Semantic Scholar + MiniLM + juez LLM). Este módulo la usa
como dependencia externa:

| Función importada de src/novelty/ | Reutilizada en |
|---|---|
| `mathlib_checker.check_in_mathlib()` | D1 sobre C_F |
| `arxiv_search.search_semantic_scholar/arxiv()` | D1 sobre C_I etapa A |
| `block_comparator` (MiniLM) | D1 sobre C_I etapa A (filtro grueso) |
| `llm_judge.judge_theorem_pair()` | D1 sobre C_I etapa B |
| `_cache.cache_or_fetch()` | caching compartido todas las dimensiones |

## Estructura

```
novelty_v2/
├── __init__.py          ← exporta NoveltyVerdict, Verdict, D1/D2/D3Result
├── types.py             ← dataclasses de veredictos (los 5 de la spec + ZONA_GRIS)
├── dimensions/
│   ├── d1_existence.py  ← Día 5 (adelantado): no-existencia en C_F y C_I
│   ├── d2_triviality.py ← Día 4: cierre por tácticas T_auto
│   └── d3_premises.py   ← Días 8-9: LeanDojo + Jaccard
└── orchestrator.py      ← Día 8: árbol de decisión combinado
```

## Los cinco veredictos (spec §6)

| Veredicto | Condición |
|---|---|
| `NO_NOVEDOSO_trivial` | D2 cerró con táctica estándar |
| `NO_NOVEDOSO_redundante` | match en C_F + D3 pruebas cercanas |
| `NOVEDAD_DEMOSTRACION` | match en C_F + D3 pruebas distantes |
| `CONOCIDO_LITERATURA` | match en C_I pero no en C_F |
| `NOVEDAD_ENUNCIADO` | sin match en C_F ni C_I, no trivial |
| `ZONA_GRIS` | generalización/especialización según juez LLM |

## Orden de decisión (árbol, spec §6)

```
1. D2 (trivialidad) — si cierra → NO_NOVEDOSO_trivial, fin
2. D1 sobre C_F (Leandex) — si match → ir a paso 4
3. D1 sobre C_I (etapa A barata, etapa B cara si A dispara)
   - sin match → NOVEDAD_ENUNCIADO, fin
   - match en C_I pero no C_F → CONOCIDO_LITERATURA, fin
   - generalization/specialization → ZONA_GRIS, fin
4. D3 (Jaccard sobre premisas)
   - distantes → NOVEDAD_DEMOSTRACION
   - cercanas  → NO_NOVEDOSO_redundante
```
