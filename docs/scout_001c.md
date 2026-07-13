# Scout 001c — Reconstrucción del estado real

**Generado:** 2026-07-12  
**Propósito:** Determinar qué código está realmente en disco tras la Run 001-b fallida, antes de cualquier acción correctiva.

---

## 1. Git status

```
On branch main (ahead 6)
Changes not staged:
  modified:   scripts/run_experiment_001.py

Untracked:
  docs/experiment_run_001b_report.md
  results/experiment_run_001b.csv
  results/formalizations/
```

**Conclusión:** Los dos parches sobre `run_experiment_001.py` SÍ están en el working tree (modificado, no commiteado). El diff confirma ambos hunks:
- **Hunk 1 (líneas 162-177):** fallback a `reasoning_content` cuando `content` está vacío.
- **Hunk 2 (líneas 225-236):** extracción de bloques de código ```lean...``` del texto de reasoning.

---

## 2. Estado de los .lean en `results/formalizations/`

| Archivo | Bytes | Contenido real |
|---------|-------|---------------|
| `1609_02090v1.lean` | 5877 | ❌ Raw reasoning_content (chat del modelo, no código) |
| `1207_0631v1.lean` | 399 | ✅ Código Lean válido (`import Mathlib`, `theorem ... := by\n  -- sorry`) |
| `1212_0196v1.lean` | 129 | ⚠️ Fragmento mínimo (`def Congruent (n : ℕ) : Prop := ...`) |
| `1004_3381v1.lean` | 7790 | ❌ Raw reasoning_content |
| `math_0604362v1.lean` | 8074 | ❌ Raw reasoning_content |

**Explicación:** El fix de extracción de código (`re.search(r"```(?:lean)?...")`) solo encontró bloques de código en los papers 2 y 3. Para los papers 1, 4 y 5, el `reasoning_content` no contenía un bloque markdown ```lean bien formado, y el fallback (strip de fences) dejó todo el reasoning como "código". El archivo resultante no compila (es lenguaje natural).

---

## 3. HALLAZGO RETROACTIVO: Run 001 original fue artefacto

**Defecto:** En la Run 001 original (2026-07-06), los 5 `.lean` eran de **0 bytes**. El script `_verify_lean` escribe el `lean_code` (vacío, porque la API devolvía `content: ""`) a disco, y luego ejecuta `lake env lean <file>`. **Lean 4 compila archivos vacíos con exit code 0.**

**Consecuencia:** El reporte original de "5/5 formalizados" era falso. Los archivos vacíos no contienen ningún teorema. Los veredictos `MATCH_ENCONTRADO_PENDIENTE_D3` se basaron en código Lean inexistente.

**Registrar como defecto instructivo para el paper:** La herramienta de verificación debe incluir una guardia anti-vacío (ver PARTE 1). Lean no falla ante archivos vacíos — es responsabilidad del pipeline detectar este caso.

---

## 4. ¿Qué parches se aplicaron y cuáles no?

| Parche | Estado | Efecto |
|--------|--------|--------|
| Fallback `reasoning_content` | ✅ Aplicado | Los 5 papers ahora tienen contenido en .lean (antes: 0 bytes) |
| Extracción bloque ```lean | ✅ Aplicado (parcial) | Solo funciona si el modelo pone código en fences. Funcionó en 2/5. |
| Guardia anti-vacío | ❌ NO aplicado | Un archivo con reasoning puro (sin declaraciones Lean) se considera "compilado" si Lean no da error de sintaxis |

**Conclusión:** Los parches aliviaron el síntoma (archivos vacíos → archivos con contenido) pero no resolvieron la causa raíz: la formalización vía API casera no produce código Lean compilable. Se requiere migrar al pipeline real (PARTE 2).
