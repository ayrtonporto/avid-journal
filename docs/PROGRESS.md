# AViD Journal - Development Progress

**Last Updated:** February 20, 2025

---

## 🎯 Project Goal

Build the first fully automated mathematics journal that:
1. Accepts `.tex` papers
2. Formalizes proofs in Lean 4
3. Verifies correctness
4. Checks novelty (Mathlib + ArXiv)
5. Auto-publishes if valid

---

## 📅 Timeline

**Target:** 2-month MVP (February - April 2025)
- **Weeks 1-4:** Core novelty check system
- **Weeks 5-6:** Formalization integration
- **Weeks 7-8:** Web interface + polish

---

## ✅ Completed (Weeks 0-1)

### Week 0: Foundation
- [x] Project vision defined
- [x] Architecture designed
- [x] Stack decided (Python + Lean 4 + Claude API)

### Week 1: Parser + Database
- [x] LaTeX parser (`src/parser/latex_parser.py`)
  - Extracts theorems, lemmas, definitions
  - Dependency graph extraction
  - Handles custom environments
- [x] CLI for parser (`src/parser/parse_tex.py`)
- [x] Database schema (`src/database/db.py`)
  - SQLite with topological sorting
  - Paper + blocks + novelty results tables
- [x] Lean project manager (`src/formalization/lean_project.py`)
  - Creates lakefile
  - Manages Paper.lean accumulation
  - Import statements from Mathlib

---

## ⏳ In Progress (Week 2)

### Current Focus: ArXiv Paper Search

**Goal:** Given a theorem, find top-K similar papers from ArXiv.

**Components:**
- [ ] `src/novelty/arxiv_search.py`
  - Semantic Scholar API integration
  - MSC code filtering
  - Abstract-level retrieval
  - Reranking by relevance

**Deliverables:**
- Working script: `python arxiv_search.py "theorem text" --top-k 10`
- Accuracy >70% on Boolean algebra test set
- <5s per query

**ETA:** February 22, 2025

---

## 🔜 Planned

### Week 3: Theorem-Level Comparison

**Components:**
- [ ] `src/novelty/paper_extractor.py`
  - Download PDFs from ArXiv
  - Extract text from PDFs
  - Parse LaTeX source if available

- [ ] `src/novelty/theorem_extractor.py`
  - Extract theorems from paper text
  - Regex + heuristics
  - Handle different formats

- [ ] `src/novelty/comparator.py`
  - LLM-as-judge (Claude API)
  - Semantic comparison of theorems
  - Verdict: equivalent / generalization / different

**Deliverables:**
- End-to-end novelty check on 10 test papers
- Precision >80%, Recall >70%

**ETA:** February 29, 2025

---

### Week 4: Formalization Integration

**Components:**
- [ ] `src/formalization/numina_interface.py`
  - Wrapper for Numina-Lean-Agent
  - Input construction with context
  - Result parsing

- [ ] `src/formalization/orchestrator.py`
  - Full pipeline: parser → novelty → formalization
  - Handle dependency ordering
  - Error recovery

**Deliverables:**
- Process 1 complete paper end-to-end
- Generate verified Paper.lean

**ETA:** March 7, 2025

---

### Weeks 5-6: Backend API

**Components:**
- [ ] `src/web/api.py` (FastAPI)
  - /upload endpoint
  - /status/{job_id} (polling)
  - /results/{job_id}

- [ ] Job queue (Celery)
  - Async processing
  - Progress tracking

- [ ] Database improvements
  - PostgreSQL migration
  - Caching layer

**Deliverables:**
- REST API functional
- Process papers asynchronously

**ETA:** March 21, 2025

---

### Weeks 7-8: Web Interface

**Components:**
- [ ] Frontend (React)
  - Upload form
  - Progress tracker
  - Results viewer

- [ ] Deployment
  - Backend: Railway/Render
  - Frontend: Vercel
  - Database: Hosted PostgreSQL

**Deliverables:**
- Public demo site
- Process 10 demo papers
- Video walkthrough

**ETA:** March 31, 2025

---

## 📊 Metrics

### Current Status

| Component | Status | Completion |
|-----------|--------|------------|
| Parser | ✅ Done | 100% |
| Database | ✅ Done | 100% |
| Lean Project Manager | ✅ Done | 100% |
| ArXiv Search | ⏳ In Progress | 30% |
| Theorem Comparison | 🔜 Planned | 0% |
| Formalization | 🔜 Planned | 0% |
| Web Interface | 🔜 Planned | 0% |

**Overall Progress:** ~35% complete

---

## 🎯 Success Criteria (MVP)

**Must Have:**
- [x] Parse .tex files correctly (✅ Done)
- [ ] Search ArXiv for similar papers
- [ ] Compare theorems semantically
- [ ] Formalize in Lean 4 (via Numina)
- [ ] Verify correctness
- [ ] Generate novelty report

**Nice to Have:**
- [ ] Web interface
- [ ] Quality assessment
- [ ] Citation generation

**Demo Requirements:**
- Process 1 complete paper end-to-end
- <5 minutes total time
- Accuracy >75% on novelty detection

---

## 🐛 Known Issues

1. **LeanDex API** - Not publicly accessible
   - **Workaround:** Use Numina's built-in LeanDex
   - **Status:** Non-blocker

2. **Semantic Scholar API** - Rate limits
   - **Solution:** Implement caching + backoff
   - **Status:** To implement in Week 2

3. **Numina setup** - Complex dependencies
   - **Solution:** Dockerize in Week 5
   - **Status:** Future work

---

## 💡 Decisions Made

### Technology Stack
- **Parser:** Custom Python (regex + heuristics)
- **Novelty:** Semantic Scholar + Claude LLM judge
- **Formalization:** Numina-Lean-Agent (not reimplementing)
- **Database:** SQLite → PostgreSQL later
- **Web:** FastAPI + React

### Scope Decisions
- **NOT implementing:** Custom Lean tactics
- **NOT implementing:** Training custom models
- **NOT implementing:** Full ArXiv indexing (too expensive)
- **Focus:** Integration of existing tools into coherent system

---

## 🚀 Next Actions

**This Week:**
1. ✅ Setup GitHub repository
2. ⏳ Implement ArXiv search (Semantic Scholar API)
3. ⏳ Test on Boolean algebra papers

**Next Week:**
1. PDF extraction
2. Theorem comparison
3. Golden dataset expansion

---

## 📝 Notes

- Pivoted from "LeanDex integration" to "ArXiv search" when LeanDex API wasn't accessible
- Decided to leverage Numina's built-in LeanDex instead
- Focus shifted to what's truly novel: ArXiv paper novelty detection
