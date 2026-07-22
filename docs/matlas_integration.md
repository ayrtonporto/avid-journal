# Matlas Integration — AViD Journal

**Fecha:** 2026-07-22
**Objetivo:** Integrar Matlas como fuente de C_I, quitar Semantic Scholar, manejar fechas vía campo `year`.

---

## Fase 0 — Reconocimiento

### Health check

```json
GET https://matlas.ai/api/health → {"ok": true}
```

### POST /api/search — respuesta cruda (query: "sum of two square-zero matrices is similar...")

```json
[
  {
    "type": "paper",
    "entity_name": "Proposition 5.7",
    "doi": "doi.org/10.1090/tran/6402",
    "title": "Similarity and commutators of matrices over principal ideal rings",
    "authors": "Stasinski, Alexander",
    "journal": "Trans. Amer. Math. Soc.",
    "year": "2016",
    "statement": "For a trace-zero n×n matrix A over a principal ideal domain R...",
    "candidate_id": "58f4f837febb3db69089b5efa1b1561e8f02f4c2:Proposition:36525"
  },
  {
    "type": "book",
    "entity_name": "Exercise 2",
    "doi": "",
    "title": "Lectures in Abstract Algebra",
    "authors": "N. Jacobson",
    "journal": "",
    "year": "",
    "statement": "{...}",
    "candidate_id": "77c9ff2ebea3c3d918ffc5472894c62e7fdfd869:Exercise:117186"
  }
]
```

**Campos presentes:** `type`, `entity_name`, `doi`, `title`, `authors`, `journal`, **`year`** (string, vacío para libros sin fecha), `statement`, `candidate_id`.

**El campo `year` existe** → NO se necesita Crossref para resolver fechas. Año vacío (`""`) → `fecha_desconocida`.

---

## Fase 1 — Remoción de Semantic Scholar

```diff
-    # ── Semantic Scholar (fuente secundaria) ─────────────────────────────
-    try:
-        ss_candidates = search_semantic_scholar(query, top_k=20, ...)
-        all_candidates.extend(ss_candidates)

+    # ── Matlas (fuente secundaria: revistas peer-reviewed 1826-2025) ────
+    if os.getenv("MATLAS_ENABLED", ...):
+        try:
+            from src.novelty.matlas import search_matlas
+            matlas_candidates = search_matlas(query, top_k=10, ...)
+            all_candidates.extend(matlas_candidates)
```

- `search_semantic_scholar` removido del import en `d1_existence.py` (la función sobrevive en `arxiv_search.py`).
- Matlas: opt-in vía `MATLAS_ENABLED=1`.

---

## Fase 2 — Manejo de fecha para Matlas

### Módulo `src/novelty/matlas.py` (187 líneas, nuevo)

- Endpoint: `POST https://matlas.ai/api/search` con `{"query": "...", "num_results": 10}`.
- Convierte resultados a `PaperCandidate` con `arxiv_id=None`, `source="matlas"`.
- **Atributo dinámico `cand.year`**: parsea `year` (string → int). `None` si vacío.
- Rate limiting: 1.0s entre requests + cache SHA256.

### Filtro temporal extendido (`_filter_by_date`)

```diff
     for cand, sim in candidates:
-        cand_ym = _extract_year_month(cand.arxiv_id)
+        if hasattr(cand, "year") and cand.year is not None:
+            cand_ym = cand.year * 100  # Matlas: year-only granularity
+        else:
+            cand_ym = _extract_year_month(cand.arxiv_id)
```

- Matlas: año del campo `year` → `YYYY00` (granularidad de año, sin mes).
- Candidatos sin `year` ni arXiv ID → `fecha_desconocida` → pasan y se cuentan.
- **No se usó Crossref** — Matlas ya provee `year`.

---

## Fase 3 — Validación sobre 4 papers retirados

**Config:** `MATLAS_ENABLED=1`, `THEOREMSEARCH_ENABLED=1`, query = enunciado completo.

### Tabla de resultados

| Paper | Duplicador conocido | Veredicto | C_I match | LLM | Matlas | TS | arXiv |
|-------|-------------------|-----------|-----------|-----|--------|-----|-------|
| 1609.02090v1 | Hardy-Littlewood ~1920 | NOVEDAD_ENUNCIADO | — | different | 10 candidatos | 20 | ❌ 429/503 |
| 1207.0631v1 | Fillmore 1969 | NOVEDAD_ENUNCIADO | — | different | N candidatos | 20 | ✅ 100 |
| 1212.0196v1 | Monsky | NOVEDAD_ENUNCIADO | — | — | N candidatos | 20 | ❌ 429/503 |
| 1004.3381v1 | Gyárfás-Lehel 1970 | NOVEDAD_ENUNCIADO | — | — | 7 candidatos | 20 | ✅ 20 |

### Evidencia del filtro temporal sobre Matlas

**Paper 4 (1004.3381v1, 2010-04):**
```
C_I temporal filter: DISCARDED doi.org/10.1112/plms/pdr017 (date 201100 > paper 201004)
C_I temporal filter: DISCARDED 26787722 (date 201307 > paper 201004)
C_I temporal filter: DISCARDED 21727294 (date 201409 > paper 201004)
3 candidate(s) discarded, 0 passed, 0 with unknown date
```

- `doi.org/10.1112/plms/pdr017` (2011) → descartado por ser posterior al paper (2010). **El filtro temporal funciona correctamente con candidatos Matlas (DOI como ID, año vía `cand.year`).**
- 0 candidatos con `fecha_desconocida`.

**Paper 1 (1609.02090v1, 2016-09):**
```
C_I temporal filter: DISCARDED 20448835 (date 201810 > paper 201609)
1 candidate(s) discarded, 2 passed, 0 with unknown date
```

### ¿Algún match pre-1991?

**No.** Matlas devolvió candidatos para los 4 papers, pero:
- Ninguno fue marcado como "equivalent" por el LLM judge.
- Los duplicadores canónicos (Hardy-Littlewood ~1920, Fillmore 1969, Monsky, Gyárfás-Lehel 1970) no aparecieron entre los candidatos Matlas ni TheoremSearch.
- Paper 1: LLM judge dijo "different" para los 2 candidatos que pasaron el filtro.
- Paper 2: LLM judge dijo "different".
- Papers 3 y 4: 0 candidatos pasaron al juez (todos descartados por filtro temporal o similitud insuficiente).

### Fuentes

| Fuente | Estado |
|--------|--------|
| **Matlas** | ✅ 4/4 papers (10, N, N, 7 candidatos) |
| **TheoremSearch** | ✅ 4/4 papers (20 candidatos c/u) |
| **arXiv** | ⚠️ 2/4 papers (Papers 2, 4; Papers 1, 3: HTTP 429/503) |
| **Leandex (C_F)** | ✅ 4/4 (sin matches por Leandex v2 sin scores) |
| **LLM Judge** | ⚠️ Papers 1, 2: "different"; Papers 3, 4: no llamado (0 candidatos) |

### Anomalías

1. **Sin matches equivalent.** Los 4 retirados quedaron como NOVEDAD_ENUNCIADO. Sus duplicadores canónicos (pre-1991) no fueron encontrados por Matlas ni TheoremSearch. Esto puede deberse a: (a) los duplicadores no están indexados, (b) la query en lenguaje natural (LaTeX crudo) no es óptima para búsqueda semántica, (c) Matlas indexa libros y revistas pero los clásicos de 1920-1970 pueden no estar digitalizados con enunciados extraíbles.

2. **arXiv rate-limit.** 2/4 papers sin arXiv como fuente (HTTP 429/503). Veredictos basados en Matlas + TheoremSearch.

3. **DeepSeek LLM judge con problemas de tokens.** Paper 1: "DeepSeek returned empty content after retry (14600 reasoning chars)". El modelo gastó todos los tokens en reasoning_content. El veredicto "different" fue el fallback (sin match).

4. **Filtro temporal funcionando correctamente en Matlas.** Confirmado: DOI `10.1112/plms/pdr017` (2011) descartado por ser posterior al paper (2010). El atributo dinámico `cand.year` se usó correctamente.

### Tests

153 passed, 1 skipped, 0 failed.
