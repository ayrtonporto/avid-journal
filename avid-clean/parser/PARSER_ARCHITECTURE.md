# AViD Journal — Arquitectura del Parser LaTeX

`latex_parser.py` (630 líneas) + `parse_tex.py` (335 líneas, CLI).

## 1. Visión general

El parser toma un archivo `.tex` y devuelve una lista de bloques estructurados. Cada bloque es un dict con 6 campos que alimentan directamente al formalizador:

```python
{
    'type': 'definition' | 'theorem' | 'lemma' | 'proposition' | 'corollary',
    'label': 'def:group' | None,        # de \label{...}
    'title': 'Grupo' | None,            # de \begin{theorem}[Título]
    'content_latex': 'Un grupo es...',  # contenido entre \begin y \end
    'proof_latex': 'Sea G...' | None,   # contenido de \begin{proof} adyacente
    'references': ['def:group'] | None  # labels referenciados con \ref{}
}
```

Estos 6 campos son **exactamente** lo que el orquestador necesita:
- `type` → determina `Mode.SIMPLE` / `MEDIUM` / `HARD` / `EXTERNAL`
- `label` → genera el nombre Lean (`lean_ident_for`)
- `references` → construye el DAG (`topological_sort`)
- `content_latex` + `proof_latex` → input para el modelo

---

## 2. Estructura de la clase `LaTeXParser`

| Método | Líneas | Rol |
|--------|--------|-----|
| `__init__` | 40-65 | Compila regex: entornos base, variantes, proof |
| `remove_comments` | 67-95 | Elimina `%` comentarios (respeta `\%`) |
| `clean_content` | 97-124 | Saca `\textbf`, `\vspace`, normaliza whitespace |
| `extract_references` | 126-146 | Encuentra `\ref{label}` y `\eqref{label}` |
| `extract_label` | 148-174 | Extrae `\label{...}` post-`\begin` |
| `normalize_env_type` | 176-210 | Mapea variantes (español/abrevs) → 5 tipos canónicos |
| `extract_environment` | 212-252 | Contenido entre `\begin/\end` con anidamiento |
| `extract_proof` | 254-314 | Extrae `\begin{proof}` adyacente (solo whitespace entre) |
| `detect_custom_environments` | 316-352 | Encuentra `\newtheorem{...}` en el preámbulo |
| `parse_text` | 354-442 | **Loop principal**: orquesta todos los métodos |
| `parse_file` | 444-465 | Lee archivo, valida `.tex`, llama `parse_text` |
| `parse_latex` (función) | 481-492 | Conveniencia módulo-nivel |
| `test_parser` | 495-630 | Test interno con 4 bloques de ejemplo |

---

## 3. Análisis detallado por método

### 3.1 `__init__` — compilación de patrones

```python
MATH_ENVIRONMENTS = ['definition', 'theorem', 'lemma', 'proposition', 'corollary']

ENVIRONMENT_VARIANTS = {
    'teorema': 'theorem', 'definicion': 'definition', 'definición': 'definition',
    'lema': 'lemma', 'proposicion': 'proposition', 'proposición': 'proposition',
    'corolario': 'corollary',
    'thm': 'theorem', 'defn': 'definition', 'def': 'definition',
    'lem': 'lemma', 'prop': 'proposition', 'cor': 'corollary', 'corol': 'corollary'
}
```

**HECHO**: 5 tipos base + 14 variantes (español, abreviaturas). El regex compilado es:
```
\\begin\{(definition|theorem|...|corol)\}*\}(?:\[([^\]]*)\])?
```
Captura el nombre del entorno (grupo 1) y el título opcional (grupo 2). Soporta variantes starred (`theorem*`).

**HECHO**: Patrones de proof: `proof`, `prueba`, `demostracion`, `demostración`, `dem`.

**HECHO**: Si se pasan `custom_environments`, se agregan al patrón (para entornos definidos con `\newtheorem`).

---

### 3.2 `remove_comments`

**HECHO**: Elimina todo a la derecha de `%` no escapado. `\%` se preserva. Es lo primero que ejecuta `parse_text()`.

**HECHO**: `Hola % comentario` → `Hola`. `100\%` → intacto.

---

### 3.3 `clean_content`

**HECHO**: Tres tipos de limpieza:
1. Elimina comandos de espaciado: `\vspace{}`, `\hspace{}`, `\newpage`, `\clearpage`, `\pagebreak`
2. Simplifica formato: `\textbf{foo}` → `foo`, `\textit{foo}` → `foo`, `\emph{foo}` → `foo`
3. Normaliza whitespace: 3+ líneas vacías → 2, múltiples espacios → 1

**INFERIDO**: No toca comandos matemáticos (`\frac`, `\sum`, `\int`). El contenido que llega al formalizador mantiene la notación LaTeX matemática para que el LLM la entienda.

---

### 3.4 `extract_references`

**HECHO**: Busca `\ref{label}` y `\eqref{label}`. Devuelve lista sin duplicados. Se llama sobre el contenido Y sobre la prueba. Los resultados se mergean.

**HECHO**: Esto alimenta el DAG: si el Teorema B referencia `\ref{def:group}`, el orquestador sabe que B depende de la Definición con label `def:group`.

---

### 3.5 `extract_label`

**HECHO**: Busca `\label{...}` en los primeros 200 caracteres después de `\begin{entorno}[título]`. El patrón `^\s*\\label\{([^}]+)\}` con `re.MULTILINE` permite que el label esté en la línea siguiente.

---

### 3.6 `normalize_env_type`

**HECHO**: Normaliza cualquier nombre a uno de los 5 tipos canónicos:
1. Si está en `ENVIRONMENT_VARIANTS` → traducción directa
2. Si ya es canónico → se devuelve tal cual
3. Si es desconocido → heurística: `'th'`/`'teo'` → theorem, `'def'` → definition, etc.
4. Si nada funciona → se devuelve en lowercase (el orquestador lo filtrará)

**INFERIDO**: La heurística del paso 3 puede fallar con nombres muy exóticos. Para esos casos conviene pasar `custom_environments` explícitamente.

---

### 3.7 `extract_environment`

**HECHO**: Extrae el contenido entre `\begin{env}` y `\end{env}` con **anidamiento**. Usa contador `depth`: cada `\begin` incrementa, cada `\end` decrementa. Termina en `depth = 0`.

**HECHO**: Si no encuentra cierre, devuelve todo hasta EOF (no crashea). Acepta variantes starred.

---

### 3.8 `extract_proof`

**HECHO**: Busca `\begin{proof}` **inmediatamente después** del entorno. Solo whitespace entre ambos. Si encuentra cualquier otro carácter no-whitespace, retorna `None`. Esto evita asociar proofs a bloques equivocados.

**HECHO**: Maneja anidamiento de proofs (raro pero posible).

---

### 3.9 `detect_custom_environments`

**HECHO**: Escanea el preámbulo en busca de:
- `\newtheorem{nombre}{Título}`
- `\theoremstyle{...}\newtheorem{nombre}{...}`

Si encuentra entornos definidos por el autor, recompila los patrones con `self.__init__(custom_environments=...)`.

---

### 3.10 `parse_text` — el loop principal

**HECHO**: Flujo completo:
1. `remove_comments(text)`
2. `detect_custom_environments(text)` si `auto_detect_envs=True`
3. Loop: busca `\begin{entorno}` con el regex compilado
4. Para cada match: extrae label → contenido → proof → referencias
5. Filtra bloques con < 3 caracteres (basura)
6. Arma el dict con los 6 campos

**HECHO**: Procesa en orden de aparición. Esto preserva el orden natural del paper, necesario para el topological sort.

---

## 4. Integración con el formalizador

```
paper.tex
  │
  ▼
┌──────────────────────────────────────┐
│ LaTeXParser.parse_file(paper.tex)    │
│ → [ {type, label, title,             │
│      content_latex, proof_latex,     │
│      references}, ... ]              │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│ orchestrator.formalize_paper()       │
│ • Filtra por FORMALIZABLE_TYPES      │
│ • topological_sort() por references  │
│ • classify() por type + proof_latex  │
│ • Por cada bloque: ModelProvider     │
│   formaliza content → código Lean    │
└──────────────────────────────────────┘
```

---

## 5. Limitaciones

- **No resuelve `\input`/`\include`**: papers multi-archivo requieren pre-procesamiento.
- **Heurística de tipos custom**: puede fallar con nombres muy exóticos (solucionable con `custom_environments` explícito).
- **No extrae ecuaciones sueltas**: solo entornos semánticos (`\begin{theorem}`, etc.), no `\begin{equation}` solo.
- **No parsea matemáticas inline**: extrae el texto LaTeX crudo; la interpretación semántica la delega al LLM.

---

## 6. CLI (`parse_tex.py`)

```bash
python parse_tex.py input.tex                 # resumen en consola
python parse_tex.py input.tex -o output.json  # exporta JSON
python parse_tex.py input.tex --stats         # estadísticas
python parse_tex.py input.tex --validate      # valida bloques
python parse_tex.py input.tex --deps          # grafo de dependencias
```
