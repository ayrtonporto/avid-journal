# AViD Journal - Architecture

System design and technical decisions.

---

## 🏛️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AViD JOURNAL                           │
│              Automated Mathematics Journal                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Input: .tex     │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐    ┌──────────────┐
│   PARSER     │   │  NOVELTY     │    │ FORMALIZER   │
│              │   │   CHECK      │    │              │
│ Extract      │   │              │    │ Lean 4       │
│ blocks       │   │ Is theorem   │    │ Numina       │
│              │   │ new?         │    │              │
└──────┬───────┘   └──────┬───────┘    └──────┬───────┘
       │                  │                    │
       │                  │                    │
       └──────────────────┼────────────────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │   DECISION   │
                  │              │
                  │ Accept/      │
                  │ Reject       │
                  └──────────────┘
```

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

**Two-Layer Approach:**

#### Layer 1: Mathlib Check (via Numina)
- Numina uses LeanDex internally
- When formalizing, it searches Mathlib
- If found → imports automatically

**We don't reimplement this.**

#### Layer 2: ArXiv Check (Our Contribution)
- Search ArXiv corpus for similar papers
- Compare theorem-to-theorem
- Report: novel / exists in [paper X]

**Pipeline:**

```
Theorem text
    │
    ▼
┌─────────────────────────────┐
│ ArXiv Search                │
│ (arxiv_search.py)           │
│                             │
│ • Semantic Scholar API      │
│ • MSC code filtering        │
│ • Abstract-level retrieval  │
│                             │
│ Output: top-20 papers       │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Paper Extraction            │
│ (paper_extractor.py)        │
│                             │
│ • Download PDFs             │
│ • Extract text              │
│                             │
│ Output: paper text          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Theorem Extraction          │
│ (theorem_extractor.py)      │
│                             │
│ • Regex patterns            │
│ • Heuristic matching        │
│                             │
│ Output: theorems list       │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Comparison                  │
│ (comparator.py)             │
│                             │
│ • Embedding similarity      │
│ • LLM judge (top-3)         │
│                             │
│ Output: verdict             │
└─────────────────────────────┘
```

**Files:**
- `arxiv_search.py` - Search papers
- `paper_extractor.py` - Download & extract
- `theorem_extractor.py` - Extract theorems
- `comparator.py` - LLM-based comparison

---

### 3. Formalization Module (`src/formalization/`)

**Purpose:** Translate LaTeX → Lean 4, verify correctness.

**Tool:** Numina-Lean-Agent (external)

**Our Role:** Wrapper + orchestration

**Pipeline:**

```
Blocks (ordered topologically)
    │
    ▼
┌─────────────────────────────┐
│ Lean Project Manager        │
│ (lean_project.py)           │
│                             │
│ • Create lakefile           │
│ • Initialize Paper.lean     │
│ • Manage imports            │
└──────────┬──────────────────┘
           │
           ▼
For each block:
┌─────────────────────────────┐
│ Numina Interface            │
│ (numina_interface.py)       │
│                             │
│ 1. Build input:             │
│    - Context (prev blocks)  │
│    - Statement with sorry   │
│                             │
│ 2. Call Numina:             │
│    - Auto-formalize         │
│    - Verify with Lean-LSP   │
│                             │
│ 3. If success:              │
│    - Add to Paper.lean      │
│    - Update context         │
└─────────────────────────────┘
```

**Key Insight:** Dependency ordering matters.

Block B references Block A → Must formalize A first → A becomes context for B.

**Files:**
- `lean_project.py` - Project structure
- `numina_interface.py` - Numina wrapper
- `orchestrator.py` - Main loop

---

### 4. Database Module (`src/database/`)

**Purpose:** Persistent storage.

**Schema:**

```sql
-- Papers
papers (
  id TEXT PRIMARY KEY,
  title TEXT,
  authors TEXT,
  abstract TEXT,
  msc_codes TEXT,
  status TEXT
)

-- Blocks
blocks (
  id INTEGER PRIMARY KEY,
  paper_id TEXT,
  type TEXT,
  label TEXT,
  title TEXT,
  content_latex TEXT,
  proof_latex TEXT,
  block_refs TEXT,  -- JSON list of references
  FOREIGN KEY (paper_id) REFERENCES papers(id)
)

-- Novelty Results
novelty_results (
  id INTEGER PRIMARY KEY,
  block_id INTEGER,
  is_novel BOOLEAN,
  source_type TEXT,  -- 'mathlib' or 'arxiv'
  source_ref TEXT,   -- match details
  confidence REAL,
  FOREIGN KEY (block_id) REFERENCES blocks(id)
)

-- Lean Projects
lean_projects (
  id INTEGER PRIMARY KEY,
  paper_id TEXT,
  project_path TEXT,
  lean_full TEXT,
  status TEXT,
  FOREIGN KEY (paper_id) REFERENCES papers(id)
)
```

**Key Function:** `get_ordered_blocks_for_lean(paper_id)`
- Returns blocks in topological order
- Uses Kahn's algorithm on dependency graph

**Files:**
- `db.py` - All database operations

---

## 🔀 Data Flow

### End-to-End Flow

```
1. User submits paper.tex
         │
         ▼
2. Parser extracts blocks → Save to DB
         │
         ▼
3. For each block (in topo order):
         │
         ├─→ Novelty check (ArXiv)
         │   ├─ Search papers
         │   ├─ Extract theorems
         │   ├─ Compare
         │   └─ Save verdict to DB
         │
         ├─→ Formalization (Numina)
         │   ├─ Build Lean input
         │   ├─ Call Numina
         │   ├─ Verify with Lean
         │   └─ Save to Paper.lean
         │
         └─→ Update block status
         │
         ▼
4. Generate report:
   - Novelty summary
   - Verification summary
   - Paper.lean download
         │
         ▼
5. Decision: Accept / Reject
```

---

## 🔧 Technology Choices

### Why Python?
- Fast prototyping
- Rich ecosystem (requests, numpy, sentence-transformers)
- Easy integration with APIs

### Why SQLite → PostgreSQL?
- SQLite: Simple for MVP
- PostgreSQL: Production (concurrent access, better querying)

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

1. **Numina calls** (~30-60s per block)
   - **Solution:** Async processing, progress UI

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

### Database
- Prepared statements (SQLite safe)
- Input validation
- Rate limiting (future)

---

## 🚀 Deployment Strategy

### Phase 1: Local Development (Current)
- Run on laptop
- SQLite database
- Manual testing

### Phase 2: Hosted Backend (Week 5-6)
- FastAPI on Railway/Render
- PostgreSQL database
- Async job queue (Celery + Redis)

### Phase 3: Full Stack (Week 7-8)
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
- Database sharding

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
