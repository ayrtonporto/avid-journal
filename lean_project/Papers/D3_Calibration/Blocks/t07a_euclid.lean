import Mathlib

open Finset
open Nat

/--
T07a — Existen infinitos números primos. Prueba clásica de Euclides.

Supongamos que hay finitos primos: p₁,...,pₖ. 
Considerar N = p₁·p₂·...·pₖ + 1. N es coprimo con cada pᵢ,
luego tiene un factor primo nuevo — contradicción.

Premisas: Finset.prod, coprime_self_add_one, exists_prime_and_dvd.
-/
theorem t07a_euclid : ∀ n : ℕ, ∃ p : ℕ, n ≤ p ∧ Nat.Prime p := by
  intro n
  -- Tomar el producto de todos los números hasta n
  let M := ∏ i in range (n+1), (i+1)
  -- M+1 tiene un factor primo
  have hMpos : 1 ≤ M + 1 := by omega
  rcases Nat.exists_prime_and_dvd hMpos with ⟨p, hp_prime, hp_dvd⟩
  -- Probar que p ≥ n (de hecho p > n)
  by_cases hple : p ≤ n
  · -- Si p ≤ n, entonces p divide a M (está en el producto)
    have hpM : p ∣ M := by
      apply Finset.dvd_prod_of_mem
      simp [Finset.mem_range, hple]
    -- p divide a (M+1) - M = 1, contradicción
    have hp1 : p ∣ 1 := by
      have hsub : M + 1 - M = 1 := by omega
      have hdvd : p ∣ M + 1 - M := Nat.dvd_sub (by omega) hp_dvd hpM
      rw [hsub] at hdvd
      exact hdvd
    exact hp_prime.not_dvd_one hp1
  · -- p > n, por lo tanto p ≥ n+1 ≥ n (para n=0)
    omega
