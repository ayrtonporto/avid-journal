import Mathlib

open Matrix BigOperators

variable {α : Type*} [Fintype α] [DecidableEq α]

def IsTransitionMatrix (P : Matrix α α ℝ) : Prop :=
  (∀ i j, 0 ≤ P i j) ∧ (∀ i, ∑ j, P i j = 1)

def IsIrreducible (P : Matrix α α ℝ) : Prop :=
  ∀ i j, ∃ n : ℕ, 0 < (P ^ n) i j

def IsStationary (P : Matrix α α ℝ) (π : α → ℝ) : Prop :=
  (∀ j, 0 ≤ π j) ∧ (∑ j, π j = 1) ∧ (∀ j, ∑ i, π i * P i j = π j)

noncomputable def totalVariation (μ ν : α → ℝ) : ℝ :=
  (1 / 2 : ℝ) * ∑ i, |μ i - ν i|

noncomputable def distToStationary (P : Matrix α α ℝ) (π : α → ℝ) (n : ℕ) : ℝ :=
  sSup (Set.range fun x => totalVariation (fun j => (P ^ n) x j) π)

def IsEigenvalue (P : Matrix α α ℝ) (z : ℂ) : Prop :=
  ∃ v : α → ℂ, v ≠ 0 ∧ (P.map (algebraMap ℝ ℂ)).mulVec v = z • v

theorem spectral_lowerbound
  (P : Matrix α α ℝ)
  (hP : IsTransitionMatrix P)
  (hIrr : IsIrreducible P)
  (π : α → ℝ)
  (hπ : IsStationary P π)
  (z : ℂ)
  (hz : IsEigenvalue P z)
  (hz_ne : z ≠ 1)
  (n : ℕ) :
  distToStationary P π n ≥ (1 / 2 : ℝ) * Complex.abs z ^ n := by sorry