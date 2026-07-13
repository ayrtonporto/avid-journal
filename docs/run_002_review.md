# Run 002 — Manual Review Document

**Generated:** 2026-07-13  
**Model:** opencode/qwen3.7-max (statement-only, 5 rounds)  
**Papers:** 5 retracted + 5 controls = 10 total  
**Formalization success:** 5/10 (50%)

---

## Summary Table

| arXiv ID | Role | Compiled | Veredicto | Fidelity | D1 CF | D1 CI | D2 |
|----------|------|:--------:|-----------|:--------:|-------|-------|:--:|
| [1609.02090v1](https://arxiv.org/abs/1609.02090v1) | retracted | ✅ | NOVEDAD_ENUNCIADO | error | | different | False |
| [1207.0631v1](https://arxiv.org/abs/1207.0631v1) | retracted | ✅ | CONOCIDO_LITERATURA | error | | equivalent | False |
| [1212.0196v1](https://arxiv.org/abs/1212.0196v1) | retracted | ✅ | NOVEDAD_ENUNCIADO | error | | | False |
| [1004.3381v1](https://arxiv.org/abs/1004.3381v1) | retracted | ❌ | FORMALIZATION_FAILED | — | — | — | — |
| [math/0604362v1](https://arxiv.org/abs/math/0604362v1) | retracted | ❌ | FORMALIZATION_FAILED | — | — | — | — |
| [1501.01654v1](https://arxiv.org/abs/1501.01654v1) | control | ❌ | FORMALIZATION_FAILED | — | — | — | — |
| [1101.3431v2](https://arxiv.org/abs/1101.3431v2) | control | ❌ | FORMALIZATION_FAILED | — | — | — | — |
| [1101.3720v1](https://arxiv.org/abs/1101.3720v1) | control | ❌ | FORMALIZATION_FAILED | — | — | — | — |
| [0904.1783v3](https://arxiv.org/abs/0904.1783v3) | control | ✅ | NOVEDAD_ENUNCIADO | error | | | False |
| [math/0504586v2](https://arxiv.org/abs/math/0504586v2) | control | ✅ | NOVEDAD_ENUNCIADO | fail | | | False |

> *Fidelity column: "error" = JSON parse error (LLM judge response format), "fail" = judge found mismatch. Veredicto and D1/D2 columns for user to fill.*

---

## Paper 1 — 1609.02090v1 (retracted) ✅

### A. Original Statement

**Withdrawal comment:** "Main results originally proved in Some Problems of Partitio Numerorum (VIII) by Hardy & Littlewood."  
**Known duplicator:** Hardy & Littlewood, Partitio Numerorum VIII — γ(4)=15 por método analítico; el retirado lo reproduce con métodos elementales.  
**Target:** `\label{EvenPowers}` — Z_n covered by 15 quartics, 9 sextics, 32 octics, 12 decics.

### B. Generated Formalization (1046 bytes)

```lean
import Mathlib

def powers (n k : ℕ) : Set (ZMod n) :=
  {x | ∃ y : ZMod n, x = y ^ k}

def sumset {α : Type*} [AddCommMonoid α] (S : Set α) (m : ℕ) : Set α :=
  {x | ∃ (f : Fin m → α), (∀ i, f i ∈ S) ∧ x = ∑ i, f i}

theorem evenPowersCover (n : ℕ) (hn : n > 0) :
  (Set.univ : Set (ZMod n)) ⊆ sumset (powers n 4) 15 ∧
  (Set.univ : Set (ZMod n)) ⊆ sumset (powers n 6) 9 ∧
  (Set.univ : Set (ZMod n)) ⊆ sumset (powers n 8) 32 ∧
  (Set.univ : Set (ZMod n)) ⊆ sumset (powers n 10) 12 := by
  sorry
```

**Veredicto de fidelidad:** [ ] fiel / [ ] debilitado / [ ] incorrecto

### C. Mathlib Match (D1 formal)

*(Leandex — to fill)*

### D. D1 Informal (TheoremSearch)

*(to fill)*

**Veredicto pipeline:** `NOVEDAD_ENUNCIADO` — no match found in Mathlib or arXiv.

---

## Paper 2 — 1207.0631v1 (retracted) ✅

### A. Original Statement

**Withdrawal comment:** "Result already published with a similar proof."  
**Known duplicator:** Fillmore (1969).  
**Target:** `\label{maintheo}` — non-scalar matrix A: trace equality iff similar to matrix with given diagonal.

### B. Generated Formalization (343 bytes)

```lean
import Mathlib

theorem matrix_diagonal_similarity_equivalence {n : ℕ} {K : Type*} [Field K] 
  (A : Matrix (Fin n) (Fin n) K) 
  (hA : ¬ ∃ (k : K), A = k • 1) (c : Fin n → K) :
  (∑ i, c i = Matrix.trace A) ↔ 
  (∃ B : Matrix (Fin n) (Fin n) K, (∀ i, B i i = c i) ∧ Matrix.IsSimilar A B) := by
  sorry
```

**Veredicto de fidelidad:** [ ] fiel / [ ] debilitado / [ ] incorrecto

### C. Mathlib Match (D1 formal)

*(to fill)*

### D. D1 Informal (TheoremSearch)

**LLM Judge:** `equivalent` — TheoremSearch found a paper with the same statement.

**Veredicto pipeline:** `CONOCIDO_LITERATURA` — equivalent result found in arXiv.

---

## Paper 3 — 1212.0196v1 (retracted) ✅

### A. Original Statement

**Withdrawal comment:** "Corollary of a well-known result by Monsky."  
**Known duplicator:** Monsky (congruent numbers).  
**Target:** `\label{cor:main}` — m = product of primes ≡ 3 mod 8 with Legendre symbols = 1 ⇒ m non-congruent.

### B. Generated Formalization (438 bytes)

```lean
import Mathlib

def IsCongruentNumber (n : ℕ) : Prop :=
  ∃ (a b c : ℚ), 0 < a ∧ 0 < b ∧ 0 < c ∧ a^2 + b^2 = c^2 ∧ (1 / 2 : ℚ) * a * b = (n : ℚ)

theorem non_congruent_number_criterion (k : ℕ) (p : Fin k → ℕ)
  (h_prime : ∀ i, Nat.Prime (p i))
  (h_mod : ∀ i, p i % 8 = 3)
  (h_legendre : ∀ i j, i < j → jacobiSym (p i : ℤ) (p j) = 1) :
  ¬ IsCongruentNumber (∏ i : Fin k, p i) := by
  sorry
```

**Veredicto de fidelidad:** [ ] fiel / [ ] debilitado / [ ] incorrecto

### C. Mathlib Match (D1 formal)

*(to fill)*

### D. D1 Informal (TheoremSearch)

*(to fill)*

**Veredicto pipeline:** `NOVEDAD_ENUNCIADO` — no match found.

---

## Paper 4 — 1004.3381v1 (retracted) ❌

### A. Original Statement

**Withdrawal comment:** "Most results already known (Gyárfás & Lehel, 1970)."  
**Known duplicator:** Gyárfás & Lehel — d-separated interval piercing.  
**Target:** Rectangle slicing bound f(m) ≤ c·(2m+1)².

### B. Generated Formalization

**Status:** ❌ FORMALIZATION_FAILED — API error `[Errno 22] Invalid argument` (prompt too long for API). Partial .lean generated (1234 bytes) but not compiled.

```lean
import Mathlib

structure Rectangle where
  x1 : ℝ; x2 : ℝ; y1 : ℝ; y2 : ℝ
  hx : x1 ≤ x2; hy : y1 ≤ y2

inductive AxisParallelLine where
  | vertical : ℝ → AxisParallelLine
  | horizontal : ℝ → AxisParallelLine
```

**Veredicto de fidelidad:** [ ] N/A (no compiló)

**Notas:** El enunciado es muy largo con definiciones por casos anidadas. Qwen API rechazó el prompt por tamaño.

---

## Paper 5 — math/0604362v1 (retracted) ❌

### A. Original Statement

**Withdrawal comment:** "Result was previously known."  
**Known duplicator:** Unknown — possibly LPW.  
**Target:** `\label{thm:spectral_lowerbound}` — d(n) ≥ ½|λ_i|ⁿ.

### B. Generated Formalization

**Status:** ❌ FORMALIZATION_FAILED — compilation error. Partial .lean (1735 bytes) with definitions for `IsStochastic`, `IsIrreducibleChain`, etc. Error: `_root_.IsIrreducibleChain` — name resolution issue.

```lean
import Mathlib

variable {α : Type*} [Fintype α] [DecidableEq α] [Nonempty α]

def IsStochastic (P : Matrix α α ℝ) := ...
def IsIrreducibleChain (P : Matrix α α ℝ) := ...
def totalVariationDistance (P : Matrix α α ℝ) (π : α → ℝ) (n : ℕ) : ℝ := ...
```

**Veredicto de fidelidad:** [ ] N/A (no compiló)

---

## Paper 6 — 1501.01654v1 (control) ❌

### A. Original Statement

**Paired with:** 1609.02090v1  
**Target:** Almost universal quadratic forms — very long theorem with nested case enumeration.

### B. Generated Formalization

**Status:** ❌ FORMALIZATION_FAILED — API error `[Errno 22] Invalid argument`. Enunciado extremadamente largo (4 niveles de casos anidados).

---

## Paper 7 — 1101.3431v2 (control) ❌

### A. Original Statement

**Paired with:** 1207.0631v1  
**Target:** Mean payoff game theorem.

### B. Generated Formalization

**Status:** ❌ FORMALIZATION_FAILED — API error `[Errno 22] Invalid argument`.

---

## Paper 8 — 1101.3720v1 (control) ❌

### A. Original Statement

**Paired with:** 1212.0196v1  
**Target:** Binary cyclotomic polynomials.

### B. Generated Formalization

**Status:** ❌ FORMALIZATION_FAILED — API error `[Errno 22] Invalid argument`.

---

## Paper 9 — 0904.1783v3 (control) ✅

### A. Original Statement

**Paired with:** 1004.3381v1  
**Target:** `\label{thm:minkowski-weyl}` — Polyhedron representation.

### B. Generated Formalization (1281 bytes)

```lean
import Mathlib

variable {n : ℕ}

def IsClosedPolyhedron (S : Set (Fin n → ℝ)) : Prop :=
  ∃ (m : ℕ), ∃ (H : Fin m → (Fin n → ℝ) → ℝ), (∀ i, IsLinear ℝ (H i)) ∧ ...

theorem minkowski_weyl : True := by
  sorry
```

**Veredicto de fidelidad:** [ ] fiel / [ ] debilitado / [ ] incorrecto

### C. Mathlib Match (D1 formal)

*(to fill)*

### D. D1 Informal (TheoremSearch)

*(to fill)*

**Veredicto pipeline:** `NOVEDAD_ENUNCIADO`.

---

## Paper 10 — math/0504586v2 (control) ✅

### A. Original Statement

**Paired with:** math/0604362v1  
**Target:** `\label{pr:noncrit}` — Percolation noise sensitivity.

### B. Generated Formalization (1285 bytes)

```lean
import Mathlib

open MeasureTheory

def PercolationModel (G : Type*) [SimpleGraph G] := ...
def ProbPercolation (p : ℝ) (event : Set (∀ e : G.edgeSet, Bool)) : ℝ := ...
```

**Veredicto de fidelidad:** [ ] fiel / [ ] debilitado / [ ] incorrecto  
**LLM Judge:** `fail` — "The Lean code defines a framework but doesn't state the proposition from the LaTeX."

### C. Mathlib Match (D1 formal)

*(to fill)*

### D. D1 Informal (TheoremSearch)

*(to fill)*

**Veredicto pipeline:** `NOVEDAD_ENUNCIADO`.

---

## Final Comparative Table (for user to fill)

| Paper | Fidelidad formalización | Match formal (D1 CF) | ¿Duplicador en D1 CI? | Veredicto final |
|-------|------------------------|---------------------|----------------------|-----------------|
| 1609.02090v1 (retracted) | [ ] fiel / [ ] deb / [ ] inc | | | |
| 1207.0631v1 (retracted) | [ ] fiel / [ ] deb / [ ] inc | | | |
| 1212.0196v1 (retracted) | [ ] fiel / [ ] deb / [ ] inc | | | |
| 1004.3381v1 (retracted) | N/A | N/A | N/A | |
| math/0604362v1 (retracted) | N/A | N/A | N/A | |
| 1501.01654v1 (control) | N/A | N/A | N/A | |
| 1101.3431v2 (control) | N/A | N/A | N/A | |
| 1101.3720v1 (control) | N/A | N/A | N/A | |
| 0904.1783v3 (control) | [ ] fiel / [ ] deb / [ ] inc | | | |
| math/0504586v2 (control) | [ ] fiel / [ ] deb / [ ] inc | | | |

---

## Notes

- **5/10 API failures** caused by prompt length (`[Errno 22] Invalid argument`). The 4 controls with long target_theorems (1501, 1101.3431, 1101.3720) and paper 4 exceed Qwen's input limit. Mitigation: truncate theorem to core statement, or use model with larger context window.
- **Fidelity JSON errors** are parsing failures in `check_fidelity` — DeepSeek v4 Flash returns `reasoning_content` instead of `content`. The fidelity verdicts are unreliable. Mitigation: fix JSON extraction or use different judge model.
- **Veredictos** are pipeline-generated (D1/D2). User must review and fill the comparative table.
