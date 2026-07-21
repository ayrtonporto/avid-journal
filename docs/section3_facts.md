# Hechos técnicos para §3 (The AViD Pipeline) — sobre avid-clean/

**Propósito:** dossier de hechos verificados con ubicación en código, sin prosa de paper.
**Alcance:** `avid-clean/` (el orquestador que corrió Run 002, model comparison, wide study).
**Formato:** `archivo:línea` para cada afirmación.
**Regla:** donde avid-clean difiera de `src/`, se marca explícitamente. Donde reusa `src/`, se declara.

---

## BLOQUE 1 — Parsing e ingesta (§3.1)

### Diferencia con src/: el parser es una copia, el orquestador es nuevo
- `src/` tenía su propio orquestador + parser en `src/parser/` + `src/formalization/orchestrator.py`.
- `avid-clean/` tiene:
  - **Parser:** `avid-clean/parser/latex_parser.py` — **copia byte-idéntica** de `src/parser/latex_parser.py`. Mismos `MATH_ENVIRONMENTS` (línea 20), mismos `ENVIRONMENT_VARIANTS` (líneas 23-38), mismo mecanismo regex (línea 56-57), misma auto-detección de `\newtheorem` (líneas 316-352).
  - **Orquestador:** `avid-clean/formalization/orchestrator.py` — **nuevo**, model-agnostic (ver Bloque 2).
  - El orquestador importa el parser local: `from parser.latex_parser import LaTeXParser` (línea 88).

### Formato de entrada y módulo
- Acepta archivos `.tex` (LaTeX source).
  - `avid-clean/parser/latex_parser.py:444-465` — `parse_file()` exige `.tex`.
  - `avid-clean/formalization/orchestrator.py:773` — `LaTeXParser()`.

### Entornos extraídos (idéntico a src/)
- Entornos base: `definition`, `theorem`, `lemma`, `proposition`, `corollary`.
  - `avid-clean/parser/latex_parser.py:20`.
- Variantes: `teorema`, `definicion`/`definición`, `lema`, `proposicion`/`proposición`, `corolario`, `thm`, `defn`, `def`, `lem`, `prop`, `cor`, `corol`.
  - `avid-clean/parser/latex_parser.py:23-38`.
- Auto-detección de `\newtheorem` y `\theoremstyle`.
  - `avid-clean/parser/latex_parser.py:316-352`.

### Entornos que se PIERDEN (idéntico a src/)
- Regex compilado con nombres conocidos (línea 56-57). Cualquier variante no listada se pierde.
- `remark` y `example`: el parser los extrae, pero el orquestador los descarta.
  - `avid-clean/formalization/orchestrator.py:414-421` — `FORMALIZABLE_TYPES = frozenset({...})`.

### Localización del "teorema principal" y orden
- Sin mecanismo explícito (idéntico a src/).
- Topological sort vía `\ref{}`:
  - `avid-clean/formalization/orchestrator.py:127-170` — `topological_sort()` (Kahn).
  - Dependencias vía `extract_references()` en el parser (línea 126-146).

---

## BLOQUE 2 — Formalización (§3.1)

### DIFERENCIA CLAVE: backend multi-modelo
- **src/ hacía:** solo Claude Code, invocado como subprocess (`_run_claude_on_target`).
- **avid-clean hace:** abstracción `ModelProvider` con registry de 8 backends.

### Arquitectura de providers
- **Interfaz:** `ModelProvider` (ABC) en `avid-clean/formalization/providers/base.py:49-78`.
  - Método abstracto: `formalize(target_path, prompt, max_rounds, cwd) → FormalizationResult`.
- **Dos familias:**
  1. `AgenticProvider` (base.py:81-89): el modelo maneja su propio loop de verificación. Usado por Claude Code.
  2. `APIProvider` (base.py:92-125): API de chat sin loop interno. El sistema ejecuta `verification_loop()`. Usado por OpenAI, DeepSeek, OpenRouter, Mistral, Gemini.
- **Registry** en `avid-clean/formalization/providers/config.py:129-138`:
  - `opencode` (OpenCode Go, DeepSeek V4 Pro/Flash — **default**, línea 159)
  - `claude` (Claude Code CLI, agentic)
  - `anthropic` (Claude Sonnet 4 vía API Anthropic)
  - `openai` (GPT-4o)
  - `deepseek` (DeepSeek Chat V3 directo)
  - `openrouter` (cualquier modelo vía OpenRouter)
  - `mistral` (Mistral Large)
  - `gemini` (Gemini 2.5 Pro)
- **Resolución:** `resolve_provider()` — prioridad: parámetro explícito > `AVID_MODEL_PROVIDER` > `"opencode"`.
  - `config.py:141-170`.
- **Provider `opencode` (default):** `OpenAIChatProvider` con `base_url="https://opencode.ai/zen/go/v1"`, modelo `"deepseek-v4-pro"`.
  - `config.py:39-51`.
  - `openai_compatible.py:33-58` — temperatura 0.0, max_tokens 4096, 3 retries.
- **Provider `claude` (agentic):** `ClaudeCodeProvider` en `providers/claude_code.py:67-312`.
  - Lanza `claude` CLI como subprocess con `--output-format stream-json`.
  - Loop de continuación: primer llamado con prompt vía stdin, rondas siguientes con `claude -c --prompt "continue"`.
  - Rate-limit detection: `_PAT_RATE_LIMIT` (líneas 37-42).
  - Resuelve binario en Windows vía `shutil.which` (líneas 45-59).

### Cómo se invoca el modelo
- `avid-clean/formalization/orchestrator.py:333-380` — `_run_model_on_target()`:
  - Construye prompt = system prompt (archivo de modo) + TASK.md.
  - Llama a `provider.formalize(target_path, full_prompt, max_rounds, cwd)`.
  - Rate-limit detection: si `result.info == "RATE_LIMITED"`, aborta.

### Loop de verificación para API providers
- `avid-clean/formalization/scripts/verification_loop.py:24-93` — `verification_loop()`:
  1. Enviar prompt → recibir respuesta.
  2. Extraer código Lean (`_extract_lean_code`, busca bloques ```lean).
  3. Escribir en `target_path`.
  4. Compilar con `check_lean_file()` (importado de `src.formalization.scripts.lean_checker`).
  5. Si `has_error` o `has_sorry`: construir feedback con errores, reenviar.
  6. Si `not has_error and not has_sorry`: éxito → `FormalizationResult(success=True)`.
  7. Máximo `max_rounds` iteraciones.

### Modos de formalización (idéntico a src/)
- `avid-clean/formalization/complexity.py` — importado desde `src/` por el orquestador (línea 71-76).
  - `Mode.SIMPLE` (5 rondas), `Mode.MEDIUM` (15 rondas), `Mode.HARD` (30 rondas), `Mode.EXTERNAL` (sin modelo, emite axioma).
- **NO existe `Mode.STATEMENT_ONLY`.** El enum solo tiene 4 valores.
  - `complexity.py:15-21`.

### Statement-only (`:= by sorry`): existe como prompt, no como modo
- **El código RECHAZA `sorry`.** Tanto `verification_loop.py:73` como `check_lean_file` (línea 120) tratan `has_sorry=True` como fallo.
- **Run 002 y model comparison 001-c SÍ usaron statement-only**, pero mediante:
  - Prompts modificados que instruían al modelo a generar solo el enunciado con `:= by sorry` (`docs/scout_001c.md:75`).
  - El experimento (`run_experiment_001.py` o similar) debió relajar el criterio de éxito — aceptando `has_error=False` aunque `has_sorry=True`.
  - `docs/model_comparison_001c.md:1-5` confirma: "statement-only mode (:= by sorry)" con Qwen 3.7-max, 5/5 papers.
- **INCONSISTENCIA:** el paper brief describe statement-only como si fuera una capacidad del pipeline. El código base de avid-clean NO lo soporta sin modificar el criterio de éxito en `_run_block()` o `verification_loop()`.

### Criterio de éxito de formalización
- `check_lean_file()` en `avid-clean/formalization/scripts/lean_checker.py:78-122` (idéntico a `src/`):
  1. `lake env lean <archivo>`, timeout 180s.
  2. `has_error = (returncode != 0) or (diagnóstico de error Lean)`.
  3. `has_sorry_warning = True` si `declaration uses 'sorry'`.
  4. Éxito = `not has_error and not has_sorry_warning`.
- **Guardia anti-vacío** en `avid-clean/formalization/orchestrator.py:467-475`:
  - `_has_real_declaration()` — busca keywords Lean (`def`, `theorem`, `lemma`, etc.).
  - Idéntica a `src/`.
- El orquestador aplica ambas verificaciones en secuencia (líneas 620-634):
  1. `check_lean_file(target_path)` → rechaza errores y sorry.
  2. `_extract_declarations(target_path)` + `_has_real_declaration()` → rechaza archivos vacíos.

### Fidelity check
- **No existe** en avid-clean (igual que en src/). No hay comparación semántica entre el enunciado informal y el Lean generado.

### Flujo por bloque
- `avid-clean/formalization/orchestrator.py:550-697` — `_run_block()`:
  1. Escribe stub Lean con banner + `import {paper_module}`.
  2. Renderiza `TASK.md` con dependencias ya formalizadas (`satisfied_deps`).
  3. Invoca `_run_model_on_target()` con el provider resuelto.
  4. Verifica compilación (`check_lean_file`).
  5. Extrae código (`_extract_declarations`, líneas 387-411) + guardia anti-vacío.
  6. Acumula en `Paper.lean` y registra en `PAPER_INDEX.md`.
  7. Re-compila módulo Paper (`_lake_build_paper_module`).

---

## BLOQUE 3 — Las tres dimensiones (§3.2)

### AVISO: las dimensiones viven en src/, no en avid-clean/
- `avid-clean/` es el orquestador de **formalización** (LaTeX → Lean). No contiene código de novelty checking.
- Las dimensiones D1, D2, D3 se ejecutan como paso separado desde `src/novelty_v2/`.
- **El árbol de veredictos y las tres dimensiones son IDÉNTICOS** independientemente de qué orquestador formalizó el paper.
- A continuación se documentan con referencias a `src/` (único lugar donde existen).

### D1 — No-existencia previa
- **Archivo:** `src/novelty_v2/dimensions/d1_existence.py`
- **Rama C_F (formal):** Leandex API v2.
  - `src/novelty/mathlib_checker.py:27` — endpoint `https://leandex.projectnumina.ai/api/v1/search`.
  - Leandex v2 NO proporciona scores de similitud (línea 132-134).
  - `check_in_mathlib()` → `MathlibResult` con `found: bool` y `matches: List[MathlibMatch]`.
- **Fallback `exact?`:** en el orquestador de novelty (no en avid-clean).
  - `src/novelty_v2/orchestrator.py:207-249` — ejecuta `example : τ := by exact?`, budget 15s.
- **Rama C_I (informal):**
  - **Stage A:** arXiv + Semantic Scholar + TheoremSearch (opcional) + filtro MiniLM.
    - `d1_existence.py:99-172`.
    - Threshold `CI_SIMILARITY_THRESHOLD_A = 0.40` (línea 45).
    - **INCONSISTENCIA CON PAPER_BRIEF:** el brief dice que se bajó a 0.25 ("demasiado alto, 0 candidatos"). El código tiene 0.40. No se encuentra commit que lo haya cambiado.
  - **Stage B:** LLM Judge (DeepSeek V4 Flash, temperature=0).
    - `src/novelty/llm_judge.py:40` — modelo `deepseek-v4-flash`.
    - 4 veredictos: `equivalent`, `generalization`, `specialization`, `different` (línea 41).

### D2 — No-trivialidad
- **Archivo:** `src/novelty_v2/dimensions/d2_triviality.py`
- **Tácticas:** `["decide", "norm_num", "simp", "omega", "tauto", "aesop"]` (líneas 34-41).
- **Presupuestos:** 10s para todas, 30s para `aesop` (líneas 48-55).
  - Overhead de startup: `LEAN_STARTUP_OVERHEAD_S = 45` (línea 46).
- **Blacklist:** `norm_num` saltado si enunciado contiene `"Irrational"` (líneas 61, 167-168).
- **`exact?` REMOVIDO** de D2, movido a D1 (líneas 31-33).

### D3 — Distancia estructural
- **Archivo:** `src/novelty_v2/dimensions/d3_premises.py`
- **Identidad canónica:** `(defPath, defPos)` → `"{def_path}:{line}:{col}"` (líneas 31-41).
- **Pipeline:** deduplicar → Filtro 1 (namespace blacklist: `Init.`, `Lean.`) → Filtro 2 (statement lines) → Jaccard.
- **Filtro 1 config:** `config/d3_filter_blacklist.yaml` (prefijos `Init.` y `Lean.`).
- **Jaccard:** `1 - |intersection| / |union|` (líneas 142-184).
- **Umbral θ:** `0.5` en `types.py:130` (`D3Result.umbral_theta`).
  - `pruebas_distantes = True` si `jaccard > 0.5` (`d3_premises.py:245-247`).
- **Extracción:** `lean_project/ExtractData.lean` (519 líneas, Windows nativo).
  - `src/novelty_v2/premise_extraction.py:114-306` — wrapper Python con caché SHA256.

---

## BLOQUE 4 — Los corpus de referencia (§3.3)

### IDÉNTICO a src/ — avid-clean importa de src/
- El manejo de `Paper.lean`, `PAPER_INDEX.md` y `LeanProjectManager` es código compartido.
- `avid-clean/formalization/orchestrator.py:78-84` importa:
  ```python
  from src.formalization.lean_project import (
      AVID_REPO_ROOT, DEFAULT_PARENT_PROJECT,
      LeanProjectManager, create_paper_project, slugify,
  )
  ```
- Por tanto, toda la lógica documentada en el dossier anterior sobre Bloque 4 aplica exactamente igual.

### Contra qué se compara
1. **C_F (formal):** Mathlib v4.29.0 vía Leandex API.
   - `src/novelty/mathlib_checker.py:27`.
2. **C_I (informal):** arXiv + Semantic Scholar + TheoremSearch.
   - `src/novelty_v2/dimensions/d1_existence.py:122-149`.
   - `src/novelty/arxiv_search.py`.

### Base paralela (Paper.lean + PAPER_INDEX)
- `LeanProjectManager` en `src/formalization/lean_project.py`:
  - `register_block()` (línea 456) — acumula entradas en `PAPER_INDEX.md`.
  - `get_processed_blocks()` (línea 405) — lee el índice para modo resume.
  - `append_block()` (línea 386) — acumula código Lean en `Paper.lean`.
- **Modo resume en avid-clean:**
  - `avid-clean/formalization/orchestrator.py:829-867` — lee `PAPER_INDEX.md`, saltea bloques `verified`/`axiom`, reintenta `failed`.
- **Incrementalidad:** todos los papers comparten `lean_project/` y `.lake/`. Cada paper es `Papers/<ModuleName>/`. Los bloques formalizados quedan como dependencias Lean para papers futuros.

---

## BLOQUE 5 — El árbol de veredictos (§3.4)

### IDÉNTICO a src/ — no hay código de novelty en avid-clean/
- `avid-clean/` solo formaliza (LaTeX → Lean). El árbol de veredictos se ejecuta después, desde `src/novelty_v2/orchestrator.py`.
- Por tanto, los 8 veredictos, el árbol de decisión D2→D1→D3, y la lógica de composición son exactamente los documentados en la versión anterior del dossier.

### Los 8 veredictos (src/novelty_v2/types.py:21-52)
1. **`NOVEDAD_ENUNCIADO`** — sin match en C_F ni C_I.
2. **`NOVEDAD_DEMOSTRACION`** — match en C_F, D3 indica pruebas distantes.
3. **`CONOCIDO_LITERATURA`** — match en C_I, sin match en C_F.
4. **`NO_NOVEDOSO_redundante`** — match en C_F, D3 indica misma prueba.
5. **`NO_NOVEDOSO_trivial`** — D2 cierra con táctica estándar.
6. **`ZONA_GRIS`** — generalization/specialization según LLM judge.
7. **`MATCH_ENCONTRADO_PENDIENTE_D3`** — match en C_F, D3 pendiente.
8. **`INCONCLUSIVE`** — D3 ejecutado, premisas vacías tras filtros.

### Árbol de decisión (src/novelty_v2/orchestrator.py:60-307)
```
D2 → trivial? → NO_NOVEDOSO_trivial (FIN)
  ↓ no
D1 C_F (Leandex) → match?
  ├── SÍ → D3 → distantes? → NOVEDAD_DEMOSTRACION
  │             → cercanas?  → NO_NOVEDOSO_redundante
  │             → vacías?    → INCONCLUSIVE
  │             → no disponible → MATCH_ENCONTRADO_PENDIENTE_D3
  └── NO → exact? fallback (mismo camino que C_F si match)
           └── NO → D1 C_I (arXiv/SS + LLM judge)
                    ├── equivalent → CONOCIDO_LITERATURA
                    ├── generalización/especialización → ZONA_GRIS
                    └── different/sin candidatos → NOVEDAD_ENUNCIADO
```

### Orden por costo
- `paper/metric_spec.md:98`: D2 (local, barato) → D1 C_F (API rápida) → D1 C_I (caro) → D3 (más caro).
- `exact?` como optimización: después de Leandex, antes de C_I.

---

## Resumen de diferencias avid-clean vs src/

| Aspecto | src/ | avid-clean/ |
|---|---|---|
| Parser | `src/parser/latex_parser.py` | `avid-clean/parser/latex_parser.py` (copia idéntica) |
| Backend de formalización | Solo Claude Code (subprocess) | 8 providers vía `ModelProvider` (registry) |
| Provider default | Claude Code | OpenCode Go (DeepSeek V4 Pro) |
| Verificación de compilación | `check_lean_file` directo | `check_lean_file` + `verification_loop` (API) o Claude Code (agentic) |
| Statement-only mode | No existe | No existe como código (fue via prompts modificados + criterio relajado en Run 002) |
| PAPER_INDEX | `src/formalization/lean_project.py` | Importado de `src/` — idéntico |
| Árbol de veredictos | `src/novelty_v2/orchestrator.py` | No existe en avid-clean; se ejecuta desde `src/` — idéntico |
| Guardia anti-vacío | `_has_real_declaration()` | Idéntica |
| Fidelity check | No existe | No existe |

## Inconsistencias detectadas

1. **Threshold C_I: código 0.40 vs paper brief 0.25.**
   - `src/novelty_v2/dimensions/d1_existence.py:45` → `CI_SIMILARITY_THRESHOLD_A = 0.40`.
   - `paper/PAPER_BRIEF.md` menciona que se bajó a 0.25. No se encuentra commit que refleje este cambio.

2. **Statement-only mode: el paper brief lo trata como capacidad del sistema; el código lo rechaza.**
   - `verification_loop.py:73` exige `not has_error and not has_sorry`.
   - `check_lean_file` detecta `sorry` y lo reporta como `has_sorry=True`.
   - Run 002 usó prompts modificados + script externo con criterio relajado. Esto no está en el código base de avid-clean.

3. **D3 "on-demand via SQLite queue": el brief menciona una cola SQLite para D3. No existe en el código.**
   - D3 se ejecuta sincrónicamente en `src/novelty_v2/orchestrator.py:_run_d3_if_possible()` o queda como `MATCH_ENCONTRADO_PENDIENTE_D3` cuando no hay premisas disponibles.

4. **θ de D3 = 0.5 sin calibrar.**
   - `types.py:130` — valor inicial. `paper/decisions.md:79` lo declara pendiente de calibración. El brief reporta resultados con este valor sin recalibrar.
