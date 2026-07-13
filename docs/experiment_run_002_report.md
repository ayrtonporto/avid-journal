# Experiment Run 001 — Report

**Config:** `config/experiment_run_001.yaml`  
**Entries processed:** 10  
**Generated:** 2026-07-13 16:41 UTC-3

## Summary

| arXiv ID | Role | Verdict | D2 trivial? | D3 Jaccard | Formalized? | Duplicator found? |
|----------|------|---------|-------------|------------|-------------|-------------------|
| [1609.02090v1](https://arxiv.org/abs/1609.02090v1) | retracted | NOVEDAD_ENUNCIADO | False |  | ✅ | |
| [1207.0631v1](https://arxiv.org/abs/1207.0631v1) | retracted | CONOCIDO_LITERATURA | False |  | ✅ | |
| [1212.0196v1](https://arxiv.org/abs/1212.0196v1) | retracted | NOVEDAD_ENUNCIADO | False |  | ✅ | |
| [1004.3381v1](https://arxiv.org/abs/1004.3381v1) | retracted | FORMALIZATION_FAILED |  |  | ❌ | |
| [math/0604362v1](https://arxiv.org/abs/math/0604362v1) | retracted | FORMALIZATION_FAILED |  |  | ❌ | |
| [1501.01654v1](https://arxiv.org/abs/1501.01654v1) | control | FORMALIZATION_FAILED |  |  | ❌ | |
| [1101.3431v2](https://arxiv.org/abs/1101.3431v2) | control | FORMALIZATION_FAILED |  |  | ❌ | |
| [1101.3720v1](https://arxiv.org/abs/1101.3720v1) | control | FORMALIZATION_FAILED |  |  | ❌ | |
| [0904.1783v3](https://arxiv.org/abs/0904.1783v3) | control | NOVEDAD_ENUNCIADO | False |  | ✅ | |
| [math/0504586v2](https://arxiv.org/abs/math/0504586v2) | control | NOVEDAD_ENUNCIADO | False |  | ✅ | |

> *Duplicator found? column is for manual verification. Fill after reviewing the evidence below.*

### 1. 1609.02090v1 (retracted)

**Veredicto:** `NOVEDAD_ENUNCIADO`  
**Known duplicator:** Hardy & Littlewood, Partitio Numerorum VIII — γ(4)=15 por método analítico; el retirado lo reproduce con métodos elementales

#### D1 Top-5 (Informal Search)

| # | Score | Title | arXiv ID | Source |
|---|-------|-------|----------|--------|
| 1 | 0.641 | The Clifford-cyclotomic group and Euler-Poincaré characteristics | [1903.09497](https://arxiv.org/abs/1903.09497) | theoremsearch |
| 2 | 0.629 | A periodic approach to plane partition congruences | [1507.02260](https://arxiv.org/abs/1507.02260) | theoremsearch |
| 3 | 0.620 | Spinor representations of positive definite ternary quadratic forms | [1611.06116](https://arxiv.org/abs/1611.06116) | theoremsearch |
| 4 | 0.618 | On the minimum weights of binary linear complementary dual codes | [1807.03525](https://arxiv.org/abs/1807.03525) | theoremsearch |
| 5 | 0.617 | An Elementary Proof of the Minimal Euclidean Function on the Gaussian Integers | [2205.14043](https://arxiv.org/abs/2205.14043) | theoremsearch |

**D2 (triviality):** `False`

**🔍 Did D1 find the known duplicator?** — *manual check needed*
> Known: Hardy & Littlewood, Partitio Numerorum VIII — γ(4)=15 por método analítico; el retirado lo reproduce con métodos elementales
> Top D1 result: see above. Do they match?

---

### 2. 1207.0631v1 (retracted)

**Veredicto:** `CONOCIDO_LITERATURA`  
**Known duplicator:** Result already published with similar proof (Fillmore, 1969?)

**Formalization errors:** Compilation timed out (300s) (attempt 1)

#### D1 Top-5 (Informal Search)

| # | Score | Title | arXiv ID | Source |
|---|-------|-------|----------|--------|
| 1 | 0.793 | Sums and products of square-zero matrices | [1804.02140](https://arxiv.org/abs/1804.02140) | theoremsearch |
| 2 | 0.756 | Filmor Theorem for integers | [1704.08037](https://arxiv.org/abs/1704.08037) | theoremsearch |
| 3 | 0.694 | Filmor Theorem for integers | [1704.08037](https://arxiv.org/abs/1704.08037) | theoremsearch |
| 4 | 0.679 | On the Waring Problem for Matrices over Finite Fields | [2505.11805](https://arxiv.org/abs/2505.11805) | theoremsearch |
| 5 | 0.677 | On Fillmore's theorem extended by Borobia | [1804.05738](https://arxiv.org/abs/1804.05738) | theoremsearch |

**D2 (triviality):** `False`

**🔍 Did D1 find the known duplicator?** — *manual check needed*
> Known: Result already published with similar proof (Fillmore, 1969?)
> Top D1 result: see above. Do they match?

---

### 3. 1212.0196v1 (retracted)

**Veredicto:** `NOVEDAD_ENUNCIADO`  
**Known duplicator:** Monsky (well-known result on congruent numbers)

**Formalization errors:** Compilation error (attempt 1): D:\Mis documentos\Documentos\AViD Journal\results\formalizations\1212_0196v1.lean:10:43: error: Application type mismatch: The argument
  ↑(p j)
has type
  ℤ
but is expected to have type
  ℕ
in the ap | Compilation error (attempt 2): D:\Mis documentos\Documentos\AViD Journal\results\formalizations\1212_0196v1.lean:9:31: error(lean.synthInstanceFailed): failed to synthesize instance of type class
  Fact (Nat.Prime (p j))

Hint: Typ

#### D1 Top-5 (Informal Search)

| # | Score | Title | arXiv ID | Source |
|---|-------|-------|----------|--------|
| 1 | 0.674 | Congruent Numbers and Heegner Points | [1210.8231](https://arxiv.org/abs/1210.8231) | theoremsearch |
| 2 | 0.651 | Generalization of Some Arithmetical Properties of Fermat-Euler Dynamical Systems | [0910.5704](https://arxiv.org/abs/0910.5704) | theoremsearch |
| 3 | 0.647 | The even parity Goldfeld conjecture: congruent number elliptic curves | [2104.06732](https://arxiv.org/abs/2104.06732) | theoremsearch |
| 4 | 0.635 | On a class of quaternary complex Hadamard matrices | [1709.02873](https://arxiv.org/abs/1709.02873) | theoremsearch |

**D2 (triviality):** `False`

**🔍 Did D1 find the known duplicator?** — *manual check needed*
> Known: Monsky (well-known result on congruent numbers)
> Top D1 result: see above. Do they match?

---

### 4. 1004.3381v1 (retracted)

**Veredicto:** `FORMALIZATION_FAILED`  
**Known duplicator:** Gyárfás & Lehel (1970) — d-separated interval piercing

**Error:** API error (attempt 1): [Errno 22] Invalid argument | API error (attempt 2): [Errno 22] Invalid argument | API error (attempt 3): [Errno 22] Invalid argument

**Formalization errors:** API error (attempt 1): [Errno 22] Invalid argument | API error (attempt 2): [Errno 22] Invalid argument | API error (attempt 3): [Errno 22] Invalid argument

**🔍 Did D1 find the known duplicator?** — *manual check needed*
> Known: Gyárfás & Lehel (1970) — d-separated interval piercing
> Top D1 result: see above. Do they match?

---

### 5. math/0604362v1 (retracted)

**Veredicto:** `FORMALIZATION_FAILED`  
**Known duplicator:** desconocido — posiblemente ya conocido en literatura de mixing times (LPW?)

**Error:** Compilation error (attempt 1): D:\Mis documentos\Documentos\AViD Journal\results\formalizations\math_0604362v1.lean:12:4: error: `_root_.IsIrreducible` has already been declared
D:\Mis documentos\Documentos\AViD Journal\results\for | Compilation error (attempt 2): D:\Mis documentos\Documentos\AViD Journal\results\formalizations\math_0604362v1.lean:40:44: error(lean.unknownIdentifier): Unknown constant `Complex.abs`

 | Compilation error (attempt 3): D:\Mis documentos\Documentos\AViD Journal\results\formalizations\math_0604362v1.lean:10:4: error: `IsIrreducible` has already been declared
D:\Mis documentos\Documentos\AViD Journal\results\formalizat

**Formalization errors:** Compilation error (attempt 1): D:\Mis documentos\Documentos\AViD Journal\results\formalizations\math_0604362v1.lean:12:4: error: `_root_.IsIrreducible` has already been declared
D:\Mis documentos\Documentos\AViD Journal\results\for | Compilation error (attempt 2): D:\Mis documentos\Documentos\AViD Journal\results\formalizations\math_0604362v1.lean:40:44: error(lean.unknownIdentifier): Unknown constant `Complex.abs`

 | Compilation error (attempt 3): D:\Mis documentos\Documentos\AViD Journal\results\formalizations\math_0604362v1.lean:10:4: error: `IsIrreducible` has already been declared
D:\Mis documentos\Documentos\AViD Journal\results\formalizat

**🔍 Did D1 find the known duplicator?** — *manual check needed*
> Known: desconocido — posiblemente ya conocido en literatura de mixing times (LPW?)
> Top D1 result: see above. Do they match?

---

### 6. 1501.01654v1 (control)

**Veredicto:** `FORMALIZATION_FAILED`  
**Known duplicator:** None

**Error:** API error (attempt 1): [Errno 22] Invalid argument | API error (attempt 2): [Errno 22] Invalid argument | API error (attempt 3): [Errno 22] Invalid argument

**Formalization errors:** API error (attempt 1): [Errno 22] Invalid argument | API error (attempt 2): [Errno 22] Invalid argument | API error (attempt 3): [Errno 22] Invalid argument

**🔍 Did D1 find the known duplicator?** — *manual check needed*
> Known: None
> Top D1 result: see above. Do they match?

---

### 7. 1101.3431v2 (control)

**Veredicto:** `FORMALIZATION_FAILED`  
**Known duplicator:** None

**Error:** API error (attempt 1): [Errno 22] Invalid argument | API error (attempt 2): [Errno 22] Invalid argument | API error (attempt 3): [Errno 22] Invalid argument

**Formalization errors:** API error (attempt 1): [Errno 22] Invalid argument | API error (attempt 2): [Errno 22] Invalid argument | API error (attempt 3): [Errno 22] Invalid argument

**🔍 Did D1 find the known duplicator?** — *manual check needed*
> Known: None
> Top D1 result: see above. Do they match?

---

### 8. 1101.3720v1 (control)

**Veredicto:** `FORMALIZATION_FAILED`  
**Known duplicator:** None

**Error:** API error (attempt 1): [Errno 22] Invalid argument | API error (attempt 2): [Errno 22] Invalid argument | API error (attempt 3): [Errno 22] Invalid argument

**Formalization errors:** API error (attempt 1): [Errno 22] Invalid argument | API error (attempt 2): [Errno 22] Invalid argument | API error (attempt 3): [Errno 22] Invalid argument

**🔍 Did D1 find the known duplicator?** — *manual check needed*
> Known: None
> Top D1 result: see above. Do they match?

---

### 9. 0904.1783v3 (control)

**Veredicto:** `NOVEDAD_ENUNCIADO`  
**Known duplicator:** None

**Formalization errors:** API error (attempt 1): [Errno 22] Invalid argument

#### D1 Top-5 (Informal Search)

| # | Score | Title | arXiv ID | Source |
|---|-------|-------|----------|--------|
| 1 | 0.707 | Convex Hull of Planar H-Polyhedra | [0405089](https://arxiv.org/abs/0405089) | theoremsearch |
| 2 | 0.706 | Faces of weight polytopes and a generalization of a theorem of Vinberg | [1005.1114](https://arxiv.org/abs/1005.1114) | theoremsearch |
| 3 | 0.663 | Boundary modeling in model-based calibration for automotive engines via the vert | [1605.04552](https://arxiv.org/abs/1605.04552) | theoremsearch |

**D2 (triviality):** `False`

**🔍 Did D1 find the known duplicator?** — *manual check needed*
> Known: None
> Top D1 result: see above. Do they match?

---

### 10. math/0504586v2 (control)

**Veredicto:** `NOVEDAD_ENUNCIADO`  
**Known duplicator:** None

**Formalization errors:** API error (attempt 1): [Errno 22] Invalid argument | API error (attempt 2): [Errno 22] Invalid argument

#### D1 Top-5 (Informal Search)

| # | Score | Title | arXiv ID | Source |
|---|-------|-------|----------|--------|
| 1 | 0.786 | A survey on dynamical percolation | [0901.4760](https://arxiv.org/abs/0901.4760) | theoremsearch |
| 2 | 0.711 | Merging percolation on $Z^d$ and classical random graphs: Phase transition | [0612644](https://arxiv.org/abs/0612644) | theoremsearch |
| 3 | 0.685 | Ergodicity and indistinguishability in percolation theory | [1210.1548](https://arxiv.org/abs/1210.1548) | theoremsearch |
| 4 | 0.671 | Diffusion-limited annihilating-coalescing systems | [2305.19333](https://arxiv.org/abs/2305.19333) | theoremsearch |
| 5 | 0.669 | The Critical Radius in Sampling-based Motion Planning | [1709.06290](https://arxiv.org/abs/1709.06290) | theoremsearch |

**D2 (triviality):** `False`

**🔍 Did D1 find the known duplicator?** — *manual check needed*
> Known: None
> Top D1 result: see above. Do they match?

---
