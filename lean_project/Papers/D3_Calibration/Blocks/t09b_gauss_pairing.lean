import Mathlib

open Finset
open Nat

/--
T09b — Suma de los primeros n naturales por el truco de Gauss.
Fórmula: 0 + 1 + 2 + ... + n = n(n+1)/2

Estrategia: emparejar el primer término con el último, el segundo con
el penúltimo, etc. Cada par suma (n+1), y hay n/2 pares cuando n es par.
Generalizado: 2·S = n·(n+1).

Premisas clave: sum_add_distrib, sum_range_add, two_mul, add_comm.
-/
theorem t09b_gauss_pairing (n : ℕ) : (∑ i in range (n+1), i) = n*(n+1)/2 := by
  -- Estrategia de Gauss: calcular 2·S de dos maneras
  -- 2·S = ∑_{i=0}^{n} i  +  ∑_{i=0}^{n} i
  --     = ∑_{i=0}^{n} i  +  ∑_{i=0}^{n} (n-i)    (invirtiendo el orden)
  --     = ∑_{i=0}^{n} (i + (n-i))
  --     = ∑_{i=0}^{n} n
  --     = (n+1)·n = n·(n+1)
  have h_sum_reverse : (∑ i in range (n+1), (n - i)) = (∑ i in range (n+1), i) := by
    -- Reindexar: i ↦ n-i es una biyección de range (n+1) en sí mismo
    rw [Finset.sum_range_reflect (fun i => i) n]
  calc
    2 * (∑ i in range (n+1), i) = (∑ i in range (n+1), i) + (∑ i in range (n+1), i) := by ring
    _ = (∑ i in range (n+1), i) + (∑ i in range (n+1), (n - i)) := by rw [h_sum_reverse]
    _ = (∑ i in range (n+1), (i + (n - i))) := by rw [Finset.sum_add_distrib]
    _ = (∑ i in range (n+1), n) := by
      refine Finset.sum_congr rfl fun x hx => ?_
      rw [Finset.mem_range] at hx
      have : x ≤ n := Nat.le_of_lt_succ hx
      omega
    _ = (n+1) * n := by simp [Finset.sum_const_nsmul, smul_eq_mul]
    _ = n * (n+1) := by ring
  -- De 2·S = n·(n+1) deducimos S = n·(n+1)/2
  omega
