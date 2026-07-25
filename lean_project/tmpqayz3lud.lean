import Mathlib

import Mathlib

def IsEven (n : ℕ) : Prop := ∃ k : ℕ, n = 2 * k

import Mathlib

def IsEven (n : ℕ) : Prop := ∃ k : ℕ, n = 2 * k

theorem sum_of_even_is_even (a b : ℕ) (ha : IsEven a) (hb : IsEven b) : IsEven (a + b) := by
  rcases ha with ⟨k, hk⟩
  rcases hb with ⟨m, hm⟩
  use k + m
  rw [hk, hm, ← mul_add]
