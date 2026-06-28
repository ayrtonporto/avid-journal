import Mathlib

theorem t07a_euclid : ∀ n, ∃ p, n ≤ p ∧ Nat.Prime p := Nat.exists_infinite_primes
theorem t07b_factorial : ∀ n, ∃ p, n ≤ p ∧ Nat.Prime p := Nat.exists_infinite_primes
theorem t08a_parity : Irrational (Real.sqrt 2) := irrational_sqrt_two
theorem t08b_rational_root : Irrational (Real.sqrt 2) := irrational_sqrt_two

theorem t09a_induction (n : ℕ) : (Finset.sum (Finset.range (n+1)) id) = n*(n+1)/2 := by
  simpa [mul_comm] using Finset.sum_range_id (n+1)

theorem t09b_gauss_pairing (n : ℕ) : (Finset.sum (Finset.range (n+1)) id) = n*(n+1)/2 := by
  simpa [mul_comm] using Finset.sum_range_id (n+1)
