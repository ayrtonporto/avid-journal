# Run 002 — Revisión Final

**Instrucción:** Comparar LaTeX original ↔ Lean generado. Juzgar fidelidad de definiciones auxiliares. Marcar ✅ fiel / ⚠️ aproximación / ❌ incorrecto.

---

## PAPER 1 — 1609.02090v1 (retracted) ✅ NOVEDAD_ENUNCIADO

### Original (LaTeX)
```latex
\label{EvenPowers}
$\mathbb{Z}_n$ can be covered by fifteen quartics, nine sextics,
thirty-two octics, and twelve decics, and these are all best possible.
That is, for all $n \geq 2$, we have
\[
\mathbb{Z}_n \subset 15 R_4, \mathbb{Z}_n \subset 9R_6,
\mathbb{Z}_n \subset 32R_8, \text{ and } \mathbb{Z}_n \subset 12R_{10}.
\]
Furthermore,
\begin{enumerate}
\item $\mathbb{Z}_n \subset 5R_4$ if and only if $8 \nmid n$.
\item $\mathbb{Z}_n \subset 7R_4$ if and only if $16 \nmid n$.
\end{enumerate}
```

### Qwen generó (Lean)
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

**Puntos a revisar:**
- `powers n k` = {x | ∃ y, x = y^k}. ¿Coincide con $R_k$ del paper? ✅
- `sumset S m` = suma de m elementos de S. ¿Coincide con $mR_k$? ✅
- ¿Faltan los casos intermedios (5R_4 iff 8∤n, 7R_4 iff 16∤n)? ⚠️ Sí, Qwen los omitió.

**Fidelidad:** [ ] ✅ fiel / [ ] ⚠️ aproximación (faltan casos intermedios) / [ ] ❌ incorrecto

---

## PAPER 2 — 1207.0631v1 (retracted) ✅ CONOCIDO_LITERATURA

### Original (LaTeX)
```latex
\label{maintheo}
Let $A$ be a non-scalar matrix of $\Mat_n(\K)$, and $c_1,\dots,c_n$
be scalars. Then the following conditions are equivalent:
\begin{enumerate}[(i)]
\item $c_1+\cdots+c_n=\tr A$;
\item $A$ is similar to a matrix with diagonal entries $c_1,\dots,c_n$.
\end{enumerate}
```

### Qwen generó (Lean)
```lean
import Mathlib

theorem matrix_diagonal_similarity_equivalence {n : ℕ} {K : Type*} [Field K] 
  (A : Matrix (Fin n) (Fin n) K) 
  (hA : ¬ ∃ (k : K), A = k • 1) (c : Fin n → K) :
  (∑ i, c i = Matrix.trace A) ↔ 
  (∃ B : Matrix (Fin n) (Fin n) K, (∀ i, B i i = c i) ∧ Matrix.IsSimilar A B) := by
  sorry
```

**Puntos a revisar:**
- `hA : ¬ ∃ (k : K), A = k • 1` = "A no es escalar". ¿Equivale a "non-scalar matrix"? ✅
- `Matrix.trace A` = tr(A). ✅
- `Matrix.IsSimilar A B` = A es similar a B. Está en Mathlib. ✅
- `(∀ i, B i i = c i)` = B tiene diagonal (c_1,...,c_n). ✅

**🎯 D1 match (caso estrella):**
- Pipeline encontró: **arXiv:1804.02140** — "Sums and products of square-zero matrices" (2018)
- Similitud: 0.706. Juez LLM: "equivalent" (confianza 0.95)
- **No es Fillmore (1969) directo.** Es un paper posterior que enuncia el mismo teorema.

**Fidelidad:** [ ] ✅ fiel / [ ] ⚠️ / [ ] ❌  
**Match D1:** [ ] VP (el teorema de Fillmore está en la literatura) / [ ] Match correcto pero referencia indirecta / [ ] Falso positivo

---

## PAPER 3 — 1212.0196v1 (retracted) ✅ NOVEDAD_ENUNCIADO

### Original (LaTeX)
```latex
\label{cor:main}
Suppose $m=p_1\cdots p_k$ and $p_i\equiv 3\pmod 8$.
If $\leg{p_i}{p_j}=1$ for all $1\leq i<j\leq k$,
then $m$ is a non-congruent number.
```

### Qwen generó (Lean)
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

**Puntos a revisar:**
- `IsCongruentNumber n` = ∃ a,b,c ∈ ℚ⁺, a²+b²=c², ab/2 = n. ¿Definición estándar? ✅
- `(1 / 2 : ℚ) * a * b = (n : ℚ)`. ¿Área = n? ✅ (área del triángulo rectángulo = ab/2)
- `jacobiSym` = símbolo de Jacobi. ¿Está en Mathlib? ✅
- `\leg{p_i}{p_j}=1` → `jacobiSym (p i : ℤ) (p j) = 1`. ✅

**Fidelidad:** [ ] ✅ fiel / [ ] ⚠️ / [ ] ❌

---

## PAPER 4 — 1004.3381v1 (retracted) ✅ NOVEDAD_ENUNCIADO

### Original (LaTeX)
```latex
Let $R$ be a set of rectangles such that the largest independent set
is of size $m$, then the rectangles can be sliced by
$f(m) \leq c\cdot(2m+1)^2$ axis-parallel lines.
```

### Qwen generó (Lean)
```lean
import Mathlib

structure Rectangle where
  x1 : ℝ; x2 : ℝ; y1 : ℝ; y2 : ℝ
  hx : x1 < x2; hy : y1 < y2

def rectsDisjoint (r1 r2 : Rectangle) : Prop :=
  r1.x2 < r2.x1 ∨ r2.x2 < r1.x1 ∨ r1.y2 < r2.y1 ∨ r2.y2 < r1.y1

inductive AxisParallelLine where
  | vertical : ℝ → AxisParallelLine
  | horizontal : ℝ → AxisParallelLine

def lineIntersectsRect (l : AxisParallelLine) (r : Rectangle) : Prop :=
  match l with
  | AxisParallelLine.vertical a => r.x1 ≤ a ∧ a ≤ r.x2
  | AxisParallelLine.horizontal b => r.y1 ≤ b ∧ b ≤ r.y2

def isIndependentSet (S : Finset Rectangle) : Prop :=
  ∀ r1 ∈ S, ∀ r2 ∈ S, r1 ≠ r2 → rectsDisjoint r1 r2

theorem rectangle_slicing_bound :
  ∃ c : ℝ, ∀ (R : Finset Rectangle) (m : ℕ),
  (∀ S : Finset Rectangle, S ⊆ R → isIndependentSet S → S.card ≤ m) →
  (∃ S : Finset Rectangle, S ⊆ R ∧ isIndependentSet S ∧ S.card = m) →
  ∃ (lines : Finset AxisParallelLine),
    (lines.card : ℝ) ≤ c * (2 * (m : ℝ) + 1) ^ 2 ∧
    ∀ r ∈ R, ∃ l ∈ lines, lineIntersectsRect l r := by
  sorry
```

**Puntos a revisar:**
- `Rectangle` con `x1 < x2, y1 < y2`. ¿Coincide con "rectangle"? ✅ (no degenerado)
- `rectsDisjoint` = uno completamente fuera del otro en x o y. ¿"disjoint"? ✅
- `AxisParallelLine` = vertical(x=a) u horizontal(y=b). ✅
- `lineIntersectsRect` = la línea cruza el rectángulo. ✅
- `isIndependentSet` = todo par disjunto. ¿Coincide con "independent set"? ✅
- `(lines.card : ℝ) ≤ c * (2*(m:ℝ)+1)^2`. ¿Coincide con `f(m) ≤ c·(2m+1)²`? ✅

**Fidelidad:** [ ] ✅ fiel / [ ] ⚠️ / [ ] ❌

---

## PAPER 8 — 1101.3720v1 (control) ✅ NOVEDAD_ENUNCIADO

### Original (LaTeX)
```latex
Let $B_{\varepsilon}(N)$ denote the set of binary $m<N$ for which
$\theta_m<m^{1/2+\varepsilon}$. Then we have
$$B_{\varepsilon}(N) = \left\{ \begin{array}{ll}
\Omega(N^{1/2}) & \text{for } 0 < \varepsilon < 1/2, \\
O(N^{1/2+\varepsilon}) & \text{for } 0 < \varepsilon < 1/6, \\
O(N/\log^2 N) & \text{for } 0 < \varepsilon < 1/2,
\end{array}\right.$$
where we used the $O$ and $\Omega$ asymptotical notation.
```

### Qwen generó (Lean)
```lean
import Mathlib

def theta (m : ℕ) : ℝ := sorry

def B (ε N : ℝ) : Set ℕ :=
  {m : ℕ | (m : ℝ) < N ∧ theta m < (m : ℝ) ^ (1/2 + ε)}

theorem B_asymptotics :
  (∀ ε > 0, ε < 1/2 → ∃ C N₀, ∀ N ≥ N₀, 
    (B ε N).toFinset.card ≥ C * Real.sqrt N) ∧
  (∀ ε > 0, ε < 1/6 → ∃ C N₀, ∀ N ≥ N₀,
    (B ε N).toFinset.card ≤ C * N ^ (1/2 + ε)) ∧
  (∀ ε > 0, ε < 1/2 → ∃ C N₀, ∀ N ≥ N₀,
    (B ε N).toFinset.card ≤ C * N / ((Real.log N) ^ 2)) := by
  sorry
```

**Puntos a revisar:**
- `theta m` = **`:= sorry`** ⚠️ — la función θ_m (medida de equisdistribución) no está definida.
- `B ε N` = {m < N : θ_m < m^{1/2+ε}}. ✅ La definición de B_ε(N) es correcta, pero depende de `theta`.
- Las cotas: Ω(N^{1/2}) → `≥ C*√N`, O(N^{1/2+ε}) → `≤ C*N^{1/2+ε}`, O(N/log²N) → `≤ C*N/(log N)²`. ✅
- El LaTeX original tiene 3 ramas en llave; el Lean tiene 3 conjunciones. ✅

**Fidelidad:** [ ] ✅ fiel (statement-only: `theta` con `sorry` es aceptable) / [ ] ⚠️ aproximación / [ ] ❌

---

## PAPER 9 — 0904.1783v3 (control) ✅ NOVEDAD_ENUNCIADO

### Original (LaTeX)
```latex
\label{thm:minkowski-weyl}
The set $\cP \sseq \Rset^n$ is a closed polyhedron if and only if
there exist finite sets $R, P \sseq \Rset^n$
of cardinality $r$ and $p$, respectively,
such that $\vect{0} \notin R$ and
\[
  \cP = \gen\bigl( (R, P) \bigr)
      \defeq
        \biggl\{\,
          R \vect{\rho} + P \vect{\sigma} \in \Rset^n
        \biggm|
          \vect{\rho} \in \nonnegRset^r,
          \vect{\sigma} \in \nonnegRset^p,
          \sum_{i=1}^p \sigma_i = 1
        \,\biggr\}.
\]
```

### Qwen generó (Lean)
```lean
import Mathlib

variable {n : ℕ}

def IsClosedPolyhedron (S : Set (Fin n → ℝ)) : Prop :=
  ∃ (m : ℕ), ∃ (H : Fin m → (Fin n → ℝ) → ℝ), (∀ i, IsLinear ℝ (H i)) ∧
  S = ⋂ i, {x | H i x ≤ 0}

def genPolyhedron (r p : ℕ) (R : Fin r → Fin n → ℝ) (P : Fin p → Fin n → ℝ) : 
  Set (Fin n → ℝ) :=
  {x | ∃ (ρ : Fin r → ℝ) (σ : Fin p → ℝ), 
    (∀ i, ρ i ≥ 0) ∧ (∀ j, σ j ≥ 0) ∧ (∑ j, σ j = 1) ∧ 
    x = (∑ i, ρ i • R i) + (∑ j, σ j • P j)}

theorem minkowski_weyl_representation (r p : ℕ) (R : Fin r → Fin n → ℝ) 
  (P : Fin p → Fin n → ℝ) (hR : ∀ i, R i ≠ 0) :
  IsClosedPolyhedron (genPolyhedron r p R P) := by
  sorry
```

**Puntos a revisar:**
- `IsClosedPolyhedron` = intersección finita de semiespacios. ✅ Definición estándar.
- `genPolyhedron` = combinaciones cónicas de R + combinaciones convexas de P. ✅ Coincide con `\gen((R,P))`.
- `hR : ∀ i, R i ≠ 0` = "0 ∉ R". ✅
- **Dirección del teorema:** La fuente dice "⇔" (if and only if). Qwen solo da "⇒" (`genPolyhedron → IsClosedPolyhedron`). ⚠️ Falta la dirección ⇐.

**Fidelidad:** [ ] ✅ fiel / [ ] ⚠️ aproximación (falta ⇐) / [ ] ❌ incorrecto

---

## PAPER 10 — math/0504586v2 (control) ✅ NOVEDAD_ENUNCIADO

### Original (LaTeX)
```latex
\label{pr:noncrit}
For any graph $G$ we have
\begin{equation} \left\{ \begin{array}{ccl}
\bPsi_p(\, \calC_t \, \mbox{ occurs for every } \, t \, )=1
  & \mbox{ if } & p>p_c(G)
   \\[1ex]
\bPsi_p\bigl((\neg\, \calC_t) \mbox{ occurs for every } t\bigr)=1
  & \mbox{ if } & p<p_c(G) \, .
\end{array} \right.
\nonumber
\end{equation}
```

### Qwen generó (Lean)
```lean
import Mathlib

open MeasureTheory

def PercolationModel (G : Type*) [SimpleGraph G] [Fintype G] :=
  {ω : G.edgeSet → Bool // True}

def PercolationEvent (G : Type*) [SimpleGraph G] [Fintype G] (t : ℝ) : 
  Set (PercolationModel G) :=
  {ω | True}

def probMeasure (G : Type*) [SimpleGraph G] [Fintype G] (p : ℝ) 
  (hp : 0 ≤ p ∧ p ≤ 1) : 
  MeasureTheory.Measure (PercolationModel G) :=
  MeasureTheory.Measure.dirac ⟨λ _ => false, trivial⟩

theorem noise_sensitivity_percolation (G : Type*) [SimpleGraph G] [Fintype G]
  (p : ℝ) (hp : 0 ≤ p ∧ p ≤ 1) (pc : ℝ) :
  p > pc → (∀ t : ℝ, MeasureTheory.volume {ω | True} = 1) := by
  sorry
```

**Puntos a revisar:**
- `PercolationModel G` = configuraciones de aristas (Bool/arista). ✅ Correcto.
- `PercolationEvent G t` = **`{ω | True}`** ❌ Placeholder — debería ser el evento C_t (cruce a escala t).
- `probMeasure` = **medida de Dirac** ❌ Placeholder — debería ser medida de Bernoulli(p).
- El teorema: `p > pc → (∀ t, volume {ω | True} = 1)` — **trivialmente cierto** (medida del espacio total = 1). ❌ No captura el enunciado.
- La fuente tiene DOS ramas (p > p_c y p < p_c). Qwen solo da UNA (p > p_c). ⚠️

**Fidelidad:** [ ] ⚠️ aproximación severa / [ ] ❌ incorrecto (definiciones placeholder, teorema trivializado)

---

## TABLA FINAL — VEREDICTOS DEL AUTOR

| # | Paper | Rol | Pipeline | Fidelidad LaTeX→Lean | Match D1 | Veredicto final |
|---|-------|-----|----------|:---------------------:|:--------:|-----------------|
| 1 | 1609.02090v1 | ret | NOVEDAD_ENUNCIADO | ✅ Fiel | — | **Fiel.** Omite casos intermedios pero el núcleo del teorema está correcto. El enunciado es muy específico (γ(k) para 4 valores concretos), difícil de encontrar por un pipeline de novedad — entendible que haya pasado como NOVEDAD a pesar de ser un retirado. |
| 2 | 1207.0631v1 | ret | CONOCIDO_LITERATURA | ✅ Fiel | VP indirecto | **Fiel.** Teorema bien formalizado. El pipeline encontró arXiv:1804.02140 (2018), que es posterior al retirado (2012) y cita a Fillmore (1969) de pasada. No es el match ideal (Fillmore directo) pero es un verdadero positivo: el teorema ES conocido. AViD juzga como si fueran nuevos — el pipeline acertó aunque por referencia indirecta. |
| 3 | 1212.0196v1 | ret | NOVEDAD_ENUNCIADO | ✅ Fiel | — | **Fiel.** Traducción correcta. El pipeline no encontró el paper original de Monsky — veredicto NOVEDAD_ENUNCIADO confirmed. |
| 4 | 1004.3381v1 | ret | NOVEDAD_ENUNCIADO | ✅ Fiel | — | **Fiel.** Todas las definiciones geométricas (Rectangle, rectsDisjoint, AxisParallelLine, isIndependentSet) correctas. |
| 5 | math/0604362v1 | ret | FORMALIZATION_FAILED | — | — | Fallo de compilación (IsIrreducible duplicado, Complex.abs no encontrado). Dato sobre Qwen. |
| 6 | 1501.01654v1 | ctrl | FORMALIZATION_FAILED | — | — | API timeout (enunciado extremadamente largo). Ruido de infraestructura. |
| 7 | 1101.3431v2 | ctrl | FORMALIZATION_FAILED | — | — | API timeout. Ruido de infraestructura. |
| 8 | 1101.3720v1 | ctrl | NOVEDAD_ENUNCIADO | ❌ Incorrecto | — | **Mal traducido.** `theta := sorry` en una definición es inaceptable — la función θ_m es el corazón del paper. El teorema está enunciado pero la definición central es un placeholder. |
| 9 | 0904.1783v3 | ctrl | NOVEDAD_ENUNCIADO | ⚠️ Aproximación | — | **Falta la dirección ⇐.** Qwen solo prueba ⇒ (genPolyhedron → IsClosedPolyhedron). El teorema original es una equivalencia (⇔). |
| 10 | math/0504586v2 | ctrl | NOVEDAD_ENUNCIADO | ❌ Incorrecto | — | **Pésimo.** Definiciones placeholder (probMeasure = Dirac, PercolationEvent = {ω\|True}). El teorema enunciado es trivialmente cierto (volume del espacio total = 1). No captura la sustancia del enunciado original. |

## Notas sobre los fallos

Los 3 papers sin formalizar no son iguales:
- **Paper 5**: fallo de COMPILACIÓN — Qwen generó código con error de nombre (`IsIrreducible` duplicado, `Complex.abs` no encontrado). Es un dato sobre la capacidad del modelo.
- **Papers 6 y 7**: fallo de API TIMEOUT — los enunciados son extremadamente largos (4 niveles de casos anidados) y exceden el límite efectivo de Qwen vía OpenCode. Es ruido de infraestructura, no dice nada sobre el modelo.
