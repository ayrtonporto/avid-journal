import Mathlib

/--
T08a — √2 es irracional vía el criterio general de irracionalidad de raíces.
Estrategia: 2 no es un cuadrado perfecto → √2 ∉ ℚ.
Premisas: Nat.not_square, Irrational.sqrt_of_nonsquare.
-/
theorem t08a_parity : Irrational (Real.sqrt 2) := by
  have h : ¬∃ n : ℕ, n * n = (2 : ℕ) := by
    intro h
    rcases h with ⟨n, hn⟩
    have hle : n ≤ 2 := by
      nlinarith
    interval_cases n
    · norm_num at hn
    · norm_num at hn
    · norm_num at hn
  -- 2 no es cuadrado → √2 irracional
  exact irrational_sqrt_of_nonsquare h
