# Bitácora de decisiones de diseño

**Propósito:** registrar cada decisión de diseño no trivial del proyecto AViD Journal, con fecha, alternativas consideradas, y el porqué de la elección. Cuando un reviewer (o Wenda Li, o un supervisor de PhD) pregunte "¿por qué decidiste X?", la respuesta está acá.

**Formato sugerido por entrada:**
- **Fecha** (YYYY-MM-DD)
- **Decisión** (qué se decidió, en una oración)
- **Alternativas consideradas** (qué otras opciones había)
- **Razonamiento** (por qué se eligió esta)
- **Reversibilidad** (qué tan caro sería cambiar después)

---

## Decisiones tomadas durante el diseño del sprint (pre-Día 3)

### 2026-05-XX — Métrica de novedad como conjunción de tres dimensiones independientes

**Decisión:** definir novedad como conjunción de (D1) no-existencia previa, (D2) no-trivialidad, (D3) distancia estructural de pruebas.

**Alternativas consideradas:**
- Solo D1 (el baseline de Kasaura et al.): rechazado porque marca "suma de 4 pares" como novedoso.
- D1 + D2 sin D3: rechazado porque no captura "misma afirmación, prueba nueva".
- Métrica única continua en lugar de tres binarias: rechazado por dificultad de interpretación y calibración.

**Razonamiento:** las tres dimensiones miden cosas conceptualmente independientes y los modos de falla son distintos. Combinarlas en un escalar único oculta información diagnóstica útil para el paper.

**Reversibilidad:** alta. Se puede agregar D4 más adelante o reformular D3 sin tocar las otras.

### 2026-05-XX — Distancia de Jaccard sobre conjuntos de premisas para D3

**Decisión:** medir distancia entre pruebas como `1 - |P(π₁) ∩ P(π₂)| / |P(π₁) ∪ P(π₂)|`.

**Alternativas consideradas:**
- Distancia coseno sobre vectores TF-IDF de premisas: más sofisticada pero introduce un parámetro extra (IDF requiere corpus de referencia).
- Distancia sobre grafos de dependencia completos (no solo conjuntos): más fina pero mucho más cara de calcular.
- Edit distance sobre términos de prueba como árboles de sintaxis: frágil, ruido de formalización.
- Homotopía entre términos: rechazado por proof irrelevance en `Prop` (los términos colapsan).

**Razonamiento:** Jaccard es simple, sin parámetros libres adicionales, geométricamente interpretable, y la literatura cercana (Axiom-Based Atlas de Yoo) la usa. Las mejoras (IDF, grafos) son trabajo futuro declarado.

**Reversibilidad:** media. La función de distancia es modular; cambiarla no toca el resto del pipeline.

### 2026-05-XX — Filtro de trivialidad vía tácticas estándar (no por presencia en mathlib)

**Decisión:** D2 corre tácticas `T_auto = {decide, omega, simp, norm_num, aesop, tauto}` sobre el enunciado. Si alguna lo cierra → trivial.

**Alternativas consideradas:**
- "Trivial = no está en mathlib": rechazado porque colapsa trivialidad con ausencia (mathlib contiene teoremas profundísimos).
- "Trivial = prueba corta (pocas líneas)": rechazado porque la longitud no refleja dificultad matemática.

**Razonamiento:** las tácticas estándar son el proxy honesto de "cerrable sin idea". Sobre-aproxima (a veces `aesop` cierra cosas no triviales), pero el sesgo va hacia "no novedoso", que es el error seguro.

**Reversibilidad:** alta. Agregar o quitar tácticas de `T_auto` es trivial.

### 2026-05-XX — AViD autoformaliza el par teorema-demostración, no solo el enunciado

**Decisión:** el sistema autoformaliza tanto `τ` como `π`. La evaluación se hace end-to-end.

**Alternativas consideradas:**
- Formalizar a mano los teoremas del eval set: rechazado porque oculta el eslabón más frágil del sistema (la traducción).
- Autoformalizar solo el enunciado y dejar la prueba a un prover externo: rechazado por complejidad de coordinación en v1.

**Razonamiento:** evaluar lo que el sistema *realmente* va a hacer, no una versión idealizada. La fragilidad de la traducción se reporta como Capa 1 separada de la Capa 2 (clasificación), para no confundir errores de traducción con errores de métrica.

**Reversibilidad:** alta. Si en v2 conviene separar las etapas, se hace.

### 2026-05-XX — Eval set con 26 teoremas firmes + 9 slots TBD

**Decisión:** las categorías 2 (clásicos no en mathlib), 5 (literatura no formalizada) y 6 (teoremas muy nuevos) se llenan durante implementación, no a ciegas.

**Razonamiento:** poblar esas categorías exige verificar mathlib y arXiv en vivo. Inventar a ciegas contaminaría el ground truth.

**Reversibilidad:** trivial.

---

## Decisiones pendientes para resolver durante el sprint

- Valor inicial del umbral `θ` para D3. Empezar con 0.5 y calibrar contra T07/T08/T09.
- Implementación de `isDefEq` (D1 nivel 1) o quedarse con D1 nivel 0 sintáctico para v1.
- Si los tres pares estrella (T07/T08/T09) entran todos o si T09 queda en reserva.
- Stack de la web demo: Gradio (más simple) vs. Streamlit vs. Next.js (más profesional).

---

## Decisiones tomadas durante implementación

### 2026-05-31 — Preservar "generalization" y "specialization" del juez LLM como Caso 5 ("zona gris")

**Decisión:** los veredictos `generalization` y `specialization` que emite `llm_judge.judge_theorem_pair()` de `src/novelty/` no se descartan en `src/novelty_v2/`. Se mapean al Caso 5 de la matriz taxonómica de la spec ("tipos relacionados pero no iguales — zona gris que requiere revisión humana") y se exponen en el campo `revision_humana=True` del veredicto de salida.

**Alternativas consideradas:**
- Colapsar ambos en `NOVEDAD_ENUNCIADO`: rechazado — una generalización no es una afirmación nueva independiente; confunde el mensaje al usuario.
- Ignorarlos y relanzar la búsqueda: rechazado — descarta información valiosa del juez.

**Razonamiento:** la spec ya prevé este caso ("zona gris") y recomienda explícitamente no forzar etiqueta. El juez LLM ya distingue estos casos con alta precisión. Preservarlos respeta el diseño de la spec y enriquece la salida del demo (el usuario ve "este enunciado es una generalización de X — revisión humana sugerida").

**Reversibilidad:** alta. El campo `revision_humana` es aditivo; colapsarlo a otro veredicto en v2 es un cambio local en `types.py`.

### 2026-06-01 — LeanDojo v1 para extracción de premisas (D3); LeanDojo-v2 como segunda capa del demo post-sprint

**Decisión:** para el sprint actual, usamos **LeanDojo v1** (`lean-dojo` en PyPI) para extracción de premisas (D3). LeanDojo-v2 queda reservado como segunda capa del demo público post-sprint (ver `future_work.md` P4).

**Aclaración conceptual (para evitar confusión futura):** LeanDojo v1 y LeanDojo-v2 NO son versiones de la misma herramienta — son herramientas con propósitos completamente distintos:
- **LeanDojo v1:** extracción de datos de pruebas — tracing, `get_premises()`, conjuntos de premisas. Es la herramienta de D3.
- **LeanDojo-v2:** framework para agentes de demostración automática (train + prove). No tiene API de extracción de premisas. Es la capa de prueba del demo post-sprint.

**Alternativas consideradas:**
- Usar LeanDojo-v2 para D3: rechazado — v2 no expone extracción de premisas (confirmado buscando en repo y PyPI).
- Extractor custom en Lean metaprogramming: rechazado — semanas de trabajo, fuera del scope del sprint.

**Razonamiento:** la literatura que cita la spec (Magnushammer de Wenda Li, Piotrowski et al.) usa LeanDojo v1 para premise selection. Usar la misma infraestructura es correcto para el paper y para el posicionamiento frente a esa literatura.

**Reversibilidad:** alta. Son módulos independientes; añadir v2 al demo post-sprint no toca D3.

### 2026-06-01 — Pipeline en tiempo real para D1 + D2; D3 a pedido offline

**Decisión:** el demo del sprint procesa papers en tiempo real mostrando progreso en pantalla. **D1** (no-existencia, vía mathlib + arXiv) y **D2** (trivialidad, vía tácticas estándar) corren automáticamente sobre cada teorema. **D3** (distancia de premisas vía LeanDojo) se ofrece como análisis adicional a pedido del usuario, procesado offline en máquina local con WSL+LeanDojo y devuelto asincrónicamente.

**Alternativas consideradas:**
- D3 también automática en tiempo real: descartado por costo computacional (ver decisión D-XX-B sobre tracing transitivo) — un usuario que sube un paper no puede esperar las horas que toma un tracing.
- D3 totalmente excluido del demo: descartado porque la distancia de premisas es la dimensión más distintiva del paper (lo que diferencia AViD del baseline de Kasaura et al.).

**Razonamiento:** la cola asíncrona conserva el valor científico de D3 sin bloquear la experiencia interactiva del demo. El usuario ve el veredicto D1+D2 inmediatamente; si pide D3 sobre un teorema marcado como "enunciado similar encontrado", recibe el análisis en una segunda pasada.

**Reversibilidad:** alta. Si LeanDojo (o un sucesor) se vuelve escalable a tiempo real post-sprint, D3 puede migrarse al pipeline automático sin tocar D1/D2 ni la API del demo.

### 2026-06-01 — Hallazgo empírico: LeanDojo traza dependencias transitivas, no solo archivos del proyecto

**Decisión / hallazgo:** contrario a la asunción de trabajo inicial, LeanDojo no traza únicamente los archivos `.lean` del proyecto cargado — procesa toda la cadena de imports transitiva. En el smoke test sobre `yangky11/lean4-example` (que tiene 2 teoremas en un único archivo, y NO importa Mathlib), LeanDojo inició el procesamiento de 1518 archivos correspondientes a la stdlib de Lean 4 e infraestructura de Lake.

**Implicaciones para el sprint:**
- El "tracing puntual de archivos sueltos" que asumíamos posible para el demo en tiempo real no es alcanzable con la API actual de LeanDojo v1.
- Para D3 manual del Día 7 sobre los pares estrella (T07, T08, T09), aceptamos una corrida larga única que traza mathlib una vez y reusamos los resultados extraídos.
- El tiempo realista de tracing de mathlib `v4.29.0` en CPU sigue sin estar documentado; va a ser una de las primeras mediciones del Día 7.

**Reversibilidad:** N/A. Es un hallazgo empírico que reorienta arquitectura, no una decisión reversible. Registrado como tal para futuro reviewer y para no repetir el experimento.

### 2026-06-03 — Presupuesto de tiempo por táctica en D2

**Decisión:** los presupuestos en segundos para el filtro de trivialidad (D2) son:
- `decide`, `omega`, `simp`, `norm_num`, `tauto`, `exact?`: 10 s cada una.
- `aesop`: 30 s (búsqueda más exhaustiva, puede tardar más).
- Límite duro de OS: `budget + 5 s` de timeout en subprocess (independiente de `maxHeartbeats`).

**Alternativas consideradas:**
- Presupuesto uniforme de 30 s para todas: rechazado — `decide`/`omega`/`norm_num` son instantáneos; esperar 30 s en cada uno alarga innecesariamente los casos no triviales.
- Sin `maxHeartbeats` (solo OS timeout): rechazado — `maxHeartbeats` permite que Lean cierre limpiamente antes del kill, evitando archivos corruptos. Se usa la conversión `400_000 heartbeats/s` como techo generoso.
- Presupuesto separado para `exact?` mayor que 10 s: rechazado para v1; si en la práctica `exact?` necesita más, se ajusta.

**Razonamiento:** `aesop` es el único que justifica más tiempo por su estrategia de búsqueda iterativa. Los valores son iniciales y ajustables — lo que importa es que queden registrados como defaults en `d2_triviality.py` y aquí.

**Reversibilidad:** trivial. Son parámetros en un `dict` en `d2_triviality.py`.

### 2026-06-01 — Demo del sprint como Versión 2 asíncrona incompleta (pipeline end-to-end con streaming)

**Decisión:** el demo no será una galería estática de ejemplos precomputados. Será una interfaz que recibe papers `.tex` completos del usuario, los procesa con streaming visual del progreso (parser → autoformalización → D1 → D2), y devuelve una tabla de teoremas con su veredicto. Cada teorema marcado como "enunciado similar encontrado" exhibe un botón **"solicitar análisis fino"** que dispara D3 vía cola asincrónica con respuesta diferida.

**Alternativas consideradas:**
- Galería de ejemplos precomputados: descartado por bajo valor demostrativo — no muestra que AViD funciona sobre input nuevo.
- Demo enteramente síncrono: descartado porque D3 no se puede hacer en tiempo real (ver decisión sobre LeanDojo transitivo).

**Razonamiento:** el demo es simultáneamente una herramienta técnica y un dispositivo narrativo. La interfaz asíncrona refleja honestamente la arquitectura real del sistema y comunica que D3 es una operación cara — un dato relevante para la audiencia de Wenda Li / Welleck / van Doorn.

**Reversibilidad:** media. La cola SQLite y el endpoint asincrónico se pueden extraer del demo público si en algún momento se desea servirlo a escala con backend dedicado.

### 2026-06-07 — Pipeline automatizado corre en Windows nativo; WSL preservado solo para D3 manual

**Decisión:** el pipeline de formación y la métrica de novedad (D1 + D2) corren en **Windows nativo** (Lean 4.29.0 `x86_64-w64-windows-gnu`, commit `98dc76e3`). WSL queda preservado exclusivamente para el **Día 7**: corrida manual de LeanDojo sobre los pares T07/T08/T09 (necesita Python ≥3.10 + LeanDojo en Linux). El resto del sprint es 100% Windows.

**Contexto de la decisión:** se intentó usar WSL como entorno primario para el pipeline automatizado (razón original: LeanDojo solo funciona en Linux). Durante el Día 4 se peleó con el caché de Mathlib en WSL: dos corridas de `lake exe cache get` resultaron en archivos `.ltar` corruptos (lectura y escritura concurrentes), dejando 5 759 oleans válidos pero `Mathlib.olean` faltante. La pipeline de D2 falló completamente. Al mismo tiempo, Windows nativo tenía 8 247 oleans completos (0 vacíos), `Mathlib.olean` presente, y el pipeline de formalizción ya funcionaba ahí.

**Evidencia que soporta la decisión:**
- `lake env lean` en Windows: `exit=0` en 165.8 s (primera corrida fría) y ~30 s con caché de OS caliente.
- WSL post-corrupción: `import Mathlib` → error, `Mathlib.olean` ausente sin corrección fácil.
- Overhead de inicio fijo: ~30 s/invocación en Windows con caché caliente (medido empíricamente: decide=31.6s, norm_num=28.8s, omega=28.4s). Absorber con `LEAN_STARTUP_OVERHEAD_S = 45`.

**Alternativas consideradas:**
- Reparar el caché de Mathlib en WSL: descartado. El problema era concurrencia en la descompresión de `.ltar` — requería una corrida limpia larga y arriesgada. Windows ya funciona.
- Mantener WSL como entorno principal con Mathlib reconstruido: descartado. Tiempo del sprint > valor de uniformidad de entorno.
- Docker con imagen Lean: descartado para el sprint actual (overhead de setup + no resuelve LeanDojo en D3).

**Razonamiento:** el criterio es pragmático — usar el entorno que ya funciona. LeanDojo (la única razón para WSL) es manual y puntual (Día 7). Todo lo demás ya corría bien en Windows. La decisión elimina una fuente de bloqueo sin comprometer nada.

**Reversibilidad:** alta. Si en el futuro se necesita Linux para CI u otra razón, los archivos de Python son agnósticos de plataforma; el único cambio necesario es ajustar `LEAN_STARTUP_OVERHEAD_S` y los paths por defecto.

### 2026-06-09 — Orden de D1 sobre corpus: C_F prevalece sobre C_I

**Decisión:** cuando D1 sobre C_F (Mathlib vía Leandex) encuentra match, el pipeline **no** ejecuta D1 sobre C_I. El veredicto provisional es `MATCH_ENCONTRADO_PENDIENTE_D3`.

**Alternativas consideradas:**
- Siempre correr ambas D1 (C_F y C_I): rechazado por costo computacional sin beneficio claro para el árbol de decisión — un hit en C_F ya determina el camino relevante (D3).
- Correr C_I en paralelo con C_F y consolidar al final: rechazado por complejidad sin ganancia de precisión.

**Razonamiento:**
1. Estar formalizado en Mathlib es información más fuerte que estar mencionado en literatura informal. Un hit en C_F + D3 es la vía de decisión relevante.
2. Una funcionalidad secundaria de AViD es recomendar teoremas candidatos a agregar a Mathlib. Buscar en C_I después de un hit en C_F no aporta a esa funcionalidad.
3. Reduce costo computacional (una llamada a Semantic Scholar + una a Claude) sin perder precisión en el árbol de decisión.

**Reversibilidad:** alta. Se puede agregar flag `mode="full_evaluation"` después si conviene para la sección de evaluación del paper (correr ambas C_F y C_I siempre).

### 2026-06-09 — Veredicto provisional MATCH_ENCONTRADO_PENDIENTE_D3

**Decisión:** cuando un teorema tiene match en D1-C_F pero D3 no se ha ejecutado (D3 es manual offline para pares estrella), el sistema emite veredicto `MATCH_ENCONTRADO_PENDIENTE_D3`. El mensaje al usuario es: "El enunciado se encontró en Mathlib. Para determinar si la prueba propuesta es novedosa o redundante, solicite análisis estructural fino (D3)."

**Alternativas consideradas:**
- `NO_NOVEDOSO_redundante` con caveat: rechazado — es conjetural y viola el principio de honestidad operacional (asume que las pruebas son cercanas sin medirlo).
- `PROBABLE_REDUNDANTE`: rechazado por la misma razón.
- Bloquear el pipeline hasta que D3 responda: rechazado — D3 puede tardar horas (LeanDojo traza Mathlib completo).

**Razonamiento:** el demo presenta resultados honestos. Si D3 no corrió, decirle al usuario "probablemente redundante" es incorrecto. El veredicto provisional hace explícita la incertidumbre y la resuelve a pedido.

**Reversibilidad:** alta. Cuando D3 se automatice post-sprint, este veredicto provisional desaparece y se reemplaza por `NOVEDAD_DEMOSTRACION` o `NO_NOVEDOSO_redundante` según el valor de Jaccard.

### 2026-06-09 — Cache organizado por endpoint con políticas de invalidación separadas

**Decisión:** toda función que consume API externa usa `src/novelty/_cache.cache_or_fetch` con `namespace` específico por endpoint. La estructura en disco es `cache/novelty/<namespace>/`. Los namespaces activos y su correspondencia con los endpoints son:

| Namespace (en código) | Endpoint | Equivalente en DECISIÓN C |
|---|---|---|
| `mathlib` | Leandex (búsquedas Mathlib) | `leandex/` |
| `judge_theorem` | Anthropic API (comparación enunciados) | `llm_judge/` |
| `judge_method` | Anthropic API (comparación métodos) | `llm_judge/` |
| `d2_lean` | (reservado, opcional) | `d2_lean/` |

Reglas adicionales:
- Para `judge_theorem` y `judge_method`, la clave incluye el texto completo del prompt (que contiene ambos enunciados + versión del modelo), hasheada con SHA1.
- `temperature=0` en **todas** las llamadas al LLM judge (ver PASO 3.C para implementación).
- Política de invalidación: las entradas no se invalidan automáticamente. Invalidación manual por namespace completo cuando cambia el modelo o la versión del prompt.

**Alternativas consideradas:**
- Cache plano en un solo directorio: rechazado por dificultad de invalidación selectiva.
- Base de datos SQLite: rechazado — overhead de setup sin ganancia para el sprint.

**Razonamiento:** la estructura por namespace permite borrar (e.g.) todas las respuestas del LLM judge sin tocar el cache de Leandex, y viceversa. Costo de setup: cero (ya implementado en `_cache.py`).

**Reversibilidad:** media. Los nombres de namespace están hardcodeados en `src/novelty/` (congelado). Cambiarlos requeriría migrar archivos de cache. Para `novelty_v2`, usar siempre los nombres de la tabla.

### 2026-06-10 — Trivialidad operacional como propiedad relativa a (T_auto, Mathlib_version)

**Decisión:** D2 define trivialidad respecto al par exacto `(T_auto, Mathlib_version)` en el momento de la evaluación. En este paper: `T_auto = {decide, omega, simp, norm_num, aesop, tauto, exact?}`; Mathlib v4.29.0 (commit `8a178386`). Esta relatividad **no es limitación** — es la definición operacional correcta de trivialidad para novelty checking. Si un resultado se obtiene sin idea matemática usando herramientas estándar actuales, no es contribución genuina.

**Caso paradigmático:** T01 y T08 (`Irrational (Real.sqrt 2)`) son cerrados por `norm_num` en Mathlib v4.29.0 en 14 s. La intuición pre-sprint los marcaba como "no triviales" desde la perspectiva matemática clásica (requieren ~5 páginas en estilo Weierstrass). D2 los marca trivial porque `norm_num` incorpora decisión algebraica de irracionalidad de raíces. Esto es correcto — ya no requieren idea matemática.

**Implicación para reproducibilidad:** el paper reporta explícitamente `T_auto` y la versión de Mathlib usada. Reproducciones cross-versión deben actualizar ambos; es esperable que resultados difieran cuando Mathlib amplía las extensiones de tácticas.

**Alternativas consideradas:**
- Definir trivialidad respecto a una versión congelada de Mathlib como "trivialidad canónica": rechazado porque congela la métrica contra el avance del campo. Un resultado que hoy requiere 5 páginas y mañana cierra con `omega` ES menos novedoso mañana.
- No mencionar la relatividad en el paper y reportar resultados como absolutos: rechazado — un reviewer sofisticado (Wenda Li, Jeremy Avigad) lo notará y lo señalará como ingenuidad metodológica.

**Razonamiento:** la relatividad bien declarada es una fortaleza metodológica. Permite que el paper contribuya dos cosas: (1) el framework de novelty checking y (2) una instantánea del estado de la automatización matemática en Mathlib v4.29.0. Comparar con futuras versiones es investigación derivada válida.

**Reversibilidad:** alta. Solo afecta narrativa del paper y sección de Methodology. El código no cambia.
