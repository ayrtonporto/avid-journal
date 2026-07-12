# Run 001 — Manual Review Document

**Generated:** 2026-07-06  
**Papers:** 5 retracted (smoke test)  
**Verdicts:** all `MATCH_ENCONTRADO_PENDIENTE_D3`

---

## Paper 1 — 1609.02090v1

### A. Original Statement

**Withdrawal comment:** Paper withdrawn as main results are not original. Main results originally proved in "Some Problems of 'Partitio Numerorum' (VIII)" by G.H. Hardy and J.E. Littlewood.

**Known duplicator:** Hardy & Littlewood, Partitio Numerorum (VIII)

**Target theorem (LaTeX):**
```latex
\label{SquaresZn}
$\mathbb{Z}_n \subset 2R_2$ if and only if $n$ satisfies the condition
that when $p^2 \mid n$, then $p \equiv 1 \pmod{4}$ for every odd prime $p$,
and $n \not\equiv 0 \pmod{16}$.
```

### B. Generated Formalization

**Status:** ✅ Compiled on attempt 1 (24s)

⚠️ **The generated Lean code was not saved.** The formalization pipeline writes to a temporary file, compiles it, and deletes it on success. The code is lost. _This is a gap to fix in the pipeline._

**Veredicto de fidelidad:** [ ] fiel / [ ] debilitado / [ ] incorrecto

**Notas:**

### C. Mathlib Match

**Lean name:** `Nat.eq_sq_add_sq_iff`  
**Score:** 1.0 (Leandex exact match)  
**Source:** `Mathlib/NumberTheory/SumTwoSquares.lean`

**Mathlib statement:**
```lean
/-- A (positive) natural number `n` is a sum of two squares if and only if the exponent of
every prime `q` such that `q % 4 = 3` in the prime factorization of `n` is even.
(The assumption `0 < n` is not present, since for `n = 0`, both sides are satisfied;
the right-hand side holds, since `padicValNat q 0 = 0` by definition.) -/
theorem Nat.eq_sq_add_sq_iff {n : ℕ} :
    (∃ x y, n = x ^ 2 + y ^ 2) ↔ ∀ q ∈ n.primeFactors, q % 4 = 3 → Even (padicValNat q n) := by
  ...
```

**Veredicto de match:** [ ] mismo teorema / [ ] pariente cercano / [ ] no relacionado

**Notas:** The paper's theorem (representation of Z_n as sum of two squares) is a modular variant of the classic sum-of-two-squares theorem. The Mathlib match is the classical integer version.

### D. D1 Informal (TheoremSearch)

| # | Score | Title | arXiv |
|---|-------|-------|-------|
| 1 | 0.645 | On superspecial abelian varieties over finite fields | [1602.02541](https://arxiv.org/abs/1602.02541) |
| 2 | 0.639 | Some Properties of Overpartitions into Nonmultiples of Two Integers | [2412.18938](https://arxiv.org/abs/2412.18938) |
| 3 | 0.637 | Representing Integers as the Sum of Two Squares in the Ring Z_n | [1404.0187](https://arxiv.org/abs/1404.0187) |
| 4 | 0.630 | Cliques of orders three and four in the Paley-type graphs | [2301.07021](https://arxiv.org/abs/2301.07021) |
| 5 | 0.627 | On a Paley-type graph on Z_n | [2012.09735](https://arxiv.org/abs/2012.09735) |

**Known duplicator:** Hardy & Littlewood, Partitio Numerorum (VIII)

**¿Duplicador encontrado?:** [ ] sí, en posición __ / [ ] no / [ ] no verificable

**Notas:**

---

## Paper 2 — 1207.0631v1

### A. Original Statement

**Withdrawal comment:** 4 pages, withdrawn since the result has already been published with a similar proof.

**Known duplicator:** Published elsewhere with similar proof (Fillmore, 1969?)

**Target theorem (LaTeX):**
```latex
\label{keylemma}
Assume $n \geq 2$.
Let $A \in \Mat_n(\K)$ be a non-scalar matrix, and let $a \in \K$.
Then there exists a matrix $B \in \Mat_n(\K)$ that is similar to $A$
and whose diagonal equals $(a, \tr(A)-a, 0, \dots, 0)$.
```

### B. Generated Formalization

**Status:** ✅ Compiled on attempt 1 (28s)

⚠️ **The generated Lean code was not saved** (same gap as Paper 1).

**Veredicto de fidelidad:** [ ] fiel / [ ] debilitado / [ ] incorrecto

**Notas:**

### C. Mathlib Match

**Lean name:** `Matrix.scalar_apply`  
**Score:** 1.0 (Leandex exact match)  
**Source:** `Mathlib/Data/Matrix/Basic.lean`

**Mathlib statement:**
```lean
@[simp]
theorem scalar_apply (a : α) : scalar n a = diagonal fun _ => a :=
  rfl
```

⚠️ **This is a trivial lemma about scalar matrices, not Fillmore's theorem on the diagonal of similarity classes.** The Leandex score of 1.0 is suspicious — it suggests the formalization produced by the pipeline was exactly `Matrix.scalar_apply` (or something trivially equivalent), rather than the actual Fillmore theorem. This is a likely formalization fidelity issue: the model may have simplified the theorem to something that compiles but doesn't capture the original statement.

**Veredicto de match:** [ ] mismo teorema / [ ] pariente cercano / [ ] no relacionado

**Notas:**

### D. D1 Informal (TheoremSearch)

| # | Score | Title | arXiv |
|---|-------|-------|-------|
| 1 | 0.754 | Filmor Theorem for integers | [1704.08037](https://arxiv.org/abs/1704.08037) |
| 2 | 0.737 | Sums and products of square-zero matrices | [1804.02140](https://arxiv.org/abs/1804.02140) |
| 3 | 0.701 | Sums and products of square-zero matrices | [1804.02140](https://arxiv.org/abs/1804.02140) |
| 4 | 0.686 | The Waring Problem for Matrix Algebras, II | [2302.05106](https://arxiv.org/abs/2302.05106) |
| 5 | 0.678 | Matrix evaluations of noncommutative rational functions and Waring problems | [2401.11564](https://arxiv.org/abs/2401.11564) |

**Known duplicator:** Fillmore, 1969?

**¿Duplicador encontrado?:** [ ] sí, en posición __ / [ ] no / [ ] no verificable

**Notas:**

---

## Paper 3 — 1212.0196v1

### A. Original Statement

**Withdrawal comment:** This paper has been withdrawn by the author because it is a corollary of a well-known result by Monsky.

**Known duplicator:** Monsky (well-known result on congruent numbers)

**Target theorem (LaTeX):**
```latex
\label{cor:main}
Suppose $m=p_1\cdots p_k$ and $p_i\equiv 3\pmod 8$.
If $\leg{p_i}{p_j}=1$ for all $1\leq i<j\leq k$,
then $m$ is a non-congruent number.
```

### B. Generated Formalization

**Status:** ✅ Compiled on attempt 1 (31s)

⚠️ **The generated Lean code was not saved** (same gap as Paper 1).

**Veredicto de fidelidad:** [ ] fiel / [ ] debilitado / [ ] incorrecto

**Notas:**

### C. Mathlib Match

**Lean name:** `CongruentNumber.not_congruentNumber_1`  
**Score:** 1.0 (Leandex exact match)  
**Source:** `Mathlib/NumberTheory/CongruentNumber.lean`

**Mathlib statement:**
```lean
/-- 1 is not a congruent number, as proved by Fermat via infinite descent. -/
@[category textbook, AMS 11]
theorem not_congruentNumber_1 : ¬ congruentNumber 1 := by
  sorry
```

⚠️ **The Mathlib match is `1 is not a congruent number`, not the paper's theorem about products of primes ≡ 3 mod 8.** This is a weaker/simpler statement. The formalization may have been simplified toward this known lemma.

**Veredicto de match:** [ ] mismo teorema / [ ] pariente cercano / [ ] no relacionado

**Notas:**

### D. D1 Informal (TheoremSearch)

| # | Score | Title | arXiv |
|---|-------|-------|-------|
| 1 | 0.674 | Congruent Numbers and Heegner Points | [1210.8231](https://arxiv.org/abs/1210.8231) |
| 2 | 0.649 | Generalization of Some Arithmetical Properties of Fermat-Euler Dynamical Systems | [0910.5704](https://arxiv.org/abs/0910.5704) |
| 3 | 0.647 | The even parity Goldfeld conjecture: congruent number elliptic curves | [2104.06732](https://arxiv.org/abs/2104.06732) |
| 4 | 0.635 | A New Generalization of Fermat's Last Theorem | [1310.0897](https://arxiv.org/abs/1310.0897) |

**Known duplicator:** Monsky

**¿Duplicador encontrado?:** [ ] sí, en posición __ / [ ] no / [ ] no verificable

**Notas:**

---

## Paper 4 — 1004.3381v1

### A. Original Statement

**Withdrawal comment:** Withdrawn, because we found out that most of the results were already known (under a different name). The result that T_d(m) exists was first proved by Gyárfás and Lehel in 1970.

**Known duplicator:** Gyárfás & Lehel (1970) — d-separated interval piercing

**Target theorem (LaTeX):**
```latex
Let $R$ be a set of rectangles such that the largest independent set
is of size $m$, then the rectangles can be sliced by at most
$O(m \log m)$ lines.
```

### B. Generated Formalization

**Status:** ✅ Compiled on attempt 1 (35s)

⚠️ **The generated Lean code was not saved** (same gap as Paper 1).

**Veredicto de fidelidad:** [ ] fiel / [ ] debilitado / [ ] incorrecto

**Notas:**

### C. Mathlib Match

**Lean name:** `Green85.green_85`  
**Score:** 1.0 (Leandex exact match)  
**Source:** `Archive/` or `Counterexamples/`

**Mathlib statement:**
```lean
/--
Suppose that $A$ is an open subset of $[0, 1]^2$ with measure $\alpha$. Are there four points in
$A$ determining an axis-parallel rectangle with area $\gt c \alpha^2$?
-/
@[category research open, AMS 28 52]
theorem green_85 :
  answer(sorry) ↔ ∃ c > 0, ∀ A : Set (ℝ × ℝ),
    IsOpen A →
    A ⊆ Icc 0 1 ×ˢ Icc 0 1 →
    A.Nonempty →
    let α := (volume A).toReal
    ∃ x₁ x₂ y₁ y₂,
      {(x₁, y₁), (x₂, y₁), (x₂, y₂), (x₁, y₂)} ⊆ A ∧
      c * α ^ 2 ≤ |x₁ - x₂| * |y₁ - y₂| := by
  sorry
```

⚠️ **This is an OPEN PROBLEM (Green's conjecture on rectangles), not the slicing/piercing result from the paper.** This is clearly NOT the same theorem. The formalization must have been incorrect or the Leandex match found a theorem with a coincidental structural similarity.

**Veredicto de match:** [ ] mismo teorema / [ ] pariente cercano / [ ] no relacionado

**Notas:**

### D. D1 Informal (TheoremSearch)

| # | Score | Title | arXiv |
|---|-------|-------|-------|
| 1 | 0.764 | An Erdős--Hajnal analogue for permutation classes | [1511.01076](https://arxiv.org/abs/1511.01076) |
| 2 | 0.739 | Permutation classes | [1409.5159](https://arxiv.org/abs/1409.5159) |
| 3 | 0.715 | Well-Quasi-Order for Permutation Graphs Omitting a Path and a Clique | [1312.5907](https://arxiv.org/abs/1312.5907) |
| 4 | 0.675 | Independent sets and hitting sets of bicolored rectangular families | [1411.2311](https://arxiv.org/abs/1411.2311) |
| 5 | 0.645 | Independent and Hitting Sets of Rectangles Intersecting a Diagonal Line | [1309.6659](https://arxiv.org/abs/1309.6659) |

**Known duplicator:** Gyárfás & Lehel (1970)

**¿Duplicador encontrado?:** [ ] sí, en posición __ / [ ] no / [ ] no verificable

**Notas:**

---

## Paper 5 — math/0604362v1

### A. Original Statement

**Withdrawal comment:** This paper has been withdrawn because I have been made aware that the result was previously known.

**Known duplicator:** Unknown — possibly known in mixing time literature (LPW?)

**Target theorem (LaTeX):**
```latex
\label{thm:spectral_lowerbound}
The eigenvalues $\lambda_i\neq 1$ of a finite, irreducible Markov chain satisfy
$$d(n) \le \max_{i\ge 2} |\lambda_i|$$
where $d(n)$ is the total variation distance.
```

### B. Generated Formalization

**Status:** ✅ Compiled on attempt 1 (34s)

⚠️ **The generated Lean code was not saved** (same gap as Paper 1).

**Veredicto de fidelidad:** [ ] fiel / [ ] debilitado / [ ] incorrecto

**Notas:**

### C. Mathlib Match

**Lean name:** `eVariationOn.sum_le`  
**Score:** 1.0 (Leandex exact match)  
**Source:** `Mathlib/Analysis/BoundedVariation.lean`

**Mathlib statement:**
```lean
theorem sum_le {f : α → E} {s : Set α} {n : ℕ} {u : ℕ → α} (hu : Monotone u) (us : ∀ i, u i ∈ s) :
    (∑ i ∈ Finset.range n, edist (f (u (i + 1))) (f (u i))) ≤ eVariationOn f s :=
  le_iSup_of_le ⟨n, u, hu, us⟩ le_rfl
```

⚠️ **This is a lemma about bounded variation of functions, not about Markov chain mixing times.** This is clearly a different theorem — the formalization either simplified to a triviality or Leandex returned a structurally similar but semantically different match.

**Veredicto de match:** [ ] mismo teorema / [ ] pariente cercano / [ ] no relacionado

**Notas:**

### D. D1 Informal (TheoremSearch)

| # | Score | Title | arXiv |
|---|-------|-------|-------|
| 1 | 0.756 | Rapid mixing from spectral independence beyond the Boolean domain | [2007.08091](https://arxiv.org/abs/2007.08091) |
| 2 | 0.745 | Shuffling via Transpositions | [2504.07918](https://arxiv.org/abs/2504.07918) |
| 3 | 0.739 | Cutoff for a One-sided Transposition Shuffle | [1907.12074](https://arxiv.org/abs/1907.12074) |
| 4 | 0.737 | Topics in Markov chains: mixing and escape rate | [1506.04850](https://arxiv.org/abs/1506.04850) |
| 5 | 0.729 | The Spectral Gap of Sparse Random Digraphs | [1708.00530](https://arxiv.org/abs/1708.00530) |

**Known duplicator:** Unknown (LPW?)

**¿Duplicador encontrado?:** [ ] sí, en posición __ / [ ] no / [ ] no verificable

**Notas:**

---

## Summary Table (for user to fill)

| Paper | Fidelidad formalización | Match formal | ¿Duplicador encontrado? |
|-------|------------------------|-------------|------------------------|
| 1609.02090v1 (Waring / Z_n) | [ ] fiel / [ ] debilitado / [ ] incorrecto | [ ] mismo / [ ] pariente / [ ] no relacionado | [ ] sí, pos __ / [ ] no / [ ] no verificable |
| 1207.0631v1 (Fillmore / diagonal) | [ ] fiel / [ ] debilitado / [ ] incorrecto | [ ] mismo / [ ] pariente / [ ] no relacionado | [ ] sí, pos __ / [ ] no / [ ] no verificable |
| 1212.0196v1 (Monsky / congruent) | [ ] fiel / [ ] debilitado / [ ] incorrecto | [ ] mismo / [ ] pariente / [ ] no relacionado | [ ] sí, pos __ / [ ] no / [ ] no verificable |
| 1004.3381v1 (Gyárfás-Lehel / slicing) | [ ] fiel / [ ] debilitado / [ ] incorrecto | [ ] mismo / [ ] pariente / [ ] no relacionado | [ ] sí, pos __ / [ ] no / [ ] no verificable |
| math/0604362v1 (Markov / spectral) | [ ] fiel / [ ] debilitado / [ ] incorrecto | [ ] mismo / [ ] pariente / [ ] no relacionado | [ ] sí, pos __ / [ ] no / [ ] no verificable |

---

## Gaps Found

1. **Generated Lean code not saved.** The formalization writes to a temp file, compiles, and deletes it. The actual code is unrecoverable. **Fix needed:** save the Lean code to the CSV or a log file before deletion.

2. **Leandex scores are all 1.0.** This suggests Leandex is returning exact-match confidence for the formalized statements, but the matches appear semantically wrong for papers 2, 4, and 5. The formalization may be producing trivial/simplified Lean that happens to match a basic lemma.

3. **Withdrawal comments not in experiment YAML.** They were extracted from `retracted_candidates.yaml` instead. In future runs, the experiment YAML should include them for reference.
