import Mathlib.Analysis.InnerProductSpace.Basic

variable {E : Type*} [NormedAddCommGroup E] [InnerProductSpace ℝ E]

theorem thm_1607_03618 (x y : E) : |inner x y| ≤ ‖x‖ * ‖y‖ :=
  abs_inner_le_norm x y