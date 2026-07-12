# Audit de Estado — Bloque de Experimentos con Retirados

**Fecha:** 2026-07-12
**Alcance:** READ-ONLY. No se modificó, creó ni borró ningún archivo.
**Contexto:** Run 001 con defectos, fixes aplicados, 001-b pendiente de ejecución.

---

## 1. INVENTARIO

### 1.1 Árbol de archivos del bloque

```
config/
├── retracted_candidates.yaml          # 33 candidatos (output de build_retracted_dataset.py)
├── _retracted_limited.yaml            # Subset/resumen (2 entradas visibles, 33 total según header)
├── control_candidates.yaml            # 26 pares × 2 controles
├── experiment_run_001.yaml            # 5 retirados + 5 controles para el smoke test
│
scripts/
├── build_retracted_dataset.py         # FASE 1-2: arXiv API → candidates YAML (531 líneas)
├── build_control_candidates.py        # FASE 3: matched controls
├── build_selection_dossier.py         # FASE 4: cached LaTeX → fichas Markdown (453 líneas)
├── run_experiment_001.py              # Ejecución del pipeline (552 líneas)
├── _extract_control_stmts.py          # Helper: extraer statements de caches ctrl (38 líneas)
│
docs/
├── retracted_dataset_report.md        # Reporte de los 33 candidatos
├── selection_dossier.md               # 26 fichas con evidencia por paper (1212 líneas)
├── experiment_run_001_report.md       # Reporte de Run 001 (131 líneas)
├── run_001_review.md                  # Revisión manual de Ayrton post-Run 001 (356 líneas)
│
results/
├── experiment_run_001.csv             # Output de Run 001 (5 filas)
├── d3_validation.csv                  # (no es parte del bloque; preexistente)
├── probe_theoremsearch.txt            # (no es parte del bloque; preexistente)
│
cache/retracted_dataset/
├── meta_*.json                        # Metadatos de caché (~50 archivos)
├── src_*/                             # Fuentes .tex descargados de arXiv
├── ctrl_meta_*.json                   # Metadatos de controles cacheados
├── ctrl_src_*/                        # Fuentes .tex de controles cacheados
│
src/novelty/mathlib_checker.py         # PARCHED (working tree, not committed)
src/novelty_v2/dimensions/d1_existence.py   # PARCHED
src/novelty_v2/orchestrator.py              # PARCHED
src/novelty_v2/types.py                     # PARCHED
src/novelty_v2/dimensions/d3_premises.py    # PARCHED
src/novelty/theoremsearch.py           # UNTRACKED (nuevo)
scripts/run_eval_full.py               # PARCHED
pytest.ini                             # PARCHED
```

### 1.2 Estado de Git

**Branch:** `main` (HEAD: `f29de4e`, 2026-07-03)
**Working tree:**
- **7 modified** (no staged): `mathlib_checker.py`, `d1_existence.py`, `orchestrator.py`, `types.py`, `d3_premises.py`, `run_eval_full.py`, `pytest.ini`
- **43 untracked**: todos los scripts del experimento, configs, docs, results, tests nuevos, theoremsearch.py, y módulos nuevos (`informal_match.py`, `premise_extraction.py`, `premise_autolocation.py`)

**Hallazgo crítico:** NINGÚN archivo del bloque de experimentos está commiteado. Las fixes están como modificaciones en el working tree desde 2026-07-06.

---

## 2. VERIFICACIÓN DE LOS 3 FIXES POST-RUN-001

### 2a. Persistencia del código Lean generado

**Estado:** ✅ FIX APLICADO (working tree)

**Evidencia:**
- `scripts/run_experiment_001.py:242-272` — función `_verify_lean()`:
  ```python
  # Líneas 250-255
  safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", arxiv_id)
  formal_dir = _REPO_ROOT / "results" / "formalizations"
  formal_dir.mkdir(parents=True, exist_ok=True)
  lean_file = formal_dir / f"{safe_id}.lean"
  lean_file.write_text(lean_code, encoding="utf-8")
  # THEN compile — no deletion on success
  ```
  El archivo se escribe ANTES de compilar y NO se borra si la compilación es exitosa.

- `scripts/run_experiment_001.py:224-226` — el path se registra en el resultado:
  ```python
  result["lean_path"] = str(
      _REPO_ROOT / "results" / "formalizations" / f"{safe_id}.lean"
  )
  ```

**Confirmación de que Run 001 NO tenía esta fix:**
- `results/formalizations/` no existe (verificado con `ls results/`)
- `docs/run_001_review.md:29,95,158,220,295` — para cada paper dice "The generated Lean code was not saved."
- `run_experiment_001.py` es untracked → fue creado/modificado después del último commit (2026-07-03)

**Ubicación de guardado:** `results/formalizations/<arxiv_id_sanitizado>.lean`

### 2b. Scores del buscador formal (Leandex)

**Estado:** ✅ FIX APLICADO (working tree, NO commiteado)

**Evidencia del código ACTUAL (post-fix):**

`src/novelty/mathlib_checker.py:118-196` — función `_extract_matches()`:
- Línea 182: `similarity = None` (default)
- Líneas 170-181: solo extrae `raw_similarity` de campos que la API realmente provee (`similarity`, `score`, `relevance`)
- Línea 183: comentario explícito: `# Leandex v2: no scores — similarity stays None, no synthetic proxy.`

**Evidencia del código VIEJO (pre-fix, en commit `42af896`):**

El `git diff` muestra que las líneas removidas eran:
```python
# Líneas borradas del viejo _extract_matches:
else:
    # Leandex v2 no da puntajes → orden como proxy (1.0, 0.9, 0.8, ...)
    similarity = max(0.0, 1.0 - i * 0.1)
```
Y el docstring viejo decía: "Como Leandex no asigna puntajes, usamos el orden de resultados como proxy de relevancia: el primer resultado es el mejor match (similarity = 1.0), los siguientes decrecen (0.9, 0.8, ...)."

**Código de fallback `exact?`:** `src/novelty_v2/orchestrator.py:228` hardcodea `"similarity": 0.95` para matches vía `exact?`, pero esto es correcto — es un match real encontrado por el tactic, no un score sintético.

**Restos de lógica antigua:** NO ENCONTRADOS. La búsqueda de `1.0 - i` o `0.1` en el código actual no arroja resultados en `mathlib_checker.py`.

**Cómo se comporta el pipeline ahora:** `check_in_mathlib()` (línea 249-271) filtra a `proven` matches, y solo marca `found=True` si al menos un match tiene `similarity >= SIMILARITY_THRESHOLD` (0.85). En Leandex v2 (sin scores), `found` será `False` y se emite un warning: "Returning found=False for manual review."

### 2c. Corpus formal: filtrado de teoremas con `sorry` (statement_only)

**Estado:** ✅ FIX APLICADO (working tree, NO commiteado)

**Detección de `sorry`/`axiom`:**

`src/novelty/mathlib_checker.py:96-115` — función `_proof_status_detect()`:
- Detecta `:= sorry` o `:= by sorry` → `"statement_only"`
- Detecta keyword `axiom` → `"statement_only"`
- Detecta cuerpos de prueba reales (`:= by`, `:= fun`, `:= match`, etc.) → `"proven"`
- Default → `"unknown"`

**Punto de filtrado:**

`src/novelty/mathlib_checker.py:248-249` — en `check_in_mathlib()`:
```python
proven = [m for m in matches if m.proof_status == "proven"]
```
Solo los matches con `proof_status == "proven"` se consideran para determinar `found`.

**Impacto en Run 001 (pre-fix):** El CSV de Run 001 muestra dos matches con `sorry` que NO fueron filtrados:
- `1212.0196v1` → `CongruentNumber.not_congruentNumber_1` (contiene `:= by\n  sorry`)
- `1004.3381v1` → `Green85.green_85` (contiene `:= by\n  sorry`)

Con el fix actual, estos serían `proof_status = "statement_only"` y se excluirían del cómputo de `found`.

---

## 3. ENUNCIADO CORRUPTO: math/0604362v1

### 3.1 La corrupción

**Dossier** (`docs/selection_dossier.md:1141`):
```latex
d(n) ≥ ½|λ_i|^n   and   d(t) ≥ ½ e^{-(1-Re λ_i)t}
```

**Config YAML** (`config/experiment_run_001.yaml:81`):
```latex
d(n) ≤ max_{i≥2} |λ_i|
```

Diferencias:
| Aspecto | Dossier (correcto) | Config YAML (corrupto) |
|---------|-------------------|----------------------|
| Desigualdad | `≥` (lower bound) | `≤` (upper bound) |
| Fórmula | `½|λ_i|^n` | `max_{i≥2} |λ_i|` |
| Parte continua | `d(t) ≥ ½ e^{-(1-Re λ_i)t}` | ausente |

**Severidad:** CRÍTICA. No es un error de notación o escaping LaTeX — es un teorema matemáticamente diferente (dirección opuesta, fórmula diferente).

### 3.2 Origen de la corrupción

**NO fue un script de extracción automática.** Evidencia:

1. `scripts/build_retracted_dataset.py` extrae statements del fuente .tex de arXiv. El dossier (`selection_dossier.md`) se generó con `build_selection_dossier.py`, que usa el mismo fuente cacheado. El dossier tiene el enunciado CORRECTO (línea 1141).

2. `config/experiment_run_001.yaml` fue **editado manualmente** por Ayrton. Los 10 enunciados se copiaron/adaptaron del dossier, no fueron generados por ningún script (no hay script que produzca este YAML).

3. **Hipótesis más probable:** error de transcripción manual al crear el YAML. Posiblemente Ayrton leyó el abstract del paper (que menciona un upper bound diferente) o confundió teoremas del mismo paper (el paper tiene 19 entornos de teorema; el dossier extrajo el #3).

### 3.3 Comparación de TODOS los enunciados: Dossier vs Config YAML

| # | arXiv ID | ¿Coinciden? | Detalle |
|---|----------|-------------|---------|
| 1 | 1609.02090v1 | ⚠️ PARCIAL | Dossier (línea 384): `Z_n ⊂ 2R_2 iff … p ≡ 1 mod 4`. YAML (líneas 12-17): mismo, PERO agrega `and n ≢ 0 mod 16`. El dossier truncó el teorema (el original del PDF incluye la condición mod 16). |
| 2 | 1207.0631v1 | ❌ DIFERENTE | Dossier (línea 704): descomposición en bloque `A ≃ [a [?]; [?] B]`. YAML (líneas 31-35): matriz similar con diagonal `(a, tr(A)-a, 0, ..., 0)`. Son dos lemas DISTINTOS del mismo paper (el dossier extrajo el Lemma 1, el YAML tiene el Lemma 2/key lemma). |
| 3 | 1212.0196v1 | ⚠️ PARCIAL | Dossier (línea 292): incluye "If moreover k is even, then 2m is also a non-congruent number". YAML (líneas 48-51): omite esa cláusula. |
| 4 | 1004.3381v1 | ❌ DIFERENTE | Dossier (línea 659): `f(m) ≤ c·(2m+1)²` axis-parallel lines. YAML (líneas 63-64): `O(m log m)` lines. Son cotas diferentes — posiblemente teoremas distintos del paper. |
| 5 | **math/0604362v1** | **❌ CORRUPTO** | Desigualdad invertida, fórmula diferente. Ver 3.1. |
| 6 | 1501.01654v1 (control) | ⚠️ NO VERIFICADO | Control paper. El dossier tiene la ficha de su par (1609.02090v1) pero no del control mismo. El YAML (líneas 95-105) tiene un enunciado con enumerate truncado (`...`). Posiblemente extraído con `_extract_control_stmts.py` de cached source. |
| 7 | 1101.3431v2 (control) | ⚠️ NO VERIFICADO | Enunciado truncado con `...` en YAML (líneas 113-121). |
| 8 | 1101.3720v1 (control) | ⚠️ NO VERIFICADO | YAML (líneas 129-139): fórmula con `Ω(N^{1/2})`. |
| 9 | 0904.1783v3 (control) | ⚠️ NO VERIFICADO | YAML (líneas 148-155): polyhedra theorem con `...`. |
| 10 | math/0504586v2 (control) | ⚠️ NO VERIFICADO | YAML (líneas 164-173): percolation theorem truncado con `...`. |

**Conclusión:** 2 de 5 retirados tienen enunciados diferentes/sustancialmente editados respecto al dossier (1207.0631v1, 1004.3381v1). 1 está corrupto (math/0604362v1). Los 5 controles no tienen ficha en el dossier (son controles, no retirados), así que no se pudo verificar su fuente.

---

## 3-bis. FORMATO DE ENTRADA DE PAPERS

### a) ¿Qué toma el pipeline como fuente?

**El pipeline de ejecución (`run_experiment_001.py`) NO descarga nada.** Toma el campo `target_theorem` directamente del YAML.

- `scripts/run_experiment_001.py:99-109` — `make_minimal_tex()`: envuelve el `target_theorem` en un documento LaTeX mínimo. No lee PDFs ni fuentes .tex de arXiv.
- `scripts/run_experiment_001.py:202-203` — `formalize_statement()`: envía el LaTeX crudo (truncado a 2000 chars) al prompt de OpenCode API.
- `scripts/run_experiment_001.py:328-331` — TheoremSearch: usa `theorem_latex[:500]` como query textual.

**El arxiv_id solo se usa para:**
- Etiquetado del CSV y report
- Excluir self-matches en TheoremSearch (`run_experiment_001.py:330`)
- Nombre del archivo .lean guardado

**Conclusión:** los enunciados se **pegaron a mano** en el YAML. No hay ingesta automática de PDF ni .tex en el script de ejecución.

### b) ¿Hay extracción de PDF?

**NO.** No se usa ningún extractor de PDF en ningún script del bloque. No hay imports de `pymupdf`, `pdfplumber`, `pdftotext`, ni similares.

### c) Código que SÍ maneja fuente .tex de arXiv

Existe pero NO se usa en el pipeline de ejecución:

| Script | Qué hace | Usado por run_experiment? |
|--------|---------|--------------------------|
| `scripts/build_retracted_dataset.py:156-184` | Descarga `.tar.gz`/`.gz`, descomprime, busca `\begin{theorem}` | ❌ No |
| `scripts/build_selection_dossier.py:38-41` | Extrae `\begin{theorem}...\end{theorem}` vía regex | ❌ No |
| `scripts/_extract_control_stmts.py:8-30` | Extrae primer theorem/proposition de cache ctrl | ❌ No |
| `src/novelty_v2/informal_match.py` | Descarga arXiv source, extrae proof blocks | ❌ No |

**Pattern de extracción usado en el dossier:**
- `build_retracted_dataset.py` → descarga fuente v1 (v1 sobrevive al retiro) → `_extract_arxiv_source()` maneja `.tar.gz` y `.gz` (líneas 156-184)
- `build_selection_dossier.py` → lee el fuente cacheado → regex `\begin{theorem}...\end{theorem}` con soporte para `thm`, `lem`, `prop`, `cor` (líneas 32-39)

### d) Costo de cambiar de "manual YAML" a "extracción automática de .tex"

**Puntos de entrada a modificar:**
1. `scripts/run_experiment_001.py:99-109` — `make_minimal_tex()`: en vez de usar `target_theorem` del YAML, llamaría a una función de extracción.
2. `scripts/run_experiment_001.py:49-94` — `load_config()`: el YAML podría pasar de tener `target_theorem: "..."` a tener `target_theorem_env: 3` (índice del entorno a extraer).

**Funciones a tocar (o crear):**
- Reutilizar `build_selection_dossier.py:38-41` (`_STATEMENT_BLOCK_RE`) o `informal_match.py` para extracción
- El fuente ya está cacheado en `cache/retracted_dataset/src_<hash>/` — no hay que volver a descargar
- Los supuestos downstream (OpenCode prompt espera LaTeX crudo) NO cambian — solo cambia el origen del string

**Riesgos:**
- La extracción automática puede elegir el entorno equivocado (el dossier ya muestra este problema: para 1207.0631v1 extrajo el Lemma 1, no el Lemma 2 que Ayrton quería)
- `\newcommand` personalizadas no se resuelven automáticamente
- El dossier reporta 17 `\newcommand` en 1212.0196v1 y 16 en 1207.0631v1

**Costo estimado:** bajo-medio. La infraestructura de descarga y caché ya existe. El trabajo principal es decidir qué entorno extraer (primer `\begin{theorem}`? ¿el que tiene `\label{thm:main}`? ¿selección manual por índice en el YAML?).

---

## 4. ESTADO POR PAPER (Run 001)

| # | arXiv ID | Role | Enunciado en YAML | Lean persistido | Leandex match (C_F) | Top-5 informal (C_I) | Veredicto |
|---|----------|------|-------------------|-----------------|--------------------|--------------------|-----------|
| 1 | 1609.02090v1 | retracted | ✅ (extendido) | ❌ no guardado | `Nat.eq_sq_add_sq_iff` (sim=1.0 sintético) | max 0.645 | MATCH_ENCONTRADO_PENDIENTE_D3 |
| 2 | 1207.0631v1 | retracted | ⚠️ diferente del dossier | ❌ no guardado | `Matrix.scalar_apply` (sim=1.0 sintético) | max 0.754 | MATCH_ENCONTRADO_PENDIENTE_D3 |
| 3 | 1212.0196v1 | retracted | ⚠️ truncado | ❌ no guardado | `CongruentNumber.not_congruentNumber_1` ⚠️ tiene `sorry` (sim=1.0 sintético) | max 0.674 | MATCH_ENCONTRADO_PENDIENTE_D3 |
| 4 | 1004.3381v1 | retracted | ❌ cota diferente | ❌ no guardado | `Green85.green_85` ⚠️ tiene `sorry` (sim=1.0 sintético) | max 0.764 | MATCH_ENCONTRADO_PENDIENTE_D3 |
| 5 | math/0604362v1 | retracted | ❌ CORRUPTO | ❌ no guardado | `eVariationOn.sum_le` (sim=1.0 sintético) | max 0.756 | MATCH_ENCONTRADO_PENDIENTE_D3 |
| 6 | 1501.01654v1 | control | ✅ (truncado con ...) | — (confirmed:false) | — | — | — |
| 7 | 1101.3431v2 | control | ✅ (truncado con ...) | — (confirmed:false) | — | — | — |
| 8 | 1101.3720v1 | control | ✅ | — (confirmed:false) | — | — | — |
| 9 | 0904.1783v3 | control | ✅ (truncado con ...) | — (confirmed:false) | — | — | — |
| 10 | math/0504586v2 | control | ✅ (truncado con ...) | — (confirmed:false) | — | — | — |

**Notas sobre la tabla:**
- Los 5 controles tienen `confirmed: false` → no se ejecutaron en Run 001.
- Los matches Leandex de Run 001 usan scores sintéticos (1.0) — con el fix actual, `check_in_mathlib()` devolvería `found=False` para todos ellos (Leandex v2 no provee scores reales).
- Los matches para papers 3 y 4 (`CongruentNumber.not_congruentNumber_1`, `Green85.green_85`) contienen `sorry` → con el fix actual serían `statement_only` y se excluirían.
- Ningún `.lean` fue persistido → con el fix actual se guardarían en `results/formalizations/`.

---

## 5. PENDIENTES Y ANOMALÍAS

### 5.1 Anomalías detectadas en Run 001

| # | Anomalía | Evidencia | Severidad |
|---|----------|-----------|-----------|
| A1 | **Score sintético 1.0 en todos los matches Leandex** | `results/experiment_run_001.csv:2-6` — columna `d1_match_cf` contiene `"similarity":1.0` para los 5 papers | CRÍTICA — invalida todos los veredictos de Run 001 |
| A2 | **Matches Leandex semánticamente incorrectos** | `docs/run_001_review.md:114,178,251,314` — ej: paper 4 (rectangle slicing) matcheó con `Green85.green_85` (Green's open problem), paper 5 (Markov mixing) matcheó con `eVariationOn.sum_le` (bounded variation) | ALTA — el sintético 1.0 hizo que Leandex pareciera encontrar matches donde no los había |
| A3 | **Código Lean no persistido** | `docs/run_001_review.md:29,95,158,220,295` — "The generated Lean code was not saved" para los 5 papers. `results/formalizations/` no existe. | ALTA — imposible verificar fidelidad de la formalización |
| A4 | **2 matches son `statement_only` (contienen `sorry`)** | `results/experiment_run_001.csv:4-5` — `CongruentNumber.not_congruentNumber_1` y `Green85.green_85` tienen `:= by\n  sorry` | ALTA — el pipeline tomó teoremas no probados como "evidencia de existencia previa" |
| A5 | **Enunciado corrupto para math/0604362v1** | Ver §3.1 — desigualdad invertida, fórmula cambiada | CRÍTICA — el pipeline corrió sobre un teorema que no es el del paper |
| A6 | **Enunciados diferentes al dossier para 2/5 retirados** | 1207.0631v1 y 1004.3381v1 tienen teoremas distintos entre dossier y YAML | MEDIA — posible error de transcripción manual |

### 5.2 TODOs y FIXMEs en el código

**No se encontraron TODOs ni FIXMEs explícitos** en los scripts del bloque. Sin embargo:

- `scripts/run_experiment_001.py:106` — el enunciado de 1501.01654v1 termina con `...` (truncado en el YAML).
- `scripts/run_experiment_001.py:121` — ídem para 1101.3431v2.
- `scripts/run_experiment_001.py:154` — ídem para 0904.1783v3.
- `scripts/run_experiment_001.py:173` — ídem para math/0504586v2.
- `scripts/_extract_control_stmts.py:28` — `return m.group(1).strip()[:1000]` trunca a 1000 chars. Si se usó este script para poblar los controles, el truncamiento explicaría los `...`.

### 5.3 Archivos huérfanos o de función desconocida

| Archivo | ¿Usado? | Nota |
|---------|---------|------|
| `config/_retracted_limited.yaml` | Desconocido | Subconjunto de `retracted_candidates.yaml` con solo 2 entradas visibles (probablemente WIP abandonado) |
| `scripts/_extract_control_stmts.py` | Probablemente | El underscore sugiere script auxiliar. Extrae statements de caches de control. Posiblemente se usó para poblar los `target_theorem` de los controles en el YAML. |
| `docs/experiment_run_001_report.md` | Output | Generado por `write_report()` en `run_experiment_001.py:413-498`. Contiene solo los 5 retirados (controles no ejecutados). |
| `docs/run_001_review.md` | Revisión manual | Escrito por Ayrton. Contiene análisis detallado de cada match y las gaps encontradas. |

### 5.4 Inconsistencias Run 001 vs working tree

| Aspecto | Run 001 | Working tree actual |
|---------|---------|-------------------|
| Scores Leandex | Sintéticos (1.0, 0.9, ...) | `None` cuando Leandex no provee |
| `similarity` type | `float` | `Optional[float]` |
| `proof_status` | No existía | `"proven"` / `"statement_only"` / `"unknown"` |
| Filtro `sorry` | No se filtraba | Excluidos del cómputo de `found` |
| Persistencia `.lean` | No se guardaba | Guardado en `results/formalizations/` |
| Veredicto `INCONCLUSIVE` | No existía | Agregado en `types.py` (8 veredictos) |
| TheoremSearch en C_I | No integrado | Integrado en `_run_ci_stage_a()` |
| D3 via `compute_d3` | Stub (`activa=False`) | Implementación completa con filtros y Jaccard |

### 5.5 Recomendaciones para 001-b (NO implementadas — solo observaciones)

1. **Corregir `target_theorem` de math/0604362v1** antes de ejecutar. Usar el enunciado del dossier (línea 1141) o verificarlo contra el PDF original.
2. **Revisar enunciados de 1207.0631v1 y 1004.3381v1** — decidir cuál teorema del paper se quiere testear (el dossier extrae el primer lemma; el YAML actual tiene otros teoremas).
3. **Completar los `...` de los 4 controles** — los enunciados truncados pueden producir formalizaciones incorrectas o triviales.
4. **Prever que con el fix de scores, TODOS los matches Leandex pueden desaparecer** — `check_in_mathlib()` devolverá `found=False` para Leandex v2 sin scores. El pipeline caerá a C_I (TheoremSearch + LLM judge) para todos los papers.
5. **Los controles necesitan `confirmed: true`** para ejecutarse.

---

## Resumen de hallazgos

- **3/3 fixes aplicados** correctamente en el working tree (NO commiteados).
- **Run 001 es inválida** como baseline: scores sintéticos, sin filtro de `sorry`, sin persistencia de código.
- **1 enunciado corrupto** (math/0604362v1), **2 con diferencias sustanciales** vs dossier, **4 controles truncados**.
- **La ingesta es 100% manual** — el YAML se edita a mano. Hay infraestructura de extracción automática de .tex pero no se usa en la ejecución.
- **Todos los archivos del bloque están sin commitear** → riesgo de pérdida de trabajo.
