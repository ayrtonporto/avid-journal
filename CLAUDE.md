# CLAUDE.md

**AViD Journal** — Automated Verification in Demonstrations.  
Pipeline: `.tex` → parse blocks → formalize in Lean 4 → verify correctness → check novelty (Mathlib + arXiv) → auto-publish if valid.  
Author: Ayrton Porto (UNICEN, Argentina). PhD applications target: Wenda Li (Edinburgh), Welleck (CMU), van Doorn (Bonn).

## Architecture

```
.tex → src/parser/ → src/formalization/ (Claude Code + Lean 4) → src/novelty_v2/ (3 dimensions) → verdict
```

**Three novelty dimensions** (spec: `paper/metric_spec.md`):
- **D1** — No-existencia previa: Mathlib via Leandex (C_F) + arXiv/Semantic Scholar + LLM judge (C_I)
- **D2** — No-trivialidad: tácticas `{decide, norm_num, simp, omega, tauto, exact?, aesop}` con presupuestos
- **D3** — Distancia estructural: Jaccard sobre premisas extraídas con LeanDojo (manual/offline en este sprint)

**Six verdicts:** `NOVEDAD_ENUNCIADO`, `NOVEDAD_DEMOSTRACION`, `CONOCIDO_LITERATURA`, `NO_NOVEDOSO_redundante`, `NO_NOVEDOSO_trivial`, `ZONA_GRIS`

**Decision order (by cost):** D2 first → D1 on C_F → D1 on C_I → D3

## Irrevocable design decisions

1. **Windows native** for automated pipeline. WSL2 reserved only for D3 manual (LeanDojo requires Linux). Do not move automated flow to WSL.
2. **`src/novelty/` is frozen** — import as dependency, never modify. All new code in `src/novelty_v2/`.
3. **`src/parser/` and `src/formalization/`** — do not touch.
4. **D3 manual offline** for star pairs (T07, T08, T09). LeanDojo traces transitive dependencies; not automatable in sprint timeframe.
5. **Demo v2**: D1+D2 real-time with streaming; D3 on-demand via SQLite queue.
6. **Back-translation fidelity** is explicit future work for PhD.

## Current state (June 27, 2026)

**Branch:** `main` at merge commit (includes `claude/agitated-lovelace-e10f00` merged 2026-06-27).

**Done:**
- ✅ D2 (`d2_triviality.py`, 166 lines) — working. Tested on 24 theorems: 20/23 = 87% accuracy.
- ✅ D1 implementation (on `agitated-lovelace` branch) — 480 lines, integrates Leandex + Semantic Scholar + LLM judge.
- ✅ D2 eval set full run (scripts + results CSVs on `agitated-lovelace` branch).
- ✅ Landing page: `avid-journal.github.io`.
- ✅ `metric_spec.md`, `eval_set.csv` (26 firm + 9 TBD), `decisions.md`, `limitations.md`.
- ✅ `types.py` with all 6 verdicts + dataclasses.

**Pending / blocked:**
- ⏳ Merge `agitated-lovelace` branch.
- ⏳ `orchestrator.py` (D2→D1→D3 decision tree).
- ⏳ D3 on T07/T08/T09 (LeanDojo in WSL).
- ⏳ **LLM judge decision** — API Anthropic ($5-15) vs. local model vs. Claude Code as judge. `ANTHROPIC_API_KEY` not configured.
- ⏳ Demo web (Gradio + Hugging Face Spaces).
- ⏳ Preprint (arXiv).
- ⏳ Outreach emails (deadline was July 7 — rescheduling needed).

**Key findings for paper:**
- **L10**: `norm_num` in Mathlib v4.29.0 closes `Irrational (Real.sqrt 2)` in 14s — operational triviality boundary moves with tactic power.
- **L11**: Mathlib is monolithic — only `import Mathlib` and `import Mathlib.Tactic` work standalone. Specific imports fail.
- **D2 overhead**: ~30s per `lake env lean` invocation on Windows with warm OS cache.

## Working rules

1. **Read before coding.** Order: this file → `paper/metric_spec.md` → `paper/eval_set.csv` → `paper/decisions.md` → `paper/results_log.md`.
2. **Show real output**, not descriptions. Run code, paste results.
3. **Conventional Commits**: `feat(scope):`, `fix(scope):`, `docs:`, `refactor:`, `chore:`.
4. **No AI attribution in commits.**
5. **Don't touch frozen modules** (`src/novelty/`, `src/parser/`, `src/formalization/`).
6. **Implement only what's asked.** No extra features, logging, refactors, or tests.
7. **Update `paper/results_log.md`** at end of each day.
8. **2-hour stall rule**: if a technical setup blocks progress for >2h, pivot and report.
9. **Long processes warning**: if something takes >1 min, warn first. >5 min, stop and reconsult.
10. **Mark facts vs. inferences.** If it's an inference, say "probably" or "according to my understanding."

## Environment

- **OS**: Windows 10 (native). Git Bash for terminal.
- **Lean**: 4.29.0 (`x86_64-w64-windows-gnu`) in `lean_project/`. Mathlib compiled: 8247 oleans.
- **Python**: 3.10+ with venv at `.venv/`. Dependencies in `requirements.txt`.
- **WSL2**: Ubuntu 22.04 at `D:\WSL\Ubuntu2204\`. LeanDojo 4.20.0 installed. Mathlib cache broken — not for automated pipeline.
- **Repo**: `D:\Mis documentos\Documentos\AViD Journal\`. Public: `github.com/ayrtonporto/avid-journal`.

## Key files map

```
src/novelty_v2/
├── types.py              ← Verdict enum + D1/D2/D3Result dataclasses
├── dimensions/
│   ├── d1_existence.py   ← stub on main (3 lines); full impl on agitated-lovelace (480 lines)
│   ├── d2_triviality.py  ← ✅ D2 filter (166 lines)
│   └── d3_premises.py    ← stub (3 lines)
src/novelty/              ← FROZEN: mathlib_checker, arxiv_search, llm_judge, _cache, paper_extractor, block_comparator
src/parser/               ← FROZEN: latex_parser, parse_tex
src/formalization/        ← FROZEN: orchestrator, lean_project, complexity, mathlib_search, scripts/
paper/
├── metric_spec.md        ← THE spec (source of truth)
├── eval_set.csv          ← 26 firm theorems + 9 TBD slots
├── decisions.md          ← all design decisions with rationale
├── results_log.md        ← daily progress log
├── limitations.md        ← declared limitations
├── related_work.md       ← literature positioning
├── future_work.md        ← out-of-scope items
├── eval_set_lean_statements.md  ← Lean 4 versions of eval theorems (on agitated-lovelace branch)
└── preprint/             ← draft, abstract
scripts/d2/               ← D2 test scripts + result CSVs (some on agitated-lovelace branch)
docs/                     ← ARCHITECTURE, PROGRESS, QUICKSTART, GUIA_INSTALACION
```

## What NOT to do

- Don't rewrite `metric_spec.md`.
- Don't modify `src/novelty/`, `src/parser/`, `src/formalization/`.
- Don't re-litigate WSL vs. Windows — decided.
- Don't re-litigate LeanDojo in automated pipeline — decided.
- Don't add "Version 3" features to sprint scope.
- Don't assume "it should work" — test with real code.
- Don't generate synthetic demo cases — use eval set + real uploads.
