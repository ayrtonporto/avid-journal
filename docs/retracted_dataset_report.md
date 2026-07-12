# Reporte de Viabilidad — Dataset de Retirados

**Fecha:** 2026-07-05 (generación) / 2026-07-06 (actualización)  
**Propósito:** Construir las listas de candidatos para el experimento de papers retirados de AViD Journal  
**Outputs:** `config/retracted_candidates.yaml`, `config/control_candidates.yaml`

---

## 1. Fuente de datos

### 1.1 WithdrarXiv (Rao et al. 2024)

El dataset **WithdrarXiv** (arXiv:2412.03775, Rao, Young, Dietterich, Callison-Burch) contiene
~14,000 preprints retirados de arXiv con taxonomía de 10 categorías de motivos de retiro.
Está disponible en HuggingFace como `darpa-scify/withdrarxiv` (17.2 MB, Apache 2.0) pero es
**gated** — requiere login y aceptación de términos. No se pudo acceder programáticamente sin
token de HF.

El repositorio GitHub (`darpa-scify/withdrarxiv`) solo contiene README y .gitignore;
los datos están exclusivamente en HuggingFace.

### 1.2 Plan B: arXiv API directa

Se implementó búsqueda directa sobre la API de arXiv (`export.arxiv.org`):

```
Query: cat:math.* AND co:withdrawn
Total: 2600 papers retirados en matemática
```

Sobre esos 2600, se aplicaron **23 patrones de duplicación** (expresiones regulares)
para identificar retiros cuyo motivo es "resultado ya conocido" / "ya demostrado" /
"duplicación de trabajo previo", excluyendo papers retirados por errores, gaps,
o problemas administrativos.

---

## 2. Resultados de la búsqueda

### 2.1 Candidatos retirados

| Métrica | Valor |
|---------|-------|
| Papers analizados | 2600 |
| Candidatos identificados | 33 |
| **Viables (fuente LaTeX + teoremas)** | **26** |
| No viables | 7 (tienen .tex pero 0 entornos de teorema) |

### 2.2 Distribución por categoría (viables)

| Categoría | Count |
|-----------|-------|
| math.CO (Combinatorics) | 4 |
| math.AG (Algebraic Geometry) | 3 |
| math.CV (Complex Variables) | 2 |
| math.NT (Number Theory) | 2 |
| math.AT (Algebraic Topology) | 2 |
| math.AP (Analysis of PDEs) | 2 |
| math.CT (Category Theory) | 1 |
| math.QA (Quantum Algebra) | 1 |
| math.DS (Dynamical Systems) | 1 |
| math.RA (Rings and Algebras) | 1 |
| math-ph (Mathematical Physics) | 1 |
| cs.DM (Discrete Math) | 1 |
| math.GT (Geometric Topology) | 1 |
| math.KT (K-Theory) | 1 |
| cs.CG (Computational Geometry) | 1 |
| math.PR (Probability) | 1 |
| math.CA (Classical Analysis) | 1 |

**Total: 17 categorías distintas, 26 papers viables.**

### 2.3 Rango de años

2001–2026, con concentración en 2007–2016.

### 2.4 Patrones de retiro más frecuentes

| Patrón | Ocurrencias |
|--------|-------------|
| "result was/is already known" | 5 |
| "had already been proved by [autor]" | 4 |
| "results are not new/original" | 4 |
| "subsumed by" | 4 |
| "previously proved/proven by" | 3 |
| "result has already been published" | 3 |
| "overlap with existing literature" | 2 |
| "corollary of well-known result" | 1 |
| "problem has already been solved" | 1 |

### 2.5 Evidencia de trabajo previo

De los 26 viables, **12 citan explícitamente el trabajo previo** que duplica su resultado
(autores, arXiv IDs, o referencias a journals). Los 14 restantes mencionan que el resultado
"ya era conocido" sin especificar la fuente.

**Casos destacados con cita explícita:**
- 0907.3263v2 → Silver & Whitten, math.GT/0405462
- 1212.0196v2 → Monsky (well-known result)
- 1307.2069v5 → Kuran, J. London Math. Soc. 44 (1969), 303-309
- 1407.0626v2 → Peterson & Woodall
- 1609.02090v2 → Hardy & Littlewood, Partitio Numerorum (VIII)
- 2605.05526v2 → Luczak, Rucinski, Urbanski, Discrete Math 236 (2001)
- 1302.3933v2 → Crawley-Boevey, Lectures on Representations of Quivers

---

## 3. Viabilidad de extracción LaTeX

### 3.1 Método

Para cada candidato se intentó descargar la fuente LaTeX v1 desde `arxiv.org/src/{id}v1`.
arXiv **conserva la fuente de la versión v1** incluso cuando el paper es retirado en v2+.

**Hallazgo clave:** Los tarballs de arXiv vienen en dos formatos:
- `.tar.gz` (archivo tar comprimido con gzip) — contiene múltiples archivos
- `.gz` (archivo único comprimido con gzip) — contiene UN solo `.tex`

El script de extracción maneja ambos formatos automáticamente.

### 3.2 Resultados

| Fuente LaTeX | Count |
|-------------|-------|
| Descargable y extraíble | 33/33 (100%) |
| Con archivo .tex principal | 33/33 (100%) |
| Con ≥1 entorno de teorema | 26/33 (78.8%) |
| Con ≥1 entorno de proof | 22/33 (66.7%) |

Los 7 papers "no viables" tienen fuente LaTeX descargable pero usan formatos no estándar:
- **AMS-TeX** (`\documentstyle{amsppt}`) en lugar de LaTeX — usa `\definition{...}`
  en lugar de `\begin{theorem}...\end{theorem}`
- **Nombres abreviados** (`\newtheorem{thm}{Theorem}` → `\begin{thm}` en lugar de `\begin{theorem}`)
- Pattern de `\newtheorem` personalizado que el contador simple no captura

**Actualización (2026-07-06):** Una inspección detallada muestra que varios de los
"no viables" SÍ contienen entornos de teorema con nombres abreviados (thm, lem, prop, cor).
Con un contador expandido, la mayoría tendría >10 entornos de teorema. Ver sección 3.3.

### 3.3 Falsos negativos en el contador de teoremas

Los 7 papers marcados como "no viables" (0 theorem_envs_found) en realidad SÍ contienen
entornos de teorema, pero con nombres no estándar:

| arXiv ID | Entornos reales (estimado) | Formato |
|----------|---------------------------|---------|
| 0805.4701v2 | ~12 | `\newtheorem` custom + `\begin{inizio}`, `\begin{numero}`, etc. |
| 1001.4969v2 | ~5 | AMS-TeX (`\definition{...}`, `\theorem{...}`) |
| 0709.3531v2 | ~16 | `\newtheorem{thm}`, `\newtheorem{lem}`, `\newtheorem{prop}` |
| 1008.3831v3 | ~51 | `\newtheorem{thm}`, `\newtheorem{lem}`, etc. |
| math/0508555v2 | ~48 | `\newtheorem{thm}`, `\newtheorem{prop}`, etc. |
| 1303.4093v2 | ~2 | `\newtheorem{lemma}`, etc. (paper corto) |
| math/0508141v3 | ~42 | `\newtheorem{thm}`, `\newtheorem{step}`, etc. |

**Con un contador expandido, el número real de viables sería ~31-32/33.**

---

## 4. FASE 3 — Candidatos de control

### 4.1 Estado: COMPLETO (2026-07-06)

Ejecutado con éxito tras agregar cortesía de red (delay 3s, backoff exponencial).

| Métrica | Valor |
|---------|-------|
| Retirados con controles | **26/26 (100%)** |
| Retirados sin control | 0 |
| Controles chequeados | 382 |
| Controles viables | 332 (87%) |
| Backoffs por rate-limit | 0 |
| Errores no reintentables | 1 (HTTP 403 en 0905.4487v1) |
| Tiempo total | 3.0 minutos |
| Delay entre requests | 3.0 segundos |

### 4.2 Estrategia de emparejamiento

Para cada retirado candidato:
1. Buscar en arXiv: `cat:{category} AND submittedDate:[{year-1}0101 TO {year+1}1231] NOT co:withdrawn`
2. Para cada resultado, descargar fuente v1 y verificar viabilidad (≥1 teorema)
3. Seleccionar 2 controles por retirado (todos tienen exactamente 2)
4. Misma categoría, año ±1

### 4.3 Cortesía de red implementada

Ambos scripts (`build_retracted_dataset.py` y `build_control_candidates.py`) incluyen:
- **`--delay N`** (default 3.0s): pausa entre requests consecutivos
- **Backoff exponencial**: 5 reintentos (5s, 10s, 20s, 40s, 80s) ante HTTP 429/503 y timeouts
- **Reanudable**: cache SHA256 por arXiv ID; el script de controles mergea pares existentes en el output
- **Log detallado**: cada backoff registra motivo y duración

### 4.4 Resultado

`config/control_candidates.yaml` contiene 26 pares retirado→[control1, control2].
Cada control tiene categoría y año coincidentes, fuente LaTeX verificada,
y ≥1 entorno de teorema.

---

## 5. Observaciones y patrones

### 5.1 Concentración de retiros

Los retiros por "resultado ya conocido" NO se concentran en un área particular de la
matemática — están distribuidos en 17 categorías. Esto sugiere que el fenómeno es
transversal a todas las áreas.

Sin embargo, **Combinatorics (math.CO)** y **Algebraic Geometry (math.AG)** tienen
la mayor representación (4 y 3 respectivamente), lo cual es consistente con ser
las categorías más grandes de math en arXiv.

### 5.2 ¿Los comentarios citan el trabajo previo?

De 26 viables:
- **12 (46%)** citan explícitamente el trabajo previo (autores, arXiv ID, journal)
- **14 (54%)** usan frases genéricas ("already known", "not new", "previously proved")
  sin especificar la fuente

Los que SÍ citan son particularmente valiosos para el experimento porque:
- Tenemos la referencia al trabajo que duplica el resultado
- Podemos verificar el ground truth
- Podemos comparar ambos proofs (retirado vs. original) con D3

### 5.3 Calidad de la fuente LaTeX

Los papers más viejos (2001-2009) tienden a usar formatos menos estándar (AMS-TeX,
nombres abreviados de entornos), mientras que los más recientes (2010+) usan
mayoritariamente LaTeX estándar con `\begin{theorem}...\end{theorem}`.

Los papers de áreas muy técnicas (math.KT, math.QA) tienden a tener pruebas más
largas y más lemas auxiliares, lo cual es bueno para D3 (más premisas para comparar).

### 5.4 Tamaño de las pruebas

| Rango de entornos de proof | Count |
|---------------------------|-------|
| 0 (sin prueba explícita) | 7 |
| 1-5 | 8 |
| 6-15 | 7 |
| 16+ | 4 |

Los papers sin `\begin{proof}` explícito pueden tener demostraciones en el texto
(estilo "Proof." sin entorno) o pueden ser papers de enunciados sin demostración.
Esto reduce la aplicabilidad de D3 (no hay proof que extraer), pero no afecta
a D1/D2 (el enunciado solo basta).

---

## 6. Próximos pasos

1. **[PENDIENTE]** Selección final de 10-15 retirados + sus controles (decisión de Ayrton)
2. **[PENDIENTE]** Correr el pipeline de novedad (D2 → D1 → D3) sobre el dataset final
3. **[PENDIENTE]** Expandir el contador de teoremas para capturar nombres abreviados (thm, lem, prop) y AMS-TeX

---

## 7. Archivos generados

| Archivo | Descripción | Estado |
|---------|-------------|--------|
| `config/retracted_candidates.yaml` | 33 candidatos retirados con viabilidad | ✅ Completo |
| `config/control_candidates.yaml` | 26 pares retirado→controles (52 controles total) | ✅ Completo |
| `scripts/build_retracted_dataset.py` | Script de búsqueda y filtrado (+ cortesía de red) | ✅ Funcional |
| `scripts/build_control_candidates.py` | Script de emparejamiento de controles (+ cortesía de red) | ✅ Funcional |
| `docs/retracted_dataset_report.md` | Este reporte | ✅ Completo |
| `cache/retracted_dataset/` | Fuentes LaTeX cacheadas (v1) | ✅ 33+382 papers |
