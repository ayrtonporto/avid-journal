import Mathlib

variable {α : Type*} [Fintype α] [DecidableEq α] [Nonempty α]

/-- A matrix is stochastic if all entries are non-negative and each row sums to 1. -/
def IsStochastic (P : Matrix α α ℝ) : Prop :=
  (∀ i j, 0 ≤ P i j) ∧ (∀ i, ∑ j, P i j = 1)

/-- A Markov chain is irreducible if every state can be reached from every other state. -/
def IsIrreducible (P : Matrix α α ℝ) : Prop :=
  ∀ i j, ∃ n : ℕ, 0 < (P ^ n) i j

/-- A probability distribution π is stationary for P if π P = π. -/
def IsStationary (P : Matrix α α ℝ) (π : α → ℝ) : Prop :=
  (∀ i, 0 ≤ π i) ∧ (∑ i, π i = 1) ∧ (∀ j, ∑ i, π i * P i j = π j)

/-- Total variation distance between two distributions on a finite state space. -/
def totalVariationDistance (μ ν : α → ℝ) : ℝ :=
  (1 / 2) * ∑ i, |μ i - ν i|

/-- The mixing distance d(n) is the maximum total variation distance to stationarity
    over all initial states after n steps. -/
noncomputable def mixingDistance (P : Matrix α α ℝ) (π : α → ℝ) (n : ℕ) : ℝ :=
  sSup (Set.range (fun i : α => totalVariationDistance (fun j => (P ^ n) i j) π))

/-- λ is an eigenvalue of the real matrix P (viewed over ℂ). -/
def IsEigenvalue (P : Matrix α α ℝ) (λ : ℂ) : Prop :=
  ∃ v : α → ℂ, v ≠ 0 ∧ ∀ i, ∑ j, (P i j : ℂ) * v j = λ * v i

theorem spectral_lowerbound (P : Matrix α α ℝ) (π : α → ℝ) (λ : ℂ)
    (hP_stoch : IsStochastic P)
    (hP_irred : IsIrreducible P)
    (hπ_stat : IsStationary P π)
    (hλ_eig : IsEigenvalue P λ)
    (hλ_ne_one : λ ≠ 1) :
    ∀ n : ℕ, mixingDistance P π n ≥ (1 / 2 : ℝ) * ‖λ‖ ^ n := by sorry