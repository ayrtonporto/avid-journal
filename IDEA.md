Hola. Soy Ayrton Porto, matemático argentino, recibido en UNICEN
(Universidad Nacional del Centro de la Provincia de Buenos Aires)
con tesis sobre dualidades para retículos distributivos acotados.
GPA 9.41/10. Estoy aplicando a programas de PhD en formal theorem
proving / matemática asistida por IA.

Estoy desarrollando AViD Journal y voy a continuar el trabajo
contigo. Este mensaje te da el contexto completo. Por favor leelo
entero antes de responder. Al final hay tres preguntas que quiero
que me confirmes para verificar que entendiste bien.

═══════════════════════════════════════════════════════════════════
QUÉ ES AVID JOURNAL
═══════════════════════════════════════════════════════════════════

AViD Journal es un sistema automatizado para chequear novedad y
verificar formalmente teoremas matemáticos. El usuario sube un
archivo LaTeX, el sistema parsea bloques (teoremas, definiciones,
lemas), los autoformaliza a Lean 4, los verifica, y mide novedad
contra dos corpus: mathlib (corpus formal) y arXiv + Semantic
Scholar (corpus informal).

El proyecto tiene dos objetivos simultáneos:
1. Ser un producto funcional ofreciendo chequeo de novedad como
   servicio (MVP que va a estar online en avid-journal.github.io
   + demo en Hugging Face Spaces).
2. Producir un paper que sirva como credencial para aplicaciones
   de PhD (Wenda Li / Edinburgh, Sean Welleck / CMU, Floris van
   Doorn / Bonn) y eventualmente como base de research para tesis.

═══════════════════════════════════════════════════════════════════
MOTIVACIÓN — POR QUÉ EXISTE AVID
═══════════════════════════════════════════════════════════════════

En febrero de 2026, Axiom Math presentó la conjetura de Fel como
contribución nueva en matemática asistida por IA. Resultó ser
literatura tergiversada (caso público, Scientific American). Los
sistemas actuales (Axiom, Harmonic, ProofFlow, etc.) miden
CORRECTITUD pero no NOVEDAD. El baseline ingenuo "novedad = no
está en mathlib" falla por dos razones documentadas en literatura:

- Falla por trivialidad: hay teoremas no presentes en mathlib que
  las tácticas estándar cierran en milisegundos. No es novedad, es
  trivialidad.
- Falla por existencia informal: hay teoremas ausentes de mathlib
  pero ya probados en papers de arXiv. No es contribución nueva.

AViD cierra esa brecha midiendo novedad como CONJUNCIÓN de tres
dimensiones independientes.

═══════════════════════════════════════════════════════════════════
LA MÉTRICA — TRES DIMENSIONES
═══════════════════════════════════════════════════════════════════

D1 — NO-EXISTENCIA EN CORPUS
  ¿El enunciado ya existe en mathlib (C_F) o en literatura informal
  (C_I)? Dos sub-chequeos:
  - D1 sobre C_F: búsqueda semántica en mathlib via Leandex.
    Igualdad sintáctica tras normalización (nivel 0). Nivel 1
    deseable (isDefEq) queda como future work.
  - D1 sobre C_I: pipeline de dos etapas. Etapa A: embeddings sobre
    abstracts de Semantic Scholar/arXiv (filtro grueso, MiniLM).
    Etapa B: para papers que pasan el filtro, autoformalizar el
    teorema rival y comparar tipos. LLM judge con cuatro veredictos
    posibles (equivalent, generalization, specialization, different).

D2 — NO-TRIVIALIDAD
  ¿τ es matemáticamente trivial? Operacionalmente: τ es trivial
  cuando alguna táctica de T_auto = {decide, omega, simp, norm_num,
  aesop, tauto, exact?} lo cierra dentro de presupuesto fijo de
  tiempo. Se genera `example : τ := by T` por cada táctica y se
  verifica con `lake env lean`.

  HALLAZGO CONCEPTUAL CLAVE (importante para el paper):
  La trivialidad bajo D2 es RELATIVA al par (T_auto, Mathlib_version)
  en el momento de evaluación. Caso paradigmático: `Irrational
  (Real.sqrt 2)` — lo que Borel probó en cinco páginas en 1870, hoy
  norm_num lo cierra en 14 segundos. Esta relatividad no es
  limitación del diseño, es propiedad arquitectural correcta de
  novelty checking operacional.

D3 — DISTANCIA ESTRUCTURAL DE PRUEBAS
  Cuando D1 encontró match de tipo, ¿las pruebas usan ideas
  similares? Medida via distancia de Jaccard sobre conjuntos de
  premisas extraídas del proof term elaborado (vía LeanDojo).
  
  Por qué premisas y no homotopía: en Lean 4, los teoremas viven en
  Prop que es proof-irrelevant — dos términos del mismo Prop son
  definicionalmente iguales (Abel-Coquand decidible) pero la
  homotopía general es indecidible (Novikov 1955, Boone 1958 vía
  reducción al word problem). Las premisas son señal computable y
  semánticamente significativa.

═══════════════════════════════════════════════════════════════════
ÁRBOL DE DECISIÓN COMBINADO
═══════════════════════════════════════════════════════════════════

Aplicación en orden de costo creciente:

1. D2 primero. Si trivial → veredicto NO_NOVEDOSO_trivial. FIN.

2. D1 sobre C_F (Leandex, barato). Si match en mathlib → veredicto
   MATCH_ENCONTRADO_PENDIENTE_D3 (texto explicativo al usuario
   ofreciendo análisis estructural fino). FIN. NO ejecutar C_I.

3. Si no hay match en C_F → D1 sobre C_I (etapa A barata, etapa B
   cara con LLM judge).
   - Si match en C_I → CONOCIDO_LITERATURA
   - Si no match → NOVEDAD_ENUNCIADO. FIN.

4. (Modo manual offline) D3 aplicado a pares estrella del eval set
   (T07, T08, T09). Distancia de Jaccard sobre premisas. Si > θ →
   NOVEDAD_DEMOSTRACION. Si ≤ θ → NO_NOVEDOSO_redundante.

Cinco veredictos finales: NOVEDAD_ENUNCIADO, NOVEDAD_DEMOSTRACION,
CONOCIDO_LITERATURA, NO_NOVEDOSO_redundante, NO_NOVEDOSO_trivial.
Más MATCH_ENCONTRADO_PENDIENTE_D3 cuando D3 es offline.

═══════════════════════════════════════════════════════════════════
DECISIONES ARQUITECTURALES (cerradas, justificadas)
═══════════════════════════════════════════════════════════════════

DECISIÓN A — Orden de D1: C_F prevalece sobre C_I.
DECISIÓN B — Veredicto MATCH_ENCONTRADO_PENDIENTE_D3 cuando D3
  es manual y offline.
DECISIÓN C — Cache ordenado por endpoint con políticas claras,
  temperature=0 en llm_judge para reproducibilidad.
DECISIÓN D — Trivialidad operacional como propiedad relativa.

Decisiones operativas:
- Pipeline corre en Windows nativo, no WSL.
- src/novelty/ está congelado (código previo al sprint, funciona),
  se importa como dependencia desde src/novelty_v2/.
- src/novelty_v2/ es donde vive el código nuevo del sprint.
- D3 manual offline para pares estrella, no se automatiza en sprint.
- Demo Versión 2: D1+D2 en tiempo real con streaming visible al
  usuario, D3 a pedido vía cola SQLite.
- Autoformalización: usa pipeline existente (basado en
  Numina-Lean-Agent). Back-translation y verificación de fidelidad
  semántica multi-formalizador agnóstica son future work + dirección
  de research para el PhD.

═══════════════════════════════════════════════════════════════════
EVAL SET
═══════════════════════════════════════════════════════════════════

26 teoremas firmes curados a mano + 9 TBD. Para D2 se evalúan 24
únicos (los pares T07/T08/T09 cuentan como uno cada uno + T19
generado por LLM). Categorías:
- clasico_en_mathlib (T01-T06)
- par_distinta_prueba (T07a/b, T08a/b, T09a/b)
- enunciados_cercanos_distintos (T10-T13, T26)
- trivial (T14-T18)
- generado_IA (T19, T20, T21)
- caso_falla (T22-T25)

═══════════════════════════════════════════════════════════════════
ESTADO ACTUAL DEL SPRINT (a 19 de junio de 2026)
═══════════════════════════════════════════════════════════════════

Sprint arrancó el 8 de junio. Objetivo: 7 de julio (envío de emails
a supervisores con preprint + demo URL).

DÍA 5 CERRADO. Cinco commits en main (después del merge del branch
claude/agitated-lovelace-e10f00):
- a8363fb: temperature=0 en llm_judge
- 8111751: árbol D1 actualizado según DECISIÓN A
- 1858bf7: registro de DECISIONES A/B/C en decisions.md
- 8bce499: cierre Día 5 con resultados eval set + L10/L11 + rerun script
- a95674e: reformulación de L10 + DECISIÓN D

CORRIDA D2 SOBRE EVAL SET: ejecutada. 24 teoremas, 26 minutos
total (mucho más rápido que estimado 90-130 min, gracias a prewarm
+ caché de OS). Resultados:
- 8 cierres por D2: T01 (norm_num, FP), T08 (norm_num, FP),
  T15 (decide), T16/T17/T22 (norm_num), T19 (aesop), T25 (exact?)
- Accuracy 20/23 = 87%
- T14/T18/T23/T26 originalmente fallaron por error de import (L11:
  Mathlib monolítico, solo `import Mathlib` o `import Mathlib.Tactic`
  funcionan como entry points). Re-corridos con import Mathlib
  completo. T23 confirmó FP via tauto en 30.6s.

LANDING PAGE: lista, deployada en avid-journal.github.io. Diseño
brutalismo académico + retrofuturismo de computación temprana
(serif académica + monospace + paleta granate). Repo:
github.com/avid-journal/avid-journal.github.io.

═══════════════════════════════════════════════════════════════════
LO QUE FALTA HASTA 7 DE JULIO
═══════════════════════════════════════════════════════════════════

Días 6-7 — Pipeline D1+D2 end-to-end sobre eval set. Necesita
resolver una cuestión técnica primero: el llm_judge requiere
llamadas a la API de Anthropic y todavía hay que decidir cómo lo
implementamos (ver siguiente sección).

Día 7-8 — D3 manual sobre pares estrella (probablemente recortado a
1-2 pares por restricciones de tiempo) usando LeanDojo en WSL.

Días 11-15 — Demo web Gradio + deploy a Hugging Face Spaces.

Días 17-21 — Preprint con secciones Methodology, Evaluation,
Limitations.

Días 22-26 — Pulido, abstract, subida a arXiv.

Día 30 (7 julio) — Emails a Wenda Li, Welleck, van Doorn, Heath
Sanchez (Metalogic Labs).

═══════════════════════════════════════════════════════════════════
CUESTIÓN TÉCNICA PENDIENTE
═══════════════════════════════════════════════════════════════════

El llm_judge necesita un modelo de lenguaje. Tres opciones que
estoy considerando:

A. API de Anthropic con saldo prepagado. Requiere $5-15 USD para
   el sprint. Costo manejable pero implica gasto monetario.
B. Vos (vía Claude Code) actuando como judge en bucle interactivo.
   Cero costo monetario pero rompe automatización.
C. Modelo local con Ollama (Llama 3, Mistral). Cero costo pero la
   calidad del judge cae notablemente.

Aún no decidido. Es lo primero que necesito resolver para arrancar
Día 6.

═══════════════════════════════════════════════════════════════════
PREGUNTAS DE RESEARCH ABIERTAS (para el paper + PhD)
═══════════════════════════════════════════════════════════════════

Q1 — Representación de pruebas: ¿cómo construir representaciones
de pruebas formales que sean (i) robustas a variación de
formalización y (ii) capturen la distinción matemática entre prueba
alternativa, generalización, especialización y novedad de
enunciado? Conecta directo con el trabajo de Wenda Li en
Magnushammer y la extensión de premise selection a representaciones
estructuradas.

Q2 — Generalización vs novedad: ¿cómo distinguir formalmente entre
"generalización de A" y "novedad relacionada con A"?

Q3 — Fidelidad de autoformalización: ¿cómo medir fidelidad semántica
de autoformalizaciones que type-checkean pero pueden no representar
lo que el paper dice? Conecta con el caso Axiom-Fel y con la idea
de capa multi-formalizador agnóstica para AViD.

═══════════════════════════════════════════════════════════════════
TRES COSAS QUE QUIERO QUE ME CONFIRMES
═══════════════════════════════════════════════════════════════════

Antes de continuar, decime:

1. ¿Entendiste por qué la métrica son tres dimensiones independientes
   y no una sola fórmula combinada? Explicalo brevemente con tus
   palabras.

2. ¿Cuál es tu lectura honesta sobre cuál de las tres opciones para
   el LLM judge conviene? Argumentá con criterio.

3. Algo que NO te quedó claro o tenés dudas. Cualquier cosa, no
   importa si parece tonta — prefiero clarificar ahora que descubrir
   un malentendido después.

Después de tus respuestas, vamos al Día 6.

Voy a pasarte también un documento técnico que Claude Code (la
sesión anterior que trabajaba conmigo en el sprint) preparó sobre
la estructura del repo, qué módulos hay, qué corre y qué no. Eso
te da el detalle implementacional.
