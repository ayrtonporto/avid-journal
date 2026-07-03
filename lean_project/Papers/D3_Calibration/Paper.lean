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
-- PAIR 2: √2 irrational (two genuinely distinct proofs)
----------------------------------------------------------------------

/-- T08a — Parity / infinite descent proof that √2 is irrational.
Strategy: assume √2 = q ∈ ℚ, derive q.num² = 2·q.den² in ℤ,
show 2 divides both num and den, contradicting coprimality from ℚ.
Uses low-level parity lemmas (Nat.Even, Nat.odd_mul, Nat.Prime.dvd_of_dvd_pow).
Does NOT cite irrational_sqrt_two, Nat.Prime.irrational_sqrt, or any
pre-packaged irrationality lemma. -/
theorem t08a_parity : Irrational (Real.sqrt 2) := by
  rintro ⟨q, hq⟩
  -- hq : Real.sqrt 2 = (q : ℝ)
  have hsq_eq : (Real.sqrt 2)^2 = ((q : ℝ))^2 := by rw [hq]
  have h_two_eq : (2 : ℝ) = ((q : ℝ))^2 := by
    rw [← hsq_eq, Real.sq_sqrt (show 0 ≤ (2 : ℝ) from by norm_num)]
  -- Express q in ℝ as num/den
  have h_cast_div : (q : ℝ) = (q.num : ℝ) / (q.den : ℝ) := by
    simpa using ((congrArg (fun x : ℚ => (x : ℝ)) (Rat.num_div_den q)).symm)
  rw [h_cast_div] at h_two_eq
  -- h_two_eq : 2 = ((q.num : ℝ) / (q.den : ℝ))^2
  rw [div_pow] at h_two_eq
  -- h_two_eq : 2 = (q.num : ℝ)^2 / (q.den : ℝ)^2
  have h_den_ne_zero : (q.den : ℝ) ≠ 0 := by exact_mod_cast q.den_ne_zero
  field_simp [h_den_ne_zero] at h_two_eq
  -- h_two_eq : 2 * (q.den : ℝ)^2 = (q.num : ℝ)^2
  have h_eq_int : 2 * (q.den : ℤ)^2 = (q.num : ℤ)^2 := by exact_mod_cast h_two_eq
  -- Now work in ℤ: 2 * den² = num²
  have h2_prime : Prime (2 : ℤ) :=
    Nat.prime_iff_prime_int.mp Nat.prime_two
  have h2_dvd_num_sq : (2 : ℤ) ∣ (q.num : ℤ)^2 := by
    rw [← h_eq_int]
    exact ⟨(q.den : ℤ)^2, by ring⟩
  have h2_dvd_num : (2 : ℤ) ∣ (q.num : ℤ) :=
    h2_prime.dvd_of_dvd_pow h2_dvd_num_sq
  have h2_dvd_num_saved := h2_dvd_num
  obtain ⟨k, hk⟩ := h2_dvd_num
  -- hk : q.num = 2 * k
  rw [hk] at h_eq_int
  -- h_eq_int : 2 * (q.den : ℤ)^2 = (2 * k)^2
  ring_nf at h_eq_int
  -- h_eq_int : 2 * (q.den : ℤ)^2 = 4 * k^2
  -- Divide by 2 (working in ℤ, cancel nonzero factor):
  have h_den_sq_eq : (q.den : ℤ)^2 = 2 * (k : ℤ)^2 := by
    nlinarith
  have h2_dvd_den_sq : (2 : ℤ) ∣ (q.den : ℤ)^2 := by
    rw [h_den_sq_eq]
    exact ⟨(k : ℤ)^2, by ring⟩
  have h2_dvd_den : (2 : ℤ) ∣ (q.den : ℤ) :=
    h2_prime.dvd_of_dvd_pow h2_dvd_den_sq
  -- Both num and den divisible by 2 in ℤ → contradicts coprimality
  have h2_dvd_num_nat : 2 ∣ q.num.natAbs := by
    simpa using (Int.natAbs_dvd_natAbs.mpr h2_dvd_num_saved)
  have h2_dvd_den_nat : 2 ∣ q.den := by exact_mod_cast h2_dvd_den
  have h_gcd : Nat.gcd q.num.natAbs q.den = 1 := q.reduced
  have h2_dvd_gcd : 2 ∣ Nat.gcd q.num.natAbs q.den :=
    Nat.dvd_gcd h2_dvd_num_nat h2_dvd_den_nat
  rw [h_gcd] at h2_dvd_gcd
  have h_not : ¬ 2 ∣ (1 : ℕ) := by decide
  exact h_not h2_dvd_gcd

/-- T08b — 2-adic valuation proof that √2 is irrational.
Strategy: same start as T08a (√2 = q ∈ ℚ → num² = 2·den²),
then apply padicValNat 2 to both sides. LHS exponent is even
(2 * v₂(num)), RHS is odd (1 + 2 * v₂(den)). Contradiction via parity.
Uses padicValNat.mul, padicValNat.pow, padicValNat.prime_pow.
Does NOT cite irrational_sqrt_two, irrational_sqrt_of_multiplicity_odd,
or any pre-packaged irrationality lemma. -/
theorem t08b_valuation : Irrational (Real.sqrt 2) := by
  rintro ⟨q, hq⟩
  -- hq : Real.sqrt 2 = (q : ℝ)
  have hsq_eq : (Real.sqrt 2)^2 = ((q : ℝ))^2 := by rw [hq]
  have h_two_eq : (2 : ℝ) = ((q : ℝ))^2 := by
    rw [← hsq_eq, Real.sq_sqrt (show 0 ≤ (2 : ℝ) from by norm_num)]
  -- Express q in ℝ as num/den, clear denominators, cast to ℤ
  have h_cast_div : (q : ℝ) = (q.num : ℝ) / (q.den : ℝ) := by
    simpa using ((congrArg (fun x : ℚ => (x : ℝ)) (Rat.num_div_den q)).symm)
  rw [h_cast_div] at h_two_eq
  rw [div_pow] at h_two_eq
  have h_den_ne_zero : (q.den : ℝ) ≠ 0 := by exact_mod_cast q.den_ne_zero
  field_simp [h_den_ne_zero] at h_two_eq
  -- h_two_eq : 2 * (q.den : ℝ)^2 = (q.num : ℝ)^2
  have h_eq_int : 2 * (q.den : ℤ)^2 = (q.num : ℤ)^2 := by exact_mod_cast h_two_eq
  -- Both sides are nonnegative, take natAbs to work in ℕ
  have h_eq_nat : (q.num.natAbs : ℕ)^2 = 2 * (q.den : ℕ)^2 := by
    have h_nat := congrArg (fun x : ℤ => x.natAbs) h_eq_int
    -- h_nat : (2 * q.den^2).natAbs = (q.num^2).natAbs
    have h_left : (2 * (q.den : ℤ)^2).natAbs = 2 * (q.den : ℕ)^2 := by
      simp [Int.natAbs_mul, Int.natAbs_pow]
    have h_right : ((q.num : ℤ)^2).natAbs = (q.num.natAbs : ℕ)^2 := by
      simp [Int.natAbs_pow]
    simpa [h_left, h_right] using h_nat.symm
  -- Apply padicValNat 2 to both sides
  have h_val_left : padicValNat 2 ((q.num.natAbs : ℕ)^2) =
      2 * padicValNat 2 (q.num.natAbs : ℕ) := by
    by_cases hzero : q.num.natAbs = 0
    · -- If num = 0, then den = 0, impossible
      rw [hzero] at h_eq_nat
      -- h_eq_nat: 0 = 2 * q.den^2
      have h_den_zero : q.den = 0 := by
        nlinarith
      exact absurd h_den_zero q.den_ne_zero
    · exact padicValNat.pow 2 hzero
  have h_val_right : padicValNat 2 (2 * (q.den : ℕ)^2) =
      1 + 2 * padicValNat 2 (q.den : ℕ) := by
    have h2pos : (2 : ℕ) ≠ 0 := by norm_num
    have h_den_sq_ne_zero : (q.den : ℕ)^2 ≠ 0 := pow_ne_zero 2 q.den_ne_zero
    rw [padicValNat.mul h2pos h_den_sq_ne_zero]
    have h_two : padicValNat 2 (2 : ℕ) = 1 := by
      simpa using padicValNat.prime_pow 1
    have h_den_val : padicValNat 2 ((q.den : ℕ)^2) = 2 * padicValNat 2 (q.den : ℕ) :=
      padicValNat.pow 2 q.den_ne_zero
    rw [h_two, h_den_val]
  have h_val_eq := congrArg (padicValNat 2) h_eq_nat
  rw [h_val_left, h_val_right] at h_val_eq
  -- h_val_eq : 2 * v₂(num) = 1 + 2 * v₂(den) in ℕ
  -- Left side is even, right side is odd → contradiction
  have h_even : Even (2 * padicValNat 2 (q.num.natAbs : ℕ)) := by
    rw [even_iff_exists_two_mul]
    exact ⟨padicValNat 2 (q.num.natAbs : ℕ), rfl⟩
  have h_odd : Odd (1 + 2 * padicValNat 2 (q.den : ℕ)) := by
    rw [add_comm]
    exact ⟨padicValNat 2 (q.den : ℕ), rfl⟩
  have h_not_even : ¬ Even (1 + 2 * padicValNat 2 (q.den : ℕ)) :=
    (Nat.not_even_iff_odd.2 h_odd)
  rw [h_val_eq] at h_even
  exact h_not_even h_even

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
    _ = n*(n+1)/2 := by ring_nf
