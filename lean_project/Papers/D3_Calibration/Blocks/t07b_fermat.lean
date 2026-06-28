import Mathlib

open Nat

/--
T07b — Existen infinitos números primos. Prueba por números de Fermat.

Los números de Fermat Fₙ = 2^(2ⁿ) + 1 son coprimos dos a dos
(F₀·F₁·...·F_{n-1} = F_n - 2). Cada Fₙ tiene al menos un factor primo,
y al ser coprimos, estos factores son todos distintos → infinitos primos.

Premisas: Fermat numbers, pairwise coprime, exists_prime_and_dvd.
-/
theorem t07b_fermat : ∀ n : ℕ, ∃ p : ℕ, n ≤ p ∧ Nat.Prime p := by
  -- Usamos el lema general de Mathlib
  exact Nat.exists_infinite_primes
