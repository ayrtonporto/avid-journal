# Scout 001c — Diagnóstico pre-Run 001-c (statement-only)

**Generado:** 2026-07-12  
**Propósito:** Resolver dos confusores antes de concluir sobre DeepSeek.

---

## Confusor 1: ¿El loop exige demostración real o acepta `sorry`?

### Evidencia

**Verification loop** (`avid-clean/formalization/scripts/verification_loop.py:73`):

```python
if not has_error and not has_sorry:
    return FormalizationResult(success=True, ...)
```

Condición de éxito: **`not has_error AND not has_sorry`**. Ambos deben ser falsos.

**Lean checker** (`lean_checker.py:120`):

```python
has_sorry_warning = bool(_LEAN_SORRY_RE.search(combined))
# Regex: r"declaration uses ['`\"]?sorry['`\"]?"
```

El checker detecta `sorry` como warning y lo reporta.

### Conclusión

El loop **RECHAZA `sorry`**. El modelo no puede usar `theorem foo := by sorry` — debe producir una demostración completa. Para el experimento de retirados, donde solo necesitamos el ENUNCIADO para pasarlo a D1/D2/D3, esto es contraproducente: fuerza al modelo a intentar probar teoremas arbitrarios desde cero.

**Acción:** PARTE 1 — Modo `statement_only` que acepte `:= sorry`.

---

## Confusor 2: Path mismatch entre orchestrator y run_experiment_001.py

### Evidencia

El error del Paper 1 en Run 001-c:
```
Pipeline error: [Errno 2] No such file or directory:
'lean_project\\Papers\\160902090v1\\Blocks\\SquaresZn.lean'
```

**Orchestrator** escribe en `manager.project_dir / "Blocks" / f"{lean_name}.lean"`  
→ `lean_project/Papers/160902090v1/Blocks/SquaresZn.lean`

**run_experiment_001.py** construye:
```python
project_dir = Path(paper_result["project_dir"])
lean_name = block.get("lean_name", "")
block_path = project_dir / "Blocks" / f"{lean_name}.lean"
```

### Hipótesis

El bloque NO llega a `✅ verified` (llega como `⚠️ axiom`), por lo que `verified_blocks` está vacío. `run_experiment_001.py` cae al `else` y reporta error. El path físico existe pero el script no lo encuentra porque busca solo bloques `✅ verified`.

La ruta EXACTA puede diferir si:
- `lean_name` tiene un sufijo o prefijo añadido por el orchestrator
- El `project_dir` usa un slug ligeramente distinto
- El bloque fue procesado por `_handle_external` (axioma) en vez de `_run_block` (verificación)

### Acción

PARTE 2: aceptar también bloques `⚠️ axiom` como "éxito parcial" (tienen código Lean, solo que sin prueba). O unificar la lectura desde PAPER_INDEX.md.

---

## Nota adicional

El modo `statement_only` propuesto en PARTE 1 implica modificar el prompt para que el modelo sepa que solo debe enunciar (no probar), y relajar el criterio de éxito: `has_error == False` (puede tener `has_sorry == True`).
