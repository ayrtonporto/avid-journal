# CLAUDE.md

**AViD Journal** — Automated Verification in Demonstrations.  
Pipeline: `.tex` → parse blocks → formalize in Lean 4 → verify correctness → check novelty (Mathlib + arXiv) → auto-publish if valid.  
Author: Ayrton Porto (UNICEN, Argentina). PhD applications target: Wenda Li (Edinburgh), Welleck (CMU), van Doorn (Bonn).

## Architecture

```
.tex → src/parser/ → src/formalization/ (Claude Code + Lean 4) → src/novelty_v2/ (3 dimensions) → verdict
```

**Three novelty dimensions** (spec: `paper/metric_spec.md`):
- **D1** — No-existencia previa: Mathlib via Leandex (C_F) + exact? fallback + arXiv/Semantic Scholar + LLM judge DeepSeek V4 Flash (C_I)
- **D2** — No-trivialidad: tácticas `{decide, norm_num, simp, omega, tauto, aesop}` con presupuestos. `exact?` movido a D1. `norm_num` blacklist para `Irrational`.
- **D3** — Distancia estructural: Jaccard sobre premisas extraídas con ExtractData.lean (funciona en Windows). Calibración pendiente.

**Seven verdicts:** `NOVEDAD_ENUNCIADO`, `NOVEDAD_DEMOSTRACION`, `CONOCIDO_LITERATURA`, `NO_NOVEDOSO_redundante`, `NO_NOVEDOSO_trivial`, `ZONA_GRIS`, `MATCH_ENCONTRADO_PENDIENTE_D3`

**Decision order (by cost):** D2 first → D1 on C_F → D1 on C_I → D3

## Irrevocable design decisions

1. **Windows native** for automated pipeline. WSL2 reserved only for D3 manual (LeanDojo requires Linux). Do not move automated flow to WSL.
2. **`src/novelty/` is frozen** — import as dependency, never modify. All new code in `src/novelty_v2/`. Exception: `mathlib_checker.py` and `llm_judge.py` were patched for Leandex v2 API and DeepSeek migration (2026-06-27).
3. **`src/parser/` and `src/formalization/`** — do not touch.
4. **D3 vía ExtractData standalone** — bajado `ExtractData.lean` (515 líneas), sin dependencia del paquete `lean-dojo-v2`.
5. **Demo v2**: D1+D2 real-time with streaming; D3 on-demand via SQLite queue.
6. **LLM Judge**: DeepSeek V4 Flash vía OpenCode Go API (2026-06-27).
7. **`exact?` en D1**: fuente secundaria de C_F, no táctica de trivialidad (2026-06-27).

## Current state (June 28, 2026)

**Branch:** `main` at `0c7c391`. All work merged and pushed.

**Done:**
- ✅ D2 (`d2_triviality.py`) — working. `exact?` removed, `norm_num` blacklist for `Irrational`.
- ✅ D1 C_F — Leandex v2 format fixed. Encuentra 18/24 teoremas en Mathlib.
- ✅ D1 C_I — arXiv como fuente primaria, Semantic Scholar secundaria. LLM Judge DeepSeek V4 Flash.
- ✅ Orchestrator (`orchestrator.py`) — árbol D2→D1→D3 completo con 7 veredictos.
- ✅ Eval script (`run_eval_full.py`) — checkpointing, resume, 24 teoremas en 32 min.
- ✅ Eval results: 18 MATCH_ENCONTRADO_PENDIENTE_D3 + 6 NO_NOVEDOSO_trivial. 83% precisión.
- ✅ D3 ExtractData — funciona en Windows. 2062 premisas extraídas de Irrational.lean. Jaccard demostrado.
- ✅ D3 Paper calibración — 6 teoremas compilados en `Papers/D3_Calibration/Paper.lean`.
- ✅ LLM Judge — DeepSeek V4 Flash, temperature=0, retry automático.
- ✅ 88/88 tests pasando.
- ✅ Landing page: `avid-journal.github.io`.

**Pending / blocked:**
- ⏳ D1 C_I no produce candidatos — threshold MiniLM (0.40) muy alto. Bajar a 0.25.
- ⏳ D3 pruebas genuinamente distintas — T09a = T09b actualmente (usan mismo lema).
- ⏳ 9 slots TBD del eval set.
- ⏳ Demo web (Gradio + Hugging Face Spaces).
- ⏳ Preprint (arXiv).
- ⏳ Outreach emails.

**Key findings for paper:**
- **L10**: `norm_num` in Mathlib v4.29.0 closes `Irrational (Real.sqrt 2)` — operational triviality boundary moves with tactic power. Mitigado con blacklist.
- **L11**: Mathlib is monolithic — only `import Mathlib` and `import Mathlib.Tactic` work standalone.
- **Leandex v2**: API cambió de formato (sin scores). Similarity sintética por orden de resultado.
- **ExtractData en Windows**: funciona con `lake env lean --run ExtractData.lean <archivo>`.

## Working rules

1. **Read before coding.** Order: this file → `paper/metric_spec.md` → `paper/decisions.md` → `paper/results_log.md`.
2. **Show real output**, not descriptions. Run code, paste results.
3. **Conventional Commits**: `feat(scope):`, `fix(scope):`, `docs:`, `refactor:`, `chore:`.
4. **No AI attribution in commits.**
5. **`src/novelty/` mostly frozen** — `mathlib_checker.py` and `llm_judge.py` patched but minimize further changes.
6. **Update `paper/results_log.md`** at end of each day.
7. **2-hour stall rule**: if a technical setup blocks progress for >2h, pivot and report.
8. **Long processes warning**: if something takes >1 min, warn first. >5 min, stop and reconsult.

## Environment

- **OS**: Windows 10 (native). Git Bash for terminal.
- **Lean**: 4.29.0 (`x86_64-w64-windows-gnu`) in `lean_project/`. Mathlib compiled: 8247 oleans.
- **Python**: 3.11+ with venv at `.venv/`. Run with `.venv/Scripts/python.exe`.
- **LLM Judge API**: OpenCode Go (`OPENCODE_GO_API_KEY` in `~/.hermes/.env`). Model: `deepseek-v4-flash`.
- **WSL2**: Ubuntu 22.04 at `D:\WSL\Ubuntu2204\`. LeanDojo 4.20.0 installed. Not for automated pipeline.
- **Repo**: `D:\Mis documentos\Documentos\AViD Journal\`. Public: `github.com/ayrtonporto/avid-journal`.

## Key files map

```
src/novelty_v2/
├── orchestrator.py       ← ✅ Árbol D2→D1→D3 completo
├── types.py              ← Verdict enum (7 valores) + D1/D2/D3Result dataclasses
├── dimensions/
│   ├── d1_existence.py   ← ✅ D1: Leandex C_F + arXiv/SS C_I + exact? fallback
│   ├── d2_triviality.py  ← ✅ D2 filter (6 tácticas, sin exact?, blacklist Irrational)
│   └── d3_premises.py    ← ✅ Stub documentado con check_premise_distance()
src/novelty/
├── mathlib_checker.py    ← PARCHED: Leandex v2 API format (2026-06-27)
├── llm_judge.py          ← PARCHED: DeepSeek V4 Flash vía OpenCode Go (2026-06-27)
├── arxiv_search.py       ← arXiv + Semantic Scholar
└── _cache.py             ← Cache compartido
lean_project/
├── ExtractData.lean      ← Extractor de premisas (515 líneas)
└── Papers/D3_Calibration/ ← 6 teoremas compilados para calibración D3
paper/
├── metric_spec.md        ← THE spec (source of truth)
├── eval_set.csv          ← 26 firm theorems + 9 TBD slots
├── decisions.md          ← all design decisions
├── results_log.md        ← daily progress log (actualizado 2026-06-28)
├── limitations.md        ← L10, L11, etc.
└── eval_set_lean_statements.md  ← Lean 4 versions of eval theorems
scripts/
├── run_eval_full.py      ← ✅ Eval script con checkpointing
└── eval/                 ← Resultados CSV de corridas
