# PROJECT STATE — AViD Journal

**Generado:** 2026-07-12 (regenerable — refleja el estado actual del repo en cada ejecución)
**Branch:** `main` (HEAD: `9ad7254`, 2026-07-12 — rescue snapshot pre-cleanup)
**Working tree:** limpio (post-commit de rescate + cambios de limpieza sin commitear)

---

## 1. QUÉ EXISTE (inventario funcional)

### Parser — extracción de bloques LaTeX
- **Archivo:** `src/parser/latex_parser.py`
- **Qué hace:** Extrae teoremas, lemas, definiciones, proposiciones, corolarios con grafo de dependencias (`\ref`), soporta entornos custom y variantes en español.
- **Estado:** Estable. Congelado por CLAUDE.md (regla 3: no modificar).

### Formalización — traducción LaTeX→Lean vía Claude Code
- **Archivo principal:** `src/formalization/orchestrator.py`
- **Qué hace:** Orden topológico de Kahn sobre bloques, genera TASK.md por bloque, invoca Claude Code para formalizar, verifica compilación con `lean_checker.py`, escribe Paper.lean incremental, mantiene PAPER_INDEX.md y REVIEW.md.
- **Archivos auxiliares:** `src/formalization/lean_project.py` (proyecto Lean compartido), `src/formalization/complexity.py` (clasificador SIMPLE/MEDIUM/HARD/EXTERNAL), `src/formalization/mathlib_search.py` (fallback de axiomas Mathlib).
- **Estado:** Estable. Congelado por CLAUDE.md (regla 3).

### D2 — Filtro de trivialidad
- **Archivo:** `src/novelty_v2/dimensions/d2_triviality.py` (191 líneas)
- **Qué hace:** Itera `T_AUTO_ORDER = [decide, norm_num, simp, omega, tauto, aesop]`. Genera `example : τ := by T`, ejecuta `lake env lean` con presupuesto. Primer éxito → trivial. `norm_num` tiene blacklist para `Irrational`. `exact?` removido (movido a D1 como fallback de C_F).
- **Estado:** Estable. Bug conocido: T14 (suma de 4 pares) es FN — `aesop` necesita ~215s pero el budget es 30s (+45s overhead = 75s timeout).
- **Toggles:** `LEAN_STARTUP_OVERHEAD_S=45`, budgets: `decide/norm_num/simp/omega/tauto=10s`, `aesop=30s`, `NORM_NUM_BLACKLIST=["Irrational"]`.

### D1 formal (C_F) — Búsqueda en Mathlib vía Leandex
- **Archivo principal:** `src/novelty/mathlib_checker.py` (284 líneas) — API Leandex v2
- **Wrapper:** `src/novelty_v2/dimensions/d1_existence.py` (523 líneas) — `_check_cf()`
- **Qué hace:** Consulta Leandex (`api/v1/search`) con el enunciado informal. Extrae matches del nuevo formato SSE (sin scores). Similaridad sintética 1.0/0.9/... por orden de resultado. Fallback: `exact?` como fuente secundaria de C_F (15s budget).
- **Estado:** Parcheado 2026-06-27 (formato v2, basura en match_C_F corregida). Encuentra 18/24 teoremas del eval set.
- **Toggle:** `CI_SIMILARITY_THRESHOLD_A=0.40` (en d1_existence.py; aplica a C_I etapa A, no a C_F).

### D1 informal (C_I) — Búsqueda en literatura (arXiv + Semantic Scholar + LLM judge)
- **Archivos:**
  - `src/novelty/arxiv_search.py` — arXiv API + Semantic Scholar. Estable.
  - `src/novelty/llm_judge.py` — DeepSeek V4 Flash vía OpenCode Go, temperature=0, max_tokens=2048 con retry a 4096. Reescrito 2026-06-27.
  - `src/novelty/theoremsearch.py` — TheoremSearch API (UNTRACKED, nuevo).
- **Pipeline:** Etapa A (filtro grueso MiniLM, arXiv primario → Semantic Scholar secundario) → Etapa B (LLM judge sobre candidatos que pasan threshold).
- **Estado:** Con bugs conocidos. arXiv y Semantic Scholar no producen candidatos que superen el threshold MiniLM actual (0.40). Rama C_I no se activa para ningún teorema del eval set. Fix pendiente: bajar threshold a 0.25.
- **Toggle:** `CI_SIMILARITY_THRESHOLD_A=0.40` (src/novelty_v2/dimensions/d1_existence.py:53).

### D3 formal — Distancia de premisas (Jaccard)
- **Archivo canónico:** `src/novelty_v2/dimensions/d3_premises.py` (307 líneas) — `compute_d3()`
- **Qué hace:** Pipeline fijo: (1) extraer premisas de listas de dicts PremiseTrace, (2) deduplicar por identidad canónica (defPath, defPos), (3) Filter 1: namespace blacklist (`config/d3_filter_blacklist.yaml`), (4) Filter 2: eliminar premisas del enunciado por rango de líneas, (5) Jaccard = 1 − |A∩B|/|A∪B|. Umbral θ = 0.5.
- **Extracción de premisas:**
  - `lean_project/ExtractData.lean` (515 líneas) — extractor standalone. Funciona en Windows. 2062 premisas de Irrational.lean, 27 de Infinite.lean.
  - `src/novelty_v2/premise_extraction.py` (306 líneas, UNTRACKED) — wrapper Python con caché SHA256. Degradación elegante: cualquier fallo → None + log.
- **Auto-localización de teoremas:**
  - `src/novelty_v2/premise_autolocation.py` (414 líneas, UNTRACKED) — busca teoremas en Papers/Blocks/ (lado A) y en fuentes Mathlib vía ripgrep (lado B).
  - `config/d3_extraction_map.yaml` — mapa manual theorem_id → archivo .lean + rangos de línea (pares de calibración: T07a/b, T08a/b, T09a/b).
- **D3 sobre matches informales:**
  - `src/novelty_v2/informal_match.py` (404 líneas, UNTRACKED) — PoC: descarga arXiv source, extrae prueba, intenta formalizarla para extraer premisas y comparar.
- **Estado:** D3 sobre C_F funciona (Jaccard T07 vs T08 = 0.965). D3 integrado en orchestrator vía auto-location desde 2026-07-03. D3 sobre C_I es PoC sin tasa de éxito medida. T09a = T09b actualmente (colapso: mismo lema `sum_range_id`).

### Orchestrator — Árbol D2→D1→D3
- **Archivo:** `src/novelty_v2/orchestrator.py` (473 líneas)
- **Qué hace:** `check_novelty(block, lean_statement, ...)` → árbol completo con 8 veredictos. Orden: D2 → D1 C_F (+ D3 si hay premisas) → exact? fallback → D1 C_I.
- **Estado:** Estable. Auto-location de Side B integrada. `compute_d3` es la única función canónica de distancia. `check_novelty()` en orchestrator.py es el único punto de entrada al árbol de decisión.
- **8 veredictos:** `NOVEDAD_ENUNCIADO`, `NOVEDAD_DEMOSTRACION`, `CONOCIDO_LITERATURA`, `NO_NOVEDOSO_redundante`, `NO_NOVEDOSO_trivial`, `ZONA_GRIS`, `MATCH_ENCONTRADO_PENDIENTE_D3`, `INCONCLUSIVE`.
- **Archivo de tipos:** `src/novelty_v2/types.py` (197 líneas).

### Dataset y experimentos
- **Eval set base:** `paper/eval_set.csv` — 26 teoremas firmes (T01–T26) + 9 slots TBD (TBD_27–TBD_35). Categorías: clásicos en mathlib, pares con distinta prueba, enunciados cercanos, triviales, generados por IA, casos de falla.
- **Dataset de retirados:**
  - `config/retracted_candidates.yaml` — 33 candidatos de arXiv (math.* withdrawn), 26 viables.
  - `config/control_candidates.yaml` — 26 pares × 2 controles emparejados por categoría y año.
  - `config/experiment_run_001.yaml` — 5 retirados + 5 controles seleccionados para smoke test. Compuerta `confirmed:true`.
- **Scripts del experimento (todos UNTRACKED):**
  - `scripts/build_retracted_dataset.py` (531 líneas) — FASE 1-2: arXiv API → candidates YAML.
  - `scripts/build_control_candidates.py` — FASE 3: matched controls.
  - `scripts/build_selection_dossier.py` (453 líneas) — FASE 4: cached LaTeX → fichas Markdown.
  - `scripts/run_experiment_001.py` (552 líneas) — ejecución del pipeline con compuerta `confirmed`.
- **Docs del experimento (todos UNTRACKED):**
  - `docs/retracted_dataset_report.md` — reporte de los 33 candidatos.
  - `docs/selection_dossier.md` (1212 líneas) — 26 fichas con evidencia.
  - `docs/experiment_run_001_report.md` (131 líneas) — reporte de Run 001.
  - `docs/run_001_review.md` (356 líneas) — revisión manual de Ayrton (parcial).
  - `docs/audit_experimento_retirados_2026-07-12.md` (346 líneas) — auditoría de estado.

### Scripts de soporte
- `scripts/run_eval_full.py` (559 líneas) — eval D1+D2 sobre eval set con checkpointing y resume.
- `scripts/validate_d3.py` — validación D3 sobre pares de calibración.
- `scripts/prewarm_premise_cache.py` — precalentamiento de caché de premisas.
- `scripts/batch_formalize_informal.py` — formalización por lote de papers informales.
- `scripts/d2/test_eval_set.py`, `scripts/d2/test_eval_set_full.py` — tests de D2.

### Entorno
- **OS:** Windows 10 nativo para pipeline automatizado. WSL2 (Ubuntu 22.04 en `D:\WSL\Ubuntu2204\`) solo para D3 manual.
- **Lean:** 4.29.0 (`x86_64-w64-windows-gnu`). Mathlib: 8247 oleans, 0 vacíos.
- **Python:** 3.11.15, venv en `.venv/`. Dependencias: `requirements.txt`.
- **LLM Judge:** DeepSeek V4 Flash vía OpenCode Go API (`OPENCODE_GO_API_KEY` en `~/.hermes/.env`).
- **Repositorio:** `github.com/ayrtonporto/avid-journal`. Landing page: `avid-journal.github.io`.

---

## 2. NÚMEROS VIGENTES

| Cifra | Valor | Respaldo |
|---|---|---|
| Tests pasando | 166 passed, 1 skipped, 1 flaky (autolocation) = 167/168 efectivos | `pytest tests/ -q` (2026-07-12) |
| Test flaky | `test_locate_mathlib_irrational_sqrt_two` — falla en corrida completa, pasa aislado | `tests/test_autolocation.py` |
| Tamaño eval set | 26 firmes + 9 TBD = 35 slots | `paper/eval_set.csv` |
| Candidatos retirados | 33 total, 26 viables | `config/retracted_candidates.yaml` |
| Controles emparejados | 26 pares × 2 controles = 52 | `config/control_candidates.yaml` |
| Smoke test (Run 001) | 5 retirados + 5 controles | `config/experiment_run_001.yaml` |
| Última run eval D1+D2 | 2026-06-28, 24 teoremas, 32 min | `scripts/eval/eval_full_20260628_143702.csv` |
| MATCH_ENCONTRADO_PENDIENTE_D3 | 18/24 (75%) | Mismo CSV |
| NO_NOVEDOSO_trivial | 6/24 (25%) | Mismo CSV |
| Precisión D1+D2 | 20/24 = 83% (4 FP/fallo esperado) | `paper/results_log.md` §Día 7 |
| Premisas Irrational.lean | 2062 | `paper/results_log.md` §Día 7 |
| Premisas Infinite.lean | 27 | Mismo |
| Jaccard T07 vs T08 | 0.035 (distancia = 0.965) | Mismo |
| Tasa formalización enunciados | No medida | `docs/scout_d3_informal.md` |
| Tasa formalización pruebas ajenas | No medida (PoC con 2 papers) | `docs/scout_d3_informal.md` |
| Match Leandex sobre eval set | 18/24 (75%) | `eval_full_20260628_143702.csv` |
| CI_SIMILARITY_THRESHOLD_A actual | 0.40 — no produce candidatos | `src/novelty_v2/dimensions/d1_existence.py:53` |

---

## 3. QUÉ ESTÁ EN CURSO

### Generado pero no revisado
- **Run 001 review:** `docs/run_001_review.md` (356 líneas). Revisión manual de Ayrton sobre 5 papers retirados. Incompleta: Paper 1 tiene secciones B/C/D parcialmente llenas, Papers 2-5 sin revisar.

### Esperan confirmación del usuario (compuerta `confirmed`)
- **`config/experiment_run_001.yaml`:** 5 papers con `confirmed:true`. Si se agregan más papers del dataset de 33, requieren revisión manual de Ayrton y cambio a `confirmed:true`.
- **Selección de casos:** qué papers entran al experimento lo decide Ayrton. El script `run_experiment_001.py` rechaza entradas con `confirmed:false` (salvo `--force`).

### Bloqueado
- **Rama C_I completa:** CI_SIMILARITY_THRESHOLD_A = 0.40 no deja pasar candidatos de arXiv/Semantic Scholar. Fix: bajar a 0.25. Documentado en `paper/results_log.md` §Día 7.
- **Validación D3 sobre T09:** T09a y T09b usan el mismo lema (`sum_range_id`), colapsan a Jaccard = 0. Fix: escribir T09a con `sum_range_succ` + `ring`. Documentado en `paper/results_log.md` §Día 7.
- **9 slots TBD del eval set:** sin poblar. Documentado en `paper/eval_set.csv` líneas 31-39.

### Pendiente (no bloqueado, requiere tiempo de desarrollo)
- Demo Gradio + deploy Hugging Face Spaces (`paper/results_log.md` §Días 10-12)
- Preprint arXiv (`paper/results_log.md` §Días 13-15)
- Outreach emails (`paper/results_log.md` §Días 16+)

---

## 4. QUÉ FALTA (sin priorizar)

| # | Qué | Bloqueado por | Documentado en |
|---|---|---|---|
| 1 | Bajar CI_SIMILARITY_THRESHOLD_A de 0.40 a 0.25 | Nada (cambio de una constante) | `results_log.md` §Día 7, `d1_existence.py:53` |
| 2 | Escribir T09a con prueba por inducción (`sum_range_succ` + `ring`) | Nada (requiere escribir Lean) | `results_log.md` §Día 7 |
| 3 | Llenar 9 slots TBD del eval set | Requiere verificar mathlib y arXiv en vivo | `eval_set.csv` líneas 31-39 |
| 4 | Integrar D3 en corrida eval completa (D1+D2+D3) | #2, #3 | `results_log.md` §Día 7 |
| 5 | Demo Gradio con upload .tex + streaming D1+D2 + botón D3 | Nada técnico, requiere build | `results_log.md` §Días 10-12 |
| 6 | Preprint arXiv (draft completo) | #5 (parte de la narrativa) | `results_log.md` §Días 13-15 |
| 7 | Outreach emails a Wenda Li, Welleck, van Doorn | #6 | `results_log.md` §Días 16+ |
| 8 | Run 001-b: re-ejecutar experimento con fixes | Revisión manual de Run 001 completada | `docs/audit_experimento_retirados_2026-07-12.md` |
| 9 | Calibrar umbral D3 θ (actual 0.5) contra T07/T08/T09 | #2 | `decisions.md` §pendientes |
| 10 | Implementar isDefEq (D1 nivel 1) para equivalencia definicional | No prioritario para v1 | `metric_spec.md` §4.1, `decisions.md` §pendientes |
| 11 | Medir y mejorar tasa de autoformalización de pruebas ajenas (D3 informal) | Depende de avances en autoformalización | `docs/scout_d3_informal.md` |
| 12 | Guardar código Lean generado en Run 001 (actualmente se pierde) | Fix en pipeline de formalización | `docs/run_001_review.md` Paper 1 §B |
| 13 | Módulo de paráfrasis LaTeX→lenguaje natural (mejora queries) | Nada (diferido post Run 001-b) | `docs/TECH_DEBT.md`, `decisions.md` §Out of scope |

---

## 5. DECISIONES DE DISEÑO VIGENTES

Reglas que un chat nuevo debe conocer para no proponer lo ya descartado:

1. **D3 solo formal por ahora.** El puente informal (autoformalizar prueba de arXiv → extraer premisas → Jaccard) tiene resultado negativo medido: la tasa de éxito de formalización de pruebas ajenas es ~0% en el PoC actual. No proponer D3 sobre C_I como camino viable sin evidencia nueva.
   - Doc: `docs/scout_d3_informal.md`

2. **Matches `statement_only` no cuentan como existencia.** Un match en Leandex que solo comparte estructura superficial pero no el enunciado matemático no activa D1. La equivalencia requerida es de tipo (enunciado), no sintáctica superficial.
   - Doc: `metric_spec.md` §4.1

3. **Scores sintéticos prohibidos como feature.** La similaridad 1.0/0.9/... por orden de resultado en Leandex v2 es un workaround porque la API no devuelve scores. No debe presentarse como método de scoring ni usarse para thresholds cuantitativos.
   - Doc: `decisions.md` §2026-06-27, `results_log.md` §Día 7

4. **Compuertas `confirmed` manuales.** El campo `confirmed:true/false` en los YAML de experimento lo setea Ayrton manualmente tras revisar cada paper. El script `run_experiment_001.py` rechaza entradas con `confirmed:false`. `--force` solo para testing.
   - Doc: `experiment_run_001.yaml`, `run_experiment_001.py`

5. **La selección de casos es del usuario.** Qué papers entran al dataset de experimento lo decide Ayrton, no el sistema ni el agente.
   - Doc: regla del proyecto (memory)

6. **Degradación elegante en todo.** Cualquier fallo en extracción de premisas, auto-localización, o formalización → `None` + log warning. Nunca excepción hacia arriba que rompa el pipeline.
   - Doc: `premise_extraction.py` líneas 6-7, `orchestrator.py` try/except en auto-location

7. **Windows nativo para pipeline automatizado; WSL2 solo para D3 manual.** No proponer migrar el pipeline a WSL ni a Docker.
   - Doc: `decisions.md` §2026-06-07

8. **C_F prevalece sobre C_I.** Si Leandex encuentra match en Mathlib, no se ejecuta la búsqueda en arXiv/Semantic Scholar.
   - Doc: `decisions.md` §2026-06-09

9. **`exact?` es D1, no D2.** La táctica busca teoremas existentes en el entorno Lean — es verificación de existencia previa (C_F), no de trivialidad.
   - Doc: `decisions.md` §2026-06-27

10. **`norm_num` blacklist para `Irrational`.** Evita el falso positivo L10 donde `norm_num` cierra `Irrational (Real.sqrt 2)` en Mathlib v4.29.0.
    - Doc: `d2_triviality.py:61`, `results_log.md` §Día 7

11. **LLM Judge: DeepSeek V4 Flash vía OpenCode Go.** Temperature=0, max_tokens=2048 con retry a 4096 para `reasoning_content`. No proponer cambiar de proveedor sin evidencia de falla.
    - Doc: `decisions.md` §2026-06-27

12. **Caché organizado por endpoint.** `cache/novelty/<namespace>/` con invalidación manual por namespace. No usar caché unificado ni SQLite.
    - Doc: `decisions.md` §2026-06-09

13. **Umbral D3 θ = 0.5.** Placeholder declarado. Las distancias se reportan crudas (valor de Jaccard sin threshold binario). Calibración contra T07/T08/T09 bloqueada por colapso T09. Wontfix v1.
    - Doc: `types.py:138`, `decisions.md` §Out of scope v1

14. **T14 / aesop budget insuficiente.** `aesop` necesita ~215s pero el budget es 30s. Falso negativo conocido. Wontfix v1: la trivialidad es relativa al presupuesto.
    - Doc: `decisions.md` §Out of scope v1, `limitations.md` L5

15. **Demo HF Spaces en alcance**, secuenciada después de Run 001-b + controles.
    - Doc: `decisions.md` §Out of scope v1

---

## 6. CONTRADICCIONES Y ZONAS GRISES

Las contradicciones 1–6 listadas en la versión anterior de este documento fueron resueltas en la sesión de limpieza del 2026-07-12 (commit posterior a `9ad7254`). Resumen:

1. ~~`check_premise_distance` dead code~~ → Ya no existía en el código fuente; docs corregidos (CLAUDE.md, PROJECT_STATE.md).
2. ~~Campos deprecated en D3Result~~ → `premisas_candidato`/`premisas_nueva` eliminados de `types.py`.
3. ~~Orquestador duplicado~~ → `check_novelty_verdict_simple` y su `__main__` eliminados de `d1_existence.py`.
4. ~~`src/novelty/` congelado vs parcheado~~ → CLAUDE.md regla 2 reescrita: "no se modifica al paso; solo mediante fix-packs explícitos".
5. ~~Columnas eval_set.csv no documentadas~~ → `docs/eval_set_schema.md` creado.
6. ~~T23 expectativa vs resultado~~ → `eval_set.csv` actualizado con nota del resultado observado.

### Zonas grises remanentes

7. **Umbral D3 θ = 0.5: ¿espec fija o calibrable?** La spec dice "empezar con 0.5 y calibrar". `types.py` hardcodea 0.5. La calibración nunca ocurrió (bloqueada por colapso T09). Decisión tomada 2026-07-12: placeholder declarado, distancias se reportan crudas. Wontfix v1.
   - Doc: `metric_spec.md`, `types.py`, `decisions.md` §Out of scope

8. **D2 — T14: budget insuficiente para `aesop`.** FN conocido sin resolver. Decisión tomada 2026-07-12: wontfix v1, se reporta como hallazgo.
   - Doc: `results_log.md` §Día 5, `decisions.md` §Out of scope
