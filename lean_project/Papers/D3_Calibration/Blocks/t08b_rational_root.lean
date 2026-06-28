import Mathlib

/--
T08b — √2 es irracional vía el teorema de Eisenstein para polinomios.
x² - 2 es irreducible por Eisenstein (p=2) → no tiene raíces racionales.
Premisas: Polynomial.eisenstein, Polynomial.irreducible, Rat.not_mem.
-/
theorem t08b_rational_root : Irrational (Real.sqrt 2) := by
  -- x² - 2 es irreducible sobre ℚ por el criterio de Eisenstein con p=2
  -- Por lo tanto no tiene raíces racionales → √2 irracional
  refine irrational_of_polynomial_irreducible (Polynomial.X^2 - 2) ?_
  -- Eisenstein: los coeficientes de x²-2 son [1, 0, -2]
  -- El primo 2 divide a 0 y -2, 2²=4 no divide a 1
  apply Polynomial.eisensteinCriterion (p := 2)
  · -- 2 es primo
    norm_num [Nat.prime_iff]
  · -- 2² = 4 no divide al coeficiente líder 1
    norm_num
  · -- 2 divide los demás coeficientes
    intro i hi
    fin_cases i <;> norm_num
