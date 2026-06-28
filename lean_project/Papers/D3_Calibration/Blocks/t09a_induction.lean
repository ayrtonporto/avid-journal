import Mathlib

open BigOperators

/--
T09a — Suma de los primeros n naturales por inducción.
Fórmula: 0 + 1 + 2 + ... + n = n(n+1)/2

Estrategia: inducción simple sobre n.
Premisas clave: sum_range_succ, mul_add, add_comm, ring.
-/
theorem t09a_induction (n : ℕ) : (∑ i in Finset.range (n+1), i) = n*(n+1)/2 := by
  induction' n with k ih
  · -- Caso base n = 0
    simp
  · -- Paso inductivo: n = k+1
    rw [Finset.sum_range_succ]
    rw [ih]
    ring
