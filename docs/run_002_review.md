# Run 002 — Auxiliar de Revisión Final

**Propósito:** Todo lo que necesitás para sentenciar los 7 papers formalizados.  
**Instrucción:** Revisar definiciones auxiliares (no el teorema en sí). Marcar ✅ fiel / ⚠️ aproximación / ❌ incorrecto.

---

## PAPER 1 — 1609.02090v1 (retracted) ✅ NOVEDAD_ENUNCIADO

**Teorema (fuente):** Z_n cubierto por 15 cuárticas, 9 séxticas, 32 ócticas, 12 décicas + casos intermedios de cuárticas (5R_4 iff 8∤n, 7R_4 iff 16∤n).

**Código Lean (1046 bytes):**
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

**Definiciones a revisar:**
- `powers n k` = conjunto de k-ésimas potencias en ZMod n. **¿Es la definición estándar?** ✅ Sí: `{x | ∃ y, x = y^k}`.
- `sumset S m` = m-fold sumset (suma de m elementos de S). **¿Correcto?** ✅ Sí, usa Fin m y suma finita.
- **Faltan:** los casos intermedios de cuárticas (5R_4 iff 8∤n, 7R_4 iff 16∤n) — Qwen los omitió.

**Tu veredicto de fidelidad:** [ ] ✅ fiel / [ ] ⚠️ aproximación (faltan casos intermedios) / [ ] ❌ incorrecto

---

## PAPER 2 — 1207.0631v1 (retracted) ✅ CONOCIDO_LITERATURA

**Teorema (fuente):** Matriz A no escalar: Σc_i = tr(A) ↔ A es similar a matriz con diagonal (c_1,...,c_n). Teorema de Fillmore (1969).

**Código Lean (343 bytes):**
```lean
import Mathlib

theorem matrix_diagonal_similarity_equivalence {n : ℕ} {K : Type*} [Field K] 
  (A : Matrix (Fin n) (Fin n) K) 
  (hA : ¬ ∃ (k : K), A = k • 1) (c : Fin n → K) :
  (∑ i, c i = Matrix.trace A) ↔ 
  (∃ B : Matrix (Fin n) (Fin n) K, (∀ i, B i i = c i) ∧ Matrix.IsSimilar A B) := by
  sorry
```

**Definiciones a revisar:**
- No hay definiciones auxiliares — el teorema va directo.
- `hA : ¬ ∃ (k : K), A = k • 1` = "A no es escalar". **¿Correcto?** ✅ Sí.
- `Matrix.IsSimilar A B` = ¿existe en Mathlib? Verificar: `Matrix.IsSimilar` está en `Mathlib/LinearAlgebra/Matrix/Similar`. ✅

**🎯 CASO ESTRELLA — D1 match:**
- **Paper matcheado:** arXiv:1804.02140 — "Sums and products of square-zero matrices" (2018)
- **Similitud:** 0.706
- **Juez LLM:** "equivalent" (confidence 0.95)
- **Razonamiento:** "Both statements assert the same condition for similarity to a matrix with a given diagonal: the sum of diagonal entries must equal the trace of the matrix, for any non-scalar matrix over a field."

**Análisis:** El match NO es Fillmore (1969) directo, es un paper de 2018 que enuncia el mismo teorema. ¿Es un verdadero positivo? **Sí** — el teorema ES conocido en la literatura. El pipeline lo detectó correctamente aunque por una referencia indirecta (no la canónica). Para el paper, esto cuenta como: "D1 CI encontró un enunciado equivalente en la literatura (arXiv:1804.02140), confirmando que el resultado era conocido."

**Tu veredicto de fidelidad:** [ ] ✅ fiel / [ ] ⚠️ / [ ] ❌  
**Tu veredicto del match:** [ ] Verdadero positivo (es el teorema de Fillmore) / [ ] Match correcto pero referencia indirecta / [ ] Falso positivo

---

## PAPER 3 — 1212.0196v1 (retracted) ✅ NOVEDAD_ENUNCIADO

**Teorema (fuente):** m = ∏ p_i con p_i ≡ 3 mod 8, Legendre symbols = 1 ⇒ m no es número congruente.

**Código Lean (438 bytes):**
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

**Definiciones a revisar:**
- `IsCongruentNumber n` = ∃ triángulo rectángulo racional con área n. **¿Correcto?** ✅ La definición estándar es exactamente esta: ∃ a,b,c ∈ ℚ⁺, a²+b²=c², ab/2 = n.
- `jacobiSym` = símbolo de Jacobi. **¿Está en Mathlib?** Sí, `jacobiSym` en `NumberTheory/LegendreSymbol/JacobiSymbol`. ✅

**Tu veredicto de fidelidad:** [ ] ✅ fiel / [ ] ⚠️ / [ ] ❌

---

## PAPER 4 — 1004.3381v1 (retracted) ✅ NOVEDAD_ENUNCIADO (recuperado)

**Teorema (fuente):** Conjunto de rectángulos con largest independent set de tamaño m ⇒ se pueden cortar con ≤ c·(2m+1)² líneas axis-parallel.

**Código Lean (1224 bytes):**
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

**Definiciones a revisar:**
- `Rectangle` con `x1 < x2, y1 < y2`. **¿Correcto?** ✅ Rectangle no degenerado (lados positivos).
- `rectsDisjoint` = disjuntos si uno está completamente a la derecha/izquierda/arriba/abajo del otro. **¿Correcto?** ✅ Definición estándar de rectángulos axis-aligned disjuntos.
- `AxisParallelLine` = línea vertical u horizontal. **¿Correcto?** ✅ Inductivo con vertical y horizontal.
- `lineIntersectsRect` = la línea cruza el rectángulo. **¿Correcto?** ✅ Para vertical: x entre x1 y x2; para horizontal: y entre y1 y y2.
- `isIndependentSet` = conjunto donde todo par es disjunto. **¿Correcto?** ✅ Definición estándar de conjunto independiente en geometría.

**Tu veredicto de fidelidad:** [ ] ✅ fiel / [ ] ⚠️ / [ ] ❌

---

## PAPER 8 — 1101.3720v1 (control) ✅ NOVEDAD_ENUNCIADO (recuperado)

**Teorema (fuente):** B_ε(N) = {binary m < N: θ_m < m^{1/2+ε}}. Cotas asintóticas: Ω(N^{1/2}) para ε<1/2, O(N^{1/2+ε}) para ε<1/6, O(N/log²N) para ε<1/2.

**Código Lean (947 bytes):**
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

**Definiciones a revisar:**
- `theta m` = **¿definida?** ❌ Está como `:= sorry` — Qwen dejó la definición de la función θ sin especificar. La función θ_m (medida de equisdistribución de los primeros m dígitos binarios) es el corazón del paper original.
- `B ε N` = {m < N : θ_m < m^{1/2+ε}}. **¿Correcto?** ✅ La definición es correcta, pero depende de `theta` que está sin definir.
- Las cotas asintóticas están correctamente expresadas como `∀ ε > 0, ε < umbral → ∃ C N₀, ∀ N ≥ N₀, |B| ⋚ C · f(N)`.

**⚠️ ALERTA:** `theta` está sin definir. Esto es un placeholder. El teorema está enunciado correctamente pero la definición central falta. ¿Es aceptable para statement-only? Depende de tu criterio — el enunciado del teorema es correcto pero la definición auxiliar es un agujero.

**Tu veredicto de fidelidad:** [ ] ✅ fiel (statement-only: el teorema está bien, la def es aceptable) / [ ] ⚠️ aproximación (theta sin definir) / [ ] ❌ incorrecto

---

## PAPER 9 — 0904.1783v3 (control) ✅ NOVEDAD_ENUNCIADO

**Teorema (fuente):** P es poliedro cerrado ⇔ ∃ R, P finitos, 0 ∉ R: P = {Rρ + Pσ | ρ≥0, σ≥0, Σσ_i=1}.

**Código Lean (1281 bytes):**
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

**Definiciones a revisar:**
- `IsClosedPolyhedron` = intersección finita de semiespacios cerrados (H_i(x) ≤ 0). **¿Correcto?** ✅ Definición estándar de poliedro (Minkowski-Weyl: equivalentemente, conjunto de combinaciones convexas de P más combinaciones cónicas de R).
- `genPolyhedron` = generado por rayos R y puntos P. **¿Correcto?** ✅ ρ_i ≥ 0 (rayos), σ_j ≥ 0, Σσ_j = 1 (combinación convexa de puntos). La suma ponderada es `∑ρ_i·R_i + ∑σ_j·P_j`.
- `hR : ∀ i, R i ≠ 0` = **¿Coincide con "0 ∉ R"?** ✅ Sí, todos los rayos son no nulos.
- **Dirección del teorema:** Qwen enuncia `IsClosedPolyhedron (genPolyhedron ...)` = "el conjunto generado es un poliedro cerrado". La fuente dice la equivalencia completa (⇔). Qwen da solo una dirección (⇒). **¿Es aceptable?** Depende de tu criterio.

**Tu veredicto de fidelidad:** [ ] ✅ fiel / [ ] ⚠️ aproximación (falta la dirección ⇐) / [ ] ❌ incorrecto

---

## PAPER 10 — math/0504586v2 (control) ✅ NOVEDAD_ENUNCIADO

**Teorema (fuente):** Para cualquier grafo G: Ψ_p(C_t occurs for every t)=1 si p>p_c, y Ψ_p(¬C_t occurs for every t)=1 si p<p_c. Noise sensitivity de percolación crítica.

**Código Lean (1285 bytes):**
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

**Definiciones a revisar:**
- `PercolationModel G` = espacio de configuraciones de aristas (Bool por arista). **¿Correcto?** ✅ La definición de percolación de aristas: cada arista está abierta (true) o cerrada (false).
- `PercolationEvent G t` = placeholder (`{ω | True}` = todo el espacio). **⚠️** Qwen no definió C_t (el evento de cruce a escala t). La definición real de C_t es compleja (existencia de camino abierto que cruza una caja de lado t).
- `probMeasure` = placeholder (medida de Dirac en la configuración toda cerrada). **❌** Esto no es una medida de percolación Bernoulli(p). La medida real es ∏_e p^{ω_e} (1-p)^{1-ω_e}.
- El `theorem` mismo es un placeholder: `∀ t, volume {ω | True} = 1` es trivialmente cierto (la medida del espacio total es 1).

**⚠️ ALERTA:** Este es el caso más grave de placeholder. Ni la medida ni los eventos están correctamente definidos. El teorema enunciado es trivial. Qwen no logró capturar la sustancia del enunciado.

**Tu veredicto de fidelidad:** [ ] ⚠️ aproximación severa / [ ] ❌ incorrecto (definiciones placeholder, teorema trivializado)

---

## TABLA FINAL — Para tu sentencia

| # | Paper | Rol | Pipeline | Defs correctas? | Match D1 correcto? | Tu veredicto final |
|---|-------|-----|----------|:---------------:|:------------------:|-------------------|
| 1 | 1609.02090v1 | retracted | NOVEDAD_ENUNCIADO | [ ] ✅ [ ] ⚠️ [ ] ❌ | — | |
| 2 | 1207.0631v1 | retracted | CONOCIDO_LITERATURA | [ ] ✅ [ ] ⚠️ [ ] ❌ | [ ] VP [ ] Indirecto | |
| 3 | 1212.0196v1 | retracted | NOVEDAD_ENUNCIADO | [ ] ✅ [ ] ⚠️ [ ] ❌ | — | |
| 4 | 1004.3381v1 | retracted | NOVEDAD_ENUNCIADO | [ ] ✅ [ ] ⚠️ [ ] ❌ | — | |
| 5 | math/0604362v1 | retracted | FORMALIZATION_FAILED | — | — | — |
| 6 | 1501.01654v1 | control | FORMALIZATION_FAILED | — | — | — |
| 7 | 1101.3431v2 | control | FORMALIZATION_FAILED | — | — | — |
| 8 | 1101.3720v1 | control | NOVEDAD_ENUNCIADO | [ ] ✅ [ ] ⚠️ [ ] ❌ | — | |
| 9 | 0904.1783v3 | control | NOVEDAD_ENUNCIADO | [ ] ✅ [ ] ⚠️ [ ] ❌ | — | |
| 10 | math/0504586v2 | control | NOVEDAD_ENUNCIADO | [ ] ✅ [ ] ⚠️ [ ] ❌ | — | |

**Nota sobre los 3 fallos:**
- Paper 5 (math/0604362v1): **Fallo de COMPILACIÓN** — `IsIrreducible already declared`, `Complex.abs unknown`. Dato sobre Qwen (generó código con errores de nombre).
- Papers 6-7 (1501.01654v1, 1101.3431v2): **Fallo de API TIMEOUT** — enunciados extremadamente largos (4 niveles de casos anidados) exceden límite efectivo de Qwen. Ruido de infraestructura, no dice nada del modelo.

---

## Lo que yo puedo afirmar con seguridad

| Afirmación | Confianza |
|-----------|:---------:|
| Paper 1: `powers` y `sumset` son definiciones correctas | ✅ Alta |
| Paper 2: `¬∃k, A=k·1` es "no escalar" correcto | ✅ Alta |
| Paper 2: D1 match NO es Fillmore directo, es arXiv:1804.02140 | ✅ Certeza |
| Paper 3: `IsCongruentNumber` es la definición estándar | ✅ Alta |
| Paper 4: Todas las definiciones geométricas son correctas | ✅ Alta |
| Paper 8: `theta` está sin definir (placeholder) | ✅ Certeza |
| Paper 9: Solo da una dirección del teorema (⇒, falta ⇐) | ✅ Certeza |
| Paper 10: Definiciones placeholder, teorema trivializado | ✅ Certeza |

**Lo que requiere tu ojo matemático:**
- Paper 1: ¿La omisión de los casos intermedios (5R_4, 7R_4) invalida el enunciado?
- Paper 3: ¿`(1/2 : ℚ)*a*b = (n : ℚ)` es exactamente área = n para triángulo racional? (Sí, pero verificá)
- Paper 4: ¿`x1 < x2` vs `x1 ≤ x2` para rectángulos? (Qwen usó `<`, la fuente no especifica)
- Paper 9: ¿La dirección única es suficiente o necesitás la equivalencia?
- Paper 10: ¿Esto cuenta como formalización o es placeholder total?
