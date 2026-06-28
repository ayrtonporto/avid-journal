import Mathlib

open Nat

/--
T07b — Existen infinitos números primos. Prueba usando n! + 1.

Para cualquier n, el número N = n! + 1 tiene un factor primo p.
Como p divide a N, no puede dividir a n! (pues entonces dividiría a N - n! = 1).
Por lo tanto p > n (si p ≤ n, entonces p | n!). Luego hay un primo mayor que n.
Como n es arbitrario, hay infinitos primos.

Premisas: Nat.factorial, Nat.dvd_factorial, Nat.coprime_self_add_one, 
          Nat.exists_prime_and_dvd.
-/
theorem t07b_factorial : ∀ n : ℕ, ∃ p : ℕ, n ≤ p ∧ Nat.Prime p := by
  intro n
  -- Considerar N = n! + 1
  let N := n.factorial + 1
  have hNpos : 1 ≤ N := by
    have : 1 ≤ n.factorial := Nat.one_le_factorial n
    omega
  -- N > 1, luego tiene un factor primo
  rcases Nat.exists_prime_and_dvd hNpos with ⟨p, hp_prime, hp_dvd⟩
  refine ⟨p, ?_, hp_prime⟩
  -- Probar que p > n (o al menos p ≥ n si n=0)
  by_contra! hlt
  -- Si p ≤ n-1, entonces p divide a n!
  have hp_fact : p ∣ n.factorial := by
    apply Nat.dvd_factorial (by omega) (by omega)
  -- Pero p también divide a N = n! + 1
  -- Entonces p divide a 1 = N - n!
  have hp_one : p ∣ 1 := by
    have : p ∣ N - n.factorial := Nat.dvd_sub ?_ hp_dvd hp_fact
    · simpa [N] using this
    · exact Nat.one_le_factorial n
  -- Contradicción: p es primo y divide a 1
  have := hp_prime.not_dvd_one
  exact this hp_one
