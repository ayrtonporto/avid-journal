# D3 Validation Report — 2026-07-12

**Objetivo:** Destrabar la validación de D3 reescribiendo T09a (colapso Jaccard=0)
y agregando un juez LLM de distintividad de pruebas.

## Tabla de resultados

| Par | Tipo esperado | Juez LLM | Distancia | ∩ | ∪ | user_label |
|-----|--------------|----------|-----------|---|---|------------|
| T07_euclid_vs_factorial | same_disguised | same_disguised | 0.5000 | 1 | 2 | |
| T08_parity_vs_valuation | genuinely_different | genuinely_different | **0.7222** | 5 | 18 | |
| T09_induction_vs_gauss | genuinely_different | genuinely_different | 1.0000 | 0 | 6 | |
| control_self_T08a | control_self | — | 0.0000 | 9 | 9 | |
| control_unrelated_T07xT08 | control_unrelated | — | 1.0000 | 0 | 10 | |

### Controles ✅

- **control_self**: 0.0000 — perfecto (la misma prueba vs sí misma).
- **control_unrelated**: 1.0000 — perfecto (teoremas sin relación: infinitos primos vs √2 irracional).

### T08 — regresión ✅

Distancia **0.7222** exacta (mismo valor pre-reescritura). Intocable.

## Justificaciones del juez LLM

### T07 — `same_disguised`

> **Idea A:** The proof directly invokes the theorem `Nat.exists_infinite_primes` which asserts the existence of a prime at least as large as any given natural number.
>
> **Idea B:** The proof directly invokes the theorem `Nat.exists_infinite_primes` which asserts the existence of a prime at least as large as any given natural number.
>
> **Justificación:** Both proofs are identical, consisting solely of the line `Nat.exists_infinite_primes n`. There is no variation in reasoning, tactic usage, or mathematical structure.

_Nota:_ T07a y T07b son marcadores de lugar idénticos. Una prueba genuinamente Euclid (producto de primos + 1) requiere código Lean custom (future work). La distancia 0.5000 con solo 2 premisas (1 compartida, 1 posicionalmente distinta) refleja este marcador de lugar.

### T08 — `genuinely_different`

> **Idea A:** Assume √2 = p/q in lowest terms, derive 2q² = p², use primality of 2 to force 2|p and 2|q, contradicting coprimality.
>
> **Idea B:** Assume √2 = p/q, derive 2q² = p², apply 2-adic valuation to both sides to get a parity contradiction (even vs odd) without needing coprimality.
>
> **Justificación:** Proof A relies on prime divisibility (h2_prime.dvd_of_dvd_pow) and the reduced condition (q.reduced) to derive a contradiction from a common divisor 2. Proof B uses padicValNat properties (padicValNat.mul, padicValNat.pow) to obtain an equation 2*v2(p)=1+2*v2(q), which is impossible due to parity. The two proofs employ fundamentally different number-theoretic machinery and obtain contradictions from distinct logical inconsistencies, so they are genuinely different.

### T09 — `genuinely_different`

> **Idea A:** Use induction on n and exploit the fact that k*(k+1) is always even to rewrite the arithmetic expression.
>
> **Idea B:** Use the known identity Finset.sum_range_id that gives the sum of the first n natural numbers directly.
>
> **Justificación:** Proof A builds the formula from scratch using induction and a parity argument to handle division by 2, while Proof B simply invokes the precomputed lemma Finset.sum_range_id and then commutes the product. These rely on fundamentally different mathematical insights: one is a low-level inductive proof with explicit evenness reasoning, the other is a high-level appeal to an already-established formula (itself often proved by Gauss pairing). Hence they are genuinely different.

## Qué cambió

### T09a reescrita (Paper.lean)

**Antes (colapso):**
```lean
theorem t09a_induction (n : ℕ) : (∑ i ∈ range (n+1), i) = n*(n+1)/2 := by
  have h := Finset.sum_range_id (n+1)
  simpa [mul_comm, add_comm] using h
```

**Ahora (inducción genuina):**
```lean
theorem t09a_induction (n : ℕ) : (∑ i ∈ range (n+1), i) = n*(n+1)/2 := by
  induction n with
  | zero => simp
  | succ k ih =>
    rw [Finset.sum_range_succ, ih]
    -- arithmetic: parity lemma 2∣k(k+1) → extract q → ring
    ...
```

- Usa `Finset.sum_range_succ` (NO `sum_range_id`)
- Paridad: `Nat.even_or_odd` → `2 ∣ k*(k+1)` → `rcases` para extraer q
- División: `Nat.mul_div_cancel_left` con `0 < 2`
- Árithmetic: `ring`

**Resultado:** Distancia Jaccard pasó de 0.0000 (colapso) a **1.0000** (0 premisas compartidas de 6 totales).

### proof_pair_judge.py (módulo nuevo)

- `src/novelty_v2/proof_pair_judge.py` (303 líneas)
- Infraestructura DeepSeek V4 Flash (misma que `llm_judge.py`)
- Chequeo mecánico: extrae enunciados Lean → compara tipos → `statement_mismatch` si difieren
- LLM: describe idea central (1 frase) + veredicto `genuinely_different | same_disguised` + justificación (2-3 oraciones)
- El veredicto es **OPINIÓN**: campo `user_label` vacío para firma del usuario
- `max_tokens=4096` (retry a 8192) + truncamiento a 2500 chars/prueba

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `lean_project/Papers/D3_Calibration/Paper.lean` | T09a reescrita con inducción + paridad |
| `src/novelty_v2/proof_pair_judge.py` | Módulo nuevo: juez LLM de pares |
| `config/validation_pairs.yaml` | 5 pares: T07, T08, T09, control_self, control_unrelated |
| `config/d3_extraction_map.yaml` | Rangos de línea actualizados para T09a/T09b |
| `scripts/run_d3_validation.py` | Script runner completo (judge + validate + regresión) |
| `results/pair_judgments.json` | Veredictos del juez para T07, T08, T09 |
| `results/d3_validation.csv` | Distancias Jaccard frescas (post-reescritura) |

## Suite

- **Tests:** 167 passed, 1 skipped ✅
- **Compilación Lean:** Paper.lean compila (solo warning preexistente de `simpa`→`simp`)
- **T08 regresión:** 0.7222 ✅ (intocable)

## Pendiente para el usuario

- [ ] **Firmar `user_label`** para T07, T08, T09 en `results/pair_judgments.json`
- [ ] **T07**: Ambas pruebas son idénticas (`Nat.exists_infinite_primes`). La distancia 0.5000 con ∩=1 ∪=2 refleja el marcador de lugar. Una prueba Euclid genuina requiere Lean custom.
- [ ] **T09**: distancia 1.0000 (0 premisas compartidas). Las pruebas son estructuralmente independientes. Verificar que esto es correcto (la inducción no comparte ningún lemma con Gauss pairing).
