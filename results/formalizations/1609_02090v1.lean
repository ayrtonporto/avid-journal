import Mathlib

def powers (n k : ℕ) : Set (ZMod n) :=
  {x | ∃ y : ZMod n, x = y ^ k}

def sumset {α : Type*} [AddCommMonoid α] (S : Set α) (m : ℕ) : Set α :=
  {x | ∃ (f : Fin m → α), (∀ i, f i ∈ S) ∧ x = ∑ i : Fin m, f i}

theorem even_powers_covering :
  (∀ n : ℕ, n ≥ 2 → Set.univ ⊆ sumset (powers n 4) 15) ∧
  (∀ n : ℕ, n ≥ 2 → Set.univ ⊆ sumset (powers n 6) 9) ∧
  (∀ n : ℕ, n ≥ 2 → Set.univ ⊆ sumset (powers n 8) 32) ∧
  (∀ n : ℕ, n ≥ 2 → Set.univ ⊆ sumset (powers n 10) 12) ∧
  (∃ n : ℕ, n ≥ 2 ∧ ¬(Set.univ ⊆ sumset (powers n 4) 14)) ∧
  (∃ n : ℕ, n ≥ 2 ∧ ¬(Set.univ ⊆ sumset (powers n 6) 8)) ∧
  (∃ n : ℕ, n ≥ 2 ∧ ¬(Set.univ ⊆ sumset (powers n 8) 31)) ∧
  (∃ n : ℕ, n ≥ 2 ∧ ¬(Set.univ ⊆ sumset (powers n 10) 11)) ∧
  (∀ n : ℕ, n ≥ 2 → (Set.univ ⊆ sumset (powers n 4) 5 ↔ ¬(8 ∣ n))) ∧
  (∀ n : ℕ, n ≥ 2 → (Set.univ ⊆ sumset (powers n 4) 7 ↔ ¬(16 ∣ n))) := by sorry