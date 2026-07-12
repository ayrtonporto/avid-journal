# EVAL_SET_SCHEMA — Columnas esperadas por run_eval_full.py

**Archivo leído:** `paper/eval_set.csv`
**Script que lo consume:** `scripts/run_eval_full.py` → `load_eval_set()`

## Columnas del CSV

| Columna | Tipo | Requerida | Uso en run_eval_full.py |
|---|---|---|---|
| `id` | `str` | Sí | Identificador del teorema (T01, T02, ..., T26). Se filtra si está vacío o empieza con `TBD`. Los IDs con sufijo `b` (T07b, T08b, T09b) se omiten si existe el `a` correspondiente (solo se evalúa el type-level, no cada prueba). |
| `par_id` | `str` | No | ID del par para D3 (T07, T08, T09). No usado directamente por run_eval_full.py. |
| `enunciado_informal` | `str` | Sí | Texto en español del enunciado. Se usa como `block["content_latex"]` para D1 (Leandex y C_I). **NOTA HISTÓRICA:** antes de 2026-06-27 el CSV usaba columnas `title`/`content_latex` que no existían; se corrigió mapeando a `enunciado_informal`. |
| `categoria` | `str` | No | Categoría del eval set. No usado por el script. |
| `rama_arbol_testeada` | `str` | No | Rama del árbol de decisión que se espera probar. No usado por el script. |
| `etiqueta_esperada` | `str` | No | Veredicto esperado. No usado por el script (solo para referencia humana). |
| `notas` | `str` | No | Notas libres. No usado por el script. |

## Cómo construye el bloque para D1

```python
block = {
    "title": row["enunciado_informal"][:100],   # primeros 100 chars como título
    "content_latex": row["enunciado_informal"],  # texto completo
}
```

## Cómo obtiene el enunciado Lean para D2

El enunciado Lean NO viene del CSV. Se lee de `paper/eval_set_lean_statements.md`, que tiene secciones por teorema:

```markdown
## T01 — Título
```lean
theorem T01 : <tipo> := sorry
```

Imports:
import Mathlib...
```

El script extrae el tipo (`theorem TXX : <type> := sorry`) y los imports del bloque.

## Filtros aplicados

1. **IDs vacíos:** se ignoran
2. **IDs TBD_*:** se ignoran (slots no poblados)
3. **IDs con sufijo `b` (T07b, T08b, T09b):** se ignoran si existe el `a` correspondiente. Esto es correcto porque D2 evalúa el tipo (enunciado), no la prueba. T07a y T07b comparten el mismo tipo.
