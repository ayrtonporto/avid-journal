import Mathlib

theorem matrix_diagonal_similarity_equivalence {n : ℕ} {K : Type*} [Field K] 
  (A : Matrix (Fin n) (Fin n) K) 
  (hA : ¬ ∃ (k : K), A = k • 1) (c : Fin n → K) :
  (∑ i, c i = Matrix.trace A) ↔ 
  (∃ (P B : Matrix (Fin n) (Fin n) K), Matrix.det P ≠ 0 ∧ P * B = A * P ∧ ∀ i, B i i = c i) := by sorry