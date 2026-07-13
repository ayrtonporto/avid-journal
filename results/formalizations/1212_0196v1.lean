import Mathlib

def IsCongruentNumber (n : ℕ) : Prop :=
  ∃ (a b c : ℚ), 0 < a ∧ 0 < b ∧ 0 < c ∧ a^2 + b^2 = c^2 ∧ (1 / 2 : ℚ) * a * b = (n : ℚ)

theorem non_congruent_number_criterion (k : ℕ) (p : Fin k → ℕ)
  (hp_prime : ∀ i, Nat.Prime (p i))
  (hp_mod8 : ∀ i, p i % 8 = 3)
  (h_legendre : ∀ i j, i < j → jacobiSym (p i : ℤ) (p j) = 1) :
  ¬ IsCongruentNumber (∏ i : Fin k, p i) := by sorry