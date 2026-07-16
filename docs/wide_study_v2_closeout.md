# Wide Study v2 — Closeout

**Date:** 2026-07-16  
**Data:** `results/wide_study.csv` (v2, auto-exclusion active, 37 evaluable papers)  
**Status:** Final. No re-execution.

---

## 1. Skipped Papers (15/52)

| # | arXiv ID | Role | Skip reason |
|---|----------|------|-------------|
| 1 | 0909.0395v3 | retracted | no_theorem_env |
| 2 | 1010.2295v3 | retracted | no_theorem_env |
| 3 | math-ph/0108016v4 | retracted | no_theorem_env |
| 4 | 1002.2004v7 | retracted | no_theorem_env |
| 5 | 1608.00364v2 | retracted | no_theorem_env |
| 6 | math/0307046v1 | control | no_theorem_env |
| 7 | 0904.2445v1 | control | no_theorem_env |
| 8 | 1101.3431v2 | control | no_theorem_env |
| 9 | math-ph/0207026v2 | control | no_theorem_env |
| 10 | 1401.7852v2 | control | no_theorem_env |
| 11 | 0808.0064v1 | control | no_theorem_env |
| 12 | 1201.4026v2 | control | no_theorem_env |
| 13 | math/0402452v2 | control | no_theorem_env |
| 14 | 0904.1783v3 | control | no_theorem_env |
| 15 | 1501.01768v3 | control | no_theorem_env |

**Breakdown:**

| Role | Count |
|------|:-----:|
| Retracted | 5 |
| Control | 10 |

**Reason:** 100% `no_theorem_env` — the LaTeX source was found in cache and had a tex file >1KB, but no `\begin{theorem}`, `\begin{lemma}`, `\begin{proposition}`, or `\begin{corollary}` environment was found. These papers use custom environment names (e.g., `\begin{thm}`, `\begin{prop}`) or have theorems in non-standard forms that the simple regex (`\begin{theorem}` with no variants) doesn't capture.

**Skew:** Controls were twice as likely to be skipped as retracted papers (10 vs 5). Possible cause: the control papers in `control_candidates.yaml` were selected by arXiv category match, not by theorem-statement availability. Some controls may be short notes, survey articles, or papers where the main result is in a custom environment.

---

## 2. Strong Matches (score ≥ 0.75) — 7 papers

### Match #1 — 0711.2941v2 (retracted)
- **Query:** "Holomorphic fillability and cohomology"
- **Match:** [0712.3484](https://arxiv.org/abs/0712.3484) — "On the cohomology rings of holomorphically fillable manifolds"
- **Score:** 0.8126 | **Years:** query ~2007, match ~2007
- **Relation:** **Vecino temático.** Same mathematical area (cohomology of fillable manifolds). Not the known duplicator — both papers are in the same subfield.

### Match #2 — 0711.1149v2 (retracted)
- **Query:** "Stein or Milnor fillability and cohomology"
- **Match:** [0712.3484](https://arxiv.org/abs/0712.3484) — "On the cohomology rings of holomorphically fillable manifolds"
- **Score:** 0.8198 | **Years:** query ~2007, match ~2007
- **Relation:** **Vecino temático.** Same area as Match #1. Both retracted papers from the same author group matched the same paper. Not the known duplicator.

### Match #3 — 1011.3176v2 (retracted)
- **Query:** "Rotation sets of invariant separating continua of annular homeomorphisms"
- **Match:** [1012.0981](https://arxiv.org/abs/1012.0981) — "Prime end rotation numbers of invariant separating contunua of annular homeomorphisms"
- **Score:** 0.8228 | **Years:** query ~2010, match ~2010
- **Relation:** **Vecino temático.** Highly overlapping topic (rotation numbers, continua, annular homeomorphisms). Titles are almost identical in subject matter. Likely the same research group or a closely competing result.

### Match #4 — 0904.2489v1 (control)
- **Query:** "Entropies of compact strictly convex projective manifolds"
- **Match:** [2206.04334](https://arxiv.org/abs/2206.04334) — "From Cascades to J-holomorphic Curves and Back"
- **Score:** 0.7793 | **Years:** query ~2009, match ~2022
- **Relation:** **No relacionado.** Match is 13 years newer and about a completely different topic (J-holomorphic curves vs projective manifolds entropy). High score likely from shared vocabulary ("manifold", "curves", "compact") rather than genuine theorem overlap.

### Match #5 — 1212.0196v2 (retracted) ⭐
- **Query:** "On non-congruent numbers with 3 modulo 8 prime factors"
- **Match:** [1208.2149](https://arxiv.org/abs/1208.2149) — "On non-congruent numbers with 1 modulo 4 prime factors"
- **Score:** 0.8696 | **Years:** query ~2012, match ~2012
- **Relation:** **Duplicador conocido.** The retracted paper (1212.0196) was withdrawn as "a corollary of a well-known result by Monsky." The matched paper (1208.2149) is the Monsky-style result on non-congruent numbers. TheoremSearch found the actual known result that caused the retraction. **This is a true positive — the highest score in the entire study (0.8696).**

### Match #6 — 1501.01654v1 (control)
- **Query:** "Almost universal quadratic forms"
- **Match:** [1402.1640](https://arxiv.org/abs/1402.1640) — "A characterization of almost universal ternary quadratic polynomials with odd prime power conductor"
- **Score:** 0.7902 | **Years:** query ~2015, match ~2014
- **Relation:** **Vecino temático.** Same mathematical area (quadratic forms, almost universal). The matched paper is one year older and on a closely related topic.

### Match #7 — 1004.3381v4 (retracted)
- **Query:** "Rectangle slicing bound f(m) ≤ c·(2m+1)²"
- **Match:** [1409.5159](https://arxiv.org/abs/1409.5159) — "Permutation classes"
- **Score:** 0.7856 | **Years:** query ~2010, match ~2014
- **Relation:** **No relacionado.** Completely different topic (permutation classes vs rectangle slicing). The paper 1004.3381 was withdrawn because "most results were already known (Gyárfás & Lehel, 1970)" — TheoremSearch did NOT find the actual duplicator. High score likely from vocabulary overlap in combinatorics ("size m", "independent set").

---

## 3. Statistical Comparison — Retracted vs Control Scores

**Samples:**

- Retracted: n=21, mean=0.7167, median=0.6970, σ=0.0716
- Control: n=16, mean=0.7107, median=0.7170, σ=0.0452

```
Retracted scores (sorted):
0.599, 0.648, 0.656, 0.657, 0.662, 0.672, 0.673, 0.683, 0.690, 0.693,
0.697, 0.715, 0.716, 0.723, 0.725, 0.730, 0.786, 0.813, 0.820, 0.823, 0.870

Control scores (sorted):
0.650, 0.651, 0.654, 0.676, 0.684, 0.690, 0.704, 0.705, 0.717, 0.724,
0.730, 0.730, 0.741, 0.747, 0.779, 0.790
```

**Mann-Whitney U test (two-sided):**
- U = 161.50
- **p = 0.854**

**Welch's t-test (unequal variance):**
- t = 0.324
- **p = 0.748**

Both tests fail to reject the null hypothesis that the two distributions are identical. The p-values are far above any conventional significance threshold (0.05, 0.01, 0.001). **The two groups are statistically indistinguishable in their TheoremSearch similarity scores.**

---

## Summary Table

| Metric | Retracted (n=21) | Control (n=16) |
|--------|:---:|:---:|
| Mean score | 0.7167 | 0.7107 |
| Median score | 0.6970 | 0.7170 |
| Std dev | 0.0716 | 0.0452 |
| Min score | 0.5993 | 0.6505 |
| Max score | 0.8696 | 0.7902 |
| Strong matches (≥0.75) | 5 | 2 |
| Mann-Whitney p | — | **0.854** |
| Skipped (no_theorem_env) | 5 | 10 |
