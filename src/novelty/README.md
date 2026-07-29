# src/novelty — Novelty metric (D1 · D2 · D3)

Given a formalized block, decide whether it is *new* to the mathematical record and
return one of seven verdicts. Dimensions are evaluated **cheapest-first: D2 → D1 → D3**.

## The three dimensions

| Dim | Question | Method |
|---|---|---|
| **D2** — triviality | Does a standard tactic close it? | `decide`, `norm_num`, `simp`, `omega`, `tauto`, `aesop` with budgets, run on the resident REPL pool. `norm_num` is blacklisted for `Irrational`. |
| **D1** — existence | Does it already exist? | **C_F** (formal): Mathlib via Leandex + `exact?` fallback. **C_I** (informal): arXiv + an LLM judge (DeepSeek). Every network/judge call is fail-open under timeout. |
| **D3** — proof distance | Is the *proof* structurally new? | Jaccard over the premise sets of the candidate proof vs. the matched Mathlib theorem. Premises are extracted from the resident Lean env (side A via env-chaining, side B via a metaprogram over the match). |

## The seven verdicts

| Verdict | Condition |
|---|---|
| `NO_NOVEDOSO_trivial` | D2 closed it with a standard tactic |
| `NO_NOVEDOSO_redundante` | match in C_F **and** D3 says the proof is close |
| `NOVEDAD_DEMOSTRACION` | match in C_F **and** D3 says the proof is distant |
| `CONOCIDO_LITERATURA` | match in C_I but not in C_F |
| `NOVEDAD_ENUNCIADO` | no match in C_F or C_I, and not trivial |
| `ZONA_GRIS` | generalization/specialization per the LLM judge |
| `INCONCLUSIVE` | D3 could not decide (e.g. all match premises filtered out) |

## Decision tree

```
1. D2 — if a tactic closes it → NO_NOVEDOSO_trivial, done
2. D1 on C_F (Leandex) — if match → go to step 4
3. D1 on C_I (cheap stage A; expensive judge stage B only if A fires)
     no match                         → NOVEDAD_ENUNCIADO, done
     match in C_I but not C_F          → CONOCIDO_LITERATURA, done
     generalization/specialization     → ZONA_GRIS, done
4. D3 (Jaccard over premises)
     distant proofs → NOVEDAD_DEMOSTRACION
     close proofs   → NO_NOVEDOSO_redundante
```

## Key files

| File | Role |
|---|---|
| `orchestrator.py` | The D2→D1→D3 tree; emits the final verdict. |
| `types.py` | `Verdict` enum + `D1/D2/D3Result` dataclasses. |
| `dimensions/d1_existence.py` | D1: Leandex C_F + arXiv/judge C_I. |
| `dimensions/d2_triviality.py` | D2: the six tactics + `Irrational` blacklist. |
| `dimensions/d3_premises.py` | D3: `compute_d3()`, Jaccard + premise filters. |
| `premise_extraction.py` | Extracts premise sets from the resident REPL env (sides A/B). |
| `mathlib_checker.py` | Leandex v2 API client. |
| `llm_judge.py` | DeepSeek judge via the OpenCode Go API. |
| `arxiv_search.py` | arXiv candidate search. |
| `_cache.py` | Shared disk cache for external calls. |
| `run_eval_full.py` | Evaluation harness with checkpoint/resume. |
| `d3_extraction_map.yaml` | Maps eval theorem IDs → `.lean` files for D3. |
