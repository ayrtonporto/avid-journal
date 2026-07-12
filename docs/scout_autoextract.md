# Scout Auto-Extraction — Phase 0 Reconnaissance

**Date:** 2026-07-04
**Status:** COMPLETED — waiting for confirmation before Phase 1

---

## 1. Procedimiento manual actual de extracción

### Comando exacto

```bash
cd D:/Mis documentos/Documentos/AViD Journal/lean_project
lake env lean --run ExtractData.lean Papers/D3_Calibration/Paper.lean
```

### Prerrequisito

El archivo target debe estar compilado (`.olean` presente). Esto se hace con:

```bash
lake build Papers.D3_Calibration.Paper
```

Sin el `.olean`, ExtractData falla con `unknown module prefix`.

### Output

Dos archivos generados en `.lake/build/ir/<ruta-relativa>/`:

| Archivo | Tamaño | Contenido |
|---------|--------|-----------|
| `Paper.ast.json` | 4.6 MB | JSON con `premises[]` (379 total, 52 únicos), `tactics[]` (121), `commandASTs[]` |
| `Paper.dep_paths` | 96 B | Rutas de imports a nivel módulo (no útil para D3) |

### Evidencia

Ejecución verificada hoy (2026-07-04):
- START: ~02:33
- END: 02:38:48
- Ambos archivos regenerados con timestamp 02:38
- ast.json: 4,592,137 bytes (idéntico tamaño al anterior)

---

## 2. Puente wsl.exe

### Estado de WSL

```bash
$ wsl.exe -l -v
  NAME              STATE      VERSION
* Ubuntu-22.04      Stopped    2
```

WSL existe pero:
- **Lean NO está instalado/funcional** (`lean` no está en PATH)
- **Mathlib cache corrupta** (documentado en CLAUDE.md: "Mathlib cache corrupta → requiere rebuild")
- El repo está clonado en `~/avid-journal/` (usuario `ayrton`)

### El puente funciona para comandos básicos

```bash
$ wsl.exe -e bash -c "echo 'WSL bridge works' && uname -a"
WSL bridge works
Linux Moto-Z4 6.18.33.2-microsoft-standard-WSL2 ... x86_64 GNU/Linux
```

Pero no hay nada útil que ejecutar dentro de WSL porque Lean no está configurado.

---

## 3. CRONOMETRAJE

### Extracción de Paper.lean (6 teoremas, `import Mathlib`)

| Métrica | Valor |
|---------|-------|
| Tiempo total | **~4-5 minutos** |
| Premisas extraídas | 379 total, 52 únicas |
| Tácticas | 121 |
| Tamaño del ast.json | 4.6 MB |
| WARNINGs (dep_paths) | ~50 líneas (esperado, no afecta premisas) |

Los WARNINGs son normales: `findLean` en ExtractData.lean tiene path resolution frágil en Windows.
La línea `assert!` fue relajada a warning (documentado en CLAUDE.md). Las premisas se extraen
correctamente a pesar de los warnings.

### Tiempo histórico

CLAUDE.md documenta:
- "ExtractData on a file with import Mathlib takes 2-5 minutes"
- "On individual Mathlib source files (e.g. Irrational.lean), it's faster (~30-60s)"
- "First run is slowest; olean cache helps subsequent runs"

Mi medición de hoy (4-5 min) es consistente con el rango documentado. El archivo ya estaba
compilado (`lake build` previo), así que el tiempo es de re-elaboración con oleans cacheados.

### ¿Hay que repetir el trazado inicial del proyecto?

**No.** El `lake build` ya está hecho. ExtractData solo necesita el `.olean` del archivo target.
El `lake build Papers.D3_Calibration.Paper` toma ~15-20s en warm cache (ya ejecutado antes).
Lo que tarda 4-5 minutos es la re-elaboración que hace ExtractData al procesar los comandos
con `IO.processCommands`, porque `import Mathlib` carga todo el entorno.

---

## 4. Formato del ast.json y parseo existente

### Estructura del JSON

```json
{
  "commandASTs": [...],
  "tactics": [{"stateBefore": "...", "stateAfter": "...", "pos": {"byteIdx": N}, "endPos": {"byteIdx": M}}],
  "premises": [
    {
      "fullName": "irrational_nrt_of_notint_nrt",
      "modName": "Mathlib.NumberTheory.Real.Irrational",
      "defPath": ".lake/packages/mathlib/Mathlib/NumberTheory/Real/Irrational.lean",
      "defPos": {"line": 59, "column": 0},
      "defEndPos": {"line": 74, "column": 0},
      "pos": {"line": 71, "column": 6},
      "endPos": {"line": 71, "column": 34}
    }
  ]
}
```

### Parseo existente

La función `load_premises_from_ast()` en `src/novelty_v2/dimensions/d3_premises.py:256`
ya parsea el ast.json y devuelve `List[dict]` en el formato exacto que `compute_d3` espera:

```python
def load_premises_from_ast(
    ast_json_path: str | Path,
    theorem_line_start: int,
    theorem_line_end: int,
) -> List[dict]:
```

Filtra por rango de líneas y devuelve los dicts con `fullName`, `modName`, `defPath`, `defPos`, `pos`.

**No hace falta crear nuevo código de parseo.** Esta función ya existe y es la que usa
`scripts/validate_d3.py` y los tests de integración.

---

## 5. Decisión de arquitectura

### ExtractData corre en Windows, no en WSL

Hecho comprobado: la extracción funciona con `lake env lean` en Windows nativo.
El WSL no tiene Lean funcional. El puente `wsl.exe` no es necesario para la extracción.

**Implicación para el diseño del módulo:** en lugar de `wsl.exe -e bash -c "..."`,
el módulo `premise_extraction.py` debe usar `subprocess.run()` llamando a `lake` directamente
en Windows. Esto simplifica el código, elimina la dependencia de WSL, y es consistente
con cómo ya funciona D2 (`check_triviality` también usa `lake env lean` en Windows).

### Tiempo por extracción: ~4-5 minutos

Está por debajo del umbral de pivote (15 minutos). Pero es lo suficientemente alto como
para que la extracción en vivo durante el pipeline no sea práctica. El diseño debe priorizar:

1. **Caché agresiva** (hash del archivo → resultado parseado)
2. **Precalentamiento batch** (correr de noche sobre todos los pares)
3. **Degradación elegante** (timeout, fallo → None, nunca excepción)

---

## 6. Confirmación (2026-07-04)

**Decisión:** Windows nativo únicamente. `subprocess.run(["lake", "env", "lean", "--run", ...])`
con `cwd` apuntando a `lean_project/`. Sin backend wsl.exe, sin preparación para el futuro.

**Timeout default:** 15 minutos (3× el tiempo medido de ~5 min).

**Camino principal de producción:** prewarm batch nocturno → pipeline lee caché.
La extracción en vivo durante `run_eval_full.py` es el caso excepcional, no el diseño central.

---

## 7. Future work: optimización de imports mínimos

El archivo `Papers/D3_Calibration/Paper.lean` usa `import Mathlib` (monolítico), que
fuerza al elaborador a cargar todo Mathlib. Si los archivos de teoremas usaran imports
mínimos (ej. `import Mathlib.Data.Real.Irrational` en vez de `import Mathlib`), la
extracción sería mucho más rápida (~30-60s según CLAUDE.md, en vez de 4-5 min).

Esto requiere:
- Identificar los imports mínimos para cada teorema del eval set
- Recompilar los archivos con imports acotados
- Verificar que ExtractData produce los mismos conjuntos de premisas

**No implementado en esta tarea.** Se deja anotado como optimización independiente.
