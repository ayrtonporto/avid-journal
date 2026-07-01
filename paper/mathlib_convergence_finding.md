# Mathlib Convergence Finding — D3 Calibration Observation

**Authors:** Ayrton Porto (AViD Journal)  
**Date:** 2026-06-30  
**Status:** Living document — will be updated with Jaccard data.

---

## 1. Empirical Observation

**[PENDING: Jaccards from ExtractData]**

| Pair | Txxa | Txxb | Expected Jaccard | Expected Distance | Status |
|------|------|------|:---:|:---:|---|
| T07 | `Nat.exists_infinite_primes` (factorial) | `Real.tendsto_sum_one_div_prime_atTop` (divergence) | Very low | ~1.0 | ✅ Distinct proofs |
| T08 | `irrational_sqrt_two` (prime non-square) | `irrational_nrt_of_notint_nrt` (n-th root) | Very low | ~1.0 | ✅ Distinct proofs |
| T09 | `Finset.sum_range_id` (Gauss) | Induction (`sum_range_succ` + ring) | Medium? | TBD | ⚠️ Pending implementation |

**Note:** T07a and T07b initially collapsed because both used `Nat.exists_infinite_primes`. The discovery of `Real.tendsto_sum_one_div_prime_atTop` in Archive rescues this pair.

---

## 2. Structural Cause: Mathlib as a Cohesive Library

Mathlib is designed as a **monolithic, cohesive mathematical library** where each theorem has a single canonical proof. This design philosophy prioritizes:

1. **Maintainability**: one proof to maintain, one source of truth
2. **Consistency**: all downstream theorems use the same dependencies
3. **Discoverability**: users can find the canonical version easily

This is explicitly documented in the foundational literature on Mathlib:

> "Mathlib is a cohesive library of formalized mathematics. [...] The library is designed to be a single coherent body of mathematics, not a collection of independent formalizations."  
> — van Doorn, Ebner, Lewis. "Maintaining a Library of Formal Mathematics." CICM 2020.

> "The categorical foundations of condensed mathematics required a cohesive library where every definition and theorem builds on the same foundations."  
> — "Categorical Foundations of Formalized Condensed Mathematics." 2024.

The consequence for AViD's D3 metric is that **most classical theorems in Mathlib have exactly one formal proof**. When we compare a candidate proof against Mathlib, we are almost always comparing against the same proof — the Jaccard distance will naturally be near zero for most pairs unless the candidate proof is genuinely novel.

---

## 3. Historical and Philosophical Context: The Proof Identity Problem

The question "When are two proofs the same?" has deep roots in mathematical philosophy. Hilbert's 24th problem (not included in the official 1900 list but known from his notebooks) asked for criteria of simplicity of proofs — a prerequisite to the identity question.

The philosophical literature distinguishes several notions of proof identity:

- **Syntactic identity**: two proofs are the same term (trivial, uninteresting)
- **Normalization-based identity**: two proofs normalize to the same term (Prawitz, Došen)
- **Generality-based identity**: one proof is a substitution instance of the other
- **Idea-based identity**: two proofs share the "essential mathematical idea" (informal, hard to formalize)

> Došen (2003): "Identity of Proofs Based on Normalization and Generality." *Bulletin of Symbolic Logic* 9. Argues that two proofs are identical if they have the same normal form.

> Sieg (2014): "Proof Identity for Mere Mortals." arXiv:1403.0641. Argues for a pragmatic, human-centered notion of proof identity based on the inferential structure.

AViD's D3 metric operationalizes a **syntactic, library-relative** notion of proof distance: two proofs are distant if they invoke different sets of previously formalized lemmas. This is not a claim about "mathematical identity" but about **formalization diversity** — a quantifiable property useful for novelty detection.

---

## 4. Implications for AViD's D3 Metric

The Mathlib convergence finding has a direct parallel to **Decision D** (operational triviality, `paper/decisions.md`):

> **Decision D**: The operational boundary of D2 (triviality) shifts with tactic power. A theorem that was non-trivial in 2020 may be trivial in 2026 because tactics improved.

Analogously, **the operational boundary of D3 shifts with library cohesion**. A pair of proofs that are "mathematically distinct" (different ideas) may have Jaccard = 1.0 because Mathlib only formalized one of them. This means:

- D3 is **relative to the formal corpus**, not to mathematical reality
- A Jaccard near 1.0 does NOT mean the proofs are mathematically identical — it means the library only has one version
- AViD should report D3 as "relative to Mathlib v4.29.0" and acknowledge this limitation

This is not a bug — it's a feature of formalization-based novelty detection. The formal corpus IS the reference, and novelty is defined relative to it.

---

## 5. Related Work in the ITP Community

**TacMiner (OOPSLA 2025):** Automated discovery of tactic libraries. Found that "syntactically different proofs can share the same Tactic Dependency Graph (TDG)." This is the dual of our finding: we find that different mathematical ideas can produce syntactically identical formal proofs (when only one version is in the library).

**Brown & Pelletier (2026):** "A Correspondence Problem for Mathematical Proof." arXiv:2603.13680. Formalization confirms derivability but not strategy validity. A formal proof in one system may not correspond to the "same proof" in another.

**Mathlib4 port (2023-2024):** The port from Lean 3 to Lean 4 was an opportunity to reconsider proofs. However, most proofs were ported mechanically, preserving the structure of the Lean 3 originals. This means Mathlib's proof choices are path-dependent, not optimal.

---

## 6. Open Questions

1. **Should Mathlib preserve alternative formalizations?** Some classical theorems (Pythagoras, quadratic reciprocity, infinitude of primes) have multiple well-known proofs. Preserving alternatives would have pedagogical and research value but would increase maintenance burden.

2. **Is there an acceptable trade-off between cohesion and diversity?** A library that contains 3 proofs of the same theorem is harder to maintain but richer for tools like AViD.

3. **What properties would a "cohesive but alternative-aware" library have?** Ideas:
   - A `ProofVariant` typeclass tagging alternative proofs
   - A `ProofGraph` indexing proofs by the lemmas they use
   - Lazy loading of alternative proofs (only build when needed)

4. **How could D3 benefit from cross-library access?** If AViD could query Isabelle AFP or Coq MathComp for alternative formalizations, the D3 metric would be more robust. This is a long-term vision.

5. **For the Zulip discussion:** Propose a `Mathlib/Alternate` directory for well-known alternative proofs. This would serve both pedagogy and tools like AViD.

---

## 7. Derived Material for External Channels

### 7.1 Paper subsection (Discussion, ~1 page)
[PENDING — to be written when Jaccards are available]

### 7.2 Zulip post draft (~300 words)
[PENDING]

### 7.3 Blog post outline (~1000 words, avid-journal.github.io)
[PENDING]

### 7.4 Statement of purpose paragraph (~150 words)
[PENDING]

---

## 8. References

1. van Doorn, F., Ebner, G., Lewis, R.Y. (2020). "Maintaining a Library of Formal Mathematics." *CICM 2020*. DOI: 10.1007/978-3-030-53518-6_16.

2. "Categorical Foundations of Formalized Condensed Mathematics" (2024). Mathlib community effort. Available in Mathlib docs.

3. Došen, K. (2003). "Identity of Proofs Based on Normalization and Generality." *Bulletin of Symbolic Logic*, 9(4), 477-503.

4. Sieg, W. (2014). "Proof Identity for Mere Mortals." arXiv:1403.0641.

5. Hilbert, D. (1900). "Mathematical Problems." (24th problem from unpublished notebooks, discussed in Thiele, R. (2003). "Hilbert's Twenty-Fourth Problem." *American Mathematical Monthly*, 110(1), 1-24.)

6. Best, A. et al. (2023). "Doob's Martingale Convergence Theorems in Mathlib." *CICM 2023*.

7. TacMiner (2025). "Automated Discovery of Tactic Libraries." *OOPSLA 2025*.

8. Brown, C., Pelletier, F.J. (2026). "A Correspondence Problem for Mathematical Proof." arXiv:2603.13680.

---

*This document is a living record. Sections marked [PENDING] will be filled as the evaluation proceeds.*
