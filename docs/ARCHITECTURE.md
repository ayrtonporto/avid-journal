# AViD Journal - Architecture

System design and technical decisions.

> ⚠️ **Actualización (jul 2026) — este doc describe el diseño histórico.** Cambios vigentes:
> - El veredicto de novedad activo es `src/novelty_v2/` (árbol D2→D1→D3, 7 veredictos), no `src/novelty/` directamente (que quedó congelado y se usa como dependencia).
> - Fuentes de C_I: **arXiv (primaria) + TheoremSearch + Matlas (gated)**. **Semantic Scholar fue retirado** — donde este doc dice "Semantic Scholar", leer "arXiv + TheoremSearch".
> - Hay un **demo web** (`app.py` + `server.py` + `deploy/landing.html`) acelerado por un **REPL pool Lean residente** (`src/lean_repl/`, Mathlib precargado → compile-check sub-segundo).
> - Fuente de verdad de estado y decisiones: `CLAUDE.md`.

---

## 🏛️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AViD JOURNAL                            │
│                Automated Mathematics Journal                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Input: .tex     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ PARSER           │  blocks + dep graph
                    │ src/parser/      │
                    └────────┬─────────┘
                             │  topological order
                             ▼
        ┌════════ orchestrator (src/formalization/) ════════╗
        ║                                                   ║
        ║   for each block (resume mode skips done):        ║
        ║   ┌─────────────────────────────────────────┐     ║
        ║   │ FORMALIZATION + VERIFICATION (loop)     │     ║
        ║   │                                         │     ║
        ║   │  Claude Code session:                   │     ║
        ║   │   • edits Blocks/<lean_name>.lean       │     ║
        ║   │   • lean_diagnostic_messages            │     ║
        ║   │   • iterates until clean or max_rounds  │     ║
        ║   │                                         │     ║
        ║   │  Orchestrator post-session:             │     ║
        ║   │   • final lean_checker                  │     ║
        ║   │   • append → Paper.lean                 │     ║
        ║   │   • update PAPER_INDEX.md / REVIEW.md   │     ║
        ║   │   • lake build (cache olean)            │     ║
        ║   └─────────────────────────────────────────┘     ║
        ╚═══════════════════╤═══════════════════════════════╝
                            │
                            ▼
                  ┌──────────────────┐
                  │ NOVELTY CHECK    │  separate pass over blocks
                  │ src/novelty/     │  (Stages 0–3)
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ DECISION         │  Accept / Reject + citations
                  │ orchestrator     │
                  └──────────────────┘
```

The agent that writes Lean is **Claude Code**, not Numina-Lean-Agent. AViD vendors Numina's runner scripts under [src/formalization/scripts/](../src/formalization/scripts/) (`run_claude.py`, `runner.py`, `task.py`, `lean_checker.py`, `statement_tracker.py`, `extract_sublemmas.py`, `safe_verify.py`, `mcp_stats.py`) and adapts its coordinator / blueprint / sketch prompt pattern, but the inner loop is Claude Code talking to Lean through [lean-lsp-mcp](https://github.com/leanprover-community/lean-lsp-mcp).

---

## 📦 Module Design

### 1. Parser Module (`src/parser/`)

**Purpose:** Extract mathematical blocks from LaTeX.

**Input:** `.tex` file
**Output:** List of blocks (JSON)

```python
{
  "type": "theorem",
  "label": "thm:stone",
  "title": "Stone Representation",
  "content_latex": "Every Boolean algebra...",
  "proof_latex": "By duality...",
  "references": ["def:bool", "lem:filter"]  # Dependency graph
}
```

**Key Features:**
- Auto-detects custom environments
- Extracts dependency graph
- Handles nested structures

**Files:**
- `latex_parser.py` - Core parser logic
- `parse_tex.py` - CLI interface

---

### 2. Novelty Check Module (`src/novelty/`)

**Purpose:** Determine if theorems are new.

**Pipeline (Stages 0–3 implemented):**

```
Block (theorem / lemma / proposition / corollary)
    │
    ▼
┌─────────────────────────────┐
│ Stage 0: Mathlib check      │
│ (mathlib_checker.py)        │
│ • Leandex semantic search   │
│ • If match → IN_MATHLIB     │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Stage 1: ArXiv search       │
│ (arxiv_search.py)           │
│ • Semantic Scholar + ArXiv  │
│ • Dedupe + threshold        │
│ Output: top-K candidates    │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Stage 2: Paper extraction   │
│ (paper_extractor.py)        │
│ • Download PDFs             │
│ • Extract text              │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Stage 3: Block comparison   │
│ (block_comparator.py +      │
│  llm_judge.py)              │
│ • Pair the block with each  │
│   candidate; Claude judges  │
│   equivalent / specialization │
│   generalization / different│
└─────────────────────────────┘
```

[novelty_checker.py](../src/novelty/novelty_checker.py) orchestrates Stages 0–3 and emits a `NoveltyLabel` per block (`NOVEL`, `NOVEL_METHOD`, `GENERALIZATION`, `NOT_NOVEL`, `IN_MATHLIB`). Stages 4–5 (formalize candidate + tree-of-types comparison) are reserved for future work; `NoveltyChecker.__init__` keeps the parameter slots for forward compatibility.

**Files:**
- `mathlib_checker.py` - Stage 0 (Leandex)
- `arxiv_search.py` - Stage 1 (Semantic Scholar + ArXiv, dedupe, threshold)
- `paper_extractor.py` - Stage 2 (PDF download + text extraction)
- `block_comparator.py` - Stage 3 pairing logic
- `llm_judge.py` - Claude judge for theorem equivalence
- `novelty_checker.py` - Orchestrates Stages 0–3
- `_cache.py` - Disk cache for external API calls

---

### 3. Formalization Module (`src/formalization/`)

**Purpose:** Translate LaTeX → Lean 4, verify correctness.

**Approach:** drive Claude Code as a subprocess per block, with Lean-LSP for verification. The agent prompts are inspired by Numina-Lean-Agent's coordinator / blueprint / sketch pattern but adapted: there is **no separate proof agent** — the Sketch Agent formalizes statement and proof together using the paper's `proof_latex` as a guide.

**Pipeline:**

```
Blocks (ordered topologically)
    │
    ▼
┌─────────────────────────────┐
│ Lean Project Manager        │
│ (lean_project.py)           │
│                             │
│ • Create paper sub-module   │
│   under Papers/<ModuleName> │
│ • Initialize Paper.lean,    │
│   PAPER_INDEX.md, REVIEW.md │
│ • Reuse shared Mathlib build│
└──────────┬──────────────────┘
           │
           ▼
For each block:
┌─────────────────────────────┐
│ orchestrator.py             │
│                             │
│ 1. complexity.classify →    │
│    SIMPLE / MEDIUM / HARD / │
│    EXTERNAL                 │
│ 2. EXTERNAL → mathlib_search│
│    .lookup; fall back to    │
│    axiom with source comment│
│ 3. else: write TASK.md +    │
│    Blocks/<lean_name>.lean  │
│    stub, then run           │
│    scripts/run_claude.py    │
│    with the matching prompt │
│ 4. lean_checker verifies    │
│ 5. on success, extract the  │
│    declaration and append   │
│    to Paper.lean; update    │
│    PAPER_INDEX.md           │
│ 6. lake build Papers.       │
│    <ModuleName>.Paper to    │
│    cache the olean          │
└─────────────────────────────┘
```

**Key Insight:** Dependency ordering matters.

Block B references Block A → Must formalize A first → A becomes context for B. The agent reads `PAPER_INDEX.md` first (already-proven blocks in this paper), then `lean_local_search`, then `lean_leandex` (Mathlib semantic), then `lean_loogle` (Mathlib type pattern).

**Files:**
- `lean_project.py` - Per-paper project layout under `Papers/<ModuleName>/`
- `complexity.py` - SIMPLE / MEDIUM / HARD / EXTERNAL classifier
- `mathlib_search.py` - Mathlib lookup for proof-less blocks
- `orchestrator.py` - Main loop, topo sort, resume mode, olean caching
- `scripts/run_claude.py` - Launches Claude Code on a target file (Numina-derived)
- `scripts/lean_checker.py` - Runs `lake env lean` against a target file
- `scripts/{runner,task,statement_tracker,extract_sublemmas,safe_verify,mcp_stats}.py` - Numina-derived runtime utilities

---

### 4. Persistent state

Today, AViD has no database layer. The persistent state of a formalized paper lives in three files under `lean_project/Papers/<ModuleName>/`:

- `Paper.lean` — the accumulative Lean module; the agent never edits this directly.
- `PAPER_INDEX.md` — the per-paper "theorem DB": one entry per block with type, status (`verified` / `axiom` / `failed`), line in `Paper.lean`, dependencies, and (for axioms) the source citation. The agent consults this file first when searching for dependencies.
- `REVIEW.md` — human-review log: axioms declared, blocks that failed verification, notes.

The orchestrator owns these files. The Claude session only edits its assigned `Blocks/<lean_name>.lean` stub.

---

## 🔀 Data Flow

### End-to-End Flow

```
1. User submits paper.tex
         │
         ▼
2. Parser extracts blocks (list of dicts in memory)
         │
         ▼
3. Orchestrator: topo sort → for each block (resume mode skips done):
         │
         ├─→ Novelty check (optional, runs independently of formalization)
         │   ├─ Stage 0 Mathlib (Leandex)
         │   ├─ Stage 1 ArXiv (Semantic Scholar)
         │   ├─ Stage 2 paper extraction
         │   └─ Stage 3 block↔candidate comparison (Claude judge)
         │
         ├─→ Formalization
         │   ├─ classify complexity (SIMPLE / MEDIUM / HARD / EXTERNAL)
         │   ├─ EXTERNAL → axiom with source comment
         │   ├─ else: write TASK.md + Blocks/<lean_name>.lean stub,
         │   │   launch Claude via scripts/run_claude.py
         │   ├─ verify with lean_checker (lake env lean)
         │   ├─ append verified declaration to Paper.lean
         │   ├─ update PAPER_INDEX.md (and REVIEW.md if axiom/failed)
         │   └─ lake build Papers.<ModuleName>.Paper (cache olean)
         │
         ▼
4. Output: Paper.lean (verified module), PAPER_INDEX.md (per-block log),
   REVIEW.md (human review items), optional --json summary.
```

---

## 🔧 Technology Choices

### Why Python?
- Fast prototyping
- Rich ecosystem (requests, numpy, sentence-transformers)
- Easy integration with APIs

### Why Numina vs. Custom Lean Tactics?
- **Time:** 2 months MVP
- **Expertise:** Not Lean experts
- **Quality:** Numina is state-of-the-art
- **Focus:** Integration, not reimplementation

### Why Semantic Scholar vs. Indexing ArXiv?
- **Cost:** Indexing ArXiv = $1000s in compute
- **Time:** Weeks to set up
- **Maintenance:** Constant updates
- **S.Scholar:** Free API, 200M papers, good embeddings

### Why Claude API vs. Other LLMs?
- **Quality:** Best for mathematical reasoning
- **Context:** 200k tokens (can fit long theorems)
- **Cost:** $150 budget sufficient for testing

---

## ⚡ Performance Considerations

### Bottlenecks

1. **Claude Code sessions** (~30–60s per block, longer for HARD mode)
   - **Solution:** resume mode skips already-verified blocks; olean caching avoids re-typechecking the rest of `Paper.lean` on each verification

2. **ArXiv PDF downloads** (~2-5s per paper)
   - **Solution:** Cache PDFs, parallel downloads

3. **LLM judge** (~$0.01-0.05 per comparison)
   - **Solution:** Only use on top-3 candidates

### Optimizations

- **Caching:** All ArXiv results, embeddings
- **Batching:** Multiple LLM calls in one request
- **Parallelization:** Download PDFs concurrently

---

## 🔐 Security

### API Keys
- Never commit to repo
- Use `.env` file
- `.gitignore` includes all key files

### User Uploads
- Sanitize .tex input
- Limit file size
- Virus scanning (future)

---

## 🚀 Deployment Strategy

### Phase 1: Local Development (Current)
- Run on laptop
- Per-paper state in `PAPER_INDEX.md` / `Paper.lean` / `REVIEW.md`
- Manual testing

### Phase 2: Hosted Backend
- FastAPI on Railway/Render
- Async job queue (Celery + Redis)

### Phase 3: Full Stack
- Frontend on Vercel
- Backend API
- CI/CD with GitHub Actions

---

## 📊 Scalability

### Current Limits (MVP)
- ~10 papers/day
- ~50 blocks/paper
- ~500 total formalized blocks

### Future Scaling
- Horizontal scaling (multiple workers)
- Caching layer (Redis)
- CDN for static files

---

## 🧪 Testing Strategy

### Unit Tests
- Parser: test on sample .tex files
- Novelty: test with golden dataset
- Each module isolated

### Integration Tests
- End-to-end on 1 complete paper
- Check all intermediate outputs

### Acceptance Tests
- Process 10 diverse papers
- Accuracy >75%
- <5 min total time

---

## 📝 Design Decisions

### Why Not Use Existing Tools?

**Q:** Why not use MerLean?
**A:** MerLean doesn't have novelty detection. We add that layer.

**Q:** Why not use Approach Zero?
**A:** Requires full ArXiv indexing. Too expensive for MVP. We use Semantic Scholar instead.

**Q:** Why not train custom models?
**A:** 2-month timeline, $150 budget. Use existing embeddings + LLMs.

### Why This Architecture?

**Modularity:** Each component replaceable
**Testability:** Each module testable independently
**Scalability:** Easy to add workers/caching later
**Maintainability:** Clear separation of concerns

---

## 🔮 Future Extensions

### Quality Assessment
- Citation prediction
- Impact scoring
- Importance ranking

### Multi-Domain Support
- Not just Boolean algebra
- Auto-detect domain (MSC codes)
- Domain-specific validators

### Collaborative Features
- User accounts
- Review system
- Discussion threads

### AI Research Assistant
- Suggest related work
- Propose generalizations
- Auto-generate conjectures
