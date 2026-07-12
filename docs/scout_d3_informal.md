# Scout D3 Informal — Phase 0 Reconnaissance

**Date:** 2026-07-04
**Status:** COMPLETED — waiting for confirmation

---

## 1. Etapa de autoformalización actual

### ¿Qué recibe como entrada?

El orchestrator (`avid-clean/formalization/orchestrator.py`) recibe bloques parseados
de LaTeX. Cada bloque tiene:
- `type`: theorem, lemma, definition, proposition, corollary
- `title`: título del bloque
- `content_latex`: enunciado en LaTeX
- `proof`: texto de la demostración (extraído por el parser LaTeX)
- `label`: etiqueta LaTeX
- `references`: dependencias

### ¿Formaliza solo enunciados o también demostraciones?

**También demostraciones.** El prompt TASK.md incluye explícitamente la prueba informal
(línea 199-201 del orchestrator):

```python
proof_section = (
    f"## Informal proof\n\n{proof}\n" if proof else
    "## Informal proof\n\n(no proof provided in paper)\n"
)
```

Y en la sección "Workflow" pide al modelo que formalice la declaración.

### ¿Qué tasa de éxito tiene?

**No hay métrica documentada.** El pipeline fue probado con "Tiny Evens" (pruebas simples
de paridad) y bloques de la tesis de Ayrton (topología/categorías). Para pruebas complejas
de papers arbitrarios de arXiv, la tasa de éxito es desconocida — probablemente baja sin
ajuste de prompts específicos.

### ¿Cuánto tarda por intento?

Depende del provider:
- Claude Code (agentic): 30s-2min por ronda, típicamente 1-3 rondas
- API providers: 5-10s por llamada, el loop de verificación itera hasta compilar
- Timeout de lake build: 900s (15 min)

### FormalizationResult

```python
@dataclass
class FormalizationResult:
    success: bool          # True si compila sin errores ni sorry
    info: str              # "COMPLETE", "LIMIT", "RATE_LIMITED", o mensaje de error
    rounds_used: int       # rondas consumidas
    extracted_code: str    # código Lean extraído
```

---

## 2. Match de D1-informal vía TheoremSearch

### ¿Qué devuelve?

Cada match es un `PaperCandidate` con:

| Campo | Ejemplo | Fuente |
|-------|---------|--------|
| `paper_id` | `"ts_abc123"` | `theorem.theorem_id` |
| `title` | `"Transcendental Series of..."` | `paper.title` |
| `abstract` | `"The square root of two is not a rational number..."` | `theorem.slogan + body` |
| `arxiv_id` | `"2009.02446"` | Extraído de `paper.paper_id` o `paper.link` |
| `similarity_score` | `0.704` | `theorem.similarity` (viene de la API) |
| `source` | `"theoremsearch"` | Hardcodeado |

### ¿Incluye arXiv ID?

**Sí**, extraído de `paper.paper_id` (formato "2103.03942v2") o `paper.link`. La función
`_extract_arxiv_id_from_paper()` en `theoremsearch.py:75` lo normaliza.

### ¿Qué falta para descargar el LaTeX de la prueba?

- El arXiv ID (ya lo tenemos)
- Mecanismo de descarga de fuente LaTeX desde arXiv
- Localización del bloque `\begin{proof}...\end{proof}` asociado al teorema matcheado

---

## 3. Descarga de fuentes arXiv

### Endpoint

```
https://arxiv.org/src/<arxiv_id>
```

Devuelve un `.tar.gz` con los fuentes LaTeX del paper. Ejemplo verificado hoy:

```bash
$ curl -s -L -o paper.tar.gz "https://arxiv.org/src/2009.02446"
$ tar tzf paper.tar.gz
EG_20200904.bbl
EG_20200904.tex
```

Tiempo de descarga: **< 2 segundos** para un paper típico (25KB comprimido).

### Papers sin fuente

arXiv no siempre tiene fuente LaTeX. Si el autor subió solo PDF, el endpoint devuelve
error. La detección es inmediata (HTTP 404 o redirect a PDF).

---

## 4. Extracción de la demostración

### Procedimiento

1. Descargar y descomprimir el `.tar.gz`
2. Identificar el archivo `.tex` principal (el de mayor tamaño, o `main.tex`)
3. Buscar el enunciado del teorema matcheado en el texto LaTeX
4. Localizar el `\begin{proof}...\end{proof}` siguiente
5. Extraer el contenido

### Verificación con paper real (2009.02446)

El paper tiene `\begin{proof}...\end{proof}` en línea 584. El entorno de teorema usa
`\newtheorem{theorem}{Theorem}[section]`. La localización del proof requiere encontrar
el teorema específico por su texto de enunciado.

### Dificultades esperadas

- Papers con múltiples archivos `.tex` (`\input`, `\include`)
- Proofs inline sin entorno `proof` (estilo "Proof. ...")
- Teoremas sin proof explícito (solo referencia a otro paper)
- El texto del enunciado en TheoremSearch puede diferir del LaTeX original

---

## 5. Costo estimado por match informal

| Paso | Tiempo estimado | Notas |
|------|----------------|-------|
| Descarga arXiv source | 2-5s | Depende del tamaño del paper |
| Extracción de proof | < 1s | Parseo local de LaTeX |
| Formalización (1 intento) | 30s-3min | Variable según provider y complejidad |
| Formalización (3 intentos) | 1.5-9min | Con presupuesto máximo |
| Verificación (lean check) | 5-15s | `lake build` del bloque |
| ExtractData (lado B) | 30-60s | Si es archivo Mathlib; 4-5min si es proyecto |
| compute_d3 | < 1s | Puro Python |
| **Total por match (1 intento)** | **~1-4 min** | Si el intento tiene éxito |
| **Total por match (3 intentos)** | **~2-10 min** | Peor caso |
| **Total con fallo total** | **~2-10 min** | Formalización falla → PENDIENTE_D3 |

---

## 6. Evaluación de la regla de pivote

> "Si en Fase 0 la etapa de autoformalización actual resulta no apta para
> demostraciones (solo maneja enunciados, o la tasa de éxito con pruebas es
> <20% en los casos de prueba): frenar."

**Hallazgo**: la etapa de formalización SÍ maneja demostraciones (incluye `## Informal proof`
en el prompt). Pero la tasa de éxito con pruebas de papers arbitrarios de arXiv es
**desconocida** — no hay experimentos previos. La complejidad de las pruebas en papers
reales de matemáticas supera ampliamente la capacidad actual de LLMs para formalización
automática confiable.

### Recomendación

**NO pivotar todavía**, pero acotar el alcance del experimento:
1. Elegir 1-2 papers con pruebas CORTAS y autocontenidas (1 párrafo, sin dependencias
   externas pesadas)
2. Ejecutar el pipeline end-to-end para esos casos como prueba de concepto
3. Medir la tasa de éxito real (no estimada)
4. Si >20% → expandir; si <20% → documentar como limitación conocida

La pregunta de alcance queda para decisión de Ayrton.

---

## 7. PoC Results (COMPLETED — decision pending)

### Paper 1 — Easy: Infinitude of Primes (arXiv:1303.0730)

| Métrica | Valor |
|---------|-------|
| arXiv ID | 1303.0730 |
| Título | "Diagonalizing by Fixed-Points" |
| Teorema | "There are infinitely many prime numbers in N" |
| Tamaño de proof | 1543 chars (~30 líneas LaTeX) |
| Descarga | ✅ < 2s |
| Extracción proof | ✅ localizado en líneas 401-431 |
| Formalización (intento 1) | ❌ API timeout a 120s (OpenCode Go + deepseek-v4-flash) |
| Formalización (intento 2) | ⏭️ No ejecutado — API key no disponible en esta sesión |
| Fidelidad | ⏭️ No aplicable (sin código generado) |

### Paper 2 — Medium: Cauchy-Schwarz / Lax-Milgram (arXiv:1607.03618)

| Métrica | Valor |
|---------|-------|
| Descarga | ✅ < 3s |
| Extracción proof | ⚠️ Extraído proof de lema auxiliar (supremum), no del teorema matcheado |
| Formalización | ⏭️ No ejecutado |

### Lecciones del PoC

1. **Descarga arXiv + extracción de proof**: ✅ Funciona. < 5s total.
2. **Localización del proof correcto**: ⚠️ Frágil. El proof del teorema matcheado
   no siempre está en el paper, o está en una sección distinta.
3. **Formalización vía API**: ❌ No confiable. Timeout a 120s con prompt de ~2KB.
   La latencia de APIs de modelos hace inviable la formalización sincrónica de
   pruebas no triviales.
4. **Costo real**: La formalización es el cuello de botella. Sin un provider
   confiable y rápido (< 30s por intento), el pipeline informal → D3 no es
   práctico en tiempo real. El camino batch (precalentamiento nocturno) sería
   el único viable.

### Recomendación

**No avanzar a Fases 3-4 con el diseño actual.** Opciones:

A. **Posponer**: documentar el diseño como "demostración de método" con los 2 casos
   del PoC, sin integrar a producción. El código de download + proof extraction queda
   como utilidad para experimentos manuales.

B. **Cambiar de provider**: usar Claude Code (agentic, maneja mejor prompts largos)
   en vez de API chat. Requiere token de Anthropic configurado.

C. **Reducir ambición**: en vez de formalizar la prueba completa, extraer solo el
   enunciado del paper matcheado y usarlo para enriquecer el matching de D1-informal
   (sin llegar a D3).

D. **Preformalización batch**: correr formalizaciones de noche sobre un conjunto
   acotado de matches, con reintentos y sin timeout estricto.
