# Guía de instalación y uso — AViD Journal (formalización Lean)

Esta guía está pensada para que **cualquiera en otro equipo** pueda clonar el repo, instalar dependencias y ejecutar el pipeline de formalización (LaTeX → bloques → Claude Code → Lean + Mathlib).

---

## 1. Qué necesitas instalar (resumen)

| Componente | Para qué sirve |
|------------|----------------|
| **Git** | Clonar y versionar el proyecto |
| **Python 3.10+** (recomendado 3.11+) | Orquestador, parser LaTeX, scripts |
| **elan + Lean 4** | Compilador Lean (misma versión que `lean_project/lean-toolchain`) |
| **Lake** | Viene con Lean; descarga y construye **Mathlib** |
| **Claude Code CLI** (`claude` en el PATH) | El agente que escribe/edita los `.lean` por bloque |

No hace falta instalar Mathlib “a mano”: **Lake** lo trae como dependencia del proyecto `lean_project/` (`lakefile.toml`).

---

## 2. Instalación paso a paso

### 2.1 Git y Python

**Git** — [https://git-scm.com/downloads](https://git-scm.com/downloads)

- **macOS**: `brew install git` (o usa Xcode Command Line Tools, que ya lo incluyen).
- **Linux** (Debian/Ubuntu): `sudo apt install git`.
- **Windows**: instalador desde el enlace de arriba; incluye **Git Bash**, que es práctico.

**Python 3.10+** — [https://www.python.org/downloads/](https://www.python.org/downloads/)

- **macOS**: `brew install python@3.11` (o usa `pyenv`).
- **Linux** (Debian/Ubuntu): `sudo apt install python3 python3-venv python3-pip`.
- **Windows**: instalador desde el enlace de arriba; marca la opción **“Add Python to PATH”** durante la instalación.

### 2.2 Entorno virtual Python (recomendado)

Desde la raíz del repositorio (`AViD Journal`):

```bash
python -m venv .venv
```

Activación:

- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **macOS / Linux:** `source .venv/bin/activate`

Instalar dependencias:

```bash
pip install -r requirements.txt
```

### 2.3 Lean 4 con elan

La forma estándar es instalar **elan** y dejar que el proyecto fije la versión de Lean mediante `lean_project/lean-toolchain`.

- Instrucciones oficiales: [https://leanprover-community.github.io/get_started.html](https://leanprover-community.github.io/get_started.html)

Comprueba que Lean responde:

```bash
lean --version
```

La línea debe coincidir (o ser compatible) con la versión indicada en:

`lean_project/lean-toolchain`

### 2.4 Mathlib y primer build del proyecto compartido

El código asume un proyecto Lean compartido en:

`lean_project/`

Desde ahí:

```bash
cd lean_project
lake update
lake build
```

- La **primera vez** puede tardar mucho (descarga + compilación de Mathlib y dependencias).
- Los artefactos van a `lean_project/.lake/` (pesados; **no suelen subirse a GitHub**, ver sección 6).

Tras un build exitoso, puedes verificar un paper ya existente, por ejemplo:

```bash
lake build Papers.AyrtonPortoTesis.Paper
```

(si ese directorio existe en tu copia del repo).

### 2.5 Claude Code CLI

El orquestador invoca el ejecutable **`claude`** como subprocess.

1. Instala **Node.js LTS**: [https://nodejs.org/](https://nodejs.org/)
   - **macOS**: `brew install node`
   - **Linux** (Debian/Ubuntu): mirá las instrucciones oficiales para LTS.
   - **Windows**: instalador desde el enlace de arriba.
2. Sigue la documentación actual de Anthropic para **Claude Code** (CLI) y autenticación (cuenta / suscripción / login).

Comprueba:

```bash
claude --version
```

Si el comando no se encuentra, revisa el PATH. En Windows, el wrapper aparece como `claude.cmd` (npm); puede que necesites usar la ruta completa o reiniciar la terminal tras la instalación.

**Notas:**

- La cuota de uso de Claude es externa al repo; si se agota, el runner detecta mensajes tipo “You've hit your limit” y el orquestador puede abortar el run (comportamiento esperado tras los últimos arreglos).
- No necesitas poner una API key “en el código Python” si ya iniciaste sesión con la CLI según el flujo oficial de Claude Code.

---

## 3. Cómo ejecutarlo

Trabaja siempre desde la **raíz del repo** (donde está `src/` y `requirements.txt`).

### 3.1 Codificación

El orquestador siempre se invoca con `python -X utf8 …` para forzar UTF-8 en stdin/stdout. Esto cubre macOS, Linux y Windows.

En Windows, además, podés fijar la variable de entorno una vez por sesión si tenés problemas con otros scripts:

```powershell
$env:PYTHONIOENCODING="utf-8"
```

En macOS / Linux no suele hacer falta nada extra.

### 3.2 Dry-run (sin Claude, sin gasto)

Útil para validar parser + orden de bloques:

```bash
python -X utf8 -m src.formalization.orchestrator ruta/al/paper.tex --dry-run
```

### 3.3 Run real con proyecto Lean compartido (recomendado)

Por defecto se usa `lean_project/` como `--parent-project` si existe (ver `src/formalization/lean_project.py`).

```bash
python -X utf8 -m src.formalization.orchestrator ruta/al/paper.tex --title "Titulo del paper"
```

Opciones útiles:

| Opción | Significado |
|--------|-------------|
| `--title "..."` | Nombre legible del paper (slug del directorio bajo `lean_project/Papers/`) |
| `--blocks-range "1-13"` | Solo esos índices (1-based) entre los bloques **formalizables** |
| `--no-resume` | Ignora entradas ya `verified`/`axiom` en `PAPER_INDEX.md` |
| `--standalone` | Crea proyecto Lean aislado en `--base-dir` (legacy; más lento de mantener) |
| `--parent-project RUTA` | Otro proyecto Lean raíz en lugar de `./lean_project` |
| `--json` | Resumen final en JSON |

Ejemplo con rango y título:

```bash
python -X utf8 -m src.formalization.orchestrator "tests\mi_articulo.tex" --title "Mi articulo" --blocks-range "1-20"
```

### 3.4 Dónde queda la salida

Para un paper titulado `"Mi articulo"`, el slug típico es `MiArticulo` y la ruta:

```
lean_project/Papers/<Slug>/
├── Paper.lean           # acumulativo: todo lo ya verificado
├── PAPER_INDEX.md       # índice por bloque (estado, línea en Paper.lean, deps)
├── REVIEW.md            # axiomas / fallos / notas
├── Blocks/              # un .lean por bloque (lo que edita Claude)
│   └── ...
├── TASK.md              # generado por bloque (contexto de la tarea)
└── docs/prompts/        # copia de docs para el agente
```

Para **pair review**, lo más cómodo suele ser:

1. Leer `PAPER_INDEX.md` (mapa).
2. Abrir cada `Blocks/*.lean` (contenido por bloque).
3. Abrir `Paper.lean` para ver el módulo completo como lo verá Lean.

---

## 4. Estructura del repositorio (alto nivel)

```
├── prompts/                      # Prompts AViD para Claude Code
│   ├── prompt_avid.txt           # modo SIMPLE (definiciones, bloques cortos)
│   ├── prompt_medium_mode_avid.txt
│   ├── prompt_hard_mode_avid.txt
│   └── docs/prompts/             # avid_common.md, sketch agent, etc.
├── lean_project/                 # Proyecto Lean 4 compartido + Mathlib
│   ├── lakefile.toml
│   ├── lean-toolchain
│   └── Papers/<Slug>/...         # Un subdirectorio por paper formalizado
├── src/
│   ├── parser/                   # LaTeX → bloques + refs
│   └── formalization/
│       ├── orchestrator.py       # Pipeline principal + CLI
│       ├── lean_project.py       # creación idempotente de papers bajo Papers/
│       ├── complexity.py         # SIMPLE / MEDIUM / HARD / EXTERNAL
│       └── scripts/              # runner, run_claude, lean_checker, ...
├── tests/                        # .tex de prueba, tests pytest
├── requirements.txt
└── docs/
    └── GUIA_INSTALACION_Y_USO.md # este archivo
```

---

## 5. Qué puedes modificar en los prompts

Los archivos principales están en `prompts/`:

| Archivo | Cuándo se usa |
|---------|----------------|
| `prompt_avid.txt` | Modo **SIMPLE** (casi todas las definiciones; bloques sin prueba larga) |
| `prompt_medium_mode_avid.txt` | Modo **MEDIUM** |
| `prompt_hard_mode_avid.txt` | Modo **HARD** |

La selección la hace `src/formalization/complexity.py` (`classify`, `prompt_file_for`).

### Reglas que conviene no romper (contrato con el orquestador)

1. **Solo editar el archivo objetivo** indicado en `TASK.md` (típicamente `Blocks/<nombre>.lean`).
2. **No editar** `Paper.lean` ni `PAPER_INDEX.md` a mano desde Claude: el orquestador los actualiza al verificar cada bloque.
3. Mantener la línea `import Papers.<Slug>.Paper` en el bloque (visibilidad de definiciones previas).
4. Objetivo de verificación: código **sin errores de compilación**; `sorry` no está permitido por defecto (`allow_sorry=False` en las tareas).

### Qué sí suele ser seguro ajustar

- Tono, checklist de búsqueda en Mathlib, consejos de estilo Lean.
- Recordatorios de sintaxis ASCII (`forall`, `->`) si hay problemas de encoding en Windows.
- Límites de “cuánto buscar antes de declarar axioma” para resultados externos.

Tras cambiar prompts, un `--dry-run` + un bloque pequeño con `--blocks-range` valida que nada se rompió en el wiring.

---

## 6. Scripts útiles del repo (opcional)

Además del orquestador, en sesiones de trabajo se han usado scripts auxiliares en la raíz (si existen en tu copia), por ejemplo:

- Análisis del `.tex` sin Claude
- Limpieza de entradas `failed` tras rate limit
- Rebuild de índice desde `Blocks/`

Si los compartes en GitHub, documenta cada uno con una línea en el README.

---

## 7. Solución de problemas breve

| Síntoma | Qué revisar |
|---------|-------------|
| `claude` no encontrado | PATH / instalar CLI / en Windows usar `claude.cmd` |
| Línea de comandos demasiado larga | Ya mitigado: prompt por stdin en `runner.py` |
| `Paper.olean` no existe al verificar un `Block` | Ejecutar `lake build Papers.<Slug>.Paper` desde `lean_project/` |
| Cuota Claude agotada | Esperar reset; usar `--blocks-range` + modo resume (por defecto) |

---

## 8. Lean formalizado en el repo

La salida Lean de cada paper vive en `lean_project/Papers/<Módulo>/` (ver
[`lean_project/README.md`](../lean_project/README.md)):

| Módulo | Contenido |
|--------|-----------|
| `Papers/Paper/` | Ejemplo mínimo (`def_even`, `lem_even_sum`, `thm_four_evens`). |
| `Papers/D3_Calibration/` | Teoremas de calibración de D3. |
| `Papers/AyrtonPortoTesis/` | Bloques de la tesis del autor (topología/álgebra). |

Como entrada `.tex` de prueba, usá `tests/fixtures/sample_paper.tex`.
