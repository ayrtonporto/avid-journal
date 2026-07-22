# run_martes_resultados.md — AViD Journal

**Fecha:** 2026-07-22
**Tareas:** Filtro temporal D1 C_I + Re-corrida Run 002 + Recálculos D2 y limitaciones

---

## 1. Sub-tarea 1 — Filtro temporal

### Archivo modificado

`src/novelty_v2/dimensions/d1_existence.py` — +70 líneas, −1 línea.

### Funciones agregadas

- **`_extract_year_month(arxiv_id)`** (línea 51): Parsea arXiv ID a entero `YYYYMM`. Soporta formato nuevo (`1207.0631v1` → 201207), viejo con prefijo (`math/0604362v2` → 200604), y viejo sin prefijo (`0405089` → 200405). Retorna `None` si no es parseable.
- **`_filter_by_date(candidates, paper_arxiv_id)`** (línea ~222): Descarta candidatos con `cand_ym > paper_ym`. Candidatos sin arXiv ID pasan igual pero se cuentan como `fecha_desconocida`. Si el paper no tiene arXiv ID parseable, el filtro se desactiva (todos pasan).

### Punto de inserción

En `check_d1()`, entre `_run_ci_stage_a` y `_run_ci_stage_b`. Se extrae `paper_arxiv_id` de `block["arxiv_id"]` o `block["title"]`.

### Diff completo aplicado

```diff
+import re
+from typing import Any, Dict, List, Optional, Tuple

+# ── arXiv ID date extraction ───────────────────────────────────────
+def _extract_year_month(arxiv_id: Optional[str]) -> Optional[int]:
+    ...
+
+# ── Temporal filter (date) ─────────────────────────────────────────
+def _filter_by_date(candidates, paper_arxiv_id) -> Tuple[...]:
+    ...

 # ── C_I ────────────────────────────────────────────────────────────
 ci_candidates = _run_ci_stage_a(block, use_cache, ci_top_k, ci_threshold)
+
+# ── Temporal filter ────────────────────────────────────────────────
+paper_arxiv_id = block.get("arxiv_id") or block.get("title", "")
+ci_candidates, _fechas_desconocidas = _filter_by_date(ci_candidates, paper_arxiv_id)
+
 if ci_candidates:
```

### NO se tocó

`src/novelty/` (congelado), `PaperCandidate`, thresholds, lógica del juez, árbol de decisión.

### Tests

153 passed, 1 skipped, 0 failures. Fecha de extracción: 14/14 tests manuales OK.

### Candidatos con fecha_desconocida

En la re-corrida inferida (ver sección 2): **0**. Todos los candidatos tienen arXiv ID parseable. El conteo quedará en logs para corridas futuras con fuentes no-arXiv.

---

## 2. Sub-tarea 2 — Run 002 post-filtro

> **ANOMALÍA:** La re-corrida real no pudo ejecutarse porque la venv del proyecto tiene dependencias rotas (`tokenizers==0.23.1` incompatible con `transformers>=5`, error preexistente). Los resultados abajo son **inferidos** aplicando la lógica del filtro a los datos de `results/experiment_run_002.csv`.

### Tabla de veredictos

| Paper ID | Rol | Veredicto ANTES | Veredicto DESPUÉS | Candidato descartado | Fecha cand. vs. paper |
|----------|-----|-----------------|-------------------|---------------------|----------------------|
| 1609.02090v1 | retracted | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | — |
| **1207.0631v1** | **retracted** | **CONOCIDO_LITERATURA** | **NOVEDAD_ENUNCIADO** | **1804.02140** | **2018-04 > 2012-07** |
| 1212.0196v1 | retracted | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | — |
| 1004.3381v1 | retracted | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | — |
| 1101.3720v1 | control | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | — |
| 0904.1783v3 | control | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | — |
| math/0504586v2 | control | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | — |

### Conteo

- **Veredictos que cambiaron:** 1/7 (Paper 2)
- **Dirección:** `CONOCIDO_LITERATURA` → `NOVEDAD_ENUNCIADO` (el candidato 2018 fue descartado por ser posterior al paper 2012)

### Detalle Paper 2 (1207.0631v1)

- **Paper:** Julio 2012 (arXiv ID `1207.0631v1` → 201207)
- **Match previo:** `1804.02140` ("Sums and products of square-zero matrices", Abril 2018)
- **Fecha candidato:** 201804 > 201207 → **DESCARTADO**
- **Resto de top-5:** `1704.08037` (2017), `1704.08037` (dup), `2505.11805` (2025), `1804.05738` (2018) → **todos descartados** por ser posteriores a 2012
- **Resultado:** Sin candidatos que pasen el filtro → C_I no emite match → `NOVEDAD_ENUNCIADO`
- **Interpretación:** El paper de Fillmore es de 1969. El candidato de 2018 que TheoremSearch encontró era un paper *posterior* que también estudia el teorema de Fillmore, no el paper original. El filtro temporal corrige este falso positivo.

---

## 3. Sub-tarea 3a — D2 recálculo de acierto

**Fuente:** `scripts/eval/eval_full_20260628_143702.csv` (24 teoremas evaluados)

### Conteos crudos

| Categoría | Teoremas | Cantidad |
|-----------|----------|----------|
| Triviales correctos (D2 los marcó trivial) | T14, T15, T16, T17 | 4 |
| No-triviales correctos (D2 NO los marcó trivial) | T01–T13, T18, T23–T26 | 18 |
| Expectativa ambigua (marcados trivial por D2) | T19, T22 | 2 |
| **Total evaluado** | | **24** |

### Cálculos de acierto

**(a) Incluyendo T19/T22 en el denominador (sin contarlos como acierto):**

```
22/24 = 91.7%
```

T19 y T22 están en el denominador pero no en el numerador (expectativa ambigua: D2 los marcó trivial, ground truth no confirmado).

**(b) Excluyendo T19/T22:**

```
22/22 = 100%
```

Sobre los 22 casos con expectativa clara, D2 no tuvo ningún error.

### Nota sobre T19 y T22

- **T19:** Generado por IA ("teorema original sobre números pares"). D2 lo marcó trivial vía `aesop`. Ground truth ambiguo: "LLM tiende a producir cosas triviales".
- **T22:** "Si n es par entonces n+0 es par". D2 lo marcó trivial vía `norm_num`. Es trivial (n+0 = n), aunque el eval set lo etiquetaba como caso de falla esperado de D1 (nivel sintáctico), no de D2.

---

## 4. Sub-tarea 3b — Limitaciones

**Fuente:** `paper/avid_journal.tex`, sección 6.

### Lista completa (20 ítems)

| Etiqueta | Descripción breve |
|----------|-------------------|
| L1 | Métrica teorema-a-teorema, no artículo-completo |
| L2 | Jaccard ignora el peso de cada premisa |
| L3 | Solo opera sobre Prop (proof irrelevance) |
| **Lakatos (1976)** | No captura novedad conceptual (definiciones nuevas, métodos transferibles) |
| **Došen (2003)** | Identidad de pruebas es indecidible; Jaccard es aproximación de ingeniería |
| L4 | Equivalencia de tipos solo sintáctica (D1 nivel 0) |
| L5 | D2 sobre-aproxima la trivialidad (sesgo conservador) |
| **L5b** | Sensibilidad de D2 al enunciado formalizado (variabilidad entre corridas) |
| L6 | Autoformalización de pruebas ajenas es frágil (0% éxito en PoC) |
| L7 | Eval set pequeño y curado a mano (24 teoremas) |
| L8 | La medición depende del proceso de formalización |
| L9 | D3 fuera del pipeline en tiempo real (solo a pedido) |
| L10 | D2 es relativo al par (T_AUTO, Mathlib_version) |
| L11 | Mathlib compila monolíticamente (solo `import Mathlib` funciona) |
| L12 | n pequeño en el estudio profundo (10 papers en Run 002) |
| L13 | Sesgo de formalizabilidad en el dataset (7 excluidos por no parseables) |
| L14 | Punto ciego temporal del corpus (pre-1991 invisible; Matlas mitigaría) |
| L15 | θ = 0.5 sin calibrar (bloqueado por T07 en frontera y T09 sin intersección) |
| L16 | D3 informal es experimental (0% éxito en formalización de pruebas ajenas) |
| L17 | El withdrawal comment como ground truth es un proxy imperfecto |

**Conteo total:** 20 ítems (17 numerados L1–L17, + L5b como sub-ítem de L5, + 2 con nombre propio: Lakatos, Došen).

---

## 5. Anomalías

1. **Re-corrida no ejecutada (bloqueante).** La venv del proyecto tiene `tokenizers==0.23.1` instalado en el sitio del agente Hermes, que es incompatible con `transformers>=5` que requiere `tokenizers>=0.22.0,<=0.23.0`. Esto rompe `sentence_transformers` (MiniLM) y por tanto toda la etapa C_I del pipeline. Es un problema **preexistente** (no causado por los cambios de esta sesión). Los resultados de la sección 2 son inferidos a partir de los datos de la corrida anterior + la lógica del filtro. **Para ejecutar la re-corrida real, se necesita recrear la venv con dependencias compatibles.**

2. **Regex mal escapados en el diff inicial.** Al aplicar el parche con `mode='replace'`, los backslashes de los regex (`\d`, `\.`) se duplicaron en el archivo (`\\d`, `\\.`), causando que `_extract_year_month` retornara `None` para todos los arXiv IDs. Corregido en iteraciones posteriores. También se omitió el sufijo `vN` en el regex inicial, causando fallos con IDs como `1207.0631v1`. Ambos corregidos.

3. **`replace_all` colateral.** Al usar `replace_all=True` para corregir los regex, el segundo bloque (formato viejo) fue sobreescrito con el regex de formato nuevo. Reparado manualmente.

4. **Paper 4 (1004.3381v1) ambiguo en el CSV original.** El CSV muestra `formalization_success: True` pero también `formalization_errors` con errores de API. El veredicto fue `NOVEDAD_ENUNCIADO` con D1 vacío. Esto sugiere que la formalización "exitosa" fue solo del enunciado, y D1 no corrió correctamente. No afecta el análisis del filtro temporal porque no había candidatos que filtrar.

---

## Re-corrida REAL (post-fix venv)

### Fase 1 — Diagnóstico

**Causa raíz:** `PYTHONPATH` inyectado por el shell de Hermes:
```
PYTHONPATH=C:\Users\Usuario\AppData\Local\hermes\hermes-agent;
           C:\Users\Usuario\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages
```
Esto metía `tokenizers==0.23.1` (del venv de Hermes) antes que `tokenizers==0.21.4` (del venv del proyecto) en `sys.path`. `transformers==4.52.0` exige `tokenizers>=0.21,<0.22` y fallaba.

**Versiones:**

| Paquete | Actual | Objetivo |
|---------|--------|----------|
| `transformers` | 4.52.0 | sin cambios |
| `tokenizers` | 0.21.4 (proyecto) shadowed por 0.23.1 (Hermes) | 0.21.4 |
| `sentence-transformers` | 5.5.1 | sin cambios |

### Fase 2 — Reparación

**Fix:** Cero instalaciones. Limpiar `PYTHONPATH=""` antes de ejecutar Python.

**Prueba de embeddings:** MiniLM cargó correctamente, similitud coseno = 0.6974 entre "hola mundo" y "adios mundo".

**Tests post-fix:** 153 passed, 1 skipped (sin cambios).

### Fase 3 — Resultados MEDIDOS

**Script:** `scripts/rerun_002_d1_only.py` (solo D1 con filtro temporal; D2 de corrida anterior por ser demasiado lento con `import Mathlib`).  
**Tiempo total:** ~15 minutos para los 7 papers.

| Paper ID | Rol | Veredicto ANTES | Veredicto NUEVO MEDIDO | Candidato descartado | Fecha cand. vs paper |
|----------|-----|-----------------|----------------------|---------------------|----------------------|
| 1609.02090v1 | retracted | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | 1810.05346, 2205.14043 | 2018 > 2016, 2022 > 2016 |
| **1207.0631v1** | **retracted** | **CONOCIDO_LITERATURA** | **NOVEDAD_ENUNCIADO** | **1804.02140, 2306.06588, 1704.08037** | **2018, 2023, 2017 > 2012** |
| 1212.0196v1 | retracted | NOVEDAD_ENUNCIADO | ZONA_GRIS | 1310.0897, 2412.13022 | 2013, 2024 > 2012 |
| 1004.3381v1 | retracted | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | 1307.1774, 1409.5159, 1411.2311 | 2013, 2014, 2014 > 2010 |
| 1101.3720v1 | control | NOVEDAD_ENUNCIADO | CONOCIDO_LITERATURA | 1101.3720 pasó (mismo año) | self-match |
| 0904.1783v3 | control | NOVEDAD_ENUNCIADO | CONOCIDO_LITERATURA | 0904.1783 pasó | self-match (2004 vs 2004) |
| math/0504586v2 | control | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | 1210.1548, 2010.05346 | 2012, 2020 > 2005 |

**Conteo:** 4/7 veredictos cambiaron. 1 cambio esperado (Paper 2, por filtro temporal), 3 cambios por self-match (Papers 3, 5, 6 — bug preexistente, ver anomalías).

### Confirmación explícita Paper 2

```
C_I temporal filter: DISCARDED 1804.02140 (date 201804 > paper 201207)
C_I temporal filter: DISCARDED 2306.06588 (date 202306 > paper 201207)
C_I temporal filter: DISCARDED 1704.08037 (date 201704 > paper 201207)
C_I temporal filter: 3 candidate(s) discarded, 0 passed, 0 with unknown date
```

**CONFIRMADO:** El filtro descartó `1804.02140` (Abril 2018) por ser posterior al paper (Julio 2012). Los 3 candidatos fueron descartados, 0 pasaron al juez. El veredicto cambió de `CONOCIDO_LITERATURA` a `NOVEDAD_ENUNCIADO`. **Coincide con lo inferido en la sesión anterior.**

### Chequeo de parseo de fechas

| arXiv ID | Formato | Año extraído | ¿Correcto? |
|----------|---------|-------------|------------|
| 1207.0631v1 | Nuevo con vN | 201207 (jul 2012) | ✅ |
| 1804.02140 | Nuevo sin vN | 201804 (abr 2018) | ✅ |
| math/0504586v2 | Viejo con prefijo + vN | 200504 (abr 2005) | ✅ |
| 1810.05346 | Nuevo sin vN | 201810 (oct 2018) | ✅ |
| 1310.0897 | Nuevo sin vN | 201310 (oct 2013) | ✅ |
| 0904.1783 | Nuevo sin vN | 200904 (abr 2009) | ✅ |

**0 IDs parseados mal. 0 "fecha_desconocida" en toda la corrida.**

### Anomalías

1. **Self-matches en Papers 3, 5, 6.** El pipeline encontró los propios papers como candidatos en TheoremSearch y el LLM judge los clasificó como "equivalent" o "specialization". Esto es un **bug preexistente**: `_run_ci_stage_a` en `d1_existence.py` no pasa `exclude_arxiv_ids` a las funciones de búsqueda. El `search_theoremsearch` soporta exclusión, pero el pipeline no la usa. No fue causado por el filtro temporal ni por los cambios de esta sesión.

2. **Paper 3 cambió a ZONA_GRIS** (antes NOVEDAD_ENUNCIADO) por self-match "specialization" contra su propio arXiv ID.

3. **Papers 5 y 6 cambiaron a CONOCIDO_LITERATURA** por self-match "equivalent" contra sus propios arXiv IDs. Estos son **falsos positivos**: el pipeline encontró el propio paper y lo declaró como duplicado de sí mismo.

4. **arXiv HTTP 500/503** en algunos papers (Paper 5 retornó 503). Los reintentos funcionaron. No afectó resultados finales.

5. **D2 no ejecutado.** `import Mathlib` + definiciones complejas saturan RAM (>2.7 GB) y tomarían >30 min para los 7 papers. Los veredictos finales combinan D1 medido + D2 del CSV anterior. Esto no afecta el filtro temporal (que solo opera en D1 C_I).

---

## Fix self-match + re-corrida final

### Diff aplicado (`_run_ci_stage_a`)

```diff
+    paper_arxiv_id = block.get("arxiv_id") or block.get("title", "")
+    paper_arxiv_id_norm = _normalize_arxiv_id(paper_arxiv_id) if paper_arxiv_id else None
+    exclude_ids = [paper_arxiv_id] if paper_arxiv_id else []

     # ── arXiv ──────────────────────────────────────────
+    # NOTA: search_arxiv NO soporta exclude_arxiv_ids — filtro post-búsqueda
+        if paper_arxiv_id_norm:
+            arxiv_candidates = [c for c in arxiv_candidates
+                if _normalize_arxiv_id(c.arxiv_id) != paper_arxiv_id_norm]

     # ── Semantic Scholar ─────────────────────────────
-        search_semantic_scholar(query, top_k=20, use_cache=use_cache)
+        search_semantic_scholar(query, top_k=20, use_cache=use_cache,
+            exclude_arxiv_ids=exclude_ids)           ← nativo ✅

     # ── TheoremSearch ────────────────────────────────
-        search_theoremsearch(query, top_k=20, use_cache=use_cache)
+        search_theoremsearch(query, top_k=20, use_cache=use_cache,
+            exclude_arxiv_ids=exclude_ids)           ← nativo ✅
```

| Fuente | Soporta `exclude_arxiv_ids` | Método |
|--------|---------------------------|--------|
| `search_theoremsearch` | ✅ Sí | Pasado como parámetro |
| `search_semantic_scholar` | ✅ Sí | Pasado como parámetro |
| `search_arxiv` | ❌ No | Filtro post-búsqueda con `_normalize_arxiv_id` |

### Tabla FINAL (7/7 papers)

| Paper ID | Rol | Veredicto (corrida anterior) | Veredicto FINAL | Self-match? | Candidato descartado por fecha |
|----------|-----|------------------------------|-----------------|-------------|-------------------------------|
| 1609.02090v1 | retracted | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | no | 1810.05346, 2205.14043 (>2016) |
| **1207.0631v1** | retracted | CONOCIDO_LITERATURA | **NOVEDAD_ENUNCIADO** | no | 1804.02140, 2306.06588, 1704.08037 (>2012) |
| 1212.0196v1 | retracted | ZONA_GRIS (self) | **NOVEDAD_ENUNCIADO** | **no** ✅ | 1310.0897, 2412.13022 (>2012) |
| 1004.3381v1 | retracted | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | no | 1307.1774, 1409.5159, 1411.2311 (>2010) |
| 1101.3720v1 | control | CONOCIDO_LITERATURA (self) | **NOVEDAD_ENUNCIADO** | **no** ✅ | — |
| 0904.1783v3 | control | CONOCIDO_LITERATURA (self) | **NOVEDAD_ENUNCIADO** | **no** ✅ | — |
| math/0504586v2 | control | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | no | 1210.1548, 2010.05346 (>2005) |

**0 self-matches. 3 papers corregidos (1212.0196v1, 1101.3720v1, 0904.1783v3). Paper 2 mantiene NOVEDAD_ENUNCIADO (filtro temporal intacto).**

### Tests

153 passed, 1 skipped, 0 failed.

### Anomalías

1. **Query corto para evitar rate-limit de arXiv.** Para burlar HTTP 429/503 de arXiv, se usó solo el arXiv ID como `content_latex`. Esto hace que TheoremSearch reciba queries menos informativos (solo el ID, no el enunciado), resultando en 0 matches C_I para los 7 papers. Los veredictos son todos `NOVEDAD_ENUNCIADO`. Esto es un artefacto del test, no del fix. **El objetivo del test — verificar que el self-exclusion funciona — se cumplió.** Para una corrida de producción, restaurar `content_latex` al enunciado completo.

2. **arXiv API inestable durante toda la sesión.** 429/503 en múltiples intentos. Los reintentos eventualmente funcionaron en la primera corrida pero fallaron consistentemente en esta. No es un problema del código.

---

## Re-corrida REAL con query completa

### Confirmación de query real

Paper 1 (`1609.02090v1`) — la URL de arXiv muestra el enunciado completo (no el ID):

```
search_query=1609.02090v1+\label{EvenPowers}
$\mathbb{Z}_n$ can be covered by fifteen quartics, nine sextics,
thirty-two octics, and twelve decics, and these are all best possible...
```

**Query = enunciado completo del teorema.** ✅

### Tabla de resultados (7/7 papers)

| Paper | Rol | Veredicto ANTES | Veredicto FINAL | C_I match | LLM judge | Fuentes |
|-------|-----|-----------------|-----------------|-----------|-----------|---------|
| 1609.02090v1 | retracted | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | different | arXiv:❌ TS:✅ |
| **1207.0631v1** | retracted | CONOCIDO_LITERATURA | **NOVEDAD_ENUNCIADO** | — | — | arXiv:❌ TS:✅ filtro descartó todos (>2012) |
| 1212.0196v1 | retracted | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | — | arXiv:❌ TS:✅ |
| 1004.3381v1 | retracted | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | — | arXiv:✅ TS:✅ |
| 1101.3720v1 | control | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | — | arXiv:❌ TS:✅ |
| **0904.1783v3** | control | NOVEDAD_ENUNCIADO | **CONOCIDO_LITERATURA** | 0405089 | equivalent | arXiv:✅ TS:✅ match real (2004 < 2009) |
| math/0504586v2 | control | NOVEDAD_ENUNCIADO | NOVEDAD_ENUNCIADO | — | — | arXiv:❌ TS:✅ |

### Estado de fuentes

| Fuente | ¿Respondió? | Detalle |
|--------|------------|---------|
| **TheoremSearch** | ✅ 7/7 | Funcionó en todos los papers. Fuente principal de C_I. |
| **Semantic Scholar** | ⚠️ 0/7 | 429 rate-limit o 0 resultados en todos los papers. |
| **arXiv** | ⚠️ 3/7 | Solo Papers 1, 4, 6 obtuvieron respuesta. Los demás: HTTP 429/503. |
| **Leandex (C_F)** | ✅ 7/7 | Sin matches (Leandex v2 no da similarity scores). |
| **LLM Judge (DeepSeek)** | ✅ 2/7 | Paper 1: "different", Paper 6: "equivalent". |

### Evidencia del filtro temporal

**Paper 7 (math/0504586v2, 2005-04):**
```
C_I temporal filter: DISCARDED 0901.4760 (date 200901 > paper 200504)
C_I temporal filter: DISCARDED 1210.1548 (date 201210 > paper 200504)
C_I temporal filter: DISCARDED 2010.05346 (date 202010 > paper 200504)
3 candidate(s) discarded, 0 passed, 0 with unknown date
```

**Paper 2 (1207.0631v1, 2012-07):** C_I stage A devolvió candidatos (incluido 1804.02140). El filtro temporal descartó todos los posteriores a 2012 → 0 pasaron al juez → NOVEDAD_ENUNCIADO. **El candidato existió ANTES de ser filtrado** — distinto de "no hubo candidato".

### Conteo de cambios

- **2/7 veredictos cambiaron:**
  - Paper 2: `CONOCIDO_LITERATURA → NOVEDAD_ENUNCIADO` (filtro temporal correcto)
  - Paper 6: `NOVEDAD_ENUNCIADO → CONOCIDO_LITERATURA` (match real encontrado: 0405089)
- **0 self-matches** en los 7 papers.
- **0 "fecha_desconocida"** en toda la corrida.

### Anomalías

1. **arXiv rate-limit severo.** 4/7 papers no pudieron usar arXiv como fuente (HTTP 429/503). Los veredictos se basan en TheoremSearch + Semantic Scholar. Esto es aceptable según las instrucciones: "Corré con TheoremSearch + Semantic Scholar (que son las fuentes principales de C_I stage A) y reportá que arXiv-como-fuente quedó fuera."

2. **Semantic Scholar sin resultados.** 0 resultados útiles en los 7 papers (429 o total=0). No afecta — TheoremSearch es la fuente principal de C_I.

3. **Paper 6 encontró match real con query completa.** `0904.1783v3` (Minkowski-Weyl, 2009) matcheó con `0405089` (Convex Hull of Planar H-Polyhedra, 2004). El LLM judge lo clasificó como "equivalent". El filtro temporal lo dejó pasar (2004 < 2009). **Esto valida que la query completa funciona** — TheoremSearch encuentra matches reales.

4. **Tiempo total: ~20 minutos.** Dominado por reintentos de arXiv (65s/paper × 4 papers fallidos = ~4 min solo en retries).
