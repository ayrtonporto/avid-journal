# AViD Journal — Módulo de Autoformalización

Arquitectura, diseño y justificación del sistema que toma un artículo
matemático en LaTeX y produce código Lean 4 verificado por el compilador.

---

## 1. Novedad: formalización a nivel de paper, no de teorema aislado

El estado del arte en autoformalización (Dong et al., 2024; Numina; AlphaProof)
opera sobre **enunciados individuales**: dado un teorema, producir su prueba en Lean.
AViD Journal extiende esto a **artículos completos** mediante cuatro capacidades
que ningún sistema actual integra:

### 1.1 Parseo estructural de LaTeX

El parser (`src/parser/latex_parser.py`) extrae bloques con tipo semántico:
`definition`, `theorem`, `lemma`, `proposition`, `corollary`. No es un split
por `\begin`/`\end` genérico — identifica labels, referencias cruzadas,
enunciados y pruebas. Un paper con 30 bloques produce 30 tareas de formalización
estructuradas.

### 1.2 Orden topológico por dependencias

Los bloques extraídos se ordenan con el algoritmo de Kahn (BFS sobre grado de
entrada). Si el Teorema 2 referencea a la Definición 1, la definición se
formaliza primero. Esto garantiza que cada bloque tenga disponibles en
`Paper.lean` todas sus dependencias al momento de ser formalizado.

```python
def topological_sort(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Kahn's algorithm sobre el DAG de referencias
    # Complejidad: O(V + E)
```

### 1.3 Paper.lean acumulativo con cacheo incremental

Todos los bloques formalizados se acumulan en un único archivo `Paper.lean`.
Después de cada bloque verificado, se ejecuta `lake build` para generar el
`.olean` compilado. Los bloques subsiguientes importan `Paper.lean` y Lean
carga el `.olean` directamente — sin retypechear los bloques anteriores.
Esto evita que el costo de compilación crezca cuadráticamente con la cantidad
de bloques.

### 1.4 Modo resume con PAPER_INDEX.md

Cada bloque procesado se registra en `PAPER_INDEX.md` con label, tipo, status,
línea en Paper.lean, dependencias y enunciado. Si el pipeline se interrumpe
(rate-limit, crash, Ctrl+C), la siguiente ejecución lee este índice y saltea
los bloques ya verificados. Solo se reintentan los fallidos.

---

## 2. Arquitectura general

```
                        ┌──────────────────────────┐
                        │     formalize_paper()     │  ← entry point público
                        │     orchestrator.py       │
                        └────────────┬─────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
     ┌────────▼────────┐   ┌────────▼────────┐   ┌─────────▼────────┐
     │  LaTeXParser     │   │  topological_    │   │  LeanProject     │
     │  (parser/)       │   │  sort()          │   │  Manager         │
     └────────┬────────┘   └────────┬────────┘   └─────────┬────────┘
              │                      │                      │
              │    ┌─────────────────▼──────────────────┐   │
              │    │  classify() → Mode                  │   │
              │    │  SIMPLE | MEDIUM | HARD | EXTERNAL  │   │
              │    └─────────────────┬──────────────────┘   │
              │                      │                      │
              │    ┌─────────────────▼──────────────────┐   │
              │    │  ModelProvider.formalize()          │   │
              │    │  ┌─────────────────────────────┐    │   │
              │    │  │ ClaudeCodeProvider           │    │   │
              │    │  │ DeepSeekProvider (futuro)    │    │   │
              │    │  │ LeanstralProvider (futuro)   │    │   │
              │    │  │ OpenRouterProvider (futuro)  │    │   │
              │    │  └─────────────────────────────┘    │   │
              │    └─────────────────┬──────────────────┘   │
              │                      │                      │
              │    ┌─────────────────▼──────────────────┐   │
              │    │  check_lean_file()                  │   │
              │    │  (lake env lean → errores/sorry)    │   │
              │    └─────────────────┬──────────────────┘   │
              │                      │                      │
              │    ┌─────────────────▼──────────────────┐   │
              └────►  Paper.lean (acumulativo)           │◄──┘
                   │  PAPER_INDEX.md (persistencia)      │
                   │  REVIEW.md (revisión humana)        │
                   └────────────────────────────────────┘
```

---

## 3. Abstracción de proveedor de modelo

### 3.1 Justificación

El módulo original tenía una dependencia dura en Claude Code: el orchestrator
lanzaba `python -m src.formalization.scripts.run_claude run ...` como subprocess,
sin ninguna abstracción. Cambiar de modelo requería reescribir el orchestrator,
el runner, el CLI y las estructuras de datos.

### 3.2 Diseño

```python
class ModelProvider(ABC):
    """Interfaz uniforme para cualquier modelo que formalice código Lean."""

    @abstractmethod
    def formalize(
        self,
        target_path: Path,      # archivo .lean a editar
        prompt: str,            # prompt completo (incluye TASK.md + system prompt)
        max_rounds: int,        # presupuesto máximo de rondas
        cwd: Path,              # directorio de trabajo (proyecto Lean)
    ) -> FormalizationResult:
        """Ejecuta el modelo sobre la tarea. El modelo debe escribir en target_path."""
        ...

@dataclass
class FormalizationResult:
    success: bool               # True si el código compila sin errores ni sorry
    info: str                   # "COMPLETE" | "LIMIT" | "RATE_LIMITED" | mensaje de error
    rounds_used: int = 0
```

### 3.3 Dos familias de proveedores

**Proveedores agentic** (Claude Code, OpenCode):
Manejan el loop de verificación internamente. El provider solo invoca el CLI
y espera el resultado final. El código de retorno y END_REASON comunican el
estado.

**Proveedores API** (OpenAI, DeepSeek, Leanstral):
No tienen loop interno. El sistema ejecuta un loop de verificación agnóstico:
1. Enviar prompt al modelo → recibir código Lean
2. Escribir código en `target_path`
3. Compilar con `lake env lean`
4. Si hay errores, construir nuevo prompt con errores + código
5. Repetir hasta éxito o `max_rounds`

```python
def verification_loop(
    provider: 'APIProvider',
    target_path: Path,
    prompt: str,
    max_rounds: int,
    cwd: Path,
) -> FormalizationResult:
    """Loop de verificación agnóstico al modelo."""
    messages = [{"role": "user", "content": prompt}]
    for round_num in range(1, max_rounds + 1):
        response = provider.generate(messages)
        target_path.write_text(extract_lean_code(response))
        has_error, has_sorry, stdout, stderr = check_lean_file(target_path)
        if not has_error and not has_sorry:
            return FormalizationResult(True, "COMPLETE", round_num)
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": f"Errors:\n{stdout}\n{stderr}"})
    return FormalizationResult(False, "LIMIT", max_rounds)
```

---

## 4. Selección de modelo por configuración

El provider se selecciona mediante variable de entorno:

```bash
# Variable de entorno (más simple)
export AVID_MODEL_PROVIDER=opencode   # default: OpenCode Go (DeepSeek V4 Pro)
export AVID_MODEL_PROVIDER=claude     # Claude Code CLI (requiere claude auth login)
export AVID_MODEL_PROVIDER=anthropic  # Anthropic API directa (ANTHROPIC_API_KEY)
export AVID_MODEL_PROVIDER=openai     # OpenAI (OPENAI_API_KEY)
export AVID_MODEL_PROVIDER=deepseek   # DeepSeek directo (DEEPSEEK_API_KEY)
export AVID_MODEL_PROVIDER=openrouter # OpenRouter (OPENROUTER_API_KEY)
export AVID_MODEL_PROVIDER=mistral    # Mistral (MISTRAL_API_KEY)
export AVID_MODEL_PROVIDER=gemini     # Gemini (GEMINI_API_KEY)
```

**8 providers disponibles.** Los 7 providers API usan el mismo `OpenAIChatProvider`
con distintos `base_url`; solo Claude Code CLI es agentic (loop interno).
Anthropic tiene su propio `AnthropicProvider` porque usa `x-api-key` en vez de
`Authorization: Bearer`.

El orchestrator resuelve el provider así:

```python
def resolve_provider(model_spec: str | None = None) -> ModelProvider:
    name = model_spec or os.environ.get("AVID_MODEL_PROVIDER", "opencode")
    return PROVIDER_REGISTRY[name]()
```

Cambiar de modelo **no requiere tocar el código**. Solo cambiar la variable de entorno.

---

## 5. Flujo completo de formalize_paper()

```
formalize_paper(tex_path, model="claude")
│
├─ 1. Parseo: LaTeXParser.parse_file(tex) → bloques
│     Extrae: label, type, title, content_latex, proof_latex, references
│
├─ 2. Filtrado: solo FORMALIZABLE_TYPES (definition, theorem, lemma,
│     proposition, corollary). remark/example se omiten.
│
├─ 3. Proyecto Lean: create_paper_project(title, parent_project)
│     Crea directorio, Paper.lean vacío, PAPER_INDEX.md, REVIEW.md,
│     docs/prompts/, Blocks/
│
├─ 4. Pre-build: lake build Paper (calienta cache Mathlib, ~2 min)
│
├─ 5. Orden topológico: topological_sort(blocks)
│     Kahn's algorithm sobre DAG de referencias
│
├─ 6. Resume: leer PAPER_INDEX.md, saltar verified/axiom
│
└─ 7. Para cada bloque (en orden):
    │
    ├─ classify(block) → Mode: SIMPLE | MEDIUM | HARD | EXTERNAL
    │
    ├─ Si EXTERNAL:
    │   └─ mathlib_search.lookup() → encontrado? abbrev : axiom
    │
    └─ Si no:
        │
        ├─ Escribir stub .lean (banner + import Paper)
        ├─ Escribir TASK.md (enunciado, prueba, dependencias, reglas)
        ├─ provider.formalize(target, prompt, max_rounds, cwd)
        │   └─ El provider ejecuta el modelo y escribe código en target
        │
        ├─ check_lean_file(target) → ¿compila sin errores ni sorry?
        ├─ _has_real_declaration(code) → ¿hay código real?
        │
        ├─ Si éxito:
        │   ├─ _extract_declarations(target) → código sin imports/banner
        │   ├─ manager.append_block(code) → Paper.lean
        │   ├─ manager.register_block(...) → PAPER_INDEX.md
        │   └─ lake build Paper → cachear .olean
        │
        └─ Si fallo:
            ├─ manager.append_block(comentario de fallo)
            └─ manager.register_block(status="❌ failed")
```

---

## 6. Modos de clasificación (complexity.py)

| Modo | Condición | Rondas | Prompt |
|------|-----------|--------|--------|
| SIMPLE | `type == definition` | 5 | `prompt_avid.txt` |
| MEDIUM | Tiene prueba, no es compleja | 15 | `prompt_medium_mode_avid.txt` |
| HARD | Prueba larga (≥800 chars) o señales de complejidad | 30 | `prompt_hard_mode_avid.txt` |
| EXTERNAL | Sin prueba en el paper | 0 | No se invoca modelo |

Señales de complejidad: `induction`, `case analysis`, `WLOG`, `contradiction`,
`contrapositive`, lemas auxiliares inline, entorno `\begin{cases}`.

---

## 7. Verificación (lean_checker.py)

La verificación usa `lake env lean <archivo>` y analiza la salida con dos
criterios:

1. **Errores de compilación**: detectados por el formato estándar de Lean
   `<path>:<line>:<col>: error:` y por `returncode != 0`.

2. **Sorry warnings**: detectados por el mensaje `declaration uses 'sorry'`.
   Un `sorry` es un placeholder de "esto es cierto pero no lo demuestro".

Ambos criterios se verifican con regex precisas (no substring matching) para
evitar falsos positivos (ej. `Mathlib.Algebra.Errors` no es un error).

---

## 8. Persistencia y tolerancia a fallos

### 8.1 PAPER_INDEX.md

Base de datos local en Markdown. Cada entrada:
```markdown
## thm:lagrange — Lagrange's Theorem
Type: theorem
Status: ✅ verified
File: Paper.lean:42
Depends on: def:group, lem:subgroup
Statement: For any finite group G, the order of a subgroup H divides |G|
---
```

### 8.2 Modo resume

Al reanudar, el orchestrator lee `PAPER_INDEX.md` y saltea bloques con status
`verified` o `axiom`. Los bloques `failed` se reintentan (el fallo pudo ser
transitorio: rate-limit, timeout de compilación, error no determinista).

### 8.3 Rate-limit handling

Si el proveedor reporta rate-limit (código de retorno 99, o `RATE_LIMITED` en
el resultado), el orchestrator **aborta el run completo** sin marcar el bloque
actual como fallido. Esto permite reanudar limpiamente cuando la cuota se
restablezca.

### 8.4 REVIEW.md

Los bloques que requieren atención humana (axiomas declarados, bloques fallidos)
se registran también en `REVIEW.md` para revisión manual posterior.

---

## 9. Defensas contra falsos positivos

### 9.1 `_has_real_declaration()`

Si Claude (u otro modelo) falla silenciosamente — no edita el archivo, deja
solo el stub con banner + import — el verificador reportaría éxito (el stub
compila). `_has_real_declaration()` verifica que exista al menos una keyword
de declaración Lean (`theorem`, `lemma`, `def`, `axiom`, etc.) en el código.

### 9.2 `_extract_declarations()`

Antes de apendear a `Paper.lean`, se eliminan imports duplicados y el banner
de metadata. Solo se conserva el código Lean relevante.

---

## 10. Providers disponibles

### 10.1 Claude Code CLI (`claude`)
Provider agentic por defecto histórico. Requiere `claude auth login`.
Loop interno de verificación vía MCP (`lean_diagnostic_messages`).

### 10.2 OpenCode Go (`opencode`) — **default actual**
Usa `OPENCODE_GO_API_KEY`. Modelo default: `deepseek-v4-pro`.
Endpoint OpenAI-compatible en `https://opencode.ai/zen/go/v1`.

### 10.3 Anthropic API (`anthropic`)
Usa `ANTHROPIC_API_KEY`. Conexión directa a la API de Anthropic
(`https://api.anthropic.com/v1`) con auth `x-api-key`.
Modelo default: `claude-sonnet-4-20250514`.

### 10.4 OpenAI, DeepSeek, OpenRouter, Mistral, Gemini
Todos usan `OpenAIChatProvider` con distintos `base_url`.
Cada uno lee su propia variable de entorno para la API key
(`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, etc.).

### 10.5 Loop de verificación para providers API

Los providers API no tienen loop interno. El sistema ejecuta
`verification_loop()` (en `scripts/verification_loop.py`):
1. Enviar prompt al modelo → recibir respuesta
2. Extraer código Lean de la respuesta (busca bloques \`\`\`lean)
3. Escribir código en `target_path`
4. Compilar con `lake env lean`
5. Si hay errores o `sorry`: construir feedback y repetir
6. Hasta éxito o `max_rounds`

---

## 11. Estructura de directorios

```
avid-clean/
├── parser/
│   ├── __init__.py             # LaTeX parser package
│   ├── latex_parser.py         # Extracción de bloques matemáticos
│   └── parse_tex.py            # CLI del parser
├── formalization/
│   ├── __init__.py             # Exporta formalize_paper, ModelProvider
│   ├── orchestrator.py         # Pipeline principal (model-agnostic)
│   ├── lean_project.py         # Gestión de proyectos Lean
│   ├── mathlib_search.py       # Búsqueda en Mathlib (stub v1)
│   ├── complexity.py           # Clasificador SIMPLE/MEDIUM/HARD/EXTERNAL
│   ├── providers/              # 8 providers (nuevo)
│   │   ├── base.py, claude_code.py, anthropic.py
│   │   ├── openai_compatible.py, config.py
│   └── scripts/
│       ├── lean_checker.py, safe_verify.py
│       ├── extract_sublemmas.py, mcp_stats.py
│       ├── statement_tracker.py, verification_loop.py
├── tests/
│   └── test_tiny_evens.py      # Test de integración
└── ARCHITECTURE.md             # Este documento
```
