# AViD Journal — Architecture of the Novelty Module

> **Written:** 2026-07-01  
> **Status:** Phase 1 — understanding (no code modified)  
> **Audience:** Ayrton Porto (human reviewer)

---

## 1. Module Overview: Two Layers

The novelty module lives in two directories with a strict relationship:

```
src/novelty/       ← v1, FROZEN. Imported as a dependency, never modified.
src/novelty_v2/    ← v2, ACTIVE. All new code goes here.
```

**Rule:** `src/novelty/` is frozen. Two files were patched in-place (`mathlib_checker.py`, `llm_judge.py`) for Leandex v2 API and DeepSeek migration (2026-06-27), but further modifications are minimized. All orchestration and new dimension code lives in `src/novelty_v2/`.

The v1 module also contains `novelty_checker.py` — a `NoveltyChecker` class that implements an older 5-stage pipeline (Stages 0-3 only). **This is superseded** by `src/novelty_v2/orchestrator.py` and is not used by the eval pipeline. It remains for reference/compatibility but should not be modified.

---

## 2. File Inventory

### 2.1 `src/novelty_v2/` — Active module

| File | Role | Dim | Status |
|------|------|-----|--------|
| `orchestrator.py` | **Main entry point.** Decision tree D2→D1→D3 → `NoveltyVerdict` | All | ✅ **HECHO** — working end-to-end |
| `types.py` | Dataclasses: `Verdict` (7 values), `D1Result`, `D2Result`, `D3Result`, `NoveltyVerdict` | All | ✅ **HECHO** — stable |
| `dimensions/d1_existence.py` | D1: C_F via Leandex + C_I via arXiv/SS/MiniLM/LLM judge | D1 | ✅ **HECHO** — working, with known issue (CI_SIMILARITY_THRESHOLD_A=0.40 produces no candidates) |
| `dimensions/d2_triviality.py` | D2: 6 tactics via `lake env lean` | D2 | ✅ **HECHO** — working, 87% accuracy (20/23) |
| `dimensions/d3_premises.py` | D3: Jaccard distance on premises via ExtractData | D3 | ❌ **STUB** — returns `D3Result(activa=False)` always |
| `__init__.py` | Public API re-exports | — | ✅ |

### 2.2 `src/novelty/` — Frozen dependencies

| File | Role | Used by | Status |
|------|------|---------|--------|
| `mathlib_checker.py` | Leandex API client (SSE parsing, v2 format) | D1 C_F | ✅ **HECHO** — working, patched for Leandex v2 |
| `llm_judge.py` | DeepSeek V4 Flash via OpenCode Go API | D1 C_I stage B | ✅ **HECHO** — working, `temperature=0` |
| `arxiv_search.py` | arXiv + Semantic Scholar search + dedup | D1 C_I stage A | ✅ **HECHO** — working |
| `block_comparator.py` | MiniLM embeddings + cosine similarity | D1 C_I stage A | ✅ **HECHO** — working |
| `_cache.py` | JSON file cache (`cache/novelty/<namespace>/`) | All external calls | ✅ **HECHO** — working |
| `novelty_checker.py` | v1 orchestrator (Stages 0-3) | **NOT USED by v2** | ⚠️ **FROZEN** — superseded |
| `paper_extractor.py` | Extract blocks from arXiv papers | Only v1 orchestrator | ⚠️ **FROZEN** — not used by v2 |
| `__init__.py` | Re-exports v1 classes | — | ✅ |

### 2.3 Supporting files

| File | Role | Status |
|------|------|--------|
| `lean_project/ExtractData.lean` | Standalone Lean 4 premise extractor (519 lines). Traces `.lean` files and outputs `ast.json` with `premises[]` | ✅ **HECHO** — works on Windows |
| `scripts/run_eval_full.py` | Eval harness: runs `check_novelty()` over 24 theorems, checkpointing CSV | ✅ **HECHO** — working |
| `paper/metric_spec.md` | Formal spec of the 3 dimensions + decision tree | ✅ Source of truth |
| `paper/decisions.md` | Design decisions (A/B/C/D) | ✅ Reference |
| `paper/eval_set.csv` | 26 firm + 9 TBD theorems | ✅ Reference |
| `paper/eval_set_lean_statements.md` | Lean 4 types for each eval theorem | ✅ Reference |

---

## 3. Entry Points

### 3.1 Primary: `check_novelty()` in `orchestrator.py`

```python
from src.novelty_v2.orchestrator import check_novelty

result = check_novelty(
    block={"title": "...", "content_latex": "..."},
    lean_statement="Irrational (Real.sqrt 2)",
    lean_project_dir="lean_project",
    lean_imports="import Mathlib.Tactic",
)
# result.veredicto  → Verdict enum
# result.d1 / .d2 / .d3  → dimension results
# result.razonamiento → human-readable trace
```

This is the **only function the eval script calls** (see `scripts/run_eval_full.py` line 38).

### 3.2 Secondary: `check_d1()` in `d1_existence.py`

```python
from src.novelty_v2.dimensions.d1_existence import check_d1

d1_result = check_d1(block, use_cache=True)
# Returns D1Result with existe_en_C_F, existe_en_C_I, matches, etc.
```

Runs the full D1 pipeline (C_F → C_I stage A → C_I stage B). The orchestrator **does not call this** — it calls the internal helpers `_check_cf()`, `_run_ci_stage_a()`, `_run_ci_stage_b()` directly to have finer control over the decision tree.

### 3.3 Legacy: `check_novelty_verdict_simple()` in `d1_existence.py`

This is a **near-duplicate** of `check_novelty()` from before D3 was added to the tree. It does D2→D1 C_F→D1 C_I but always emits `MATCH_ENCONTRADO_PENDIENTE_D3` on C_F match (no D3 branch). **Kept for backward compatibility** but the docstring recommends migrating to `check_novelty()`.

### 3.4 v1: `NoveltyChecker.check_block()` in `novelty_checker.py`

The old v1 pipeline (Stages 0→1→2→3). **Not used by the eval pipeline.** Frozen.

---

## 4. Data Flow: How a Theorem Travels Through the Pipeline

```
                    block: {title, content_latex}
                    lean_statement: "Irrational (Real.sqrt 2)"
                    lean_imports: "import Mathlib.Tactic"
                              │
                              ▼
              ┌──────────────────────────────┐
              │  D2: check_triviality()       │  ◄── d2_triviality.py
              │  6 tactics, lake env lean     │
              │  Budget: 10s (aesop: 30s)     │
              └──────────────┬───────────────┘
                             │
                  ┌──────────┴──────────┐
                  │ trivial?            │
                  └──────────┬──────────┘
                    YES │          │ NO
                        ▼          │
              NO_NOVEDOSO_trivial   │
              [FIN]                 │
                                    ▼
              ┌──────────────────────────────┐
              │  D1 C_F: _check_cf()          │  ◄── mathlib_checker.py → Leandex
              │  GET leandex.projectnumina.ai │
              │  SSE parse, v2 flat format    │
              │  Threshold: 0.85              │
              └──────────────┬───────────────┘
                             │
                  ┌──────────┴──────────┐
                  │ match in Mathlib?    │
                  └──────────┬──────────┘
                    YES │          │ NO
                        ▼          │
              ┌──────────────────┐  │
              │ D3 available?     │  │
              └────┬─────────┬───┘  │
                YES│         │NO    │
                   ▼         ▼      │
         ┌────────┐   MATCH_        │
         │Jaccard │   ENCONTRADO_   │
         │> θ ?   │   PENDIENTE_D3  │
         └──┬──┬──┘   [PROVISIONAL] │
          Y│  │N                    │
           ▼  ▼                     │
  NOVEDAD_   NO_NOVEDOSO_           │
  DEMOSTRACION redundante           │
                                    │
                   ┌────────────────┘
                   ▼
    ┌──────────────────────────────────────┐
    │  D1 C_I: only if C_F had NO match    │
    │                                      │
    │  Stage A: arXiv(20) + SS(20)         │  ◄── arxiv_search.py
    │           → MiniLM cosine filter      │  ◄── block_comparator.py
    │           → dedup by arxiv_id         │
    │           → top_k=3 above threshold   │
    │                                      │
    │  Stage B: LLM Judge on each candidate │  ◄── llm_judge.py → DeepSeek V4 Flash
    │           → stops at first "equiv"    │
    │           or first "gen/spec"         │
    └──────────────┬───────────────────────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
   equivalent  gen/spec    different/none
       │           │           │
       ▼           ▼           ▼
  CONOCIDO_    ZONA_GRIS   NOVEDAD_
  LITERATURA   (revisión    ENUNCIADO
               humana)
```

### 4.1 Fallback: `exact?` in orchestrator (lines 178-216)

If Leandex finds no match in C_F, the orchestrator tries `exact?` tactic as a secondary C_F source:

```python
# orchestrator.py lines 178-216
if lean_project_dir and lean_statement:
    success, elapsed, output = _run_tactic(
        lean_statement, "exact?", lean_project_dir, budget_seconds=15, ...
    )
    if success and output:
        # Parse "Try this: <lemma_name>" from output
        # → treat as C_F match → MATCH_ENCONTRADO_PENDIENTE_D3
```

This was moved from D2 to D1 (decision 2026-06-28). It's **inline in the orchestrator**, not in the D1 module.

### 4.2 Decision A, B, C enforcement

- **Decision A (C_F over C_I):** Enforced at orchestrator.py lines 116-172: if `d1.existe_en_C_F`, the code enters the D3 branch and **never reaches C_I** (lines 218+ are after the C_F block).
- **Decision B (MATCH_ENCONTRADO_PENDIENTE_D3):** Enforced at orchestrator.py lines 157-172: when D3 returns `activa=False`, the provisional verdict is emitted.
- **Decision C (cache + temperature=0):** Cache is `_cache.cache_or_fetch(namespace, key, fetch_fn)` — keyed by query string. LLM judge uses `temperature=0.0` hardcoded in `llm_judge.py` line 139.

---

## 5. Per-Dimension Deep Dive

### 5.1 D2 — No-triviality (`d2_triviality.py`)

**What it does:** Generates `example : <lean_statement> := by <tactic>` for each tactic, runs `lake env lean`, checks if it compiles.

**Tactics (in order):** `decide`, `norm_num`, `simp`, `omega`, `tauto`, `aesop`  
**Removed from D2:** `exact?` (moved to D1 as fallback C_F source, 2026-06-28)  
**Blacklist:** `norm_num` is skipped if the statement contains `Irrational` (L10 mitigation)  

**Key code:**

```python
# d2_triviality.py lines 34-41
T_AUTO_ORDER: List[str] = [
    "decide",
    "norm_num",
    "simp",
    "omega",
    "tauto",
    "aesop",
]

# lines 61-62
_NORM_NUM_BLACKLIST = ["Irrational"]

# lines 84-112 — _run_tactic()
def _run_tactic(lean_statement, tactic, lean_project_dir, budget_seconds, lean_imports):
    source = f"{lean_imports}\n\nset_option maxHeartbeats {heartbeats}\n\nexample : {lean_statement} := by\n  {tactic}\n"
    # writes temp .lean file, runs: lake env lean <tmpfile>
    # timeout = budget_seconds + LEAN_STARTUP_OVERHEAD_S (45s)
    # returns (success: bool, elapsed: float, output: str|None)

# lines 130-191 — check_triviality()
def check_triviality(lean_statement, lean_project_dir=None, budgets=None, lean_imports="import Mathlib"):
    # Auto-detect lean_project/: Path(__file__).resolve().parents[3] / "lean_project"
    # Skip norm_num if statement contains Irrational
    # Try each tactic in order, stop at first success
    # Returns D2Result(trivial=True/False, tactica=..., all_attempts=[...])
```

**Execution environment:** Windows native, Lean 4.29.0. Temp files created via `tempfile.mkstemp(suffix=".lean")`. `lake env lean` has ~30s cold-start overhead for Mathlib olean loading.

**Budget:** `decide/norm_num/simp/omega/tauto`: 10s each. `aesop`: 30s. OS timeout adds `LEAN_STARTUP_OVERHEAD_S=45`.

**Accuracy:** 87% (20/23). 3 known failures are documented.

### 5.2 D1 — No-existencia previa (`d1_existence.py`)

#### 5.2.1 C_F: Mathlib via Leandex

```python
# d1_existence.py lines 80-98
def _check_cf(block, use_cache):
    result = D1Result()
    mathlib_res = check_in_mathlib(block, use_cache=use_cache)
    result.existe_en_C_F = mathlib_res.found
    if mathlib_res.found and mathlib_res.matches:
        best = mathlib_res.matches[0]
        result.match_C_F = {
            "lean_name": best.lean_name,
            "statement": best.statement,
            "similarity": best.similarity,
            "url": best.url,
        }
    return result
```

**Under the hood** (`mathlib_checker.py`):
- Endpoint: `GET https://leandex.projectnumina.ai/api/v1/search?q=<query>&limit=5`
- Response: Server-Sent Events (`data: {...}` lines)
- Leandex v2 format: flat `search_results[]` with `name`, `source_text`, `module`, `source_link`
- **No similarity scores from Leandex v2** — uses result order as proxy (1st = 1.0, 2nd = 0.9, ...)
- Threshold: `SIMILARITY_THRESHOLD = 0.85`
- `found = best_similarity >= 0.85`
- Cache namespace: `"mathlib"`, keyed by query string

#### 5.2.2 C_I: Informal Corpus (arXiv + Semantic Scholar + LLM Judge)

**Stage A** (`_run_ci_stage_a`, lines 105-164):
```python
# 1. Search arXiv (primary, better math coverage): search_arxiv(query, top_k=20)
# 2. Search Semantic Scholar (secondary): search_semantic_scholar(query, top_k=20)
# 3. For each candidate: MiniLM cosine similarity between block text and candidate abstract
# 4. Filter: sim >= CI_SIMILARITY_THRESHOLD_A (0.40)
# 5. Dedup by arxiv_id (keep best score)
# 6. Sort desc, return top_k=3
```

**Stage B** (`_run_ci_stage_b`, lines 167-225):
```python
# For each candidate from Stage A:
#   Call llm_judge.judge_theorem_pair(block_new, block_candidate)
#   → DeepSeek V4 Flash decides: equivalent | generalization | specialization | different
#   Stops at first "equivalent" → existe_en_C_I = True
#   Stops at first "gen/spec" → ZONA_GRIS path
#   "different" → continue to next candidate
```

**LLM Judge details** (`llm_judge.py`):
- Model: `deepseek-v4-flash` (configurable via `DEEPSEEK_MODEL` env var)
- API: OpenCode Go (`https://opencode.ai/zen/go/v1/chat/completions`)
- Auth: `OPENCODE_GO_API_KEY` from `~/.hermes/.env`
- `temperature=0.0` (hardcoded, line 139)
- Retry: if `content` empty (all tokens went to reasoning), retry with 2× `max_tokens`
- Cache namespace: `"judge_theorem"`, keyed by full prompt string

**Known issue:** `CI_SIMILARITY_THRESHOLD_A = 0.40` is too high — produces zero candidates in practice. The CLAUDE.md notes: "Bajar a 0.25."

### 5.3 D3 — Distancia estructural de premisas (`d3_premises.py`) — STUB

**Current state:** Returns `D3Result(activa=False)` unconditionally.

```python
# d3_premises.py lines 28-62
def check_premise_distance(
    lean_name_nuevo, lean_name_existente, lean_project_dir=None, umbral_theta=0.5
) -> D3Result:
    logger.warning("D3.check_premise_distance es un stub — no implementado. ...")
    return D3Result(
        activa=False,
        premisas_candidato=[],
        premisas_nueva=[],
        jaccard=None,
        umbral_theta=umbral_theta,
        pruebas_distantes=None,
    )
```

**Orchestrator integration** (`_run_d3_if_possible`, orchestrator.py lines 281-311):
```python
def _run_d3_if_possible(lean_statement, lean_name_existente, d3_star_pairs=None):
    # Always returns D3Result(activa=False)
    # Has a TODO for loading precomputed results from calibration file
    # d3_star_pairs parameter exists but is never populated
```

**What D3 needs to work:**

1. **Extract premises from two Lean proofs** using `ExtractData.lean`:
   ```bash
   cd lean_project
   lake env lean --run ExtractData.lean <path-to-.lean-file>
   # Output: .lake/packages/mathlib/.lake/build/ir/<path>/ast.json
   # Contains premises[] with {fullName, modName, defPath}
   ```

2. **Compute Jaccard distance:**
   ```
   d = 1 - |P1 ∩ P2| / |P1 ∪ P2|
   ```

3. **Compare against threshold θ** (default 0.5, to be calibrated with T07/T08/T09 pairs).

4. **Wire into orchestrator:** Replace the stub `_run_d3_if_possible()` with actual premise extraction → Jaccard → decision.

**ExtractData.lean status:**
- 519 lines, standalone (no LeanDojo package dependency)
- Works on Windows: `lake env lean --run ExtractData.lean <file.lean>`
- Tested: 2062 premises extracted from `Irrational.lean`
- `findLean` path resolution is fragile on Windows (dependency source paths may not be found — relaxed from `assert!` to warning)
- Output JSON has `premises[]` with `fullName`, `modName`, `defPath`

**D3 calibration paper:** 6 theorems compiled in `lean_project/Papers/D3_Calibration/Paper.lean`  
**Key pair for T08 (genuinely distinct proofs):**
- T08a: `irrational_sqrt_two` / `Nat.Prime.irrational_sqrt`
- T08b: `irrational_nrt_of_notint_nrt` + `Real.sq_sqrt` + `nlinarith`

---

## 6. Cache System

All external API calls go through `_cache.cache_or_fetch()`:

```
cache/novelty/
├── mathlib/          # Leandex responses (keyed by query)
├── search_ss/        # Semantic Scholar responses
├── search_arxiv/     # arXiv search responses
├── judge_theorem/    # LLM judge responses (keyed by full prompt)
└── judge_method/     # Proof method judge (unused in v2)
```

- Serialization: JSON files under `cache/novelty/<namespace>/`
- Key hashing: SHA1 for unsafe filenames, plain text for safe ones (<80 chars, alphanumeric)
- Atomic writes: write to `.tmp`, then rename
- Cache is **shared** between v1 and v2 modules
- `use_cache=True` by default; set `False` to force fresh API calls

---

## 7. External Dependencies

| Dependency | Type | Used by | Critical? |
|------------|------|---------|-----------|
| **Leandex API** (`leandex.projectnumina.ai`) | HTTP SSE | D1 C_F | Yes — no fallback except `exact?` |
| **OpenCode Go API** (`opencode.ai`) | HTTP REST | D1 C_I stage B (LLM judge) | Yes — only LLM judge backend |
| **Semantic Scholar API** (`api.semanticscholar.org`) | HTTP REST | D1 C_I stage A | No — arXiv is primary |
| **arXiv API** (via `arxiv` Python pkg) | HTTP REST | D1 C_I stage A | No — SS is secondary |
| **MiniLM** (`sentence-transformers/all-MiniLM-L6-v2`) | Local model (~80MB) | D1 C_I stage A (similarity filter) | Yes — cosine similarity |
| **Lean 4.29.0** (`lake env lean`) | Local process | D2, `exact?` fallback | Yes — triviality check |
| **ExtractData.lean** | Local Lean script | D3 (future) | Yes for D3 |
| **LeanDojo** (WSL2 only) | Python pkg + Lean env | D3 (future, manual) | Needed for premise extraction in D3 |
| **DeepSeek V4 Flash** | LLM (via OpenCode Go) | D1 C_I stage B | Yes — configurable via `DEEPSEEK_MODEL` |

---

## 8. Issues, Smells, and Technical Debt

### 8.1 Confirmed Issues

1. **D1 C_I produces zero candidates** (INFERIDO from CLAUDE.md — HECHO que el threshold 0.40 está en el código)
   - `CI_SIMILARITY_THRESHOLD_A = 0.40` in `d1_existence.py` line 51
   - CLAUDE.md says: "Bajar a 0.25"

2. **D3 is a stub** (HECHO — verified in code)
   - `check_premise_distance()` returns `D3Result(activa=False)` unconditionally
   - `_run_d3_if_possible()` in orchestrator also returns stub
   - The `d3_star_pairs` parameter exists but is never populated by any caller
   - The TODO at orchestrator.py line 308 references "archivo de calibración" that doesn't exist

3. **`exact?` fallback is inline in orchestrator** (HECHO)
   - Lines 178-216 duplicate the tactic-running logic from D2
   - Uses `_run_tactic` imported from `d2_triviality.py`
   - This is fragile: if D2's `_run_tactic` changes signature, this breaks silently at runtime (the import at line 48 imports `_run_tactic` and `LEAN_STARTUP_OVERHEAD_S` from d2_triviality)

4. **`stage_detenido` values are inconsistent** (HECHO)
   - Docstring in `types.py` lines 133-138 says: 2 = D2, 1f = D1 C_F, 1i = D1 C_I, 3 = D3
   - Actual values in orchestrator: D2 uses `stage_detenido=2` ✓, D1 C_F/D3 uses `stage_detenido=1` or `stage_detenido=3`, D1 C_I uses `stage_detenido=1`
   - The `1f`/`1i` distinction from the docstring is never used

### 8.2 Code Smells

5. **Duplicate decision tree** (HECHO)
   - `check_novelty()` in `orchestrator.py` and `check_novelty_verdict_simple()` in `d1_existence.py` are ~80% identical
   - The simple version doesn't have the D3 branch or `exact?` fallback
   - Both are ~400 lines each with copy-pasted verdict construction

6. **`_check_cf`, `_run_ci_stage_a`, `_run_ci_stage_b` are private but imported cross-module** (HECHO)
   - `orchestrator.py` line 40-46 imports these underscore-prefixed functions from `d1_existence`
   - Python convention: `_name` = module-private, but here they're part of the cross-module API

7. **`d1_existence.py` is 507 lines — too long** (HECHO)
   - Contains: C_F logic, C_I logic, public `check_d1()`, legacy `check_novelty_verdict_simple()`, and a `__main__` demo block
   - The legacy function and demo could be split out

8. **`check_d1()` is never called by the orchestrator** (HECHO)
   - The orchestrator calls `_check_cf()`, `_run_ci_stage_a()`, `_run_ci_stage_b()` directly
   - `check_d1()` is a public function that nobody uses (except possibly external consumers)
   - This means `check_d1()` always runs C_I even when C_F finds a match, violating Decision A

9. **`_cache.py` path resolution is fragile** (HECHO)
   - `_REPO_ROOT = Path(__file__).resolve().parents[2]` — assumes `src/novelty/_cache.py`
   - If the file moves, cache breaks silently (writes to wrong directory)

### 8.3 Residue from Experiments

10. **`llm_judge.py` has `judge_proof_method()` — unused in v2** (HECHO)
    - Defined for "Stage 5" in v1, never called by v2 pipeline
    - Has its own cache namespace `"judge_method"` and `MethodVerdict` dataclass

11. **`paper_extractor.py` — unused in v2** (HECHO)
    - Used by v1's `NoveltyChecker` to extract blocks from arXiv papers for block-level comparison
    - v2 pipeline doesn't do block-level comparison — it uses the LLM judge directly

12. **`block_comparator.py` has `find_similar_pairs()` — unused in v2** (HECHO)
    - Used by v1's `NoveltyChecker` for block-level embedding comparison
    - v2 only uses `get_model()` and `_cosine_similarity_text()` indirectly (via `_cosine_sim()` in `d1_existence.py`)

### 8.4 D3-Specific Gaps

13. **No `ast.json` parser exists** (HECHO)
    - ExtractData.lean outputs JSON with `premises[]`, but there's no Python code to read it
    - `_extract_premises_lean()` in `d3_premises.py` raises `NotImplementedError`

14. **Jaccard computation is not implemented** (HECHO)
    - `D3Result` has `jaccard: Optional[float]` field but nothing computes it

15. **`d3_star_pairs` parameter is dead code** (HECHO)
    - Orchestrator accepts it, passes it to `_run_d3_if_possible()`, which logs and ignores it

---

## 9. HECHO vs INFERIDO Summary

| Claim | Status | Evidence |
|-------|--------|----------|
| D1+D2 works end-to-end | **HECHO** | `scripts/run_eval_full.py` imports and calls `check_novelty()`. CLAUDE.md confirms 18/24 MATCH_ENCONTRADO_PENDIENTE_D3. |
| D2 has 87% accuracy | **INFERIDO** | CLAUDE.md says so; I didn't run the eval myself. |
| D3 is a stub | **HECHO** | Verified in `d3_premises.py` line 55: `return D3Result(activa=False)`. |
| Leandex v2 format works | **HECHO** | `mathlib_checker.py` lines 95-168 parse the flat format. CLAUDE.md confirms 18/24 theorems found. |
| LLM judge uses temperature=0 | **HECHO** | `llm_judge.py` line 139: `"temperature": temperature` where `temperature=0.0` (default param line 116). |
| Cache is keyed by endpoint+query | **HECHO** | `_cache.py`: namespace = endpoint, key = query string. |
| Decision A enforced | **HECHO** | `orchestrator.py` lines 116-172: if C_F match → D3 branch, C_I code (line 218+) unreachable. |
| `exact?` moved from D2 to D1 | **HECHO** | Removed from `T_AUTO_ORDER` in `d2_triviality.py` line 34-41. Added as fallback in `orchestrator.py` lines 178-216. |
| `norm_num` blacklisted for `Irrational` | **HECHO** | `d2_triviality.py` lines 61-62, 166-168. |
| ExtractData.lean works on Windows | **HECHO** | CLAUDE.md confirms 2062 premises extracted from Irrational.lean. |
| C_I threshold 0.40 produces no candidates | **INFERIDO** | CLAUDE.md says so; I see the constant at `d1_existence.py` line 51. |
| 88/88 tests passing | **INFERIDO** | CLAUDE.md says so; I didn't run them. |

---

## 10. Diagram: Module Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                    scripts/run_eval_full.py                     │
│                         │                                       │
│                    check_novelty()                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                src/novelty_v2/orchestrator.py                    │
│                                                                  │
│  check_novelty(block, lean_statement, ...) → NoveltyVerdict     │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ imports from v2:                                            ││
│  │   dimensions/d1_existence.py  (_check_cf, _run_ci_stage_a,  ││
│  │                                _run_ci_stage_b)              ││
│  │   dimensions/d2_triviality.py (check_triviality, _run_tactic)││
│  │   dimensions/d3_premises.py   (check_premise_distance)       ││
│  │   types.py                    (all dataclasses)              ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ d1_existence │   │ d2_triviality│   │ d3_premises  │
│              │   │              │   │  (STUB)      │
│ imports:     │   │ imports:     │   │              │
│  mathlib_    │   │  subprocess  │   │  no external │
│  checker.py  │   │  tempfile    │   │  deps yet    │
│  llm_judge.py│   │  ..types     │   │              │
│  arxiv_      │   │              │   │              │
│  search.py   │   │              │   │              │
│  block_      │   │              │   │              │
│  comparator  │   │              │   │              │
└──────┬───────┘   └──────────────┘   └──────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│         src/novelty/ (FROZEN)            │
│                                          │
│  mathlib_checker.py  → Leandex API      │
│  llm_judge.py        → DeepSeek V4      │
│  arxiv_search.py     → arXiv + SS       │
│  block_comparator.py → MiniLM           │
│  _cache.py           → JSON file cache  │
└──────────────────────────────────────────┘
```

---

*Document location: `docs/architecture_novelty.md`*  
*Next step: Ayrton reviews and provides corrections before Phase 2 (fixing) begins.*
