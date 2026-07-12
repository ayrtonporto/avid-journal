# TheoremSearch API — Scout Report para AViD D1-informal

**Fecha:** 2026-07-03  
**Resultado:** ✅ API accesible y funcional. Proceder con implementación.

## 1. API descubierta

### Endpoint
```
POST https://api.theoremsearch.com/search
Content-Type: application/json
```

### Request
```json
{
  "query": "the square root of 2 is irrational",
  "n_results": 5
}
```

- **`query`**: texto en lenguaje natural (el enunciado del teorema).
- **`n_results`**: número de resultados (probado hasta 50; no hay límite documentado).
- **Sin API key**: la API es pública, no requiere autenticación.
- **Rate limits**: no documentados explícitamente. Se recomienda un intervalo
  conservador de 1.0 s entre llamadas (igual que Semantic Scholar anónimo).

### Response
```json
{
  "theorems": [
    {
      "theorem_id": 26910464,
      "slogan_id": 11646188,
      "name": "Theorem 1.1.",
      "body": "$\\sqrt{2}$ is not rational, i.e., $\\sqrt{2} \\notin \\mathbb{Q}$",
      "slogan": "The square root of two is not a rational number...",
      "theorem_type": "theorem",
      "label": null,
      "link": null,
      "similarity": 0.7213967178587057,
      "score": 0.7213967178587057,
      "has_metadata": false,
      "paper": {
        "paper_id": "open-logic-project_sets-functions-relations_arithmetization",
        "source": "Open Logic Project",
        "title": "Sets Functions Relations: Arithmetization",
        "authors": ["..."],
        "link": "https://builds.openlogicproject.org/open-logic-complete.pdf",
        "year": null,
        "categories": [],
        "citations": 0,
        "journal_published": false
      }
    }
  ]
}
```

### Campos relevantes para AViD
| Campo TS           | Campo PaperCandidate | Nota |
|--------------------|---------------------|------|
| `theorem_id`       | `paper_id`          | ID único del teorema |
| `paper.paper_id`   | `arxiv_id`          | Extraer arXiv ID si `source == "arXiv"` |
| `paper.title`      | `title`             | Título del paper |
| `slogan` + `body`  | `abstract`          | Concatenamos slogan + body |
| `similarity`       | `similarity_score`  | Score de coseno (0-1), asignado directamente |
| `paper.link`       | —                   | URL al paper (arXiv, PDF, etc.) |
| `paper.source`     | `source`            | Fuente: "arXiv", "Open Logic Project", etc. |

## 2. Contrato esperado en D1-informal

El módulo `d1_existence.py` consume fuentes de búsqueda como funciones que
devuelven `List[PaperCandidate]`. La firma canónica (de `arxiv_search.py`):

```python
def search_semantic_scholar(
    abstract: str,
    top_k: int = 20,
    use_cache: bool = True,
    fallback_queries: Optional[Iterable[str]] = None,
    exclude_arxiv_ids: Optional[Iterable[str]] = None,
) -> List[PaperCandidate]:
```

Nuestra función `search_theoremsearch` implementará la misma firma. Las
diferencias semánticas son:

1. **El score viene de la API directamente** — no necesitamos MiniLM para
   re-ranquear (aunque `_run_ci_stage_a` aplica MiniLM sobre todos los
   candidatos combinados, así que el score final se recalcula igual).

2. **arXiv ID**: TheoremSearch no siempre devuelve un `paper_id` con formato
   arXiv. Para papers de arXiv, `paper.paper_id` tiene el formato
   `"2103.03942v2"`. Extraemos el ID base (sin versión). Para fuentes no-arXiv
   (Open Logic Project, Stacks, etc.), asignamos el `paper_id` como
   identificador.

3. **Exclusión del propio paper**: si se pasa `exclude_arxiv_ids`, filtramos
   los resultados cuyo `paper.paper_id` (normalizado) coincida.

## 3. Plan de implementación

### Archivo nuevo: `src/novelty/theoremsearch.py`

```python
def search_theoremsearch(
    query: str,
    top_k: int = 20,
    use_cache: bool = True,
    fallback_queries: Optional[Iterable[str]] = None,
    exclude_arxiv_ids: Optional[Iterable[str]] = None,
) -> List[PaperCandidate]:
```

**Configuración por variables de entorno:**
- `THEOREMSEARCH_API_URL` — default `https://api.theoremsearch.com/search`
- `THEOREMSEARCH_TIMEOUT` — default `30` (segundos)
- `THEOREMSEARCH_MIN_INTERVAL` — default `1.0` (segundos entre llamadas)

**Rate limiting**: mismo patrón que `_ss_rate_limit()` en `arxiv_search.py`.

**Manejo de errores**: timeout, respuesta no-JSON, HTTP error → log WARNING,
devolver `[]`. Nunca lanza excepción.

### Integración en `d1_existence.py` (`_run_ci_stage_a`)

Agregar un tercer bloque try/except después del de Semantic Scholar:

```python
# ── TheoremSearch (fuente terciaria, theorem-level) ─────────────
if os.getenv("THEOREMSEARCH_ENABLED", "").strip().lower() in ("1", "true", "yes"):
    try:
        ts_candidates = search_theoremsearch(query, top_k=20, use_cache=use_cache)
        all_candidates.extend(ts_candidates)
    except Exception as exc:
        logger.warning("TheoremSearch search failed: %s", exc)
```

**Activación por defecto: DESACTIVADA** (`THEOREMSEARCH_ENABLED` no seteada →
no se usa). Esto garantiza que el pipeline actual no se rompe.

### Script probe: `scripts/probe_theoremsearch.py`

Compara Semantic Scholar vs TheoremSearch con 3 enunciados hardcodeados.
Imprime tabla lado a lado con top-5 y tiempos.

## 4. Alternativas exploradas

- **HuggingFace dataset `uw-math-ai/TheoremSearch`**: disponible como plan B
  si la API se cae. Contiene los 9.2M de teoremas; requeriría búsqueda local
  con embeddings (FAISS + Qwen3-Embedding-8B). No se implementa por ahora.

- **MCP server (`https://api.theoremsearch.com/mcp`)**: herramienta para
  agentes AI vía MCP. Menos conveniente que REST para nuestro pipeline Python.

## 5. Verificación rápida

```bash
curl -s -X POST "https://api.theoremsearch.com/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "square root of 2 is irrational", "n_results": 3}' | \
  python -c "import sys,json; d=json.load(sys.stdin); print(len(d['theorems']), 'results')"
# → 3 results
```
