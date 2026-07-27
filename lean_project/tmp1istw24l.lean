import Mathlib

import Mathlib

def PaperEven (n : ℕ) : Prop :=
  ∃ k : ℕ, n = 2 * k

import Mathlib

def PaperEven (n : ℕ) : Prop :=
  ∃ k : ℕ, n = 2 * k

lemma PaperEven_add {a b : ℕ} (ha : PaperEven a) (hb : PaperEven b) : PaperEven (a + b) := by
  rcases ha with ⟨k, hk⟩
  rcases hb with ⟨m, hm⟩
  use k + m
  calc
    a + b = 2 * k + 2 * m := by rw [hk, hm]
    _ = 2 * (k + m) := by rw [← mul_add]
