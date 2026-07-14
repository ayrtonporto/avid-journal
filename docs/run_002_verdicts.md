# Run 002 — Veredictos del autor (Ayrton Porto)

**Dataset:** 10 papers (5 retirados + 5 controles)  
**Modelo:** Qwen 3.7-max vía OpenCode Go, statement-only (:= by sorry)  
**Pipeline:** D1 formal (Leandex) + D1 informal (TheoremSearch + LLM judge) + D2 (trivialidad)  
**Resultado:** 7/10 formalizados, 3 fallidos

---

## Papers aprobados (4/7)

### Paper 1 — 1609.02090v1 (EvenPowers) ✅ Fiel
- Definiciones correctas: `powers`, `sumset`
- Omite los casos intermedios del teorema (5R_4 iff 8∤n, 7R_4 iff 16∤n)
- El núcleo está bien. El enunciado es muy específico (γ(k) para 4 valores), difícil de matchear — entendible que el pipeline lo declarara NOVEDAD_ENUNCIADO

### Paper 2 — 1207.0631v1 (Fillmore) ✅ Fiel
- `hA : ¬ ∃ k, A = k·1` para "non-scalar" correcto
- Teorema bien formalizado
- D1 encontró arXiv:1804.02140 (2018) que cita a Fillmore — no es Fillmore (1969) directo pero es VP: el teorema ES conocido en la literatura
- AViD juzga como si fueran nuevos, por lo que match indirecto es aceptable

### Paper 3 — 1212.0196v1 (congruent numbers) ✅ Fiel
- `IsCongruentNumber` definición estándar (∃ a,b,c ∈ ℚ⁺, a²+b²=c², ab/2=n)
- `jacobiSym` correcto
- Pipeline no encontró el paper de Monsky — NOVEDAD_ENUNCIADO confirmed

### Paper 4 — 1004.3381v1 (rectangle slicing) ✅ Fiel
- Todas las definiciones geométricas correctas: Rectangle, rectsDisjoint, AxisParallelLine, lineIntersectsRect, isIndependentSet
- `x1 < x2` para no-degenerado, `≤` para intersección — correcto

## Papers con problemas (3/7)

### Paper 8 — 1101.3720v1 (binary cyclotomic) ❌ Incorrecto
- `theta m := sorry` — placeholder en una definición central
- La función θ_m (medida de equisdistribución) es el corazón del paper, no puede quedar sin definir
- Las cotas asintóticas están bien enunciadas pero dependen de una definición vacía

### Paper 9 — 0904.1783v3 (Minkowski-Weyl) ⚠️ Aproximación
- `IsClosedPolyhedron` y `genPolyhedron` definiciones correctas
- `hR : ∀ i, R i ≠ 0` = "0 ∉ R" correcto
- Pero el teorema original es una EQUIVALENCIA (⇔) y Qwen solo da (⇒)
- Falta: IsClosedPolyhedron → se puede representar como genPolyhedron

### Paper 10 — math/0504586v2 (percolation noise sensitivity) ❌ Incorrecto
- `PercolationEvent` = `{ω | True}` — placeholder
- `probMeasure` = medida de Dirac — debería ser Bernoulli(p)
- Teorema: `p > pc → volume {ω | True} = 1` — trivialmente cierto, no captura el enunciado
- La fuente tiene dos ramas (p > p_c y p < p_c), Qwen solo da una
- Es el peor de los 7

## Fallos de formalización (3/10)

- **Paper 5 (math/0604362v1):** Fallo de COMPILACIÓN — `IsIrreducible` duplicado, `Complex.abs` no encontrado. Dato sobre Qwen.
- **Papers 6-7 (1501.01654v1, 1101.3431v2):** Fallo de API TIMEOUT — enunciados con 4 niveles de casos anidados exceden límite de Qwen. Ruido de infraestructura.

## Resumen

| # | Paper | Rol | Fidelidad |
|---|-------|-----|:---------:|
| 1 | 1609.02090v1 | retracted | ✅ |
| 2 | 1207.0631v1 | retracted | ✅ |
| 3 | 1212.0196v1 | retracted | ✅ |
| 4 | 1004.3381v1 | retracted | ✅ |
| 5 | math/0604362v1 | retracted | ❌ comp |
| 6 | 1501.01654v1 | control | ❌ API |
| 7 | 1101.3431v2 | control | ❌ API |
| 8 | 1101.3720v1 | control | ❌ |
| 9 | 0904.1783v3 | control | ⚠️ |
| 10 | math/0504586v2 | control | ❌ |
