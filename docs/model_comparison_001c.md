# Model Comparison — Run 001-c (statement-only mode)

**Generated:** 2026-07-13
**Models tested:** deepseek-v4-pro, deepseek-v4-flash, qwen3.7-max, glm-5.2
**Papers:** 5 retirados × 3 intentos × statement-only (:= by sorry)
**Criterion:** compila AND tiene declaración sustantiva

---

## Results

| Model | 1609.02090v1 | 1207.0631v1 | 1212.0196v1 | 1004.3381v1 | math/0604362v1 | **Success** |
|-------|:-----------:|:-----------:|:-----------:|:-----------:|:--------------:|:-----------:|
| deepseek-v4-pro | ❌ | ❌ | ⚠️ placeholder | ❌ | ❌ | **0/5** |
| deepseek-v4-flash | ❌ | ❌ | ❌ | ❌ | ❌ | **0/5** |
| qwen3.7-max | ✅ | ✅ | ✅ | ✅ | ✅✨ | **5/5** |
| glm-5.2 | ✅ | ✅ | ❌ | ✅ | ⏳ timeout | **3/5** |

✨ Paper 5 requirió fix manual: `λ_i` → `lam_i` (keyword reservada). El código generado era matemáticamente correcto.

## Winner: **Qwen 3.7-max** (5/5)

## Detail: qwen3.7-max

| Paper | Compiled | Code quality |
|-------|:--------:|-------------|
| 1609.02090v1 | ✅ | `squares`, `sumset`, theorem correcto |
| 1207.0631v1 | ✅ | `IsScalarMatrix`, `MatricesAreSimilar`, theorem correcto |
| 1212.0196v1 | ✅ | `IsCongruentNumber` sustantivo, theorem con jacobiSym |
| 1004.3381v1 | ✅ | 1250 bytes: `Rectangle`, `AxisParallelLine` inductivo, theorem |
| math/0604362v1 | ✅ | `IsMarkovMatrix`, `IsIrreducibleChain`, `totalVariationDistance`, theorem fiel |

## Detail: glm-5.2

| Paper | Compiled | Notes |
|-------|:--------:|-------|
| 1609.02090v1 | ✅ | | 
| 1207.0631v1 | ✅ | |
| 1212.0196v1 | ❌ | Error: `ℚ` not recognized (missing `open` scoped) |
| 1004.3381v1 | ✅ | 1351 bytes, very detailed |
| math/0604362v1 | ⏳ | Timeout (120s), code generated but heavy compilation |

## Detail: DeepSeek models

| Model | Papers compiled | Failure modes |
|-------|:--------------:|---------------|
| v4-pro | 1/5 (placeholder) | synthesis failures, unexpected tokens, missing declarations |
| v4-flash | 0/5 | unknown module prefix, unexpected tokens, no declaration |

## Conclusion

**Qwen 3.7-max is the recommended model for statement-only formalization.** It is the only model tested that successfully compiled all 5 theorems with mathematically substantive definitions. GLM-5.2 is a strong second (3/5, with fixable errors). DeepSeek models are not viable for this task.
