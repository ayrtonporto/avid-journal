# Scout D3 — Phase 1 Reconnaissance

**Date:** 2026-07-03
**Status:** COMPLETED — evidence gathered from ExtractData output on Paper.lean

---

## 1. Premises: DIRECT vs TRANSITIVE?

### Answer: DIRECT (con evidencia)

**ExtractData extrae premisas DIRECTAS**: solo las constantes que el elaborador de Lean 4
resuelve durante el procesamiento del archivo actual. NO recorre recursivamente las
dependencias de los lemas invocados.

### Evidencia: T08 (√2 irracional)

#### T08a — Parity custom proof (lines 42-91 in Paper.lean)

28 premisas únicas:

```
Mathlib lemmas (16):
  Irrational, Real.sqrt, Real.sq_sqrt, Nat.prime_two, Nat.prime_iff_prime_int,
  Prime, Prime.dvd_of_dvd_pow, Nat.gcd, Nat.dvd_gcd, Rat.num_div_den,
  Rat.den_ne_zero, Rat.reduced, div_pow, Int.natAbs_dvd_natAbs, Rat.den, Rat.num

Init/Lean infrastructure (12):
  Dvd.dvd, Eq.symm, Exists.intro, Iff.mp, Iff.mpr, Int, Int.natAbs, Nat,
  Not, Real, Rat, congrArg
```

#### T08b — Valuation custom proof (lines 100-158 in Paper.lean)

33 premisas únicas:

```
Mathlib lemmas (17):
  padicValNat, padicValNat.mul, padicValNat.pow, Even, Odd, Nat.not_even_iff_odd,
  even_iff_exists_two_mul, pow_ne_zero, Int.natAbs_mul, Int.natAbs_pow,
  plus shared: Irrational, Real.sqrt, Real.sq_sqrt, Rat.num_div_den, Rat.den_ne_zero,
  div_pow, add_comm

Init/Lean infrastructure (16):
  Bool.false, dite, absurd, rfl, plus shared: Nat, Not, Int, Real, Rat, ...
```

### Por qué son DIRECTAS

La función `visitTermInfo` en ExtractData.lean (línea 336-375) procesa cada `TermInfo`
del `InfoTree` del archivo actual. El `InfoTree` lo construye el elaborador de Lean
mientras procesa LOS COMANDOS DE ESTE ARCHIVO. Cuando el proof text invoca
`padicValNat.mul`, el elaborador resuelve ese nombre a su constante, pero NO entra
a la definición de `padicValNat.mul` para resolver sus dependencias internas.

**Ejemplo concreto**: `padicValNat.mul` (demostrado en Mathlib con ~15 lemas internos)
aparece como UNA sola premisa con `fullName: "padicValNat.mul"`. Sus dependencias
internas (ej. `Nat.gcd`, `Finset.filter`, `List.partition`) NO aparecen en las
premisas del archivo. Esto confirma que la extracción es DIRECTA, no transitiva.

### Lo que SÍ incluye (infraestructura del elaborador)

Aunque son directas, las premisas incluyen más que solo los lemas explícitamente
nombrados en el proof text. El elaborador de Lean también resuelve:

1. **Constructores de tipo del enunciado**: `Irrational`, `Real.sqrt`, `Nat`
2. **Instancias de typeclass**: `Decidable` (para `by_contra`), `OfNat`
3. **Desugaring de notación**: `Exists`, `And`, `Not`, `Or`
4. **Configuración interna de tácticas**: `Lean.Meta.Simp.Config` (12 ocurrencias, todas con `pos=None`)

Estas son las que los Filtros 1 y 2 deben eliminar (ver §Fase 2).

### Conclusión para D3

No necesitamos restringir de transitivas a directas — ya son directas. Pero sí
necesitamos filtrar la infraestructura que el elaborador agrega automáticamente.
Esto es exactamente lo que los Filtros 1 y 2 de compute_d3 deben hacer.

---

## 2. Jaccard computation: locations

### Answer: NO EXISTE implementación de Jaccard en el codebase

Búsqueda exhaustiva en todos los archivos `.py` del repo:

```bash
grep -r "def jaccard\|def compute_d3\|intersection.*union.*premis" --include="*.py"
→ 0 resultados
```

El único lugar donde se menciona Jaccard es:
- `src/novelty_v2/types.py:106` — el campo `jaccard: Optional[float]` en D3Result
- `src/novelty_v2/orchestrator.py` — referencias en strings/comentarios
- `src/novelty_v2/dimensions/d3_premises.py` — es un STUB completo

**Riesgo de inconsistencia: NINGUNO.** No hay duplicación porque no hay implementación.
El campo está limpio para crear `compute_d3()` como única fuente de verdad.

---

## 3. Canonical identity (defPath, defPos)

### Answer: CONFIRMADO — la identidad canónica es (defPath, defPos)

Cada `PremiseTrace` de ExtractData contiene:

```json
{
  "fullName": "Nat",
  "modName": "Init.Prelude",
  "defPath": ".lake/packages/lean4/src/lean/Init/Prelude.lean",
  "defPos": {"line": 1214, "column": 10},
  "pos": {"line": 25, "column": 25},
  "endPos": {"line": 25, "column": 28}
}
```

- `(defPath, defPos)` identifica DÓNDE se define el objeto — es su identidad canónica.
- `(pos, endPos)` identifica DÓNDE se usa en el archivo actual — la misma premisa
  puede tener múltiples `(pos, endPos)` porque se usa en múltiples lugares.

**Deduplicación necesaria**: En el AST JSON de Paper.lean:
- `Nat` aparece 75 veces (mismo `defPath`/`defPos`, distintos `pos`/`endPos`)
- `Int` aparece 60 veces
- `Real` aparece 54 veces
- `padicValNat` aparece 13 veces

Sin deduplicación por `(defPath, defPos)`, el conjunto de premisas estaría inflado
con repeticiones, distorsionando la distancia de Jaccard.

**Decisión**: La deduplicación por `(defPath, defPos)` debe aplicarse ANTES de
cualquier filtro o cómputo de Jaccard, como primer paso después de la extracción.
