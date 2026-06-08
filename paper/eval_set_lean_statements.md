# Enunciados Lean 4 para el eval set — corrida D2 (Día 5)

**Propósito:** documentar los enunciados Lean 4 usados en la corrida de D2 sobre el eval set completo.
Cada entrada corresponde a un `example : <enunciado> := by <táctica>` que el script genera.

**Reglas de deduplicación para D2:**
- T07a y T07b tienen el **mismo tipo τ** (infinitos primos); D2 evalúa solo el tipo → testeamos una vez como **T07**.
- T08a y T08b tienen el **mismo tipo τ** (√2 irracional) → testeamos una vez como **T08**.
- T09a y T09b tienen el **mismo tipo τ** (suma gaussiana) → testeamos una vez como **T09**.
- T20 = mismo enunciado que T01/T08 (√2 irracional) → **excluido de D2 por redundancia** (ver nota abajo).
- T21 = TBD (requiere elegir caso de Kasaura et al.) → **excluido de esta corrida**.

**Conteo:**
26 firmes − 3 duplicados de par (T07b, T08b, T09b) = 23 únicos + T19 (agregado Día 5) = **24 teoremas**.

---

## T01 — La raíz cuadrada de 2 es irracional

Categoría: `clasico_en_mathlib`
D2 esperado: **NO TRIVIAL** (requiere demostración, ninguna táctica automática debería cerrar esto)

```lean
theorem T01 : Irrational (Real.sqrt 2) := sorry
```

Nota: En Mathlib como `irrational_sqrt_two`. Ninguna táctica de T_auto cierra `Irrational` sin guía.

---

## T02 — Existen infinitos números primos

Categoría: `clasico_en_mathlib`
D2 esperado: **NO TRIVIAL**

```lean
theorem T02 : ∀ n : ℕ, ∃ p : ℕ, n ≤ p ∧ Nat.Prime p := sorry
```

Nota: En Mathlib como `Nat.exists_infinite_primes`. No hay táctica automática que construya el testigo primo.

---

## T03 — Teorema fundamental del cálculo

Categoría: `clasico_en_mathlib`
D2 esperado: **NO TRIVIAL**

```lean
theorem T03 : ∀ (f f' : ℝ → ℝ) (a b : ℝ), a ≤ b →
    (∀ x ∈ Set.uIcc a b, HasDerivAt f (f' x) x) →
    IntervalIntegrable f' MeasureTheory.volume a b →
    ∫ x in a..b, f' x = f b - f a := sorry
```

Imports: `import Mathlib` (cubre `MeasureTheory.Measure.MeasureSpace`, `MathLib.Analysis.Calculus.FTC`).
⚠ **Riesgo de type-check:** El enunciado usa `intervalIntegral` (notación `∫ x in a..b, ...`) y
`IntervalIntegrable`. Si hay problemas de inferencia de instancias, el script registrará el error literal.
En Mathlib el teorema correspondiente es `intervalIntegral.integral_eq_sub_of_hasDerivAt`.

---

## T04 — Pequeño teorema de Fermat

Categoría: `clasico_en_mathlib`
D2 esperado: **NO TRIVIAL**

```lean
theorem T04 : ∀ (p : ℕ) (a : ℤ), Nat.Prime p → (p : ℤ) ∣ a ^ p - a := sorry
```

Nota: Forma de divisibilidad: p | aᵖ − a. En Mathlib: `Int.emod_emod_of_dvd` o `ZMod.intCast_zmod_eq_zero_iff_dvd`.
El cast `(p : ℤ)` es automático vía coerción ℕ → ℤ.

---

## T05 — Teorema de Pitágoras

Categoría: `clasico_en_mathlib`
D2 esperado: **NO TRIVIAL**

```lean
theorem T05 : ∀ (x y : EuclideanSpace ℝ (Fin 2)),
    ⟪x, y⟫_ℝ = 0 →
    ‖x + y‖ ^ 2 = ‖x‖ ^ 2 + ‖y‖ ^ 2 := sorry
```

Nota: Formulación canónica en `EuclideanSpace ℝ (Fin 2)` — la forma estándar del espacio euclídeo en Mathlib.
`⟪x, y⟫_ℝ` es la notación de producto interno (notation `inner_product`).
El cuadrado del largo de la hipotenusa = suma de cuadrados de los catetos cuando los vectores son ortogonales.
En Mathlib: `inner_add_left`, `real_inner_self_eq_norm_sq`, `norm_add_sq_real`.
Imports: `import Mathlib.Analysis.InnerProductSpace.PiL2` (contiene `EuclideanSpace` y la instancia
`InnerProductSpace ℝ (EuclideanSpace ℝ ι)` lista para usar).
⚠ Riesgo menor: si `⟪x, y⟫_ℝ` necesita `open scoped InnerProductSpace`, el statement puede requerir ajuste.
Corrección aplicada Día 5 (antes: `ℝ × ℝ` con `inner (𝕜 := ℝ)`, que usaba la instancia
`InnerProductSpace ℝ (ℝ × ℝ)` vía PiLp que puede ser problemática).

---

## T06 — Suma 1 + 2 + … + n = n(n+1)/2

Categoría: `clasico_en_mathlib`
D2 esperado: **NO TRIVIAL** (requiere inducción o lema de suma de Finset)

```lean
theorem T06 : ∀ (n : ℕ), 2 * ∑ i ∈ Finset.range (n + 1), i = n * (n + 1) := sorry
```

Nota: Formulación multiplicada por 2 para evitar división entera en ℕ.
`Finset.range (n+1) = {0, 1, …, n}`, la suma es n(n+1)/2. En Mathlib: `Finset.sum_range_id`.
`omega` y `simp` no pueden cerrar esto sin el lema de Finset.

---

## T07 — Infinitos primos (pares T07a Euclides / T07b Euler)

Categoría: `par_distinta_prueba`
D2 esperado: **NO TRIVIAL** — resultado idéntico a T02 (mismo enunciado)

```lean
-- T07a (prueba de Euclides) y T07b (prueba de Euler) tienen el mismo tipo τ.
-- D2 evalúa solo el tipo; la diferencia entre las dos pruebas aparece en D3 (Días 8-9).
theorem T07 : ∀ n : ℕ, ∃ p : ℕ, n ≤ p ∧ Nat.Prime p := sorry
```

Nota: Enunciado idéntico a T02. D2 registrará el mismo resultado.

---

## T08 — √2 irracional (pares T08a paridad / T08b raíz racional)

Categoría: `par_distinta_prueba`
D2 esperado: **NO TRIVIAL** — resultado idéntico a T01 (mismo enunciado)

```lean
-- T08a (argumento de paridad) y T08b (teorema de la raíz racional) tienen el mismo tipo τ.
theorem T08 : Irrational (Real.sqrt 2) := sorry
```

Nota: Enunciado idéntico a T01. D2 registrará el mismo resultado.

---

## T09 — Suma gaussiana (pares T09a inducción / T09b emparejamiento de Gauss)

Categoría: `par_distinta_prueba`
D2 esperado: **NO TRIVIAL** — resultado idéntico a T06 (mismo enunciado)

```lean
-- T09a (inducción) y T09b (truco de Gauss) tienen el mismo tipo τ.
theorem T09 : ∀ (n : ℕ), 2 * ∑ i ∈ Finset.range (n + 1), i = n * (n + 1) := sorry
```

Nota: Enunciado idéntico a T06. D2 registrará el mismo resultado.
Hallazgo esperado: T09b (truco de Gauss) puede no tener traducción natural en Lean 4 como prueba
distinta — documentar en resultados si T09a y T09b colapsan en D3.

---

## T10 — Todo primo mayor que 2 es impar

Categoría: `enunciados_cercanos_distintos`
D2 esperado: **NO TRIVIAL** (requiere propiedades de primos, no automatizable)

```lean
theorem T10 : ∀ (p : ℕ), Nat.Prime p → 2 < p → ¬ 2 ∣ p := sorry
```

Nota: `decide` no aplica (cuantificador universal infinito). `omega` no conoce `Nat.Prime`.
`aesop` puede intentarlo pero es improbable que cierre. En Mathlib: `Nat.Prime.odd_of_ne_two`.

---

## T11 — Todo primo mayor que 2 es ≡ 1 o 3 (mod 4)

Categoría: `enunciados_cercanos_distintos`
D2 esperado: **NO TRIVIAL**

```lean
theorem T11 : ∀ (p : ℕ), Nat.Prime p → 2 < p → p % 4 = 1 ∨ p % 4 = 3 := sorry
```

Nota: `omega` no puede usar `Nat.Prime`. Requiere teoría de números no trivial.
En Mathlib no hay un lema directo exactamente con esta forma; probablemente D1 dará zona gris.

---

## T12 — AM-GM para n=2

Categoría: `enunciados_cercanos_distintos`
D2 esperado: **NO TRIVIAL** (requiere `Real.sqrt` y desigualdades no lineales)

```lean
theorem T12 : ∀ (a b : ℝ), 0 ≤ a → 0 ≤ b → Real.sqrt (a * b) ≤ (a + b) / 2 := sorry
```

Nota: `norm_num` y `nlinarith` no cierran desigualdades con `Real.sqrt`. `nlinarith` no está en T_auto.
En Mathlib: `Real.add_sq_le_sq_mul_sq` o `Real.inner_le_iff`.

---

## T13 — AM-GM general (n variables)

Categoría: `enunciados_cercanos_distintos`
D2 esperado: **NO TRIVIAL**

```lean
theorem T13 : ∀ (n : ℕ) (hn : 0 < n) (f : Fin n → ℝ), (∀ i, 0 ≤ f i) →
    (∏ i, f i) ^ ((1 : ℝ) / ↑n) ≤ (∑ i, f i) / ↑n := sorry
```

Nota: `↑n : ℝ` es la coerción ℕ → ℝ. `(∏ i, f i) ^ ((1 : ℝ) / ↑n)` usa `Real.rpow`.
⚠ **Riesgo de type-check:** La coerción `↑n` en el exponente puede requerir anotación explícita:
`(n : ℝ)` en lugar de `↑n`. Si falla, usar:

```lean
-- Alternativa explícita para T13:
theorem T13' : ∀ (n : ℕ) (hn : 0 < n) (f : Fin n → ℝ), (∀ i, 0 ≤ f i) →
    (∏ i : Fin n, f i) ^ ((1 : ℝ) / (n : ℝ)) ≤ (∑ i : Fin n, f i) / (n : ℝ) := sorry
```

---

## T14 — Suma de cuatro enteros pares es par (YA TESTEADO Día 4)

Categoría: `trivial`
D2 esperado: **TRIVIAL** (aesop — confirmado Día 4, 215 s)

```lean
theorem T14 : ∀ (a b c d : Int), Even a → Even b → Even c → Even d →
    Even (a + b + c + d) := sorry
```

---

## T15 — 2 + 2 = 4 (YA TESTEADO Día 4)

Categoría: `trivial`
D2 esperado: **TRIVIAL** (decide — confirmado Día 4, 29 s)

```lean
theorem T15 : (2 : Nat) + 2 = 4 := sorry
```

---

## T16 — ∀ n : ℕ, n + 0 = n (YA TESTEADO Día 4)

Categoría: `trivial`
D2 esperado: **TRIVIAL** (norm_num — confirmado Día 4, 61 s)

```lean
theorem T16 : ∀ (n : Nat), n + 0 = n := sorry
```

---

## T17 — ∀ n : ℕ, n ≤ n + 1 (YA TESTEADO Día 4)

Categoría: `trivial`
D2 esperado: **TRIVIAL** (norm_num — confirmado Día 4, 60 s)

```lean
theorem T17 : ∀ (n : Nat), n ≤ n + 1 := sorry
```

---

## T18 — Suma de primeros n impares = n² — TRAMPA DE CONTROL (YA TESTEADO Día 4)

Categoría: `trivial` (control)
D2 esperado: **NO TRIVIAL** — confirmado Día 4 (ninguna táctica cierra, inducción requerida)

```lean
theorem T18 : ∀ (n : Nat), (Finset.range n).sum (fun k => 2 * k + 1) = n ^ 2 := sorry
```

---

## T19 — Teorema generado por LLM sobre números pares (AGREGADO Día 5)

Categoría: `generado_IA`
D2 esperado: **TRIVIAL** (omega — del tipo de enunciados que un LLM produce cuando se pide
"enuncia y prueba un teorema original sobre números pares")

```lean
theorem T19 : ∀ (n : ℕ), Even n → Even (n + 2) := sorry
```

Nota: Este enunciado es representativo de la categoría. `omega` cierra `Even n → Even (n+2)`
porque `Even n ↔ ∃ k, n = 2*k` y `n+2 = 2*(k+1)`, todo lineal.
La expectativa es TRIVIAL, lo cual confirmaría el modo de falla de los LLM: producen enunciados
no novedosos o triviales cuando se les pide "un teorema original."

---

## Nota sobre T20 y T21 (excluidos de esta corrida de D2)

**T20** (`generado_IA`): "Pedir a un LLM 'demuestra que sqrt(2) no es racional usando una idea
no convencional'." El enunciado autoformalizado de T20 coincide con `Irrational (Real.sqrt 2)`,
idéntico a T01 y T08 — D2 daría el mismo resultado (NO TRIVIAL) sin aportar dato nuevo.

T20 sigue siendo un caso conceptualmente distinto del eval set: su interés es D1 (¿el LLM produce
un enunciado Lean lógicamente equivalente?) y el relato narrativo (redescubrimiento disfrazado
de idea "no convencional" — caso motivante estilo Axiom-Fel). Se procesa junto con D1 en Día 6.

**T21** (`generado_IA`): "Tomar un enunciado del ConjecturingProvingLoop (Kasaura et al.)".
Requiere leer el paper original y elegir un caso específico. Pendiente para cuando se escriba
la sección de evaluación (Día 19). Anotado en results_log.md como deuda técnica de Día 5.

---

## T22 — Equivalente lógico con sintaxis distinta (caso falla D1)

Categoría: `caso_falla` — test de falso negativo de D1 nivel 0 sintáctico
D2 esperado: **TRIVIAL** (omega o simp — `n + 0 = n` es lineal)

```lean
theorem T22 : ∀ (n : Nat), Even n → Even (n + 0) := sorry
```

Nota: Lógicamente idéntico a `Even n → Even n`, pero sintácticamente distinto (`n + 0` vs `n`).
D2 lo marca como trivial (correcto). D1 puede dar falso negativo al nivel 0 sintáctico.
El interés de este caso es D1, no D2.

---

## T23 — Grafo conexo + acíclico → árbol (FALSO POSITIVO ESPERADO — YA TESTEADO Día 4)

Categoría: `caso_falla` — test de falso positivo de D2
D2 esperado: **TRIVIAL** (tauto — falso positivo confirmado Día 4, 146 s)

```lean
theorem T23 : ∀ (V : Type) [Fintype V] [DecidableEq V] (G : SimpleGraph V),
    G.Connected → G.IsAcyclic → G.IsTree := sorry
```

Nota: `SimpleGraph.IsTree` en Mathlib v4.29.0 = `Connected ∧ IsAcyclic`.
`tauto` cierra la conjunción proposicional trivialmente. Falso positivo de D2 — el teorema
matemáticamente no es trivial, pero la *definición* en Mathlib lo hace trivial sintácticamente.

---

## T24 — Esquemas coherentes sobre Noetherian (FALLA ESPERADA de formalización)

Categoría: `caso_falla` — test de límite del formalizador
D2 esperado: **ERROR de type-check** (vocabulario fuera de Mathlib v4.29.0)

```lean
-- Formalización aproximada del enunciado:
-- "Todo haz coherente sobre esquema noetheriano tiene resolución localmente libre finita."
-- CoherentSheaf y HasFiniteLocallyFreeResolution probablemente NO existen en Mathlib v4.29.0.
theorem T24 : ∀ (X : AlgebraicGeometry.Scheme)
    [AlgebraicGeometry.IsNoetherianScheme X]
    (ℱ : AlgebraicGeometry.CoherentSheaf X),
    ∃ (n : ℕ), AlgebraicGeometry.HasFiniteLocallyFreeResolution ℱ n := sorry
```

Nota: Se espera error de tipo en Lean (`unknown identifier 'CoherentSheaf'` o similar).
D2 registrará el output de error literal en el campo `all_attempts[i].output`.
Resultado en la tabla: `FALLO_FORMALIZACION` (categoría propia, distinta de TRIVIAL/NO TRIVIAL).
Este es el dato experimental para la sección Limitations del paper.

---

## T25 — Even n ↔ 2 ∣ n (caso falla D1 nivel 1 definicional)

Categoría: `caso_falla` — test de equivalencia definicional en D1
D2 esperado: **TRIVIAL** (simp — Mathlib tiene `Nat.even_iff_two_dvd` en el simp set)

```lean
theorem T25 : ∀ (n : ℕ), Even n ↔ 2 ∣ n := sorry
```

Nota: `simp [Nat.even_iff_two_dvd]` debería cerrar esto. Sin argumento explícito, `simp` a secas
puede o no encontrarlo dependiendo del simp set default. Si no cierra con `simp`, `omega` tampoco
maneja `Even` directamente — registrar resultado real.
El interés principal de T25 es D1 (¿reconoce Lean la equivalencia definicional `Even n = 2∣n`?).

---

## T26 — Suma de n números pares es par

Categoría: `enunciados_cercanos_distintos`
D2 esperado: **NO TRIVIAL** (generalización de T14; `n` cuantificado, suma sobre Fin n)

```lean
theorem T26 : ∀ (n : ℕ) (f : Fin n → ℤ), (∀ i, Even (f i)) → Even (∑ i, f i) := sorry
```

Nota: `omega` y `decide` no pueden con `∀ n, Fin n`. `simp` podría con los lemas correctos pero
no es seguro sin argumento. `aesop` podría intentarlo (búsqueda). Se espera NO TRIVIAL, pero
si `aesop` lo cierra sería un falso positivo de D2 (conectado con T14 y T22).

---

## Resumen del conteo y notas para el script

| ID    | Categoría               | Enunciado Lean (resumen)                          | D2 esperado    | Riesgo type-check |
|-------|-------------------------|---------------------------------------------------|----------------|-------------------|
| T01   | clasico_en_mathlib      | `Irrational (Real.sqrt 2)`                        | NO TRIVIAL     | —                 |
| T02   | clasico_en_mathlib      | `∀ n, ∃ p ≥ n, Nat.Prime p`                       | NO TRIVIAL     | —                 |
| T03   | clasico_en_mathlib      | TFC: `∫ f' = f b - f a`                           | NO TRIVIAL     | ⚠ medio           |
| T04   | clasico_en_mathlib      | `p ∣ aᵖ - a` para p primo                         | NO TRIVIAL     | —                 |
| T05   | clasico_en_mathlib      | Pitágoras: `‖x+y‖² = ‖x‖² + ‖y‖²` si ortogonales | NO TRIVIAL     | ⚠ menor (EucSp)   |
| T06   | clasico_en_mathlib      | `2 * Σ range(n+1) i = n*(n+1)`                    | NO TRIVIAL     | —                 |
| T07   | par_distinta_prueba     | = T02                                             | NO TRIVIAL     | —                 |
| T08   | par_distinta_prueba     | = T01                                             | NO TRIVIAL     | —                 |
| T09   | par_distinta_prueba     | = T06                                             | NO TRIVIAL     | —                 |
| T10   | enunciados_cercanos     | primo > 2 → ¬ 2 ∣ p                               | NO TRIVIAL     | —                 |
| T11   | enunciados_cercanos     | primo > 2 → p % 4 ∈ {1,3}                        | NO TRIVIAL     | —                 |
| T12   | enunciados_cercanos     | AM-GM n=2: `√(ab) ≤ (a+b)/2`                     | NO TRIVIAL     | —                 |
| T13   | enunciados_cercanos     | AM-GM general: `(∏f)^(1/n) ≤ (Σf)/n`             | NO TRIVIAL     | ⚠ medio (rpow)    |
| T14 ✓ | trivial                 | suma 4 pares (aesop, 215 s)                       | TRIVIAL        | —                 |
| T15 ✓ | trivial                 | 2+2=4 (decide, 29 s)                              | TRIVIAL        | —                 |
| T16 ✓ | trivial                 | n+0=n (norm_num, 61 s)                            | TRIVIAL        | —                 |
| T17 ✓ | trivial                 | n≤n+1 (norm_num, 60 s)                            | TRIVIAL        | —                 |
| T18 ✓ | trivial (control)       | Σ impares = n² (ninguna)                          | NO TRIVIAL     | —                 |
| T19   | generado_IA             | `Even n → Even (n+2)`                             | TRIVIAL (omega)| —                 |
| T22   | caso_falla              | `Even n → Even (n+0)`                             | TRIVIAL (omega)| —                 |
| T23 ✓ | caso_falla (FP)         | árbol = conexo+acíclico (tauto, 146 s)            | TRIVIAL (FP)   | —                 |
| T24   | caso_falla              | esquemas coherentes (vocabulario fuera de Mathlib)| FALLO tipo     | ⚠ alto (esperado) |
| T25   | caso_falla              | `Even n ↔ 2 ∣ n`                                  | TRIVIAL? (simp)| —                 |
| T26   | enunciados_cercanos     | suma n pares (Fin n → ℤ)                          | NO TRIVIAL     | —                 |

**Total: 24 teoremas.** Marcados con ✓ = ya validados en Día 4 (se re-corren para confirmar).

**Estimación de tiempo de corrida:**
- ~15 teoremas NO TRIVIAL × ~210 s (7 tácticas × 30 s) ≈ 3150 s ≈ 52 min
- ~7 teoremas TRIVIAL × ~60 s promedio ≈ 420 s ≈ 7 min
- ~2 casos con riesgo tipo-check (T03, T05, T13, T24) × variable
- Pre-warm ≈ 3 min
- **Estimación total: ~65–80 minutos**

**Notas para el script:**
1. Guardar resultado en CSV incremental después de cada teorema (no perder datos si se interrumpe).
2. Para T24: si el error es de type-check (no de táctica), registrar `d2_result = "FALLO_FORMALIZACION"` 
   y el output de error literal en el CSV. La función `check_triviality` devuelve `trivial=False`
   pero el `output` en `all_attempts` contendrá el error de compilación.
3. Para T25: registrar si cierra con `simp` sin argumentos o no (dato interesante sobre el simp set).
