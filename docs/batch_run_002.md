# Batch Run 002 — Informal Match Formalization

**Date:** 2026-07-05
**Provider:** opencode (deepseek-v4-flash via verification_loop, 3 rounds/attempt)
**Timeout per attempt:** 1200s (20 min, not reached — all failed faster)
**Max attempts:** 3
**Papers:** 2 (config/informal_matches.yaml)
**Sort:** non-delegated proofs first (shortest first), delegated proofs last

---

## Paper 1: arXiv:1303.0730 — "Diagonalizing by Fixed-Points"

**Theorem:** There are infinitely many prime numbers in N
**Proof length:** 1543 chars (self-contained Euclid-style proof using diagonal/fixed-point argument)
**Delegation flag:** none

| Attempt | Result | Time | Rounds |
|---------|--------|------|--------|
| 1 | ❌ LIMIT | ~3 min | 3 API calls |
| 2 | ❌ LIMIT | ~3 min | 3 API calls |
| 3 | ❌ LIMIT | ~3 min | 3 API calls |

**Total time:** ~10 minutes (9 API calls)
**Final status:** FAILED — All 3 attempts failed

**Analysis:** The model (deepseek-v4-flash) could not produce compilable Lean 4 code for this proof in any of the 9 verification rounds. The proof uses a non-standard diagonal/fixed-point argument with function definitions in LaTeX, which is substantially different from the canonical `Nat.exists_infinite_primes`. The verification loop sent compilation errors back to the model but it never converged.

---

## Paper 2: arXiv:1607.03618 — "The Lax-Milgram Theorem"

**Theorem:** Cauchy-Schwarz inequality in inner product spaces
**Proof length:** 279 chars
**Delegation flag:** ✅ `proof_delegates_to_lemmas`

| Attempt | Result | Time |
|---------|--------|------|
| — | ⏭️ SKIPPED | 0s |

**Final status:** FAILED — proof_delegates_to_lemmas

**Analysis:** The extracted proof is a one-liner: "Direct consequence of Lemma~\ref{l:cauchy-schwarz-inequality}, Definition~\ref{d:square-root}..." The delegation skip correctly avoided wasting API calls on an unformalizable proof pointer.

---

## Summary

| Métrica | Valor |
|---------|-------|
| Papers procesados | 2 |
| Éxitos | 0 |
| Fallos por LIMIT | 1 (1303.0730) |
| Fallos por delegación | 1 (1607.03618) |
| Tasa de éxito | **0%** |
| Tiempo total | 600s (~10 min) |
| API calls totales | 9 (3 rounds × 3 attempts for 1303.0730) |
| API calls ahorradas (delegación) | ~9 (3 attempts × 3 rounds for 1607.03618) |

---

## Cache verification

Segunda invocación del batch (post-corrida):

| Paper | Resultado |
|-------|-----------|
| 1303.0730 | CACHED (instantáneo, < 1s) |
| 1607.03618 | CACHED (instantáneo, < 1s) |

---

## Diagnosis — cuello de botella

**El cuello de botella es la capacidad del modelo (deepseek-v4-flash).**

- La extracción de proof funciona (2/2 papers, < 3s c/u)
- La verificación de compilación es rápida (olean cache de Mathlib)
- El modelo consistentemente NO logra producir Lean 4 compilable para pruebas no triviales en 3 rondas de feedback
- La prueba de 1543 chars (Euclid vía diagonal) es autocontenida pero usa un argumento no estándar — el modelo no tiene suficiente capacidad de razonamiento matemático para traducirla a Lean en 3 rondas

**La fidelidad nunca llegó a evaluarse** porque ningún intento produjo código compilable.

**Recomendación:** Probar con un provider diferente (Claude Code, que tiene loop de verificación interno más largo) o aumentar max_rounds significativamente (6-9 rounds en vez de 3). Con deepseek-v4-flash + 3 rounds, la tasa de éxito para pruebas de papers reales es 0/1 = 0%.
