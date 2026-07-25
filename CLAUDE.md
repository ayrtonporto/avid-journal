# CLAUDE.md

**AViD Journal** — Automated Verification in Demonstrations.  
Pipeline: `.tex` → parse blocks → formalize in Lean 4 → verify correctness → check novelty (Mathlib + arXiv + TheoremSearch) → auto-publish if valid.  
Author: Ayrton Porto.

## Architecture

```
.tex → src/parser/ → src/formalization/ (Claude Code + Lean 4) → src/novelty_v2/ (3 dimensions) → verdict
```

**Three novelty dimensions** (spec: `paper/metric_spec.md`):
- **D1** — No-existencia previa: Mathlib via Leandex (C_F) + exact? fallback + arXiv (primaria) + TheoremSearch (nivel-teorema) + Matlas (gated) + LLM judge DeepSeek V4 Flash (C_I). **Semantic Scholar retirado.** Etapa A = filtro grueso MiniLM (embeddings); etapa B = juez fino DeepSeek. Todas las llamadas de red con timeout fail-open.
- **D2** — No-trivialidad: tácticas `{decide, norm_num, simp, omega, tauto, aesop}` con presupuestos. `exact?` movido a D1. `norm_num` blacklist para `Irrational`.
- **D3** — Distancia estructural: Jaccard sobre premisas extraídas con ExtractData.lean (funciona en Windows). Calibración pendiente.

**Seven verdicts:** `NOVEDAD_ENUNCIADO`, `NOVEDAD_DEMOSTRACION`, `CONOCIDO_LITERATURA`, `NO_NOVEDOSO_redundante`, `NO_NOVEDOSO_trivial`, `ZONA_GRIS`, `MATCH_ENCONTRADO_PENDIENTE_D3`

**Decision order (by cost):** D2 first → D1 on C_F → D1 on C_I → D3

## Irrevocable design decisions

1. **Windows native** for automated pipeline. WSL2 reserved only for D3 manual (LeanDojo requires Linux). Do not move automated flow to WSL.
2. **`src/novelty/` no se modifica al paso** — solo mediante fix-packs explícitos aprobados por el usuario y documentados en `paper/decisions.md`. Todo código nuevo va en `src/novelty_v2/`. Últimos fix-packs autorizados: `mathlib_checker.py` (Leandex v2, 2026-06-27) y `llm_judge.py` (DeepSeek V4 Flash, 2026-06-27).
3. **`src/parser/` and `src/formalization/`** — do not touch.
4. **D3 vía ExtractData standalone** — bajado `ExtractData.lean` (515 líneas), sin dependencia del paquete `lean-dojo-v2`.
5. **Demo v2**: D1+D2 real-time with streaming; D3 on-demand via SQLite queue.
6. **LLM Judge**: DeepSeek V4 Flash vía OpenCode Go API (2026-06-27).
7. **`exact?` en D1**: fuente secundaria de C_F, no táctica de trivialidad (2026-06-27).
8. **REPL pool residente** (`src/lean_repl/`, 2026-07-25, commit `763f482`): el compile-check de formalización y las tácticas de D2 corren contra REPLs Lean con Mathlib precargado (`env 0`), no `lake env lean` frío → ~27s→sub-segundo. Módulo NUEVO, no toca `src/formalization/`. Env-gated (`AVID_REPL_POOL`), fallback frío automático. Pool de N para concurrencia real. **El olean de Mathlib solo existe en el `lean_project/` del repo main, NO en los worktrees** (`.lake` gitignored) → correr con `LEAN_PROJECT_DIR` apuntando al main.
9. **Provider "Claude Code" (OAuth) es solo-local** (2026-07-25): formalizador agéntico que spawnea `claude` anidado; funciona local pero NO en el server. Oculto en la web deployada (visible solo con `AVID_DEV_MODE=1`); el backend lo sigue aceptando.

## Current state (July 25, 2026)

**Branch:** cierre web en `claude/avid-journal-web-closure-9c85b2` (commits `763f482` + `b0ea48f`), **PR [#7](https://github.com/ayrtonporto/avid-journal/pull/7) a `main`** (mergear desde la otra compu). El demo web quedó funcional E2E; falta el deploy real.

**Done (base, ≤ jun 2026):**
- ✅ D2 (`d2_triviality.py`) — `exact?` removed, `norm_num` blacklist for `Irrational`.
- ✅ D1 C_F — Leandex v2 format fixed. ~18/24 teoremas en Mathlib.
- ✅ Orchestrator (`orchestrator.py`) — árbol D2→D1→D3 con 7 veredictos.
- ✅ D3 ExtractData — funciona en Windows. Jaccard demostrado.
- ✅ LLM Judge — DeepSeek V4 Flash, temperature=0, retry automático.
- ✅ Landing page: `avid-journal.github.io`.

**Done (cierre web, jul 25 2026 — este branch):**
- ✅ **REPL pool residente** (`src/lean_repl/`): compile-check ~27s→sub-segundo, concurrencia real (pool de 2), fallback frío. Validado E2E.
- ✅ **D2 vía pool**: ~130s→<0.1s por táctica.
- ✅ **D1 hardening**: timeout fail-open en TODAS las fuentes de red + juez; MiniLM precargado al startup; TheoremSearch activado; Semantic Scholar fuera del path.
- ✅ **Provider Claude Code (OAuth)** cableado al web como formalizador local (oculto en deploy). Test E2E: verified 3/3 en `tiny_even_numbers`, novedad ~3-4s/bloque.
- ✅ **Idioma**: `detail`/`razonamiento` del orchestrator traducidos a inglés (badges ya estaban en inglés).
- ✅ **Definiciones publicables aunque conocidas**: `_is_publishable` en `app.py` — una def no bloquea la publicación (solo si falla la formalización); el paper es publicable si cada teorema/lema es novel y hay ≥1 claim.
- ✅ Warm-up + shutdown limpio en `server.py`; config de deploy del REPL en `Dockerfile`/`.env.example`; tests `tests/test_lean_repl.py`. 28 tests del pipeline+REPL en verde.

**Pending / próximo:**
- ⏳ **Mergear PR #7** y **deploy real** (primer test E2E de la imagen Docker con el pool; ~4.5 GB, no testeada aún). Checklist deploy: `AVID_DEV_MODE=0`, `AVID_REPL_POOL=1` + `AVID_REPL_BIN` + `AVID_REPL_POOL_SIZE`, `THEOREMSEARCH_ENABLED=1`, `AVID_JUDGE_TIMEOUT=30`.
- ⏳ Bloque even+even lo formaliza Claude pero DeepSeek no (techo del modelo) — para el server-default hace falta key fuerte o proveedor mejor.
- ⏳ D1 C_I threshold MiniLM — revisar candidatos/umbral.
- ⏳ D3 pruebas genuinamente distintas; slots TBD del eval set; preprint arXiv; outreach.

**Key findings for paper:**
- **L10**: `norm_num` in Mathlib v4.29.0 closes `Irrational (Real.sqrt 2)` — la frontera de trivialidad operacional se mueve con el poder de las tácticas. Mitigado con blacklist.
- **L11**: Mathlib is monolithic — only `import Mathlib` and `import Mathlib.Tactic` work standalone.
- **Leandex v2**: API sin scores → un match exacto por nombre (ej. `Even`) se descarta (found=False, revisión manual). Por eso una def conocida puede salir NOVEL en el badge; mitigado en la política de publicación, no en el matcher (congelado).
- **REPL pool**: import único de Mathlib (~25s) amortizado por worker; `encoding="utf-8"` obligatorio en Windows o el goal state `⊢` sale mojibake; hay que neutralizar los `import` que emite el modelo (ilegales contra `env 0`).

## Working rules

1. **Read before coding.** Order: this file → `paper/metric_spec.md` → `paper/decisions.md` → `paper/results_log.md`. ⚠️ **`paper/` NO está en el repo** (no trackeado, ausente también en el main). Los specs/logs referenciados viven fuera del repo o están pendientes de crear — si vas a codear sobre la métrica, primero ubicá o recreá esos archivos; no asumas que existen en el checkout.
2. **Show real output**, not descriptions. Run code, paste results.
3. **Conventional Commits**: `feat(scope):`, `fix(scope):`, `docs:`, `refactor:`, `chore:`.
4. **No AI attribution in commits.**
5. **`src/novelty/` mostly frozen** — `mathlib_checker.py` and `llm_judge.py` patched but minimize further changes.
6. **Update `paper/results_log.md`** at end of each day.
7. **2-hour stall rule**: if a technical setup blocks progress for >2h, pivot and report.
8. **Long processes warning**: if something takes >1 min, warn first. >5 min, stop and reconsult.

## Environment

- **OS**: Windows 11 (native). Git Bash / PowerShell for terminal (PS 5.1 lee `.ps1` como ANSI → scripts deben ser ASCII puro).
- **Lean**: 4.29.0 (`x86_64-w64-windows-gnu`) in `lean_project/`. Mathlib compilado **solo en el `lean_project/` del repo main** (`.lake` gitignored → los worktrees NO lo tienen; apuntar `LEAN_PROJECT_DIR` al main).
- **REPL pool**: binario `leanprover-community/repl` (tag `v4.29.0-rc8`, toolchain sobreescrito a `v4.29.0`) en `vendor/repl/` (gitignored). Vars: `AVID_REPL_POOL`, `AVID_REPL_BIN`, `AVID_REPL_POOL_SIZE`. Launcher local: `run_local_demo.ps1`.
- **Python**: 3.11+ with venv at `.venv/`. Run with `.venv/Scripts/python.exe`.
- **LLM Judge API**: OpenCode Go (`OPENCODE_GO_API_KEY` in `~/.hermes/.env`). Model: `deepseek-v4-flash`.
- **WSL2**: Ubuntu 22.04 at `D:\WSL\Ubuntu2204\`. LeanDojo 4.20.0 installed. Not for automated pipeline.
- **Repo**: Public: `github.com/ayrtonporto/avid-journal`.

## Key files map

```
app.py                    ← Backend del demo: parse→formalize→D2→D1→veredictos + publicación.
                             compile_check vía pool; _is_publishable (def no bloquean);
                             provider Claude Code (OAuth) special-case.
server.py                 ← FastAPI/uvicorn: sirve landing.html, /api/analyze (SSE),
                             warm-up (MiniLM + REPL pool) y shutdown. Inyecta AVID_DEV_MODE.
src/lean_repl/            ← ★ NUEVO (2026-07-25): pool de REPL Lean residente
├── __init__.py          ← facade: compile_check, get_pool, warm_pool, pool_enabled
└── pool.py              ← ReplWorker (env 0 = Mathlib) + ReplPool (cola/concurrencia)
                             + _neutralize_imports + fallback frío
src/novelty_v2/
├── orchestrator.py       ← ✅ Árbol D2→D1→D3; razonamiento/detail en INGLÉS
├── types.py              ← Verdict enum (7 valores) + D1/D2/D3Result dataclasses
├── dimensions/
│   ├── d1_existence.py   ← ✅ D1: Leandex C_F + arXiv/TheoremSearch/Matlas C_I + exact?;
│   │                        MiniLM etapa A + juez etapa B; timeouts fail-open
│   ├── d2_triviality.py  ← ✅ D2 filter (6 tácticas; fast-path vía pool; blacklist Irrational)
│   └── d3_premises.py    ← ✅ D3: compute_d3() canónica; Jaccard + filtros
src/novelty/              ← CONGELADO (solo fix-packs aprobados)
├── mathlib_checker.py    ← PARCHED: Leandex v2 API format (2026-06-27)
├── llm_judge.py          ← PARCHED: DeepSeek V4 Flash vía OpenCode Go (2026-06-27)
├── arxiv_search.py       ← arXiv (Semantic Scholar fuera del path activo)
├── block_comparator.py   ← MiniLM (get_model precargado en server startup)
└── _cache.py             ← Cache compartido
deploy/
├── landing.html          ← Front del demo (badges EN; opción Claude Code data-devonly)
├── Dockerfile            ← imagen + build del REPL + env vars del pool
└── HF_README.md          ← notas Hugging Face Spaces
lean_project/             ← Mathlib compilado SOLO en el repo main (no en worktrees)
├── ExtractData.lean      ← Extractor de premisas (515 líneas)
└── Papers/D3_Calibration/ ← 6 teoremas compilados para calibración D3
run_local_demo.ps1        ← Launcher local con pool (ASCII puro; AVID_DEV_MODE=1)
measure_run.py            ← Mide /api/analyze (timeline SSE por etapa + veredictos)
vendor/repl/              ← binario REPL (gitignored)
scripts/run_eval_full.py  ← ✅ Eval script con checkpointing

paper/  ⚠️ NO PRESENTE en el repo — metric_spec.md / decisions.md / results_log.md /
        eval_set.csv / limitations.md están referenciados pero no existen en el checkout.
