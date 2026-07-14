# AViD Journal — PAPER BRIEF (esqueleto de escritura)

**Generado:** 2026-07-12  
**Propósito:** Brief completo para la fase de escritura del preprint. Contiene la espina narrativa, el esqueleto de 8 secciones con los claims y cifras que van en cada una, y punteros a las fuentes de citas y datos.  
**Fuentes de citas y cifras:** `paper/bibliography_merged.md` (referencias) + `docs/bibliography_context.md` PARTE 2 (inventario de hallazgos). **No usar otras fuentes para números o claims.**

---

## Espina narrativa (una frase)

> Construimos el primer pipeline de veredictos de novedad con grounding formal, lo evaluamos contra ground truth real (papers retirados por duplicación), y encontramos que funciona exactamente hasta donde llega el corpus — y que cada capa de verificación automática falla de maneras que solo la auditoría humana atrapa.

---

## Sección 1 — Introducción

### Gancho
- Abrir con el caso Axiom Math / conjetura de Fel (Scientific American, febrero 2026) como evidencia pública del modo de falla.
- Cita de First Proof (Abouzaid et al., arXiv:2602.05192): *"lo que nos falta es una manera sistemática de evaluar si esos lemas pueden ensamblarse en una prueba novedosa"*.
- Cita de Tao (*Machine-Assisted Proof*, 2025): "matemática a escala → hace falta filtrar novedad automáticamente".

### El problema en una oración
Los sistemas actuales de AI matemática (Axiom, Harmonic, DeepSeek-Prover) verifican **corrección** pero no **novedad**. El baseline ingenuo "novedad = no está en Mathlib" (Kasaura et al., arXiv:2509.14274) falla por dos razones: trivialidad y existencia en literatura informal.

### Contribuciones (4)
1. Taxonomía de novedad como cruce de dos ejes (tipo × premisas) → 4 casos + zona gris.
2. Métrica operacional de 3 dimensiones: D1 (existencia en corpus formal+informal), D2 (no-trivialidad), D3 (distancia estructural de premisas).
3. Implementación funcional con pipeline end-to-end (Windows nativo, Lean 4.29, DeepSeek V4 + Leandex + TheoremSearch + ExtractData).
4. Evaluación contra ground truth real: 26 papers retirados por duplicación + 24 teoremas hand-curated + 5 pares de prueba estructural (D3).

---

## Sección 2 — Related Work

Organizar en **4 frentes**, no en enumeración plana. Cada frente cierra con cómo AViD se diferencia.

### Frente 1 — Búsqueda y organización de teoremas
- **TheoremSearch** (Ilin et al., arXiv:2602.05216): 9.2M enunciados, API. → AViD lo usa como fuente y agrega veredicto.
- **TheoremGraph + LeanGraph** (arXiv:2606.25363 `[VERIFICAR]`): grafo unificado formal-informal. → Compite en infraestructura; AViD agrega capa de decisión.
- **Matlas** `[VERIFICAR]`: unfolding topológico. → Solución al problema de proofs delegados.
- **Loogle, LeanSearch, LeanExplore, Lean Finder**: campo saturado de buscadores de Mathlib. → AViD consume, no compite.

### Frente 2 — Generación y filtrado de conjeturas
- **Kasaura et al.** (arXiv:2509.14274): baseline ingenuo (novedad = ausencia).
- **LeanConjecturer** `[VERIFICAR]`: exact? + aesop como filtros. → D1-fallback + D2 ya son estándar; nuestro aporte es la integración con D1-informal y D3.
- **COMPOSE** (arXiv:2605.30333 `[VERIFICAR]`): predicción forward. → Dirección complementaria.
- **Mining Math Conjectures** (arXiv:2412.16177): pruning heurístico.
- **Synthetic Theorem Generation** (OpenReview EeDSMy5Ruj).

### Frente 3 — Verificación y autoformalización
- **Pseudo-Formalization / ArxivMathGradingBench** `[VERIFICAR]`: corrección de papers arXiv. → Vecino exacto; nosotros novedad, ellos corrección.
- **MerLean** `[VERIFICAR]`: pipeline paper→Lean sin veredicto. → AViD es la capa que delegan.
- **ProofFlow** (arXiv:2510.15981), **Aria** (arXiv:2510.04520), **Wu et al.** (NeurIPS 2022), **Patel** (arXiv:2310.07957): autoformalización y sus limitaciones.
- **First Proof** (arXiv:2602.05192): el problema es urgente y los LLMs ya lo exhiben.

### Frente 4 — Estructura de pruebas y premise selection
- **Yoo / Atlas** (arXiv:2504.00063): proof vectors + Jaccard. → Misma herramienta, propósito opuesto (organizar vs. verificar novedad).
- **Magnushammer** (Wenda Li, ICLR 2024), **Piotrowski et al.** (arXiv:2304.00994), **Kaliszyk-Urban** (MaSh/Flyspeck `[VERIFICAR]`): premise selection como input para construir pruebas. → AViD lo usa como huella para comparar pruebas (dirección inversa).
- **Network Structure of Mathlib** (arXiv:2604.24797 `[VERIFICAR]`): centralidad = infraestructura, no matemática. → Justifica nuestro Filtro 1.
- **Huch** (arXiv:2209.13305): distribución scale-free AFP. → Trabajo futuro (IDF).

### Tabla de posicionamiento (va en el paper, versión textual aquí)

| Sistema | ¿Chequea existencia? | ¿Filtra trivialidad? | ¿Mide distancia de prueba? | ¿Corpus informal? | ¿Emite veredicto? |
|---|---|---|---|---|---|
| Kasaura et al. | ✅ (solo Mathlib) | ❌ | ❌ | ❌ | ❌ (sí/no) |
| LeanConjecturer | ✅ (exact?) | ✅ (aesop) | ❌ | ❌ | ❌ |
| TheoremSearch | ✅ (9.2M) | ❌ | ❌ | ✅ | ❌ |
| Atlas (Yoo) | ❌ | ❌ | ✅ (Jaccard) | ❌ | ❌ |
| **AViD** | ✅ (Mathlib + arXiv + TS) | ✅ (6 tácticas + blacklist) | ✅ (Jaccard + filtros) | ✅ | ✅ (7 veredictos) |

---

## Sección 3 — Pipeline

### Arquitectura (3 etapas)
1. **Parser** → extrae bloques (teorema, lema, proof) de `.tex`.
2. **Formalización** → Claude Code/DeepSeek traduce a Lean 4, compila, acumula en `Paper.lean`.
3. **Veredicto** → árbol D2→D1→D3.

### Árbol de decisión (figura va en el paper)
```
D2 (trivialidad): ¿T_auto cierra τ? → NO_NOVEDOSO_trivial
  ↓ no
D1 C_F (Mathlib): ¿Leandex encuentra match? → MATCH_ENCONTRADO_PENDIENTE_D3
  ↓ no
D1 C_I (informal): ¿TheoremSearch + arXiv + Semantic Scholar encuentran? → CONOCIDO_LITERATURA
  ↓ no → NOVEDAD_ENUNCIADO

D3 (a pedido): extraer premisas → Jaccard > θ? → NOVEDAD_DEMOSTRACION
                                         → Jaccard ≤ θ? → NO_NOVEDOSO_redundante
```

### Componentes técnicos
- **D2:** `lake env lean` sobre `example : τ := by T` para `T ∈ {decide, norm_num, simp, omega, tauto, aesop}`. Budgets: 10s/30s. Blacklist: `norm_num` no corre si el tipo menciona `Irrational`.
- **D1 C_F:** Leandex API v2 (sin scores, similarity sintética por orden).
- **D1 C_I:** Stage A: TheoremSearch + Semantic Scholar + arXiv (embeddings MiniLM, threshold 0.25). Stage B: LLM Judge (DeepSeek V4 Flash, temperature=0, 4 veredictos: equivalent/generalization/specialization/different).
- **D3:** ExtractData.lean (515 líneas, Windows nativo) → `compute_d3()` → Jaccard con Filtro 1 (infraestructura: `Init`, `Lean`, `Std`) + Filtro 2 (typeclasses: `Decidable`, `OfNat`, `simp` config).

---

## Sección 4 — Validación de instrumentos (eval set)

### D3: La escalera de Jaccard
Reportar la calibración de D3 como una escalera de 5 peldaños, del más cercano al más lejano:

| Par | Teoremas | Jaccard | Distancia | Interpretación |
|---|---|---|---|---|
| T09a vs T09b | Gauss (mismo lema) | ~1.0 | ~0.0 | Misma prueba (colapso) |
| T08a vs T08b | √2 (paridad vs. valuación) | 0.7222 | 0.2778 | Pruebas distintas (validado) |
| T07a vs T07b | Infinitos primos (factorial vs. divergencia ∑ 1/p) | ~0.0 | ~1.0 | Pruebas completamente distintas |
| T07 vs T08 | Primos vs. √2 | 0.035 | 0.965 | Enunciados y pruebas distintos |

**Fuente:** `results/d3_validation.csv`, `tests/test_d3_orchestrator_integration.py`, `tests/test_premise_extraction.py`

### Convergence finding
Mathlib tiene una sola prueba canónica por teorema clásico (van Doorn-Ebner-Lewis, CICM 2020). Esto significa que D3 es relativo al corpus formal, no a la "realidad matemática". Un Jaccard cercano a 1.0 no implica pruebas matemáticamente idénticas — implica que la biblioteca solo tiene una versión. **Reportar D3 como "relativo a Mathlib v4.29.0".**

**Fuente:** `paper/mathlib_convergence_finding.md`

### D2: Accuracy 87%
- 20/23 = 87% sobre eval set (24 teoremas).
- Falsos positivos: T01/T08 (L10: `norm_num` cierra irracionalidad), T26 (`exact?` con import Mathlib).
- Falso negativo: T14 (budget insuficiente para `aesop`).
- T23: FP esperado y documentado (`IsTree = Connected ∧ IsAcyclic` → `tauto`).

**Fuente:** `paper/results_log.md` Día 5

### D1+D2 end-to-end: Precisión 83%
- Pipeline completo sobre 24 teoremas, 32 minutos.
- 18 `MATCH_ENCONTRADO_PENDIENTE_D3` + 6 `NO_NOVEDOSO_trivial`.
- 20/24 = 83%.

**Fuente:** `paper/results_log.md` Día 7

---

## Sección 5 — Experimento de retirados

### La cascada de filtrado
```
2600 papers retirados en math (arXiv API)
  → 33 con patrón de duplicación (regex, 23 patrones)
    → 26 viables (fuente LaTeX descargable, ≥1 teorema)
      → 10 seleccionados manualmente como "claramente duplicados"
```

**Fuente:** `docs/retracted_dataset_report.md`, `docs/selection_dossier.md`

### Verificación de ground truth: ¿el withdrawal comment basta?
Hallazgo: **9 de 10 papers derivan su evidencia de duplicación puramente del texto del withdrawal comment.** El comentario es la única fuente que dice "este resultado ya fue probado por X en Y". Esto hace que el withdrawal comment sea un proxy de ground truth aceptable para el experimento (aunque no perfecto — posible sesgo de autodiagnóstico del autor).

### Benchmark de referencia: Run 001 → Run 002
**Run 001 (smoke test, 5 papers):** pipeline completo D1+D2. 5/5 formalizados, los 5 marcados como `MATCH_ENCONTRADO_PENDIENTE_D3`. **4 defectos descubiertos** (código Lean no guardado, Leandex scores sospechosos, withdrawal comments fuera del YAML, fidelidad de formalización dudosa en 3/5).

**Run 002 (ampliado):** incorpora los 4 fixes. Resultado: benchmark estable para todos los runs subsiguientes.

**Estado actual del benchmark:** 0/5 → 5/5 (pipeline D1+D2 funcional sobre inputs reales). D3 pendiente de integración automática para completar el veredicto.

### Auditoría del autor (Ayrton)
**Tesis:** toda capa de verificación automática (D1, D2, D3) falla de maneras que solo la inspección humana detecta. El autor revisa:
- Fidelidad de formalización: ¿el Lean generado representa el teorema del paper? (3/5 con fidelidad dudosa en Run 001)
- Calidad del match de Leandex: ¿el teorema encontrado es realmente el mismo? (Papers 2, 4, 5 de Run 001: NO)
- Pertinencia del withdrawal comment como ground truth.

**Fuente:** `docs/run_001_review.md`, `docs/experiment_run_001_report.md`

---

## Sección 6 — Hallazgos

### Punto ciego temporal: 4/4 casos de falsos positivos triangulados
La relatividad de D2 al par (T_auto, Mathlib_version) no es un bug — es una propiedad que **triangula el punto ciego temporal**: lo que era novedoso (en 1870) puede no serlo (en 2026), y medimos exactamente ese desplazamiento. Los 4 casos del eval set que ilustran el gradiente:

| Caso | Cuándo era novedoso | Por qué ya no |
|---|---|---|
| √2 irracional (T01/T08) | 1870 (Borel, Weierstrass) | `norm_num` lo cierra en 14s |
| Suma de 4 pares (T14) | Inmemorial | `aesop` lo cierra |
| Grafo árbol (T23) | — | `tauto` sobre definición conjuntiva |
| Suma de n pares (T26) | — | `exact?` encuentra lema existente |

### Jerarquía de ilusiones (5 peldaños)
Cada capa de verificación automática produce su propia "ilusión de cobertura":

1. **Ilusión D2:** "Si no lo cierra una táctica, es genuino." → L5 (sobre-aproximación de trivialidad): `aesop` cierra cosas no triviales; `tauto` cierra definiciones.
2. **Ilusión D1 C_F:** "Si no está en Mathlib, es nuevo." → L10: Mathlib no es exhaustivo; L11: Mathlib es monolítico (imports específicos fallan).
3. **Ilusión D1 C_I:** "Si no hay paper similar, es nuevo." → Threshold MiniLM 0.40 demasiado alto (0 candidatos). Autoformalización frágil (DeepSeek Pro: 0/2 = 0%).
4. **Ilusión D3:** "Si las premisas son distintas, las pruebas son distintas." → Convergence finding: Mathlib tiene una sola prueba canónica; Jaccard ~1.0 no implica identidad matemática.
5. **Ilusión del withdrawal comment:** "Si el autor dice que ya estaba probado, es ground truth." → 3/5 papers de Run 001 tenían matches de Leandex a teoremas NO equivalentes.

### Caso 1404.0187 (prior art no encontrado por D1)
Paper 1609.02090v1 (Waring/Z_n, retirado por duplicar a Hardy & Littlewood). D1 informal top-5:
- Posición 3: "Representing Integers as the Sum of Two Squares in the Ring Z_n" [1404.0187] (score 0.637).
- **El duplicador conocido (Hardy & Littlewood) NO aparece en el top-5.**

**Interpretación:** D1-informal encuentra prior art razonable (1404.0187 es un paper de 2014 sobre exactamente el mismo problema) pero no el duplicador "canónico" (Hardy & Littlewood, ~1920). Esto ilustra que D1-informal encuentra "lo que está en arXiv con embeddings similares", no necesariamente "el paper que el autor cita como fuente".

**Fuente:** `docs/run_001_review.md:63`, `docs/experiment_run_001_report.md:30`

---

## Sección 7 — Limitaciones

### Limitaciones del framework
- **Lakatos (1976):** AViD mide novedad sobre enunciados y pruebas congelados. No captura novedad conceptual/transformacional (definiciones nuevas, reformulación de problemas).
- **Došen (2003):** Jaccard sobre premisas es una aproximación computable a un problema indecidible (identidad de pruebas). Expuesto a falsos positivos (pruebas normalización-equivalentes con premisas superficiales distintas) y falsos negativos (estrategias distintas que comparten lemas del núcleo).
- **L1:** Métrica teorema-a-teorema, no artículo-completo.
- **L2:** Jaccard ignora peso de cada premisa (IDF → future work).
- **L3:** Solo opera sobre `Prop` (proof irrelevance); `Type` requeriría homotopía.

### Limitaciones de implementación
- **L4:** D1 nivel 0 (igualdad sintáctica); `isDefEq` pendiente.
- **L5:** D2 sobre-aproxima (sesgo conservador hacia "no novedoso").
- **L6:** Autoformalización frágil (DeepSeek Pro: 45 llamadas API, 0 éxitos en formalización de pruebas ajenas). **Pendiente re-medición con Qwen 3.7-max.**
- **L7:** Eval set pequeño (26 teoremas + 9 TBD) y curado a mano.
- **L8:** Dependencia del proceso de formalización.

### Limitaciones descubiertas
- **L9:** D3 offline manual (no en tiempo real).
- **L10:** D2 relativo a (T_auto, Mathlib_version) — no es limitación, es propiedad.
- **L11:** Mathlib monolítico (solo `import Mathlib` funciona standalone).
- **Sesgo de formalizabilidad:** Los 26 papers viables del dataset de retirados son los que tenían fuente LaTeX parseable. Los 7 excluidos (AMS-TeX, nombres abreviados) introducen un sesgo de accesibilidad técnica. No sabemos si los papers excluidos son sistemáticamente más o menos "duplicables".
- **D3-informal experimental:** El puente "match informal → descargar fuente → formalizar → D3" no está validado (0% de éxito en formalización). Reportarlo como dirección, no como resultado.

---

## Sección 8 — Artefacto y Future Work

### Artefacto público
- **Demo web:** Gradio + Hugging Face Spaces (D1+D2 en tiempo real, D3 a pedido vía cola SQLite).
- **Landing page:** `avid-journal.github.io` (brutalismo académico + retrofuturismo).
- **Repositorio:** `github.com/ayrtonporto/avid-journal` (Windows nativo, 88/88 tests).
- **Dataset de retirados:** 26 papers viables + 52 controles, con YAML de configuración.

### Future work (selección para el paper)
- **F1:** Premisas ponderadas por IDF (Kaliszyk-Urban + Huch).
- **F2:** Distancia sobre grafos de dependencia (más allá de Jaccard).
- **F3:** `isDefEq` para D1 nivel 1.
- **F7:** Múltiples modelos de autoformalización (Numina, Axiom, Kimina, ProofFlow).
- **F9:** Corrida sobre Mathlib completa (~1.9M líneas).
- **F10:** Benchmark sobre corpus arXiv autoformalizado.
- **P4:** Integración LeanDojo-v2 para capacidad de prueba sobre teoremas novedosos.

---

## Apéndice: Fuentes de datos

| Qué | Dónde |
|---|---|
| **Referencias (citas)** | `paper/bibliography_merged.md` — fuente única |
| **Cifras (números)** | `docs/bibliography_context.md` PARTE 2 — fuente única |
| **Especificación de la métrica** | `paper/metric_spec.md` |
| **Decisiones de diseño** | `paper/decisions.md` |
| **Limitaciones** | `paper/limitations.md` |
| **Evaluación** | `paper/results_log.md`, `paper/eval_set_lean_statements.md` |
| **Hallazgo de convergencia** | `paper/mathlib_convergence_finding.md` |
| **Filosofía para el paper** | `paper/AViD_dosis_filosofica_paper.md` |
| **Dataset de retirados** | `docs/retracted_dataset_report.md`, `docs/selection_dossier.md` |
| **Run 001** | `docs/run_001_review.md`, `docs/experiment_run_001_report.md` |
| **Batches 002/003** | `docs/batch_run_002.md`, `docs/batch_run_003.md` |
| **D3 scouts** | `docs/scout_d3*.md`, `docs/scout_autoextract.md` |
