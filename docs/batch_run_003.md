# Batch Run 003 — Informal Match Formalization (Modelo Pro, 6 Rondas)

**Date:** 2026-07-05
**Provider:** opencode
**Model:** deepseek-v4-pro
**Timeout per attempt:** 1200s (20 min)
**Max attempts:** 3
**Max rounds per attempt:** **6** (vs 3 en corrida 002)
**Papers:** 2 (config/informal_matches.yaml)
**Sort:** shortest proof first

---

## Paper 1: arXiv:1607.03618 — "The Lax-Milgram Theorem"

**Theorem:** Cauchy-Schwarz inequality in inner product spaces
**Proof length:** 279 chars
**Delegation flag:** ✅ `proof_delegates_to_lemmas` (visible, NO salteado)

| Attempt | Result | Time | Rounds |
|---------|--------|------|--------|
| 1 | ❌ LIMIT | ~8 min | 6 API calls |
| 2 | ❌ LIMIT | ~10 min | 6 API calls |
| 3 | ❌ LIMIT | ~7 min | 6 API calls |

**Total time:** 1485s (~25 min, 18 API calls)
**Final status:** FAILED — All 3 attempts failed

**Note:** Esta prueba corrió con el flag `proof_delegates_to_lemmas` visible pero sin ser salteada. El resultado confirma que la decisión de saltarla en la corrida 002 era correcta: 18 llamadas a la API para un proof de una línea que dice "Direct consequence of Lemma...".

---

## Paper 2: arXiv:1303.0730 — "Diagonalizing by Fixed-Points"

**Theorem:** There are infinitely many prime numbers in N
**Proof length:** 1543 chars (self-contained Euclid-style proof)
**Delegation flag:** none

| Attempt | Result | Time | Rounds |
|---------|--------|------|--------|
| 1 | ❌ LIMIT | ~6 min | 6 API calls |
| 2 | ❌ LIMIT | ~7 min | 6 API calls |
| 3 | ❌ LIMIT | ~6 min | 6 API calls |

**Total time:** 1131s (~19 min, 18 API calls)
**Final status:** FAILED — All 3 attempts failed

---

## Summary

| Métrica | 002 (flash, 3 rounds) | 003 (pro, 6 rounds) |
|---------|----------------------|---------------------|
| Papers procesados | 2 | 2 |
| Éxitos | 0 | 0 |
| Tasa de éxito | 0% | 0% |
| API calls totales | 9 | **36** |
| Tiempo total | 600s (10 min) | 2616s (44 min) |
| Modelo | deepseek-v4-pro (implícito) | deepseek-v4-pro (explícito) |
| Rondas por intento | 3 | **6** |
| Delegados salteados | ✅ (1 ahorrado) | ❌ (corrieron, fallaron) |

---

## Comparación directa 002 → 003

| Factor | 002 | 003 | ¿Cambió algo? |
|--------|-----|-----|---------------|
| Modelo | pro | pro | No (ya era pro) |
| Rondas | 3 | 6 | **Sí** — el doble |
| API calls/paper | 9 | 18 | **2×** |
| Tiempo/paper | ~10 min | ~22 min | **2.2×** |
| Resultado | 0/2 | 0/2 | **No** |

**Conclusión:** Duplicar las rondas no cambió el resultado. El modelo consistentemente no puede producir código Lean 4 compilable para estas pruebas, ni con 3 ni con 6 rondas de feedback de errores. El problema es de **capacidad de razonamiento matemático del modelo**, no de presupuesto de rondas.

---

## Diagnosis final

El cuello de botella es la **capacidad del modelo**. Deepseek-v4-pro no logra formalizar pruebas matemáticas no triviales desde LaTeX a Lean 4, incluso con 6 rondas de feedback de errores de compilación por intento.

**Evidencia acumulada en 3 corridas:**
- 002: 0/2 (pro, 3 rondas, 9 API calls)
- 003: 0/2 (pro, 6 rondas, 36 API calls)
- Total: 45 API calls, 0 éxitos

**Recomendación:** Probar con Claude Code (agentic, loop interno más largo, mejor en razonamiento matemático) o restringir el pipeline a matches formales (Mathlib) donde el D3 ya funciona sin formalización adicional.
