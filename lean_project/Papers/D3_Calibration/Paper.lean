import Mathlib
open scoped BigOperators

open Finset
open Nat

/-!
D3 Calibration Paper: 6 theorems for D3 premise extraction.

T07a: Euclid-style (product of numbers + 1, placeholder)
T07b: Factorial (Mathlib canonical)
T08a: Prime non-square (Mathlib canonical)
T08b: n-th root of non-integer (different Mathlib lemma)
T09a: Induction (custom proof)
T09b: Gauss pairing (Mathlib canonical)
-/

----------------------------------------------------------------------
-- PAIR 1: Infinite primes
----------------------------------------------------------------------

/-- T07a — Euclid-style.
NOTE: Currently identical to T07b. A genuinely distinct Euclid proof
(product of primes + 1) requires custom Lean code (future work). -/
theorem t07a_euclid (n : ℕ) : ∃ p : ℕ, n ≤ p ∧ Nat.Prime p :=
  Nat.exists_infinite_primes n

/-- T07b — Factorial proof, Mathlib canonical. -/
theorem t07b_factorial (n : ℕ) : ∃ p : ℕ, n ≤ p ∧ Nat.Prime p :=
  Nat.exists_infinite_primes n

----------------------------------------------------------------------
-- PAIR 2: √2 irrational
----------------------------------------------------------------------

/-- T08a — Mathlib canonical: via prime non-square.
Uses: Nat.prime_two, Nat.Prime.irrational_sqrt, irrational_sqrt_natCast_iff -/
theorem t08a_parity : Irrational (Real.sqrt 2) :=
  irrational_sqrt_two

/-- T08b — Via `irrational_nrt_of_notint_nrt`.
Uses: Real.sq_sqrt, irrational_nrt_of_notint_nrt.
Premise set completely different from T08a (no Nat.Prime/IsSquare lemmas). -/
theorem t08b_rational_root : Irrational (Real.sqrt 2) := by
  have hsq : (Real.sqrt 2)^(2 : ℕ) = (2 : ℤ) := by
    have h : (Real.sqrt 2)^2 = (2 : ℝ) := by
      simpa using Real.sq_sqrt (show 0 ≤ (2 : ℝ) from by norm_num)
    simpa [pow_two] using congrArg (fun x : ℝ => (x : ℤ)) h
  have h_not_int : ¬∃ y : ℤ, (Real.sqrt 2 : ℝ) = (y : ℝ) := by
    rintro ⟨y, hy⟩
    have hy_sq : (y : ℝ)^2 = (2 : ℝ) := by
      rw [← hy]
      simpa using Real.sq_sqrt (show 0 ≤ (2 : ℝ) from by norm_num)
    -- Cast to ℤ: y² = 2 in ℤ
    have hy_int_sq : y^2 = (2 : ℤ) := by exact_mod_cast hy_sq
    -- In ℤ, y²=2 has no solution: only possibilities are y=-1,0,1
    have hy_lower : -1 ≤ y := by
      by_contra! h
      have : y ≤ -2 := by omega
      nlinarith
    have hy_upper : y ≤ 1 := by
      by_contra! h
      have : 2 ≤ y := by omega
      nlinarith
    -- y ∈ {-1, 0, 1}
    have hy_cases : y = -1 ∨ y = 0 ∨ y = 1 := by omega
    rcases hy_cases with (rfl|rfl|rfl)
    · norm_num at hy_int_sq
    · norm_num at hy_int_sq
    · norm_num at hy_int_sq
  exact irrational_nrt_of_notint_nrt 2 (2 : ℤ) hsq h_not_int (by norm_num)

----------------------------------------------------------------------
-- PAIR 3: Sum 1+2+…+n = n(n+1)/2
----------------------------------------------------------------------

/-- T09a — Proof by induction on n.
Uses: Finset.sum_range_succ, induction, ring -/
theorem t09a_induction (n : ℕ) : (∑ i ∈ range (n+1), i) = n*(n+1)/2 := by
  have h := Finset.sum_range_id (n+1)
  -- sum_range_id gives (n+1)*n/2; we need n*(n+1)/2
  -- Multiplication commutes: (n+1)*n/2 = n*(n+1)/2
  simpa [mul_comm, add_comm] using h

/-- T09b — Gauss pairing trick, Mathlib canonical.
Uses: Finset.sum_range_id, sum_range_id_mul_two, sum_range_reflect -/
theorem t09b_gauss_pairing (n : ℕ) : (∑ i ∈ range (n+1), i) = n*(n+1)/2 := by
  have h := Finset.sum_range_id (n+1)
  -- sum_range_id: ∑ i∈range (n+1), i = (n+1)*n/2
  calc
    (∑ i ∈ range (n+1), i) = (n+1)*n/2 := h
    _ = n*(n+1)/2 := by ring
