# CLAUDE_CODE_BRIEFING.md

**Documento de orientación para Claude Code trabajando en el sprint de AViD Journal.**

Este archivo es el punto de entrada para cualquier chat nuevo de Claude Code en el proyecto. Si estás leyendo esto como Claude Code recién empezado, leelo entero y después dame un resumen de 5-10 puntos confirmando qué entendiste, antes de tocar código.

**Última actualización:** 8 de junio de 2026 — comienzo del Día 5 del sprint.

---

## 1. Qué es AViD Journal

AViD Journal es un sistema automatizado para chequear novedad y verificar formalmente teoremas de papers matemáticos. El usuario sube un `.tex`, el sistema parsea bloques, los autoformaliza a Lean 4, los verifica, y mide novedad contra dos corpus: mathlib (formal) y arXiv/Semantic Scholar (informal).

El proyecto vive en `D:\Mis documentos\Documentos\AViD Journal\` (Windows nativo, NO WSL para flujo automático). Repo público: `https://github.com/ayrtonporto/avid-journal`.

El autor es Ayrton Porto, matemático argentino de UNICEN. El proyecto tiene dos objetivos simultáneos: ser un producto funcional ofreciendo chequeo de novedad como servicio, y producir un paper que sirva como credencial para aplicaciones de PhD (Wenda Li en Edinburgh, Welleck en CMU, van Doorn en Bonn).

## 2. El sprint en curso

Cuatro entregables para el 7 de julio de 2026:

1. **Demo web público con URL estable.** Versión 2: pipeline asíncrono que acepta papers `.tex`, los procesa con D1+D2 en tiempo real con streaming visible, ofrece D3 como análisis a pedido.
2. **Métrica implementada** según `paper/metric_spec.md`. Tres dimensiones (D1 existencia en corpus, D2 trivialidad, D3 distancia de premisas). D1+D2 automatizadas, D3 manual para pares estrella.
3. **Evidencia sobre el eval set** de `paper/eval_set.csv` (26 teoremas firmes + slots TBD).
4. **Preprint subido a arXiv** referenciando demo URL y resultados.

El día 7 de julio se envían emails de outreach a supervisores con el preprint + URL + write-up.

## 3. Decisiones arquitecturales clave (irrevocables salvo nueva evidencia)

1. **Pipeline corre en Windows nativo.** WSL2 está preservado solo para D3 manual en Días 8-9. No tocar WSL para el flujo automático.

2. **`src/novelty/` se congela.** Es el pipeline previo (stages 0-3) que funcionaba antes del sprint. Se importa como dependencia desde `src/novelty_v2/`, no se modifica.

3. **`src/novelty_v2/` implementa la spec.** Tres dimensiones según `paper/metric_spec.md`. Cinco veredictos finales: NOVEDAD_ENUNCIADO, NOVEDAD_DEMOSTRACION, CONOCIDO_LITERATURA, NO_NOVEDOSO_redundante, NO_NOVEDOSO_trivial. Más ZONA_GRIS para los casos `generalization`/`specialization` del juez LLM.

4. **D3 (distancia de premisas) es manual offline** para los pares estrella del eval set (T07, T08, T09). LeanDojo se usa una sola vez en WSL para extraer premisas de esos pares. NO se intenta automatizar D3 en el sprint.

5. **Demo en tiempo real con streaming.** D1 y D2 corren en tiempo real mostrando progreso al usuario en pantalla. D3 se ofrece como botón "Solicitar análisis estructural fino" con cola SQLite procesada offline por Ayrton.

6. **Back-translation y verificación de fidelidad de autoformalización** quedan como future work explícito. Mencionar como dirección de research para el PhD pero no implementar en el sprint.

7. **Hallazgo empírico documentado del Día 3:** LeanDojo traza dependencias transitivas, no archivos sueltos. Esto descartó la posibilidad de tracing puntual y justificó D3 manual.

8. **Hallazgo empírico documentado del Día 4:** D2 tarda ~30s por invocación de `lake env lean` en Windows con cache caliente. LEAN_STARTUP_OVERHEAD_S = 45 en el código. Implicación: D2 sobre el eval set entero tarda decenas de minutos por corrida. Demo necesita streaming visual.

9. **T23 cierra por `tauto`, no por `aesop`,** porque `IsTree = Connected ∧ IsAcyclic` en mathlib v4.29.0 es una conjunción proposicional. Falso positivo de D2 documentado, no es bug.

## 4. Estado del repo y del entorno

**Última actualización en branch main:** commit `c2e52df` "feat(novelty_v2): D2 runs on Windows native, validate on eval set T14-T18+T23" (cerró Día 4).

**Estructura relevante:**

```
src/
├── novelty/              ← congelado
│   ├── novelty_checker.py
│   ├── mathlib_checker.py     (D1 sobre C_F, vía Leandex)
│   ├── arxiv_search.py        (D1 sobre C_I, etapa A)
│   ├── block_comparator.py    (embeddings MiniLM)
│   ├── llm_judge.py           (juez LLM, etapa B)
│   ├── paper_extractor.py
│   └── _cache.py
├── novelty_v2/           ← código nuevo del sprint
│   ├── types.py          (D1Result, D2Result, D3Result, NoveltyVerdict)
│   ├── dimensions/
│   │   ├── d1_existence.py    (vacío)
│   │   ├── d2_triviality.py   (✅ implementado y validado)
│   │   └── d3_proof_distance.py (vacío)
│   └── README.md
├── formalization/        ← no se toca (pipeline de formalización previo)
└── parser/               ← no se toca (parser LaTeX)

scripts/
└── d2/test_eval_set.py   (✅ script que corre D2 sobre el eval set)

paper/
├── metric_spec.md, eval_set.csv, related_work.md,
├── decisions.md, results_log.md, limitations.md, future_work.md,
├── outreach.md, CLAUDE_CODE_BRIEFING.md (este archivo),
└── preprint/draft.md, preprint/abstract.md
```

**Entorno técnico (Windows nativo):**
- Lean 4.29.0 instalado (`lean --version` desde `lean_project/`)
- Mathlib compilada con 7871 oleans en `lean_project/.lake/`
- Python 3.10+ con venv en `D:\...\AViD Journal\.venv\` (si existe; si no, crear)
- Dependencias en `requirements.txt`

**Entorno WSL (preservado para Días 8-9):**
- Ubuntu 22.04 en `D:\WSL\Ubuntu2204\`
- Repo clonado en `~/avid-journal/`
- Venv con `lean-dojo 4.20.0` ya instalado
- Toolchain Lean v4.29.0
- Mathlib en WSL: caché corrupto, NO usable para D1+D2 (ese fue el motivo del pivot a Windows)

## 5. Roadmap día por día (8 de junio a 7 de julio)

**Notas:** Ayrton trabaja de 19:00 a 03:00 hora Argentina (UTC-3). Cada "día" del roadmap corresponde a una sesión nocturna que empieza esa fecha. Los descansos son innegociables — la calidad cae con fatiga.

### Semana 1 — Pipeline core (9-15 de junio)

- **Día 5 (lunes 9):** Correr D2 sobre los 30 teoremas del eval set completo. Producir tabla de aciertos por categoría y tiempos por táctica.
- **Día 6 (martes 10):** Integración D1 con novelty_v2. Envolver `mathlib_checker` y `llm_judge` en `D1Result`. Primer `NoveltyVerdict` end-to-end.
- **Día 7 (miércoles 11):** Pipeline D1+D2 sobre los 30 teoremas. Guardar en SQLite.
- **Día 8 (jueves 12):** Reactivar WSL. LeanDojo sobre pares T07 y T08. Anotar tiempos reales del tracing transitivo.
- **Día 9 (viernes 13):** Completar T09 si T07/T08 funcionaron. Aplicar math filter. Calcular Jaccard.
- **Sábado 14:** DESCANSO.

### Semana 2 — Demo web (15-21 de junio)

- **Día 11 (lunes 15):** Scaffold Gradio. Landing con matriz de cuatro casos y caso Axiom.
- **Día 12 (martes 16):** Upload .tex + pipeline conectado con streaming visible.
- **Día 13 (miércoles 17):** Tabla de veredictos por teorema. Botón D3. Cola SQLite.
- **Día 14 (jueves 18):** Pulido, robustez, manejo de errores.
- **Día 15 (viernes 19):** Deploy a Hugging Face Spaces (o alternativa). URL pública estable.
- **Sábado 20:** Buffer o descanso.

### Semana 3 — Preprint (22-28 de junio)

- **Día 17 (lunes 22):** Preprint: Introduction + Related Work.
- **Día 18 (martes 23):** Preprint: Methodology.
- **Día 19 (miércoles 24):** Preprint: Implementation + Evaluation.
- **Día 20 (jueves 25):** Preprint: Limitations + Future Work + Conclusion.
- **Día 21 (viernes 26):** Figuras (árbol, matriz, tabla, arquitectura).
- **Sábado 27:** DESCANSO.

### Semana 4 — Publicación y outreach (29 junio - 7 julio)

- **Día 23 (lunes 29):** Abstract + pulido del preprint.
- **Día 24 (martes 30):** Referencias + segunda lectura.
- **Día 25 (miércoles 1 jul):** Compilar PDF + revisión final.
- **Día 26 (jueves 2):** Subir a arXiv. Esperar moderación.
- **Día 27 (viernes 3):** Preparar emails personalizados + write-up técnico de 2-3 páginas.
- **Sábado 4:** Buffer.
- **Día 29 (domingo 5):** Última revisión de outreach.
- **Día 30 (lunes 7):** ENVÍO DE EMAILS A SUPERVISORES.

## 6. Reglas de trabajo no-negociables

1. **No tocar src/novelty/, src/parser/, ni src/formalization/.** Son código previo que funciona y se usa como dependencia.

2. **Marcar siempre hechos vs. inferencias.** Si decís algo como afirmación, debe ser cosa que verificaste con código o documento. Si es inferencia, marcala con "probablemente" o "según mi entendimiento".

3. **Mostrar output real, no descripciones.** Después de implementar, correr el código y mostrar el output literal. No "debería funcionar".

4. **Conventional Commits siempre.** `feat(scope): ...`, `fix(scope): ...`, `docs: ...`, `refactor: ...`, `chore: ...`.

5. **No AI attribution en commits.** El commit es del autor del repo.

6. **No procesos largos sin avisar.** Si algo va a tardar más de 1 minuto, avisar primero. Si tarda más de 5, parar y reconsultar.

7. **No `run_in_background` salvo pedido explícito.**

8. **Regla del cuelgue de 2 horas.** Si un setup técnico nos come más de 2 horas sin avanzar el día planeado, pivotear sin discutir. Avisar a Ayrton y reconsiderar la estrategia.

9. **Implementar solo lo pedido.** No agregar features extra, logging avanzado, tests exhaustivos, ni refactors no pedidos.

10. **Actualizar paper/results_log.md al final de cada día.** Dos o tres oraciones honestas: qué se hizo, qué quedó andando, qué quedó pendiente.

## 7. Archivos a leer en orden de prioridad

Para entrar al proyecto, leé en este orden antes de tocar código:

1. Este archivo (CLAUDE_CODE_BRIEFING.md).
2. `paper/metric_spec.md` — la métrica conceptual completa.
3. `paper/eval_set.csv` — los teoremas que evalúan la métrica.
4. `paper/decisions.md` — todas las decisiones de diseño y por qué.
5. `paper/results_log.md` — qué se hizo cada día.
6. `paper/limitations.md` — limitaciones declaradas (importa para el paper).
7. `paper/related_work.md` — qué hay en la literatura, dónde se ubica AViD.
8. `paper/future_work.md` — qué queda fuera del sprint conscientemente.

Para implementación:

9. `src/novelty/__init__.py` — entender qué exporta el pipeline existente.
10. `src/novelty_v2/types.py` — los tipos del pipeline nuevo.
11. `src/novelty_v2/dimensions/d2_triviality.py` — referencia de cómo está armado D2 (es el modelo para D1 y D3).

## 8. Lo que NO hay que hacer

- **No reescribir `metric_spec.md`** sin pedirlo. Es la fuente de verdad de la métrica.
- **No tocar `src/novelty/`.** Importarlo como dependencia.
- **No volver a discutir si LeanDojo entra al flujo automático.** Esa decisión está cerrada: no entra.
- **No volver a discutir WSL como entorno principal.** Está cerrado: el flujo automático corre en Windows nativo, WSL solo para Días 8-9.
- **No agregar Versión 3 del demo** (servicio pleno, paralelización, etc.) al alcance del sprint. Va a future work.
- **No ofrecer "casos demo" sintéticos** generados ad-hoc. El demo público trabaja sobre el eval set real y sobre uploads del usuario.
- **No asumir que algo "debería funcionar".** Probarlo con código y mostrar el output.

## 9. Estado actual al arrancar este chat

- **Día 4 cerrado el 8 de junio.** D2 validado en Windows nativo sobre T14-T18+T23 (5/5 correctos + falso positivo registrado en T23).
- **Próximo día:** Día 5 (9 de junio, sesión 19:00-03:00 ART). Objetivo: D2 sobre los 30 teoremas del eval set entero.
- **Bloqueos conocidos:** ninguno. El entorno Windows está validado y funcionando.

## 10. Cómo arrancar este chat

Si sos un Claude Code recién empezado y leíste hasta acá, hacé lo siguiente:

1. Leé los archivos en el orden de la Sección 7.
2. Dame un resumen de 5-10 puntos confirmando qué entendiste sobre: objetivo, arquitectura, decisiones clave, plan del día actual, reglas de trabajo.
3. **NO toques código todavía.** Esperá mi aprobación.
4. Cuando te apruebe, procedé con el día que corresponda según el roadmap (Sección 5) y el estado actual (Sección 9).

Si algo del briefing te parece contradictorio o incompleto, decímelo antes de empezar. Es mejor aclarar ahora que descubrirlo después.
