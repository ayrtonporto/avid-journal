# Model Comparison — Run 001-c (statement-only mode)

**Generated:** 2026-07-12/13  
**Models tested:** deepseek-v4-pro, deepseek-v4-flash  
**Papers:** 5 retirados × 3 intentos × statement-only (:= by sorry)  
**Criterion:** compila AND tiene declaración AND fidelity_check = pass

---

## Results

| Model | 1609.02090v1 | 1207.0631v1 | 1212.0196v1 | 1004.3381v1 | math/0604362v1 | Success rate |
|-------|:-----------:|:-----------:|:-----------:|:-----------:|:--------------:|:------------:|
| **deepseek-v4-pro** | ❌ | ❌ | ⚠️ compila, no fiel | ❌ | ❌ | 0/5 |
| **deepseek-v4-flash** | ❌ | ❌ | ❌ | ❌ | ❌ | 0/5 |
| **qwen3.7-max** | — | — | — | — | — | not run |
| **glm-5.2** | — | — | — | — | — | not run |

## Detail: deepseek-v4-pro

| Paper | Compiled | Fidelity | Notes |
|-------|----------|----------|-------|
| 1609.02090v1 | ❌ | — | Compilation errors (HAdd instance, unexpected token) |
| 1207.0631v1 | ❌ | — | Compilation errors |
| 1212.0196v1 | ✅ | ❌ fail | `def CongruentNumber := True` (placeholder) — prompt mejorado produjo `def IsCongruentNumber := n > 0 ∧ ∃ a b c, ...` pero sin theorem |
| 1004.3381v1 | ❌ | — | Compilation errors |
| math/0604362v1 | ❌ | — | Compilation errors |

## Detail: deepseek-v4-flash

| Paper | Compiled | Fidelity | Notes |
|-------|----------|----------|-------|
| 1609.02090v1 | ❌ | — | Compilation errors |
| 1207.0631v1 | ❌ | — | Compilation errors |
| 1212.0196v1 | ❌ | — | No declaration found / compilation errors |
| 1004.3381v1 | ❌ | — | Compilation errors |
| math/0604362v1 | ❌ | — | Compilation errors |

## Common failure modes

1. **Unknown module prefix** — model writes code before `import Mathlib` or uses wrong module paths
2. **Synthesis failures** — `failed to synthesize instance` for typeclasses (e.g., `HAdd (Set (ZMod n))`)
3. **Unexpected tokens** — the model produces syntactically invalid Lean (e.g., `}` without `{`)
4. **Missing theorem declaration** — model defines auxiliary concepts but forgets the `theorem` keyword

## Conclusion

**Neither DeepSeek model can reliably formalize theorem statements in Lean 4 under the statement-only protocol.** DeepSeek v4 Pro managed to compile 1/5 but with a placeholder definition. DeepSeek v4 Flash compiled 0/5. The fidelity check correctly flagged the placeholder case.

**Recommendation:** Test qwen3.7-max and glm-5.2 (available via OpenCode Go) or obtain an API key for GPT-4o / Claude via OpenRouter for comparison.
