# Split Plan for thm:binomial-main

## Definitions Needed

### f(n)

**Informal:** f(n) is the smallest positive integer Y such that there exists 1 ≤ k ≤ Y with
the property that u(n, k) > n^2. In other words, f(n) is the minimum "window size" Y for which
the maximum p-smooth part of some binomial coefficient binom(n, k) (1 ≤ k ≤ Y) exceeds n^2.

More precisely, from the upper-bound proof: we show that for Y = floor(C (log n)^2) with
C > 24/(pi^2 - 6), the average of log(u(n,k)) over k in [1,Y] exceeds 2 log n for large n,
so some k in [1, Y] has u(n,k) > n^2, hence f(n) ≤ Y. The lower bound is f(M_K - 1) > K, which
gives f(n_j) ≥ (1/2 + o(1)) log n_j.

**Lean-friendly definition:**

```lean
-- f(n) = the minimum Y ≥ 1 such that ∃ k ∈ Finset.Icc 1 Y, u n k > n^2
-- where u n k = ∏ p prime, p^(padicValNat p (Nat.choose n k))
--                         restricted to p ≤ k  (i.e., the "smooth part" of binom(n,k))
noncomputable def f (n : Nat) : Nat :=
  Nat.find (p := fun Y => 0 < Y ∧ ∃ k ∈ Finset.Icc 1 Y, n ^ 2 < u n k)
  -- (requires showing the existential holds for large n, proved by upper bound argument)
```

Note: The existence predicate requires the main theorem itself to be non-vacuous; in practice
one would provide f as existential witness for the statement or axiomatize it.

### u(n, k)

**Informal:** u(n, k) is the largest divisor of binom(n, k) whose prime factors are all ≤ k.
Equivalently, u(n, k) = product over primes p ≤ k of p^(v_p(binom(n,k))).

From the proof: the key lower bound on log(u(n,k)) comes from the Legendre formula applied to
the t=1 term. If p ≤ k and n mod p < k mod p (i.e., a carry occurs in base p at the units
digit), then p | binom(n,k), contributing log p to log(u(n,k)).

**Lean-friendly definition:**

```lean
-- The k-smooth part of binom(n, k): product of p^(padicValNat p (Nat.choose n k)) over p ≤ k
noncomputable def u (n k : Nat) : Nat :=
  ∏ p ∈ (Finset.Icc 1 k).filter Nat.Prime,
    p ^ (padicValNat p (Nat.choose n k))
```

This is a finite product, well-typed in Lean 4, and u(n,k) ≥ 1 always (empty product = 1).
Note: padicValNat p m = 0 when p does not divide m, so the formula is correct.

---

## Mathlib Availability Check

- **Legendre's formula for v_p(n!)**: FOUND — `Mathlib.NumberTheory.Padics.PadicVal.Basic`,
  theorem `padicValNat_factorial` (sum of floor(n/p^i)).

- **Kummer's theorem for v_p(binom(n,k))** (number of carries when k and n-k are added in base p):
  FOUND — `padicValNat_choose` in `Mathlib.NumberTheory.Padics.PadicVal.Basic`.
  Also `Nat.factorization_choose` in `Mathlib.Data.Nat.Choose.Factorization`.

- **p-adic valuation of binomial coefficients**: FOUND (as above, via Kummer/Legendre).

- **The specific lower bound v_p(binom(n,k)) ≥ 1_{n mod p < k mod p}**:
  NOT directly stated as a named lemma. Must be derived from `padicValNat_choose` by showing
  a carry occurs at t=1 iff n mod p < k mod p, and a single carry means padicValNat ≥ 1.

- **Chebyshev's theta function and bounds**: FOUND — `Mathlib.NumberTheory.Chebyshev` has
  `Chebyshev.theta` (= sum of log p over primes p ≤ x), `theta_le_log4_mul_x` (upper bound
  theta(x) ≤ log(4)*x), and Abel summation connecting theta to pi(x).

- **Prime Number Theorem (theta(x) ~ x, i.e., T_j = (1+o(1))Y/j)**:
  NOT FOUND in current Mathlib. The Chebyshev file explicitly marks "Prove Chebyshev's lower
  bound" as a TODO. There is no theorem of the form `theta =~[atTop] id` or
  `Chebyshev.theta isEquivalent (fun x => x)` in Mathlib (as of Lean4 v4.29 / this Mathlib rev).
  The file has `theta_le_log4_mul_x` (upper bound only) and Chebyshev-level bounds, but not PNT.

- **Sum ∑_{j=2}^∞ 1/j^2 = pi^2/6 - 1**: FOUND via `Mathlib.Analysis.SpecificLimits.Basic`
  (`Real.sum_one_div_pow_eq_pi_sq_div_six` or the Basel problem result combined with
  `Finset.sum_range_succ`).

- **Primorial and log(M_K)**:
  Primorial is in Mathlib (`Nat.primorial`). `theta_eq_log_primorial` relates theta(x) to
  log of the primorial. For log(M_K) ~ 2K via PNT, the same obstacle applies.

---

## Recommended Lean Approach

Given the above, the **full formal proof is not feasible** with current Mathlib because:
1. PNT (theta(x) ~ x) is absent, which blocks the T_j = (1+o(1))Y/j step.
2. The R_j lower bound and the log(M_K) ~ 2K computation both require PNT.
3. The averaging argument over k in [1,Y] is a non-trivial real-analysis argument.

**Recommended strategy:** Use abstract hypotheses (axioms with `-- source:` comments) for the
two PNT-dependent facts, and prove the combinatorial skeleton concretely.

Specifically:

1. **Axiomatize PNT in the form needed:**
   ```lean
   /-- source: Prime Number Theorem, standard reference e.g. Apostol "Introduction to Analytic Number Theory" -/
   axiom pnt_theta_equiv : ∀ ε > 0, ∀ᶠ x : Real in Filter.atTop,
     |Chebyshev.theta x - x| ≤ ε * x
   ```

2. **Define u and f concretely** (as above), then state the main theorem with u and f defined.

3. **Prove the Legendre lower bound** (the t=1 carry) concretely from `padicValNat_choose`
   — this IS feasible in Lean.

4. **Prove the lower bound part** (f(M_K - 1) > K) concretely, since it only requires:
   - The Kummer/Legendre formula (`padicValNat_choose`)
   - Arithmetic about M_K mod p^a (no PNT needed)
   - log(M_K) ~ 2K (requires PNT — axiomatize)

5. **For the upper bound**, the cleanest approach with abstract hypotheses:
   - Axiomatize "T_j = (1+o(1)) Y/j" as a hypothesis
   - Prove the averaging argument as a finite calculation given R_j ≥ (C^2/(2j^2) - eps)(log n)^3
   - The key combinatorial step (counting intervals and residues mod p) is provable from basic
     Finset arithmetic.

**Simplification for a first feasible block:** Since the full proof requires PNT, the most
realistic approach is:
- State thm_binomial_main with `sorry`-free sorry-replacement via PNT axioms
- Prove the lower bound (f(M_K - 1) > K part) fully — it does NOT need PNT
- Axiomatize the upper bound conclusion using the PNT-dependent lemma as an axiom

---

## Auxiliary 1 — Legendre carry lower bound

**Type**: lemma
**Informal statement**: For any prime p ≤ k with p ≤ n and n mod p < k mod p, we have
  padicValNat p (Nat.choose n k) ≥ 1.
**Informal proof**: From Kummer's theorem (`padicValNat_choose`), padicValNat p (choose n k)
  equals the number of carries when k and n-k are added in base p (over i ≥ 1). The i=1 term
  counts whether p ≤ k % p + (n-k) % p. If n % p < k % p, then (n-k) % p = n % p + p - k % p
  (borrow), so k % p + (n-k) % p = n % p + p ≥ p, giving at least one carry. Hence the count
  is ≥ 1.
**Lean feasibility**: HIGH. This is a direct consequence of `padicValNat_choose` plus modular
  arithmetic. The carry condition at t=1 corresponds to checking `p ∈ {i ∈ Ico 1 b | p^i ≤ k%p^i + (n-k)%p^i}` with i=1.

**Suggested Lean signature:**
```lean
lemma legendre_carry_lower_bound (p n k : Nat) [hp : Fact p.Prime]
    (hpk : p ≤ k) (hkn : k ≤ n) (hcarry : n % p < k % p) :
    1 ≤ padicValNat p (Nat.choose n k) := ...
```

---

## Auxiliary 2 — u(n,k) ≥ p when p ≤ k and carry occurs

**Type**: lemma
**Informal statement**: If p is prime, p ≤ k ≤ n, and n mod p < k mod p, then p ∣ binom(n,k),
  hence p divides u(n,k), so u(n,k) ≥ p.
**Informal proof**: From Auxiliary 1, padicValNat p (choose n k) ≥ 1, so p ∣ choose n k.
  Since p ≤ k, p is one of the primes in the product defining u(n,k), and its exponent is ≥ 1.
**Lean feasibility**: HIGH. Follows from Auxiliary 1 + definition of u.

---

## Auxiliary 3 — Lower bound on log(u(n,k)) sum (needs PNT as hypothesis)

**Type**: lemma (with PNT hypothesis)
**Informal statement**: With C > 24/(pi^2-6), Y = floor(C*(log n)^2), for n large enough:
  (1/Y) * ∑_{k=1}^{Y} log(u(n,k)) ≥ 2 * log(n)
**Informal proof**:
  Step 1: ∑_{k=1}^Y log(u(n,k)) ≥ ∑_{p≤Y} (floor(Y/p) - 1) * (a_p - 1) * log p
    where a_p = p - (n mod p) is the "distance to next multiple of p above n".
    This uses: for each prime p ≤ Y, in the Y/p blocks of size p in [1,Y], the k values
    for which n mod p < k mod p number exactly a_p - 1 per block.
  Step 2: Sum ≥ ∑_{j=2}^J ∑_{p in P_j} (a_p - 1) * log p = ∑_{j=2}^J (R_j - T_j)
    where P_j = {primes p ≤ Y/j}, T_j = ∑_{p in P_j} log p = theta(Y/j),
    R_j = ∑_{p in P_j} a_p * log p.
  Step 3: R_j ≥ (C^2/(2j^2) - o(1)) * (log n)^3 using Abel summation + T_j = (1+o(1))Y/j (PNT).
  Step 4: Sum ≥ (C^2/2 * ∑_{j=2}^J 1/j^2 - o(1)) * (log n)^3.
  Step 5: Divide by Y ≈ C*(log n)^2 to get average ≥ (C/2 * ∑_j 1/j^2 - o(1)) * log n > 2*log n
    by the choice of C.
**Lean feasibility**: LOW without PNT. With PNT axiomatized as a hypothesis, MEDIUM — the
  Abel summation step is the main technical hurdle; the rest is manipulations of finite sums.

---

## Auxiliary 4 — M_K construction and lower bound (no PNT needed for valuation part)

**Type**: lemma
**Informal statement**: For K ≥ 2, define M_K = ∏_{p ≤ K} p^(floor(log_p K) + 1).
  Then for all k with 0 ≤ k ≤ K and all primes p ≤ K, padicValNat p (Nat.choose (M_K - 1) k) = 0.
  Consequently, u(M_K - 1, k) = 1 < K^2/4 for all k ≤ K, so f(M_K - 1) > K.
**Informal proof**:
  Key claim: (M_K - 1) mod p^a ≥ k mod p^a for all k ≤ K and all prime powers p^a.
  - For a ≤ floor(log_p K) + 1: M_K ≡ 0 (mod p^a), so M_K - 1 ≡ p^a - 1 ≡ -1 (mod p^a),
    and p^a - 1 ≥ K ≥ k ≥ k mod p^a. So no carry at any digit ≤ floor(log_p K) + 1.
  - For a > floor(log_p K) + 1: p^a > K ≥ k, so k mod p^a = k ≤ K < p^(floor(log_p K)+1) ≤ M_K - 1,
    but (M_K - 1) mod p^a ≥ p^(floor(log_p K)+1) - 1 ≥ K ≥ k. No carry here either.
  By Kummer's theorem, no carries means padicValNat p (choose (M_K-1) k) = 0 for all p ≤ K.
  Hence u(M_K-1, k) has no prime factors ≤ K for k ≤ K. Since choose(M_K-1, k) itself may have
  prime factors > k > K, but u(n,k) only counts primes ≤ k ≤ K, we get u(M_K-1, k) = 1 for k ≤ K.
  This means f(M_K - 1) > K.

  For log(M_K) ~ 2K: log(M_K) = ∑_{p≤K} (floor(log_p K) + 1) * log p. The main term is
  ∑_{p≤K} log p = theta(K) ~ K (PNT). The sum ∑_{p≤K} floor(log_p K) * log p = psi(K) - theta(K) = o(K).
  So log(M_K) = theta(K) + psi(K) = (1 + o(1)) * 2K since psi(K) ~ K (PNT again) ... 
  Actually: log(M_K) = ∑_{p≤K} (floor(log_p K) + 1) log p = ∑_{a≥1} ∑_{p: p^a ≤ K} log p = psi(K).
  Wait: psi(K) = ∑_{p^a ≤ K} log p = ∑_{p ≤ K} floor(log_p K) * log p.
  So log(M_K) = ∑_{p≤K} (floor(log_p K) + 1) log p = psi(K) + theta(K) ~ 2K.
  This step REQUIRES PNT (both psi ~ K and theta ~ K).

**Lean feasibility**: The valuation = 0 part is HIGH feasibility (pure modular arithmetic +
  Kummer). The log(M_K) ~ 2K part needs PNT — axiomatize.

**Suggested Lean signature for the core valuation lemma:**
```lean
-- Define M_K
noncomputable def M_K (K : Nat) : Nat :=
  ∏ p ∈ (Finset.range (K + 1)).filter Nat.Prime,
    p ^ (Nat.log p K + 1)

lemma padicValNat_choose_MK_sub_one_eq_zero (K k p : Nat) [hp : Fact p.Prime]
    (hpK : p ≤ K) (hkK : k ≤ K) :
    padicValNat p (Nat.choose (M_K K - 1) k) = 0 := ...
```

---

## Auxiliary 5 — Basel sum identity

**Type**: lemma (from Mathlib)
**Informal statement**: ∑_{j=2}^∞ 1/j^2 = pi^2/6 - 1
**Lean feasibility**: HIGH — Mathlib has the Basel problem. Use `Real.sum_one_div_pow_eq_pi_sq_div_six`
  or related; subtract the j=1 term (which equals 1).

---

## Final — thm_binomial_main

**Informal proof (using auxiliaries):**

Upper bound (f(n) ≤ (24/(pi^2-6) + o(1)) (log n)^2):
  Given epsilon > 0, set C = 24/(pi^2-6) + epsilon and Y = floor(C (log n)^2).
  By Auxiliary 3 (with PNT as hypothesis), the average of log(u(n,k)) over k in [1,Y] exceeds
  2 log n for n large enough. So some k in [1,Y] satisfies u(n,k) > n^2, hence f(n) ≤ Y.

Lower bound (f(n_j) ≥ (1/2 + o(1)) log n_j along n_j = M_{K_j} - 1):
  By Auxiliary 4, f(M_K - 1) > K for all K ≥ 2.
  By the PNT-based computation log(M_K) ~ 2K, we have K ~ (1/2) log(M_K) for large K.
  Setting n_j = M_{K_j} - 1 with K_j → ∞, we get f(n_j) > K_j ~ (1/2) log n_j.

**Lean structure for thm_binomial_main:**

Given the infeasibility of a complete proof, the recommended Lean structure is:

```lean
-- PNT axioms needed
/-- source: Prime Number Theorem — theta(x) ~ x; see e.g., Davenport "Multiplicative Number Theory" -/
axiom pnt_theta (ε : Real) (hε : 0 < ε) :
    ∀ᶠ x : Real in Filter.atTop,
      (1 - ε) * x ≤ Chebyshev.theta x ∧ Chebyshev.theta x ≤ (1 + ε) * x

/-- source: Prime Number Theorem — psi(x) ~ x -/
axiom pnt_psi (ε : Real) (hε : 0 < ε) :
    ∀ᶠ x : Real in Filter.atTop,
      (1 - ε) * x ≤ Chebyshev.psi x ∧ Chebyshev.psi x ≤ (1 + ε) * x

-- Main theorem (existence form; abstract the o(1) as ∀ε∃N)
theorem thm_binomial_main :
    -- Upper bound: f(n) ≤ (24/(pi^2-6) + ε)(log n)^2 for large n
    (∀ ε : Real, 0 < ε → ∀ᶠ n : Nat in Filter.atTop,
      (f n : Real) ≤ (24 / (Real.pi ^ 2 - 6) + ε) * (Real.log n) ^ 2)
    ∧
    -- Lower bound: ∃ sequence n_j → ∞ with f(n_j) ≥ (1/2 + o(1)) log n_j
    (∀ ε : Real, 0 < ε → ∀ᶠ K : Nat in Filter.atTop,
      (1/2 - ε) * Real.log (M_K K - 1) ≤ f (M_K K - 1)) :=
  ...
```

**Implementation priority order:**
1. Define `u` and `M_K` concretely (no sorry needed).
2. Prove Auxiliary 4's valuation part (padicValNat = 0) — feasible, no PNT.
3. Prove Auxiliary 1 (carry lower bound) — feasible.
4. Add PNT axioms with `-- source:` comments.
5. Use PNT axioms to state and `sorry`-free (via axioms) the full theorem.

**Why agents produced no Lean code in 3 attempts:**
The agents likely got stuck because `f` and `u` were undefined (no prior blocks), and the proof
references PNT which is absent from Mathlib. Without defining these functions first, there is no
valid theorem statement to write. The solution is: define u and M_K as concrete Lean definitions
above the theorem, add PNT axioms, and state the theorem in the ∀ε∃N form to avoid asymptotic
notation in the type signature.
