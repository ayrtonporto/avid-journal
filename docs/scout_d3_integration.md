# Scout D3 Integration — Phase 1 Reconnaissance

**Date:** 2026-07-03
**Status:** COMPLETED

---

## 1. All calls to `check_premise_distance`

### Definition
- **`src/novelty_v2/dimensions/d3_premises.py:311`** — legacy stub function.

### Import
- **`src/novelty_v2/orchestrator.py:47`** — `from src.novelty_v2.dimensions.d3_premises import check_premise_distance`

### Call sites: **NONE**

`check_premise_distance` is imported but **never called** anywhere in the codebase
(verified by AST call-graph analysis of orchestrator.py and grep across all `.py` files).
It is dead code.

---

## 2. The REAL stub: `_run_d3_if_possible`

### Definition
- **`src/novelty_v2/orchestrator.py:280-310`** — private function, hardcoded `D3Result(activa=False)`.

### Arguments it receives:
| Param | Type | Source |
|-------|------|--------|
| `lean_statement` | `str` | Passed from `check_novelty()` — the Lean type of the candidate theorem |
| `lean_name_existente` | `str` | Extracted from `d1.match_C_F["lean_name"]` — the Mathlib theorem name |
| `d3_star_pairs` | `Optional[Dict[str,str]]` | Passed from `check_novelty()` — pre-computed pair map (unused) |

### Call site:
- **`orchestrator.py:118`** — inside `check_novelty()`, only when `d1.existe_en_C_F` is True.

### What happens with the return value:
The `D3Result` flows into verdict dispatch (lines 124-171):

```python
if d3.pruebas_distantes is True:    → NOVEDAD_DEMOSTRACION
if d3.pruebas_distantes is False:   → NO_NOVEDOSO_redundante
else:                                → MATCH_ENCONTRADO_PENDIENTE_D3
```

The `d3.jaccard` value is used in `razonamiento` string formatting:
```python
f"D3: distancia Jaccard = {d3.jaccard:.2f} > umbral θ = {d3.umbral_theta}"
```

The `d3` is embedded in `NoveltyVerdict` and serialized via `to_dict()` which includes:
- `d3.jaccard`, `d3.umbral_theta`, `d3.pruebas_distantes`
- `d3.n_premisas_candidato`, `d3.n_premisas_nueva` (derived from list lengths)

**Missing from `to_dict()`:** `intersection_size`, `union_size`, `flags`, `premises_a/b_after_filters`
(these are new fields added to D3Result in the previous session).

---

## 3. Does the stub have behavior that `compute_d3` lacks?

| Feature | `check_premise_distance` (stub) | `_run_d3_if_possible` (real stub) | `compute_d3` |
|---------|-------------------------------|-----------------------------------|-------------|
| Returns `activa=False` | Yes | Yes | No — returns `activa=True` |
| Returns `jaccard=None` | Yes | N/A (never called) | Only when sets empty |
| Returns `pruebas_distantes=None` | Yes | N/A | Computed from jaccard > theta |
| Has `umbral_theta` default 0.5 | Yes | N/A | Default from D3Result dataclass |

The pipeline depends on `activa=False` to route to `MATCH_ENCONTRADO_PENDIENTE_D3`.
`compute_d3` always returns `activa=True`. The orchestrator must be updated to handle
the None case (empty sets → INCONCLUSIVE instead of PENDIENTE).

---

## 4. Format gap: strings vs. premise traces

### What the orchestrator has at the D3 call point:
- `lean_statement`: e.g., `"Irrational (Real.sqrt 2)"` — a string, no premise data
- `lean_name_existente`: e.g., `"irrational_sqrt_two"` — a Mathlib identifier, no premise data

### What `compute_d3` expects:
- `premises_a: List[dict]` — each dict has `fullName`, `modName`, `defPath`, `defPos`, `pos`
- `premises_b: List[dict]` — same format
- Optional: `statement_lines_a`, `statement_lines_b`, `blacklist_config_path`

### Gap: **TOTAL**. The orchestrator has NO premise traces at this point.

Premises with `defPath`/`defPos` only exist after running ExtractData on a compiled `.lean` file.
The orchestrator does NOT run ExtractData (it was designed for offline D3 analysis).

### Resolution:
The format gap is expected — D3 was designed for offline evaluation, not real-time.
The integration should support two modes:

1. **Offline eval mode** (used by this task): caller provides pre-extracted premise lists
   via new optional parameters to `check_novelty`. This is how the T08 end-to-end test works.

2. **Real-time mode** (future): when premises are not available, D3 returns INCONCLUSIVE
   (replaces the old MATCH_ENCONTRADO_PENDIENTE_D3 behavior).

### Pivot rule check:
The pivot rule says: "Si descubrís que el formato de premisas NO tiene defPath/defPos, frenar."
This is NOT triggered: the premises from ExtractData DO have defPath/defPos. The issue is
that the orchestrator doesn't HAVE premises yet — it's a data availability gap, not a
format loss. The resolution is to pass premises into the orchestrator from outside.

---

## 5. Callers of `check_novelty` (for impact analysis)

| Caller | File | Passes `d3_star_pairs`? |
|--------|------|------------------------|
| `run_eval_full.py:180` | `scripts/run_eval_full.py` | No |
| `_demo()` in orchestrator | `orchestrator.py:327` | No |
| `d1_existence.py` (via `check_novelty_verdict_simple`) | Different function, not affected | N/A |

The only production caller is `run_eval_full.py`, which does NOT pass any D3 data.
All production runs currently get `MATCH_ENCONTRADO_PENDIENTE_D3` for C_F matches.

---

## 6. Plan for Phase 2

1. Add optional `d3_premises_a`, `d3_premises_b`, `d3_statement_lines_a`, `d3_statement_lines_b`
   parameters to `check_novelty()`.
2. Pass them through to `_run_d3_if_possible()`.
3. In `_run_d3_if_possible`: if premise lists are provided, call `compute_d3`.
4. Update verdict dispatch: handle `jaccard is None` → new verdict path (INCONCLUSIVE).
5. Update `to_dict()` to include new D3 fields.
6. Update `run_eval_full.py` CSV output to include D3 fields.
7. Remove dead `check_premise_distance` import and function.
8. Add integration test for T08 end-to-end.
9. Add test for empty-sets → INCONCLUSIVE.
