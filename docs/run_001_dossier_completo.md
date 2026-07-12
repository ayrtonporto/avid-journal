# Run 001 — Expediente completo para revisión

**Generado:** 2026-07-12  
**Propósito:** Toda la evidencia reunida en un solo documento para que el usuario pueda juzgar con contexto completo antes de corregir el YAML y autorizar FASE 1.  
**Fuentes:** YAML, LaTeX cacheado, dossier de selección, reporte de Run 001 anterior, review manual previa, statement_verification.md.

---

## Paper 1 — 1609.02090v1 (Waring's problem for Z_n)

### 📋 Metadata

| Campo | Valor |
|-------|-------|
| arXiv ID | [1609.02090v1](https://arxiv.org/abs/1609.02090v1) |
| Autores | David Covert, Alex Iosevich, Jonathan Pakianathan |
| Categoría | math.NT |
| Año | 2016 |
| Withdrawal comment | "Paper withdrawn as main results are not original. Main results originally proved in 'Some Problems of Partitio Numerorum (VIII)' by G.H. Hardy and J.E. Littlewood." |
| Known duplicator | Hardy & Littlewood, Partitio Numerorum (VIII) |
| Tamaño fuente | 62 KB, 770 líneas, 20 theorem envs |

### 📐 Enunciado — tres fuentes

**Fuente LaTeX** (`WaringZn.tex`, líneas 105-107):
```latex
\begin{theorem} \label{SquaresZn}
$\mathbb{Z}_n \subset 2R_2$ if and only if $n$ satisfies the condition 
that when $p^2 \mid n$, then $p \equiv 1 \pmod{4}$.
\end{theorem}
```

**Dossier** (línea 384):
```latex
\label{SquaresZn} $\mathbb{Z}_n \subset 2R_2$ if and only if $n$ satisfies 
the condition that when $p^2 \mid n$, then $p \equiv 1 \pmod{4}$.
```

**YAML actual** (`config/experiment_run_001.yaml`, líneas 10-18):
```latex
\label{SquaresZn}
$\mathbb{Z}_n \subset 2R_2$ if and only if $n$ satisfies the condition
that when $p^2 \mid n$, then $p \equiv 1 \pmod{4}$ for every odd prime $p$,
and $n \not\equiv 0 \pmod{16}$.
```

> ⚠️ **Divergencia:** YAML agrega "for every odd prime $p$" (redundante) y "and $n \not\equiv 0 \pmod{16}$" (ausente en la fuente). El fragmento sobre mod 16 aparece en la discusión posterior del paper (línea 108: "if 8|n, then four squares are necessary") pero no en el teorema.

### 📝 Definiciones relevantes del paper

```
R_k = {x^k : x ∈ Z_n}           (kth power residues modulo n)
hA  = A + A + ... + A           (h-fold sumset)
Z_n ⊂ mR_k                      (todo elemento de Z_n es suma de m k-ésimas potencias)
```

### 🔍 Leandex (D1 formal) — Run 001 anterior

| Match | Score | Fuente |
|-------|-------|--------|
| `Nat.eq_sq_add_sq_iff` | 1.0 | `Mathlib/NumberTheory/SumTwoSquares.lean` |

**Enunciado en Mathlib:**
```lean
theorem Nat.eq_sq_add_sq_iff {n : ℕ} :
    (∃ x y, n = x ^ 2 + y ^ 2) ↔ ∀ q ∈ n.primeFactors, q % 4 = 3 → Even (padicValNat q n)
```

> ⚠️ Este es el teorema clásico de suma de dos cuadrados en **enteros** (Euler), no en Z_n. Es un "pariente cercano" — mismo espíritu, dominio distinto.

### 🔎 TheoremSearch (D1 informal) — top 5

| # | Score | Title | arXiv |
|---|-------|-------|-------|
| 1 | 0.645 | On superspecial abelian varieties over finite fields | [1602.02541](https://arxiv.org/abs/1602.02541) |
| 2 | 0.639 | Some Properties of Overpartitions into Nonmultiples of Two Integers | [2412.18938](https://arxiv.org/abs/2412.18938) |
| 3 | 0.637 | **Representing Integers as the Sum of Two Squares in the Ring Z_n** | [**1404.0187**](https://arxiv.org/abs/1404.0187) |
| 4 | 0.630 | Cliques of orders three and four in the Paley-type graphs | [2301.07021](https://arxiv.org/abs/2301.07021) |
| 5 | 0.627 | On a Paley-type graph on Z_n | [2012.09735](https://arxiv.org/abs/2012.09735) |

### 🎯 Prior art: arXiv:1404.0187 (Harrington, Jones, Lamarche, 2014)

**Theorem 5** (caracterización de Z_n como suma de dos cuadrados — solución no trivial):
> n ≢ 0 (mod q²) para q≡3(mod 4), n ≢ 0 (mod 4), n ≡ 0 (mod p) para algún p≡1(mod 4), + condiciones sobre potencias de 5.

**Theorem 6** (con x, y nonzero squares):
> n ≢ 0 (mod q²) para q≡3(mod 4), n ≢ 0 (mod 4).

**Comparación con 1609.02090:** El Theorem 6 de 1404.0187 es el análogo más cercano. La condición "p²|n ⇒ p≡1(mod 4)" de 1609.02090 es equivalente a "n ≢ 0 (mod q²) para q≡3(mod 4)". Pero 1404.0187 agrega "n ≢ 0 (mod 4)" que 1609.02090 no incluye en el teorema (aunque el paper sí menciona que 8|n es un caso especial en la discusión).

### 🏗️ Traducción Lean (Run 001 anterior)

**Estado:** ✅ Compiló en 24s (attempt 1).  
**Código:** ⚠️ NO GUARDADO (el pipeline borra el archivo temporal tras compilar).

### 📊 Veredicto Run 001 anterior

`MATCH_ENCONTRADO_PENDIENTE_D3` — D2=False, D3 pendiente.

---

## Paper 2 — 1207.0631v1 (Diagonal of matrices)

### 📋 Metadata

| Campo | Valor |
|-------|-------|
| arXiv ID | [1207.0631v1](https://arxiv.org/abs/1207.0631v1) |
| Autor | Clément de Seguins Pazzis |
| Categoría | math.RA |
| Año | 2012 |
| Withdrawal comment | "withdrawn since the result has already been published with a similar proof" |
| Known duplicator | Fillmore (1969), Gibson (1975) |
| Tamaño fuente | 9.3 KB, 270 líneas, 1 lemma + 3 theorems |

### 📐 Enunciado — tres fuentes

**Fuente LaTeX — Lemma clave** (`diagonalarxiv.tex`, líneas 173-181):
```latex
\begin{lemma}\label{keylemma}
Assume $n \geq 2$.
Let $A \in \Mat_n(\K)$ be a non-scalar matrix, and let $a \in \K$.
Then there exists $B \in \Mat_{n-1}(\K)$, which may be chosen non-scalar 
if $n \geq 3$, such that
$$A \simeq \begin{bmatrix}
a & [?]_{1 \times (n-1)} \\
[?]_{(n-1) \times 1} & B
\end{bmatrix}.$$
\end{lemma}
```

**Fuente LaTeX — Theorem 3 (resultado principal)** (`diagonalarxiv.tex`, líneas 162-169):
```latex
\begin{theo}\label{maintheo}
Let $A$ be a non-scalar matrix of $\Mat_n(\K)$, and $c_1,\dots,c_n$ be scalars.
Then the following conditions are equivalent:
(i) $c_1+\cdots+c_n=\tr A$;
(ii) $A$ is similar to a matrix with diagonal entries $c_1,\dots,c_n$.
\end{theo}
```

**Dossier** (línea 704) — extrae el Lemma (correcto):
```latex
\label{keylemma} Assume $n \geq 2$. Let $A \in \Mat_n(\K)$ be a non-scalar 
matrix, and let $a \in \K$. Then there exists $B \in \Mat_{n-1}(\K)$...
```

**YAML actual** (`config/experiment_run_001.yaml`, líneas 27-37):
```latex
\label{keylemma}
Assume $n \geq 2$.
Let $A \in \Mat_n(\K)$ be a non-scalar matrix, and let $a \in \K$.
Then there exists a matrix $B \in \Mat_n(\K)$ that is similar to $A$
and whose diagonal equals $(a, \tr(A)-a, 0, \dots, 0)$.
```

> 🔴 **Divergencia crítica:** El YAML tiene `\label{keylemma}` pero el enunciado es el **Theorem 3 (maintheo)** aplicado al caso particular c₁=a, c₂=tr(A)-a, c₃=...=cₙ=0. El Lemma real (keylemma) es un resultado técnico de embedding en forma bloque. El YAML mezcla label de lemma con enunciado de theorem.

### 📝 Teorema del duplicador (Fillmore, 1969)

Del propio paper (lines 154-158), el teorema de Fillmore es:
```latex
\begin{theo}
Let $A$ be a non-scalar matrix of $\Mat_n(\K)$. Then $A$ is similar to 
a matrix with diagonal entries $\tr A,0,\dots,0$.
\end{theo}
```

Fillmore lo probó para ℂ; Gibson lo generalizó a cuerpos arbitrarios. De Seguins Pazzis (paper retirado) lo generaliza a cualquier tupla (c₁,...,cₙ) con suma = tr(A). El paper fue retirado porque esta generalización ya era conocida.

### 🔍 Leandex (D1 formal) — Run 001 anterior

| Match | Score | Fuente |
|-------|-------|--------|
| `Matrix.scalar_apply` | 1.0 | `Mathlib/Data/Matrix/Basic.lean` |

**Enunciado en Mathlib:**
```lean
theorem scalar_apply (a : α) : scalar n a = diagonal fun _ => a := rfl
```

> 🔴 Esto es un lema trivial sobre matrices escalares. NO es el teorema de Fillmore. Score 1.0 sugiere que la formalización produjo algo equivalente a `scalar_apply`, no el teorema real. **Probable false positive por mala formalización.**

### 🔎 TheoremSearch (D1 informal) — top 5

| # | Score | Title | arXiv |
|---|-------|-------|-------|
| 1 | 0.754 | Filmor Theorem for integers | [1704.08037](https://arxiv.org/abs/1704.08037) |
| 2 | 0.737 | Sums and products of square-zero matrices | [1804.02140](https://arxiv.org/abs/1804.02140) |
| 3 | 0.701 | Sums and products of square-zero matrices | [1804.02140](https://arxiv.org/abs/1804.02140) |
| 4 | 0.686 | The Waring Problem for Matrix Algebras, II | [2302.05106](https://arxiv.org/abs/2302.05106) |
| 5 | 0.678 | Matrix evaluations of noncommutative rational functions | [2401.11564](https://arxiv.org/abs/2401.11564) |

### 🏗️ Traducción Lean (Run 001 anterior)

**Estado:** ✅ Compiló en 28s (attempt 1).  
**Código:** ⚠️ NO GUARDADO.

### 📊 Veredicto Run 001 anterior

`MATCH_ENCONTRADO_PENDIENTE_D3`

---

## Paper 3 — 1212.0196v1 (Non-congruent numbers)

### 📋 Metadata

| Campo | Valor |
|-------|-------|
| arXiv ID | [1212.0196v1](https://arxiv.org/abs/1212.0196v1) |
| Autor | Shenxing Zhang |
| Categoría | math.NT |
| Año | 2012 |
| Withdrawal comment | "withdrawn by the author because it is a corollary of a well-known result by Monsky" |
| Known duplicator | Monsky (congruent numbers) |
| Tamaño fuente | 21.3 KB, 366 líneas, 7 theorems/corollaries |

### 📐 Enunciado — tres fuentes

**Fuente LaTeX** (`noncong.tex`, líneas 84-86):
```latex
\begin{cor}\label{cor:main}
Suppose $m=p_1\cdots p_k\ \text{and}\ p_i\equiv 3\pmod 8$. 
If $\leg{p_i}{p_j}=1$ for all $1\leq i<j\leq k$, 
then $m$ is a non-congruent number. 
If moreover $k$ is even, then $2m$ is also a non-congruent number. 
In particular, we can construct an infinite set $S$ of $\equiv3\pmod 8$ primes, 
such that the product of any finite primes in $S$ is an non-congruent number.
\end{cor}
```

**Dossier** (línea 292) — idéntico a la fuente.

**YAML actual** (`config/experiment_run_001.yaml`, líneas 46-53):
```latex
\label{cor:main}
Suppose $m=p_1\cdots p_k$ and $p_i\equiv 3\pmod 8$.
If $\leg{p_i}{p_j}=1$ for all $1\leq i<j\leq k$,
then $m$ is a non-congruent number.
```

> 🟡 **Divergencia baja:** Trunca la parte sobre 2m y el conjunto S. El núcleo (m es non-congruent) está correcto.

### 📝 Definiciones relevantes

```
Legendre symbol: \leg{a}{p}
\Leg{a}{n} = ½(1 - \leg{a}{n})   (additive homomorphism to F₂)
E: y² = x³ - n²x                  (congruent number elliptic curve)
Sha(E/Q)                          (Tate-Shafarevich group)
```

### 🔍 Leandex (D1 formal) — Run 001 anterior

| Match | Score | Fuente |
|-------|-------|--------|
| `CongruentNumber.not_congruentNumber_1` | 1.0 | `Mathlib/NumberTheory/CongruentNumber.lean` |

**Enunciado en Mathlib:**
```lean
theorem not_congruentNumber_1 : ¬ congruentNumber 1
```

> ⚠️ "1 no es un número congruente" (Fermat, por descenso infinito). Es un caso base del problema de números congruentes, no el teorema del paper sobre productos de primos ≡3 mod 8. Relacionado pero mucho más débil.

### 🔎 TheoremSearch (D1 informal) — top 5

| # | Score | Title | arXiv |
|---|-------|-------|-------|
| 1 | 0.674 | Congruent Numbers and Heegner Points | [1210.8231](https://arxiv.org/abs/1210.8231) |
| 2 | 0.649 | Generalization of Some Arithmetical Properties of Fermat-Euler Systems | [0910.5704](https://arxiv.org/abs/0910.5704) |
| 3 | 0.647 | The even parity Goldfeld conjecture: congruent number elliptic curves | [2104.06732](https://arxiv.org/abs/2104.06732) |
| 4 | 0.635 | A New Generalization of Fermat's Last Theorem | [1310.0897](https://arxiv.org/abs/1310.0897) |

### 🏗️ Traducción Lean (Run 001 anterior)

**Estado:** ✅ Compiló en 31s (attempt 1).  
**Código:** ⚠️ NO GUARDADO.

### 📊 Veredicto Run 001 anterior

`MATCH_ENCONTRADO_PENDIENTE_D3`

---

## Paper 4 — 1004.3381v1 (Rectangle slicing)

### 📋 Metadata

| Campo | Valor |
|-------|-------|
| arXiv ID | [1004.3381v1](https://arxiv.org/abs/1004.3381v1) |
| Autor | Daniel Werner |
| Categoría | cs.CG |
| Año | 2010 |
| Withdrawal comment | "Withdrawn, because most results were already known. T_d(m) exists was first proved by Gyárfás and Lehel in 1970." |
| Known duplicator | Gyárfás & Lehel (1970) — d-separated interval piercing |
| Tamaño fuente | 5.7 KB, 83 líneas |

### 📐 Enunciado — tres fuentes

**Fuente LaTeX** (`stab.tex`, líneas 36-38):
```latex
\begin{lemma} Let $R$ be a set of rectangles such that the largest independent 
set is of size $m$, then the rectangles can be sliced by 
$f(m) \leq c\cdot(2m+1)^2$ axis-parallel lines.
\end{lemma}
```

**Dossier** (línea 659) — idéntico a la fuente.

**YAML actual** (`config/experiment_run_001.yaml`, líneas 59-67):
```latex
Let $R$ be a set of rectangles such that the largest independent set
is of size $m$, then the rectangles can be sliced by at most
$O(m \log m)$ lines.
```

> 🔴 **Divergencia crítica:** La cota real es O(m²) (cuadrática). El YAML dice O(m log m). La frase "O(m log m)" no aparece en ninguna parte del paper. Además omite "axis-parallel" (líneas paralelas a los ejes).

### 📝 Definiciones relevantes

```
Rectangles independent: both x- and y-projections are disjoint
f(m) = minimal number of axis-parallel lines to slice all rectangles in any set 
       with max independent set of size m
```

### 🔍 Leandex (D1 formal) — Run 001 anterior

| Match | Score | Fuente |
|-------|-------|--------|
| `Green85.green_85` | 1.0 | `Archive/` o `Counterexamples/` |

**Enunciado en Mathlib:**
```lean
theorem green_85 : answer(sorry) ↔ ∃ c > 0, ∀ A : Set (ℝ × ℝ), 
    IsOpen A → A ⊆ Icc 0 1 ×ˢ Icc 0 1 → ...
```

> 🔴 Esto es un **problema abierto** (Green's conjecture on rectangles), no el resultado de slicing/piercing del paper. La formalización probablemente fue incorrecta.

### 🔎 TheoremSearch (D1 informal) — top 5

| # | Score | Title | arXiv |
|---|-------|-------|-------|
| 1 | 0.764 | An Erdős--Hajnal analogue for permutation classes | [1511.01076](https://arxiv.org/abs/1511.01076) |
| 2 | 0.739 | Permutation classes | [1409.5159](https://arxiv.org/abs/1409.5159) |
| 3 | 0.715 | Well-Quasi-Order for Permutation Graphs Omitting a Path and a Clique | [1312.5907](https://arxiv.org/abs/1312.5907) |
| 4 | 0.675 | Independent sets and hitting sets of bicolored rectangular families | [1411.2311](https://arxiv.org/abs/1411.2311) |
| 5 | 0.645 | Independent and Hitting Sets of Rectangles Intersecting a Diagonal Line | [1309.6659](https://arxiv.org/abs/1309.6659) |

### 🏗️ Traducción Lean (Run 001 anterior)

**Estado:** ✅ Compiló en 35s (attempt 1).  
**Código:** ⚠️ NO GUARDADO.

### 📊 Veredicto Run 001 anterior

`MATCH_ENCONTRADO_PENDIENTE_D3`

---

## Paper 5 — math/0604362v1 (Markov chain eigenvalues) ⚠️ CRÍTICO

### 📋 Metadata

| Campo | Valor |
|-------|-------|
| arXiv ID | [math/0604362v1](https://arxiv.org/abs/math/0604362v1) |
| Autor | Ravi Montenegro |
| Categoría | math.PR |
| Año | 2006 |
| Withdrawal comment | "withdrawn because I have been made aware that the result was previously known" |
| Known duplicator | Desconocido — posiblemente LPW (Levin-Peres-Wilmer, "Markov Chains and Mixing Times") |
| Tamaño fuente | 68.8 KB, 1147 líneas, 19 theorems |

### 📐 Enunciado — tres fuentes (CASO CRÍTICO)

**Fuente LaTeX** (`cheeger.tex`, líneas 141-147):
```latex
\begin{theorem} \label{thm:spectral_lowerbound}
The eigenvalues $\lambda_i\neq 1$ of a finite, irreducible Markov chain satisfy
$$d(n) \geq \frac 12\,|\lambda_i|^n \quad\textrm{and}\quad
d(t) \geq \frac 12\,e^{-(1-\Ree\lambda_i)t}\,.$$
\end{theorem}
```

**Dossier** (línea 1141) — ✅ Correcto (coincide con fuente):
```latex
\label{thm:spectral_lowerbound} The eigenvalues $\lambda_i\neq 1$ of a finite, 
irreducible Markov chain satisfy 
$$ d(n) \geq \frac 12\,|\lambda_i|^n \quad\textrm{and}\quad 
d(t) \geq \frac 12\,e^{-(1-\Ree\lambda_i)t}\,. $$
```

**YAML actual** (`config/experiment_run_001.yaml`, líneas 77-85) — 🔴 CORRUPTO:
```latex
\label{thm:spectral_lowerbound}
The eigenvalues $\lambda_i\neq 1$ of a finite, irreducible Markov chain satisfy
$$d(n) \le \max_{i\ge 2} |\lambda_i|$$
where $d(n)$ is the total variation distance.
```

> 🔴🔴🔴 **CORRUPCIÓN TOTAL:**
> - Desigualdad INVERTIDA: ≤ en vez de ≥
> - Falta el exponente n: |λ_i| en vez de |λ_i|ⁿ
> - Falta el factor ½
> - max_{i≥2} no existe en el teorema real (vale ∀i con λ_i≠1)
> - Falta la segunda parte (cota en tiempo continuo)
> - Agrega "where d(n) is the total variation distance" (que en el paper se define antes, no en el teorema)

### 📝 La cadena de teoremas del paper

El paper tiene una estructura de resultados encadenados. El Theorem 1 (thm:spectral_lowerbound) es solo el primer eslabón:

1. **Theorem 1** (spectral_lowerbound): cota inferior de mixing time vía eigenvalues — `d(n) ≥ ½|λ_i|ⁿ`
2. **Theorem 2** (complex-eigenvalues): relación entre eigenvalues de cadenas no reversibles y reversibilizaciones — `1-Re(λ_i) ≥ λ`, `1-|λ_i| ≥ λ_{PP*}/2`
3. **Theorem 3** (main_convex): cota de variación vía evolving sets
4. **Theorem 4** (cheeger): Generalized Cheeger Inequality — `|λ_i| ≤ C_f`
5. Corolarios sobre edge-expansion, vertex-expansion, y combinaciones

El YAML contiene una paráfrasis incorrecta que no corresponde a ningún teorema del paper.

### 📖 Posible duplicador: LPW (Levin-Peres-Wilmer)

El libro "Markov Chains and Mixing Times" (Levin, Peres, Wilmer, 2009, 2nd ed. 2017) es la referencia canónica. El Capítulo 12 (Eigenvalues and eigenfunctions) contiene cotas espectrales relacionadas. En particular, la relación `d(n) ≥ ½|λ_i|ⁿ` para cadenas reversibles es un resultado clásico (Lemma 12.6 en LPW). Montenegro lo extiende a cadenas no reversibles.

### 🔍 Leandex (D1 formal) — Run 001 anterior

| Match | Score | Fuente |
|-------|-------|--------|
| `eVariationOn.sum_le` | 1.0 | `Mathlib/Analysis/BoundedVariation.lean` |

**Enunciado en Mathlib:**
```lean
theorem sum_le {f : α → E} {s : Set α} {n : ℕ} {u : ℕ → α} 
    (hu : Monotone u) (us : ∀ i, u i ∈ s) :
    (∑ i ∈ Finset.range n, edist (f (u (i + 1))) (f (u i))) ≤ eVariationOn f s
```

> 🔴 Esto es un lema de bounded variation en análisis, no de cadenas de Markov. La formalización fue claramente incorrecta.

### 🔎 TheoremSearch (D1 informal) — top 5

| # | Score | Title | arXiv |
|---|-------|-------|-------|
| 1 | 0.756 | Rapid mixing from spectral independence beyond the Boolean domain | [2007.08091](https://arxiv.org/abs/2007.08091) |
| 2 | 0.745 | Shuffling via Transpositions | [2504.07918](https://arxiv.org/abs/2504.07918) |
| 3 | 0.739 | Cutoff for a One-sided Transposition Shuffle | [1907.12074](https://arxiv.org/abs/1907.12074) |
| 4 | 0.737 | Topics in Markov chains: mixing and escape rate | [1506.04850](https://arxiv.org/abs/1506.04850) |
| 5 | 0.729 | The Spectral Gap of Sparse Random Digraphs | [1708.00530](https://arxiv.org/abs/1708.00530) |

### 🏗️ Traducción Lean (Run 001 anterior)

**Estado:** ✅ Compiló en 34s (attempt 1).  
**Código:** ⚠️ NO GUARDADO.

### 📊 Veredicto Run 001 anterior

`MATCH_ENCONTRADO_PENDIENTE_D3`

---

## Planilla resumen para completar

| # | Paper | Enunciado YAML correcto? | Traducción fiel? | Match Leandex real? | ¿Duplicador en D1? | Veredicto esperado |
|---|-------|------------------------|-------------------|---------------------|---------------------|---------------------|
| 1 | 1609.02090v1 | ⚠️ Agrega mod 16 | ❓ Código perdido | ⚠️ `eq_sq_add_sq_iff` (pariente) | ❓ 1404.0187 en pos #3 | |
| 2 | 1207.0631v1 | 🔴 Label≠enunciado | ❓ Código perdido | 🔴 `scalar_apply` (falso) | ❓ "Filmor Theorem" en pos #1 | |
| 3 | 1212.0196v1 | 🟡 Trunca 2m | ❓ Código perdido | ⚠️ `not_congruentNumber_1` (débil) | ❓ | |
| 4 | 1004.3381v1 | 🔴 O(m log m)≠O(m²) | ❓ Código perdido | 🔴 `green_85` (falso) | ❓ | |
| 5 | math/0604362v1 | 🔴🔴🔴 Totalmente corrupto | ❓ Código perdido | 🔴 `sum_le` (falso) | ❓ LPW? | |

---

## Próximos pasos

1. **Corregir YAML** (`config/experiment_run_001.yaml`): mínimo Paper 5, idealmente todos.
2. **Confirmar** explícitamente para pasar a FASE 1.
3. **FASE 1:** Re-ejecutar `run_experiment_001.py` con enunciados corregidos + `--save-lean` para no perder el código.
4. **FASE 2:** Controles (tras segunda confirmación).
