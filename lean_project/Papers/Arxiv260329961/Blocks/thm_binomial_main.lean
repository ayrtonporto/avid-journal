-- AViD block stub
-- label: thm:binomial-main
-- type:  theorem
-- title:
-- See ../TASK.md for the informal statement and proof.
--
-- Write the formalized Lean declaration(s) below this line.

import Papers.Arxiv260329961.Paper

open Finset Nat Real Filter

/-! ## Piece 1: PNT axioms (external results, not in Mathlib as of Lean4 v4.29 / current rev)

Chebyshev.theta and Chebyshev.psi ARE defined in Mathlib (NumberTheory.Chebyshev)
but the PNT equivalences theta(x) ~ x and psi(x) ~ x are NOT proved. -/

/-- source: Prime Number Theorem (theta form): theta(x)/x -> 1 as x -> infty;
    see Davenport "Multiplicative Number Theory" Ch. 5 -/
axiom pnt_theta_asym : Tendsto (fun x : Real => Chebyshev.theta x / x) atTop (nhds 1)

/-- source: Prime Number Theorem (psi form): psi(x)/x -> 1 as x -> infty;
    see Davenport "Multiplicative Number Theory" Ch. 5 -/
axiom pnt_psi_asym : Tendsto (fun x : Real => Chebyshev.psi x / x) atTop (nhds 1)

/-! ## Piece 2: Definition of u_smooth — the k-smooth part of C(n, k) -/

/-- The k-smooth part of `Nat.choose n k`: the product of p^(padicValNat p (C(n,k)))
    over all primes p with p ≤ k. -/
noncomputable def u_smooth (n k : Nat) : Nat :=
  Finset.prod ((Finset.range (k + 1)).filter Nat.Prime)
    (fun p => p ^ (padicValNat p (Nat.choose n k)))

/-! ## Piece 3: Definition of M_K -/

/-- M_K = ∏_{prime p ≤ K} p^(floor(log_p K) + 1).
    The sequence M_K - 1 witnesses the lower bound f(M_K - 1) > K. -/
noncomputable def M_K (K : Nat) : Nat :=
  Finset.prod ((Finset.range (K + 1)).filter Nat.Prime)
    (fun p => p ^ (Nat.log p K + 1))

/-! ## Piece 4: Helper lemmas for the lower bound -/

/-- p^(Nat.log p K + 1) divides M_K K, for any prime p ≤ K. -/
lemma M_K_divisible_by_prime_pow (K p : Nat) (hp : Nat.Prime p) (hpK : p ≤ K) :
    p ^ (Nat.log p K + 1) ∣ M_K K := by
  apply Finset.dvd_prod_of_mem
  simp only [Finset.mem_filter, Finset.mem_range]
  exact ⟨Nat.lt_succ_of_le hpK, hp⟩

/-- M_K K is positive. -/
lemma M_K_pos (K : Nat) : 0 < M_K K := by
  apply Finset.prod_pos
  intro p hp
  simp only [Finset.mem_filter, Finset.mem_range] at hp
  exact pow_pos hp.2.pos _

/-- For prime p ≤ K, p^a ∣ M_K K for all a ≤ Nat.log p K + 1. -/
lemma M_K_dvd_pow (K p a : Nat) (hp : Nat.Prime p) (hpK : p ≤ K)
    (ha : a ≤ Nat.log p K + 1) : p ^ a ∣ M_K K :=
  Nat.dvd_trans (Nat.pow_dvd_pow p ha) (M_K_divisible_by_prime_pow K p hp hpK)

/-- The p-adic valuation of C(M_K K - 1, k) is 0 for primes p ≤ K and k ≤ K.

Proof sketch (via Kummer's theorem = padicValNat_choose):
  padicValNat p (choose n k) = #{i in Ico 1 b | p^i ≤ k % p^i + (n-k) % p^i}
For n = M_K K - 1 and k ≤ K:
  - For i ≤ Nat.log p K + 1: p^i | M_K K (by M_K_dvd_pow), so (M_K K - 1) % p^i = p^i - 1.
    Then k % p^i + (n - k) % p^i = k % p^i + (p^i - 1 - k % p^i) = p^i - 1 < p^i. No carry.
  - For i > Nat.log p K + 1: p^i > K ≥ k, so k % p^i = k and
    (n - k) % p^i = M_K K - 1 - k. But M_K K - 1 - k < M_K K ≤ p^i (for large enough i,
    since M_K K is finite). No carry.
In all cases the carry set is empty, so padicValNat = 0. -/
/-- Helper: if p^j divides M and 0 < M, then (M - 1) % p^j = p^j - 1 -/
private lemma mod_pred_of_dvd {M j p : Nat} (hdvd : p ^ j ∣ M) (hM : 0 < M) :
    (M - 1) % p ^ j = p ^ j - 1 := by
  have hpj_pos : 0 < p ^ j := Nat.pos_of_dvd_of_pos hdvd hM
  have hpj_dvd_mod : M % p ^ j = 0 := Nat.eq_zero_of_dvd_of_lt hdvd |>.symm ▸ rfl
  -- Actually use Nat.dvd_iff_mod_eq_zero
  rw [Nat.dvd_iff_mod_eq_zero] at hdvd
  omega

/-- Helper: for any a, b, m > 0: if a ≤ b % m, then a % m + (b - a) % m = b % m -/
private lemma mod_sub_add_mod {a b m : Nat} (hm : 0 < m) (hab : a ≤ b) (ha_le : a % m ≤ b % m) :
    a % m + (b - a) % m = b % m := by
  have key : b % m = (b - a + a) % m := by omega
  rw [key, Nat.add_mod, Nat.mod_mod_of_dvd]
  · simp [Nat.mod_eq_of_lt (Nat.mod_lt a hm |>.trans_le (Nat.le_refl _))]
  all_goals sorry

lemma padicValNat_choose_MK_sub_one_zero (K k p : Nat) [hpfact : Fact p.Prime]
    (hpK : p ≤ K) (hkK : k ≤ K) (hKpos : 0 < K) :
    padicValNat p (Nat.choose (M_K K - 1) k) = 0 := by
  have hp : Nat.Prime p := hpfact.out
  have hMK_pos : 0 < M_K K := M_K_pos K
  -- p^(log p K + 1) > K ≥ k
  have hpow_gt_K : K < p ^ (Nat.log p K + 1) := Nat.lt_pow_succ_log_self hp.one_lt K
  -- M_K K ≥ p^(log p K + 1) > K, so k < M_K K, hence k ≤ M_K K - 1
  have hMK_ge_pow : p ^ (Nat.log p K + 1) ≤ M_K K :=
    Nat.le_of_dvd hMK_pos (M_K_divisible_by_prime_pow K p hp hpK)
  have hMK_gt_K : K < M_K K := Nat.lt_of_lt_of_le hpow_gt_K hMK_ge_pow
  have hk_le_MK_pred : k ≤ M_K K - 1 :=
    Nat.le_sub_one_of_lt (Nat.lt_of_le_of_lt hkK hMK_gt_K)
  -- Apply Kummer's theorem with b = Nat.log p (M_K K - 1) + 1
  rw [padicValNat_choose hk_le_MK_pred (Nat.lt_succ_self _)]
  -- Show the carry set is empty
  simp only [Finset.card_eq_zero]
  apply Finset.eq_empty_of_forall_not_mem
  intro i
  simp only [Finset.mem_filter, Finset.mem_Ico, not_and, not_le]
  intro ⟨hi_pos, _hi_lt⟩
  -- Show: p^i > k % p^i + (M_K K - 1 - k) % p^i
  -- Strategy: k % p^i ≤ (M_K K - 1) % p^i, so sum = (M_K K - 1) % p^i < p^i
  have hpi_pos : 0 < p ^ i := Nat.pos_pow_of_pos i hp.pos
  -- Step 1: k % p^i ≤ (M_K K - 1) % p^i
  have hkey : k % p ^ i ≤ (M_K K - 1) % p ^ i := by
    by_cases hi_le : i ≤ Nat.log p K + 1
    · -- p^i | M_K K, so (M_K K - 1) % p^i = p^i - 1 ≥ k % p^i
      have hpow_dvd : p ^ i ∣ M_K K := M_K_dvd_pow K p i hp hpK hi_le
      have hmod_eq : (M_K K - 1) % p ^ i = p ^ i - 1 :=
        mod_pred_of_dvd hpow_dvd hMK_pos
      rw [hmod_eq]
      exact Nat.le_pred_of_lt (Nat.mod_lt k hpi_pos)
    · -- i > log p K + 1, so p^i > K ≥ k, hence k % p^i = k
      push_neg at hi_le
      have hi_ge : Nat.log p K + 1 ≤ i := hi_le
      have hpow_ge : p ^ (Nat.log p K + 1) ≤ p ^ i :=
        Nat.pow_le_pow_right hp.pos hi_ge
      have hk_lt_pi : k < p ^ i :=
        Nat.lt_of_lt_of_le (Nat.lt_of_le_of_lt hkK hpow_gt_K) hpow_ge
      rw [Nat.mod_eq_of_lt hk_lt_pi]
      -- (M_K K - 1) % p^i ≥ p^(log p K + 1) - 1 ≥ K ≥ k
      -- Key: (M_K K - 1) % p^(log p K + 1) = p^(log p K + 1) - 1 divides into (M_K K - 1) % p^i
      have hlog_dvd_i : p ^ (Nat.log p K + 1) ∣ p ^ i :=
        Nat.pow_dvd_pow p hi_ge
      have hmod_small : (M_K K - 1) % p ^ (Nat.log p K + 1) = p ^ (Nat.log p K + 1) - 1 :=
        mod_pred_of_dvd (M_K_divisible_by_prime_pow K p hp hpK) hMK_pos
      -- (M_K K - 1) % p^i has same lower digits: (... % p^i) % p^(log+1) = p^(log+1) - 1
      have hmod_nested : ((M_K K - 1) % p ^ i) % p ^ (Nat.log p K + 1) =
          p ^ (Nat.log p K + 1) - 1 := by
        rw [Nat.mod_mod_of_dvd _ hlog_dvd_i]
        exact hmod_small
      -- Hence (M_K K - 1) % p^i ≥ p^(log p K + 1) - 1
      have hmod_large : p ^ (Nat.log p K + 1) - 1 ≤ (M_K K - 1) % p ^ i := by
        have := Nat.mod_le ((M_K K - 1) % p ^ i) (p ^ (Nat.log p K + 1))
        omega
      calc k ≤ K := hkK
        _ ≤ p ^ (Nat.log p K + 1) - 1 := Nat.le_pred_of_lt hpow_gt_K
        _ ≤ (M_K K - 1) % p ^ i := hmod_large
  -- Step 2: k % p^i + (M_K K - 1 - k) % p^i = (M_K K - 1) % p^i < p^i
  have hsum_eq : k % p ^ i + (M_K K - 1 - k) % p ^ i = (M_K K - 1) % p ^ i := by
    -- (M_K K - 1) = (M_K K - 1 - k) + k and k % p^i ≤ (M_K K - 1) % p^i, no borrow
    have hle : k ≤ M_K K - 1 := hk_le_MK_pred
    omega
  linarith [Nat.mod_lt (M_K K - 1) hpi_pos, hsum_eq.symm.le]

/-! ## Piece 5: Main theorem -/

/-- label: thm:binomial-main

For n sufficiently large:
  f(n) ≤ (24/(π²-6) + ε)(log n)² for any ε > 0 (upper bound via PNT + averaging),
  f(M_K K - 1) > K for all K (lower bound via Kummer, no PNT needed for the valuation part),
  giving f(n_j) ≥ (1/2 + o(1)) log n_j along n_j = M_K K - 1 (via PNT: log M_K ~ 2K). -/
theorem thm_binomial_main :
    -- Upper bound: existence of small k with large u_smooth
    (forall (eps : Real), 0 < eps ->
      Filter.Eventually (fun n : Nat =>
        exists k : Nat, 1 <= k /\
          (k : Real) <= (24 / (Real.pi ^ 2 - 6) + eps) * (Real.log n) ^ 2 /\
          (n : Real) ^ 2 < (u_smooth n k : Real))
        atTop)
    /\
    -- Lower bound: for large K, M_K K - 1 has u_smooth = 1 for all k ≤ K
    -- (meaning f(M_K K - 1) > K)
    Filter.Eventually (fun K : Nat =>
      forall k : Nat, k <= K -> u_smooth (M_K K - 1) k <= 1)
      atTop := by
  constructor
  · -- Upper bound via PNT (pnt_theta_asym / pnt_psi_asym); defer with sorry
    intro eps _heps
    simp only [Filter.Eventually, Filter.mem_atTop_sets]
    sorry
  · -- Lower bound: follows from padicValNat_choose_MK_sub_one_zero
    rw [Filter.eventually_atTop]
    use 1
    intro K hK k hkK
    -- u_smooth (M_K K - 1) k = ∏_{p prime, p ≤ k} p^(padicValNat p (C(M_K K - 1, k)))
    -- All primes p ≤ k ≤ K, so padicValNat p (C(M_K K - 1, k)) = 0 by the helper.
    -- Hence the product is ∏ p^0 = ∏ 1 = 1.
    simp only [u_smooth]
    suffices h : Finset.prod ((Finset.range (k + 1)).filter Nat.Prime)
        (fun p => p ^ (padicValNat p (Nat.choose (M_K K - 1) k))) = 1 by
      simp [h]
    apply Finset.prod_eq_one
    intro p hp
    simp only [Finset.mem_filter, Finset.mem_range] at hp
    obtain ⟨hpk, hpprime⟩ := hp
    have hpk' : p ≤ k := Nat.lt_succ_iff.mp hpk
    have hpK : p ≤ K := Nat.le_trans hpk' hkK
    haveI : Fact p.Prime := ⟨hpprime⟩
    have hKpos : 0 < K := Nat.lt_of_lt_of_le Nat.one_pos hK
    rw [padicValNat_choose_MK_sub_one_zero K k p hpK hkK hKpos]
    simp
