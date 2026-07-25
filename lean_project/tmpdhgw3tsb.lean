import Mathlib



import Mathlib



import Mathlib

lemma even_add {a b : ℕ} (ha : Even a) (hb : Even b) : Even (a + b) := by
  rcases ha with ⟨k, hk⟩
  rcases hb with ⟨m, hm⟩
  use k + m
  calc
    a + b = 2*k + 2*m := by rw [hk, hm]
    _ = 2*(k + m) := by ring
