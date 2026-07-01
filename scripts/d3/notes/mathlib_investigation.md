# Mathlib Investigation — T07 and T09 canonical proofs

**Date:** 2026-06-30  
**Purpose:** Deep investigation of Mathlib v4.29.0 canonical proofs for the two collapsed pairs.

---

## T07 — Infinitude of Primes

### Canonical proof: `Nat.exists_infinite_primes`

**File:** `Mathlib/Data/Nat/Prime/Infinite.lean` (53 lines)

```lean
theorem exists_infinite_primes (n : ℕ) : ∃ p, n ≤ p ∧ Prime p :=
  let p := minFac (n ! + 1)
  have f1 : n ! + 1 ≠ 1 := ne_of_gt <| succ_lt_succ <| factorial_pos _
  have pp : Prime p := minFac_prime f1
  have np : n ≤ p :=
    le_of_not_ge fun h =>
      have h₁ : p ∣ n ! := dvd_factorial (minFac_pos _) h
      have h₂ : p ∣ 1 := (Nat.dvd_add_iff_right h₁).2 (minFac_dvd _)
      pp.not_dvd_one h₂
  ⟨p, np, pp⟩
```

**Dependency chain (3 layers):**

| Layer | Lemma | File | Depends on |
|-------|-------|------|------------|
| 0 | `exists_infinite_primes` | `Data/Nat/Prime/Infinite.lean` | ↓ |
| 1 | `Nat.minFac` | `Data/Nat/Prime/Defs.lean` | `Nat.prime_def`, `Nat.minFac_lemma` |
| 1 | `Nat.factorial_pos` | `Data/Nat/Factorial/Basic.lean` | `Nat.factorial_succ`, `Nat.succ_pos` |
| 1 | `Nat.minFac_prime` | `Data/Nat/Prime/Defs.lean` | `Nat.minFac`, `Nat.prime_def` |
| 1 | `Nat.dvd_factorial` | `Data/Nat/Factorial/Basic.lean` | `Nat.factorial_succ`, `Nat.dvd_mul` |
| 1 | `Nat.dvd_add_iff_right` | `Algebra/GroupPower/Lemmas.lean` | `Nat.dvd_add` |
| 1 | `Nat.minFac_dvd` | `Data/Nat/Prime/Defs.lean` | `Nat.minFac` |
| 1 | `Nat.minFac_pos` | `Data/Nat/Prime/Defs.lean` | `Nat.minFac`, `Nat.pos_of_ne_zero` |
| 2 | All layer-1 lemmas converge to: | `Nat.prime_def`, `Nat.dvd`, `Nat.factorial_succ`, `Nat.succ_pos` | Core arithmetic |

**Strategy:** Factorial (`n! + 1`) + minimal prime factor.  
**Key insight:** The minimal prime factor of `n! + 1` must be `> n` (otherwise it would divide `n!` and thus divide `1`).

### Alternative formulations in Mathlib

| Lemma | File | Proof strategy |
|-------|------|---------------|
| `Nat.exists_infinite_primes` | `Prime/Infinite.lean` | Factorial + minFac |
| `Nat.not_bddAbove_setOf_prime` | `Prime/Infinite.lean` | Wrapper: direct call to `exists_infinite_primes` |
| `Nat.infinite_setOf_prime` | `PrimeFin.lean` | Wrapper: `Set.infinite_of_not_bddAbove` |

**All 3 use the same proof.** They are reformulations (∃ infinite → not bddAbove → Set.Infinite), not alternative proofs.

### Independent proof found: Divergence of ∑ 1/p

**File:** `Archive/Wiedijk100Theorems/SumOfPrimeReciprocalsDiverges.lean` (234 lines)

**Theorem:** `Real.tendsto_sum_one_div_prime_atTop` — the sum of reciprocals of primes diverges.

**Proof strategy:** Erdős's proof by upper and lower estimates:
1. Assume the sum converges
2. Then ∃ k such that sum of 1/p for p > k is < 1/2
3. Partition {0,...,x-1} into M (products of small primes) and U (divisible by a large prime)
4. |U| < x/2 (bounded by the prime reciprocal sum)
5. |M| ≤ 2^k * √x (squarefree factorization argument)
6. Choose x = (2^(k+1))² → both |M|, |U| ≤ x/2 → x < x, contradiction

**Implication:** Divergence of sum → infinitely many primes (finite primes → finite sum → contradiction). This is a **genuinely distinct proof** from `Nat.exists_infinite_primes`.

**Dependency chain (completely different from factorial proof):**
- `Topology/Algebra/InfiniteSum` (topological sums)
- `Data/Nat/Squarefree` (squarefree numbers)
- `Set` operations (partitions, cardinalities)
- `Real` arithmetic (division, sqrt)
- No factorial, no `minFac`

**Verdict:** ✅ **Can be used as T07b's proof** with a short corollary: "if finitely many primes, sum would converge (finite set → finite sum), contradicting divergence." This gives completely different premise sets.

### Other approaches NOT in Mathlib
- ❌ Euclid's product of primes + 1 proof
- ❌ Furstenberg's topological proof
- ❌ Fermat numbers (pairwise coprime) proof
- ❌ Euler's phi function / Zsigmondy proof

---

## T09 — Sum 1+2+…+n = n(n+1)/2

### Canonical proof: `Finset.sum_range_id`

**File:** `Mathlib/Algebra/BigOperators/Intervals.lean` (lines 177-188)

```lean
theorem sum_range_id_mul_two (n : ℕ) : (∑ i ∈ range n, i) * 2 = n * (n - 1) :=
  calc
    (∑ i ∈ range n, i) * 2 = (∑ i ∈ range n, i) + ∑ i ∈ range n, (n - 1 - i) := by
      rw [sum_range_reflect (fun i => i) n, mul_two]
    _ = ∑ i ∈ range n, (i + (n - 1 - i)) := sum_add_distrib.symm
    _ = ∑ _ ∈ range n, (n - 1) :=
      sum_congr rfl fun _ hi => add_tsub_cancel_of_le <| Nat.le_sub_one_of_lt <| mem_range.1 hi
    _ = n * (n - 1) := by rw [sum_const, card_range, Nat.nsmul_eq_mul]

theorem sum_range_id (n : ℕ) : ∑ i ∈ range n, i = n * (n - 1) / 2 := by
  rw [← sum_range_id_mul_two n, Nat.mul_div_cancel _ Nat.zero_lt_two]
```

**Dependency chain:**

| Layer | Lemma | File | Key dependencies |
|-------|-------|------|-----------------|
| 0 | `sum_range_id` | `BigOperators/Intervals.lean` | ↓ |
| 0 | `sum_range_id_mul_two` | `BigOperators/Intervals.lean` | ↓ |
| 1 | `sum_range_reflect` | `BigOperators/Intervals.lean` | `sum_Ico_reflect` |
| 1 | `sum_add_distrib` | `BigOperators/Basic.lean` | `Finset.sum_add` |
| 1 | `sum_congr` | `BigOperators/Basic.lean` | `Finset.sum_congr` |
| 1 | `sum_const` | `BigOperators/Basic.lean` | `Finset.sum_const` |
| 1 | `add_tsub_cancel_of_le` | `Algebra/Order/Sub.lean` | `Nat.add_sub_cancel` |
| 1 | `Nat.le_sub_one_of_lt` | `Data/Nat/Basic.lean` | `Nat` ordering |
| 1 | `Nat.mul_div_cancel` | `Data/Nat/Div.lean` | `Nat` division |
| 2 | `sum_Ico_reflect` | `BigOperators/Intervals.lean` | `Nat.Ico_image_const_sub_eq_Ico` |

**Strategy:** Gauss pairing trick (`sum_range_reflect` reverses the sum, then add termwise).  
**Note the formula:** `n*(n-1)/2` (not `n*(n+1)/2`). Offset by 1.

### Alternative formulations in Mathlib

**None found.** The `sum_range_id` lemma is the ONLY proof of the sum formula in all of Mathlib. The lemma `sum_range_succ` exists (for the induction step) but nobody used induction to prove the closed form.

### Approaches NOT in Mathlib
- ❌ Induction on n (direct)
- ❌ Telescoping sum via (k+1)² - k² = 2k+1
- ❌ Binomial coefficient: C(n+1, 2)
- ❌ Combinatorial: counting handshakes

### Key obstacle for custom induction proof

`ring` tactic doesn't handle `Nat.div`. Any induction proof must either:
1. Avoid division entirely (prove `2*sum = n*(n+1)` first, then divide)
2. Use `arith` with explicit `Nat.div` lemmas

The lemma `sum_range_succ` gives: `∑ i∈range (n+1), i = (∑ i∈range n, i) + n`
Using the IH: `∑ i∈range n, i = n*(n-1)/2`
Goal: `n*(n-1)/2 + n = (n+1)*n/2`
This requires `Nat.div` arithmetic which `ring` and `omega` can't handle.

---

## Overall verdict

| Pair | Alternative proof in Mathlib? | Action |
|------|:---:|---|
| T07 (primes) | ✅ YES — `Real.tendsto_sum_one_div_prime_atTop` | Derive corollary "sum diverges → infinite primes". Completely different premises. |
| T09 (sum) | ❌ NO — only Gauss pairing exists | Must write induction proof from scratch. Strategy: prove `2*sum = n*(n+1)` via induction (avoids div), then divide. The induction step uses `sum_range_succ` and `ring` (no division). |
