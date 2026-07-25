import Mathlib

import Mathlib

def PaperEven (n : ℕ) : Prop := ∃ k : ℕ, n = 2 * k

import Mathlib

def PaperEven (n : ℕ) : Prop := ∃ k : ℕ, n = 2 * k

lemma paper_even_add (a b : ℕ) (ha : PaperEven a) (hb : PaperEven b) : PaperEven (a + b) := by
  rcases ha with ⟨k, hk⟩
  rcases hb with ⟨m, hm⟩
  use k + m
  rw [hk, hm]
  ring
