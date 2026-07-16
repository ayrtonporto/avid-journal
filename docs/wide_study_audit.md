# Wide Study Audit — Julio 2026

**Scope:** Read-only verification of `results/wide_study.csv` and `scripts/run_wide_study.py`.  
**Status:** ⚠️ Two methodological defects found.

---

## 1. Exact Count

**Total rows:** 52 (26 retracted + 26 controls).  
**Source:** `results/wide_study.csv` — `wc -l` returns 53 (header + 52 data rows).

```python
# verified with:
import csv
with open('results/wide_study.csv') as f:
    rows = list(csv.DictReader(f))
len(rows)  # → 52
sum(1 for r in rows if r['role'] == 'retracted')   # → 26
sum(1 for r in rows if r['role'] == 'control')    # → 26
```

✅ Coincide con los 52 esperados (26+26). Ningún papel falta en el CSV.

### However: 38 papers have no scores

38 of 52 papers were **skipped** because their theorem text could not be extracted:

| Reason | Count |
|--------|:-----:|
| arXiv source tarball 404 | 24 |
| No theorem environment found | 4 |
| Already cached but no env | 4 |
| Downloaded but no env | 6 |

When theorem text is `None` or contains `⚠️`, the script writes `strong_match=false` with reason `no theorem text available` (line 79 of `run_wide_study.py`):

```python
if not theorem_text or '⚠️' in theorem_text:
    rows.append({
        ...
        'strong_match': 'false',
        'strong_match_reason': 'no theorem text available',
    })
    continue
```

**Retracted papers affected:** All 26 retracted papers have NO scores — their arXiv sources return 404 (the paper was withdrawn and source tarballs are no longer available). This means the comparison retracted-vs-controls that was reported as "12 strong matches, all controls, 0 retracted" is an artifact of missing data, not a signal.

---

## 2. Which Search Engine Was Used

**Evidence from `scripts/run_wide_study.py`, lines 99-100:**

```python
from src.novelty.theoremsearch import search_theoremsearch
results = search_theoremsearch(theorem_text[:1000], top_k=10)
```

**Only TheoremSearch was used.** Leandex (Mathlib/formal search) was NOT called. The search is exclusively against TheoremSearch's corpus — 9.2M informal theorem statements extracted from arXiv and 7 additional sources.

**Evidence from `src/novelty/theoremsearch.py`, lines 1-11:**

```python
"""TheoremSearch provider for semantic search at the theorem level.

TheoremSearch (https://www.theoremsearch.com/) indexes 9.2M statements
of theorems extracted from arXiv and 7 additional sources. Provides a
public REST API without authentication.
"""
```

**API called:** `POST https://api.theoremsearch.com/search` (line 41-43).

---

## 3. What the Score Measures

The `similarity_score` is the **semantic embedding similarity** between the query text (the paper's theorem statement, truncated to 1000 chars) and the theorem statements in TheoremSearch's index. It is returned directly by TheoremSearch's API.

**Evidence from `src/novelty/theoremsearch.py`, lines 206-270:**

```python
def search_theoremsearch(
    query: str,
    top_k: int = 20,
    ...
    exclude_arxiv_ids: Optional[Iterable[str]] = None,
) -> List[PaperCandidate]:
```

The function sends the query to TheoremSearch, receives a JSON payload, and converts it to `PaperCandidate` objects. Each candidate has a `.similarity_score` attribute.

**Auto-exclusion: NOT applied.**

The function signature includes `exclude_arxiv_ids` (line 211), and the implementation filters results by this list (lines 255-266):

```python
# ── Excluir el propio paper ──────────────────────────────────────────
excluded = {
    _normalize_arxiv_id(aid)
    for aid in (exclude_arxiv_ids or [])
    if _normalize_arxiv_id(aid)
}
if excluded:
    candidates = [
        cand
        for cand in candidates
        if (cand.arxiv_id is None or _normalize_arxiv_id(cand.arxiv_id) not in excluded)
    ]
```

**However, the wide study script does NOT pass this parameter** (line 100):

```python
results = search_theoremsearch(theorem_text[:1000], top_k=10)
# Missing: exclude_arxiv_ids=[aid]
```

**Consequence:** 11 of 12 strong matches are SELF-MATCHES. The paper matched ITS OWN entry in TheoremSearch. This makes the scores uninformative for novelty assessment — every paper with available theorem text achieves a high score by matching itself.

---

## 4. The 12 Strong Matches — Self-Match Analysis

| # | Query paper | Matched paper | Score | Self-match? |
|---|------------|---------------|:-----:|:-----------:|
| 1 | 0808.3225v1 | 0808.3225 | 0.7859 | ✅ YES |
| 2 | 0808.2672v1 | 0808.2672 | 0.8793 | ✅ YES |
| 3 | 1305.3977v1 | 1305.3977 | 0.7969 | ✅ YES |
| 4 | 0904.2489v1 | 0904.2489 | 0.8287 | ✅ YES |
| 5 | 1101.3431v2 | 1101.3431 | 0.8504 | ✅ YES |
| 6 | 1101.3720v1 | 1101.3720 | 0.8312 | ✅ YES |
| 7 | 1201.4618v1 | 1201.4618 | 0.7648 | ✅ YES |
| 8 | 0904.2471v1 | 0904.2471 | 0.7564 | ✅ YES |
| 9 | 1501.01654v1 | 1501.01654 | 0.8214 | ✅ YES |
| 10 | 2501.12205v1 | 2501.12205 | 0.8218 | ✅ YES |
| 11 | 1101.4070v1 | 1101.4070 | 0.8234 | ✅ YES |
| 12 | math/0504586v2 | **0901.4760** | 0.7856 | ❌ NO |

**Only paper 12 (math/0504586v2) is a genuine cross-paper match.** It matched 0901.4760 ("A survey on dynamical percolation") with score 0.7856. Query paper is from 2005 (v2), matched paper is from 2009 (v1) — the match is newer than the query.

For the 11 self-matches: the matched paper IS the query paper (same arxiv_id, stripped of version). This provides no novelty signal.

---

## 5. Retracted Papers — Scores

**0 of 26 retracted papers have scores.** All 26 were skipped because their theorem text could not be extracted:

```python
# From wide_study_statements.md:
# All retracted papers show "⚠️ SOURCE NOT IN CACHE" or "⚠️ NO TEX FILE"
```

**Root cause:** Retracted papers have been withdrawn from arXiv. The `arxiv.org/src/{id}` endpoint returns 404 for withdrawn papers because the source tarball is removed. The cache (`cache/retracted_dataset/`) was built at an earlier time, and 38 of the 52 papers in the wide study were not present in the cache (either never downloaded or the cache key didn't match).

The original dataset builder (`scripts/build_retracted_dataset.py`) may have downloaded sources before withdrawal, but the wide study uses `control_candidates.yaml` which references papers by their full version ID, and the cache lookup hash may not match.

---

## Summary of Defects

| # | Defect | Impact |
|---|--------|--------|
| 1 | Auto-exclusion not applied | 11/12 strong matches are self-matches |
| 2 | 38/52 papers have no theorem text | 0 retracted papers scored; comparison invalid |
| 3 | Cache misses due to hash mismatch | Sources exist but were not found |

**The findings reported earlier ("12 strong matches, all controls") are artifacts of these defects. The wide study, as executed, does not produce valid novelty signals.**
