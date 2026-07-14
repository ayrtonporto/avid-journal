import Mathlib

noncomputable section

open Filter Asymptotics

variable (θ : ℕ → ℝ)

/-- The set of integers 1 ≤ m < N for which θ_m < m^{1/2 + ε}. -/
def B_set (ε : ℝ) (N : ℕ) : Finset ℕ :=
  Finset.filter (fun m => θ m < (m : ℝ) ^ ((1 : ℝ) / 2 + ε)) (Finset.Icc 1 (N - 1))

/-- The cardinality of B_ε(N). -/
def B (ε : ℝ) (N : ℕ) : ℕ :=
  (B_set θ ε N).card

theorem asymptotic_bounds_B_epsilon (ε : ℝ) :
  (0 < ε ∧ ε < (1 : ℝ) / 2 →
    IsBigO atTop
      (fun N : ℕ => (N : ℝ) ^ ((1 : ℝ) / 2))
      (fun N : ℕ => (B θ ε N : ℝ))) ∧
  (0 < ε ∧ ε < (1 : ℝ) / 6 →
    IsBigO atTop
      (fun N : ℕ => (B θ ε N : ℝ))
      (fun N : ℕ => (N : ℝ) ^ ((1 : ℝ) / 2 + ε))) ∧
  (0 < ε ∧ ε < (1 : ℝ) / 2 →
    IsBigO atTop
      (fun N : ℕ => (B θ ε N : ℝ))
      (fun N : ℕ => (N : ℝ) / (Real.log (N : ℝ)) ^ 2)) := by sorry