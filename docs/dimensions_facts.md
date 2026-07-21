# Hechos técnicos de las tres dimensiones (§3.2)

**Propósito:** documentar con precisión los mecanismos de D1, D2, D3 para redacción del paper.
**Modo:** solo lectura. `archivo:línea` en cada afirmación.
**Regla:** donde código y memoria difieran, gana el código.

---

## D1 — No-existencia previa

### 1. Orden de evaluación y lógica de cortocircuito

El orden está implementado en `src/novelty_v2/orchestrator.py:60-307` (`check_novelty`):

```
Paso 1: D2 (trivialidad)            → línea 101-120
Paso 2: D1 C_F (Mathlib/Leandex)    → línea 123
Paso 3: exact? fallback             → línea 211-249 (solo si C_F no dio match)
Paso 4: D1 C_I (arXiv/SS + LLM)     → línea 252-259 (solo si C_F no dio match)
```

**Cortocircuito documentado en el código (líneas 122-205):**
- Si `d1.existe_en_C_F == True` → se ejecuta D3 (línea 125-205) y se retorna veredicto.
- C_I **nunca se evalúa** si C_F encontró match. Esto es explícito: la rama C_I está en las líneas 252-259, que están fuera del bloque `if d1.existe_en_C_F` (línea 125) y después del `exact?` fallback.
- **C_F prevalece.** Si hay match en Mathlib, C_I es irrelevante (el teorema ya existe formalmente).

### 2. exact?: ubicación y semántica

**Dónde se llama:**
- `src/novelty_v2/orchestrator.py:211-249` — dentro de `check_novelty()`, justo después de que Leandex NO encontró match y antes de consultar C_I.

**Contra qué corre:**
- Genera `example : τ := by exact?` y ejecuta `lake env lean` con budget 15s (línea 216-217).
- Usa `_run_tactic()` de D2 (`src/novelty_v2/dimensions/d2_triviality.py:84-127`), pero con propósito distinto.

**Semántica: es búsqueda en C_F, NO test de trivialidad.**
- El docstring de D2 lo declara explícitamente (`d2_triviality.py:31-33`):
  > `exact?` se movió a D1 como fuente secundaria de C_F. La táctica busca teoremas existentes en el entorno, lo cual es una verificación de existencia previa, no de trivialidad.
- `exact?` NO está en `T_AUTO_ORDER` de D2 (línea 34-41).
- Si `exact?` cierra el goal, el resultado se trata como match en C_F con `similarity=0.95` (línea 231) y se emite `MATCH_ENCONTRADO_PENDIENTE_D3` (línea 235-247).

### 3. Thresholds de similitud: números reales del código

**C_F (Leandex):**
- `src/novelty/mathlib_checker.py:28` — `SIMILARITY_THRESHOLD = 0.85`.
- **Pero este threshold NO se aplica.** Leandex v2 no devuelve scores (línea 132-134):
  > Leandex v2 (post-2025) devuelve un formato plano sin puntajes de similitud.
  > No inventamos scores sintéticos. Si la API no devuelve similarity, el campo queda como None.
- En la práctica, **todo resultado de Leandex con `proof_status != "statement_only"` se considera match.** No hay umbral de similitud corriendo.

**C_I (informal):**
- `src/novelty_v2/dimensions/d1_existence.py:45`:
  ```python
  CI_SIMILARITY_THRESHOLD_A: float = 0.40
  ```
- Este es el **ÚNICO threshold activo.** Decide qué candidatos de Stage A pasan a Stage B.
- **Valor real hoy: 0.40.** El `PAPER_BRIEF.md` menciona que se bajó a 0.25, pero el código nunca se modificó. Buscando en `d1_existence.py`, la línea 45 tiene `0.40`. No hay commit que lo cambie.

**Bandas de decisión para C_I:**
| Similitud MiniLM | Acción |
|---|---|
| `< 0.40` | Descartado (ni siquiera va al LLM judge) |
| `≥ 0.40` | Pasa a Stage B (LLM judge) |
| Stage B: `"equivalent"` | `existe_en_C_I = True` → `CONOCIDO_LITERATURA` |
| Stage B: `"generalization"/"specialization"` | `ZONA_GRIS` (`revision_humana=True`) |
| Stage B: `"different"` | Sin match → continúa el árbol |

---

## D2 — No-trivialidad

### 4. Tácticas, orden y presupuestos

**Lista exacta y orden de ejecución:**
- `src/novelty_v2/dimensions/d2_triviality.py:34-41`:
  ```python
  T_AUTO_ORDER: List[str] = [
      "decide",
      "norm_num",
      "simp",
      "omega",
      "tauto",
      "aesop",
  ]
  ```
- Orden: tácticas baratas y específicas primero, `aesop` al final (búsqueda más exhaustiva). Docstring línea 30.
- `exact?` **NO está** — removido, movido a D1 (ver §2 arriba y líneas 31-33).

**Presupuestos por táctica:**
- `d2_triviality.py:48-55`:
  ```python
  DEFAULT_BUDGETS: Dict[str, int] = {
      "decide": 10,
      "norm_num": 10,
      "simp": 10,
      "omega": 10,
      "tauto": 10,
      "aesop": 30,
  }
  ```
- Overhead de startup Lean: `LEAN_STARTUP_OVERHEAD_S = 45` (línea 46), medido experimentalmente en Windows.
- Heartbeats: `budget_seconds * 400_000` (línea 64-67).

**Ejecución:**
- `_run_tactic()` (líneas 84-127): genera archivo temporal `example : τ := by T`, ejecuta `lake env lean`, verifica `returncode == 0`.
- Se detiene en la PRIMERA táctica que cierra el goal (línea 178: `if success: return D2Result(trivial=True, ...)`).
- Si ninguna cierra: `trivial=False` con `all_attempts` completo (líneas 186-191).

### 5. Blacklist de norm_num

**Qué excluye:**
- `d2_triviality.py:61`:
  ```python
  _NORM_NUM_BLACKLIST = ["Irrational"]
  ```
- `d2_triviality.py:167-168`:
  ```python
  if any(pred in lean_statement for pred in _NORM_NUM_BLACKLIST):
      tactics_order = [t for t in tactics_order if t != "norm_num"]
  ```

**Por qué (del código y CLAUDE.md):**
- `norm_num` en Mathlib v4.29.0 cierra `Irrational (Real.sqrt 2)` por un atajo hardcodeado (L10 en `paper/limitations.md`). Esto produciría un falso positivo: `√2 es irracional` no es trivial, pero `norm_num` lo "demuestra" por implementación interna de la táctica, no por trivialidad matemática.
- Comentario en `d2_triviality.py:58-61`:
  > Predicados que norm_num "demuestra" por atajo hardcodeado, no por trivialidad genuina. Saltamos norm_num cuando el enunciado los contiene para evitar falsos positivos (L10).

**Solo excluye `Irrational` actualmente.** La lista es extensible agregando strings.

### 6. Veredicto de D2 y composición con D1

**Si D2 cierra el goal:**
- `orchestrator.py:108-120` → `Verdict.NO_NOVEDOSO_trivial`, `stage_detenido=2`.
- **FIN del árbol.** No se evalúa D1 ni D3. El razonamiento se registra como:
  > `"D2: táctica '{tactica}' cerró el enunciado en {tiempo}s. No requiere idea matemática."`

**Si D2 NO cierra:**
- Se continúa con D1 C_F (línea 123). D2 no afecta el veredicto final — solo actúa como filtro temprano.

**Relación D2 → exact?:** `exact?` NO está en D2. Si D2 no cierra y Leandex no encuentra match, `exact?` corre como fallback de C_F (orchestrator:211-249). Si `exact?` cierra, no es `NO_NOVEDOSO_trivial` — es `MATCH_ENCONTRADO_PENDIENTE_D3` (enunciado conocido en Mathlib, novedad de prueba por determinar).

---

## D3 — Distancia estructural de pruebas

### 7. Extracción de premisas: ExtractData + solo lemas directamente invocados

**Herramienta de extracción:**
- `lean_project/ExtractData.lean` (519 líneas) — fork de LeanDojo, adaptado para Windows nativo.
- Ejecutado vía `lake env lean --run ExtractData.lean <archivo>`.
- Wrapper Python: `src/novelty_v2/premise_extraction.py:114-306` — con caché SHA256.

**Qué extrae exactamente:**
- `ExtractData.lean:336-375` — `visitTermInfo()`. Para cada `TermInfo` en el árbol de elaboración:
  1. Obtiene `ti.expr.constName?` — el nombre fully-qualified de la constante referenciada (línea 337).
  2. Resuelve `defPath` (archivo donde se define) y `defPos`/`defEndPos` (posición de la definición) vía `findDeclarationRanges?` (líneas 348-350).
  3. Resuelve `modName` (módulo Lean) vía `env.const2ModIdx` (líneas 352-356).
  4. **Filtro clave (línea 364):**
     ```lean
     if defPos != posBefore ∧ defEndPos != posAfter then
       -- Don't include definitions as premises.
     ```
     Esto excluye el sitio de DEFINICIÓN: una premisa solo se registra si la posición donde se USA (`posBefore`/`posAfter`) es distinta de donde se DEFINE (`defPos`/`defEndPos`). Esto asegura que el teorema bajo análisis no se registre a sí mismo como premisa.

**¿Premisas directas o transitivas?**
- `traverseTree` (línea 385-396) es `partial` y recorre recursivamente TODOS los hijos del `InfoTree`.
- `visitTermInfo` se llama para CADA nodo `TermInfo` en el árbol — es decir, cada referencia a una constante en el término elaborado.
- Estas son las constantes que aparecen **directamente en el proof term elaborado del archivo.** El elaborador de Lean resuelve typeclasses, simplificaciones, y despliegue de definiciones, por lo que el conjunto incluye más que "lo que el usuario escribió explícitamente" pero NO es el cierre transitivo completo del grafo de dependencias. Es el conjunto de constantes referenciadas en el término fully-elaborated.

**Filtrado post-extracción:**
- `src/novelty_v2/premise_extraction.py:287-300` — `extract_premises_for_theorem()` filtra por rango de líneas (`theorem_line_start` a `theorem_line_end`) para aislar las premisas de UN teorema específico dentro de un archivo con múltiples declaraciones.

### 8. Los DOS FILTROS previos al Jaccard

Implementados en `src/novelty_v2/dimensions/d3_premises.py:191-248` (`compute_d3()`), pipeline interno documentado en líneas 6-11.

**FILTRO 1 — Namespace blacklist (infraestructura):**
- `d3_premises.py:90-104` — `_filter1_blacklist()`.
- Elimina premisas cuyo `modName` empieza con uno de los prefijos configurados.
- **Matching por prefijo exacto** (línea 101): `mod.startswith(prefix)`. `"Init."` matchea `"Init.Prelude"` pero NO `"InitPrelude"`.
- **Configuración real** en `config/d3_filter_blacklist.yaml`:
  ```yaml
  blacklist_prefixes:
    - "Init."
    - "Lean."
  ```
- `d3_premises.py:63-87` — `_load_blacklist()`. Si el YAML no existe o está vacío, hardcoded fallback: `["Init.", "Lean."]` (línea 77).
- **Racional (del YAML, líneas 6-8):** `Init.*` y `Lean.*` contienen constructores de tipo del núcleo, instancias de typeclasses, e internals de tácticas que el elaborador resuelve automáticamente — no son contenido matemático.

**FILTRO 2 — Premisas del enunciado:**
- `d3_premises.py:111-135` — `_filter2_statement()`.
- Elimina premisas cuyo `pos.line` cae dentro del rango `[statement_line_start, statement_line_end]`.
- **Racional:** las premisas que aparecen en el enunciado del teorema (hipótesis, tipos, definiciones locales) son parte de la firma, no de la prueba. Comparar pruebas por las premisas del enunciado infla artificialmente la similitud.
- Si `statement_line_range is None` → no se filtra nada (línea 125-126).

**Orden de aplicación (inamovible, documentado en líneas 6-11):**
1. Deduplicar por identidad canónica.
2. FILTRO 1 (namespace blacklist).
3. FILTRO 2 (statement premises).
4. Calcular Jaccard.

### 9. Identidad canónica (defPath, defPos)

**Definición:**
- `d3_premises.py:31-41`:
  ```python
  def _canonical_id(premise: dict) -> str:
      def_path = premise.get("defPath", "")
      def_pos = premise.get("defPos") or {}
      line = def_pos.get("line", 0)
      col = def_pos.get("column", 0)
      return f"{def_path}:{line}:{col}"
  ```

**Qué es:**
- `defPath`: ruta al archivo `.lean` donde se define la premisa (ej: `Mathlib/Data/Real/Irrational.lean`).
- `defPos`: posición `(line, column)` dentro de ese archivo donde empieza la definición.

**Por qué se deduplica:**
- Comentario en `d3_premises.py:33-35`:
  > Dos premisas con el mismo defPath y defPos son el mismo objeto lógico, aunque aparezcan en posiciones distintas del archivo.
- Una misma función puede invocarse varias veces en una prueba (ej: `h1 : Even n` y `h2 : Even m` → `Even` aparece dos veces). Sin deduplicación, Jaccard contaría cada uso como una premisa distinta, inflando la unión.

### 10. Fórmula Jaccard y número de regresión

**Fórmula:**
- `d3_premises.py:142-184` — `_compute_jaccard_distance()`:
  ```python
  jaccard_similarity = intersection_size / union_size
  distancia = 1.0 - jaccard_similarity
  ```
- Distancia de Jaccard = `1 - |P(A) ∩ P(B)| / |P(A) ∪ P(B)|`.

**Casos extremos:**
- Si `union_size == 0` → `jaccard = None`, flag `"empty_after_filters"` (línea 169-172).
- Si solo un lado vacío → `jaccard = None`, flags `"empty_a_after_filters"` o `"empty_b_after_filters"` (líneas 174-180).
- **Nunca se lanza excepción** — siempre se retorna `None` con flags.

**Regresión T08 = 0.7222:**
- Documentado en `paper/PAPER_BRIEF.md:110`:
  > T08a vs T08b: √2 irrational (parity vs. valuation proof) → Jaccard 0.7222, Distancia 0.2778.
- Interpretación: las pruebas de irracionalidad de √2 por argumento de paridad y por valuación 2-ádica comparten ~27.8% de premisas, son estructuralmente distintas (~72.2% de distancia).
- Fuente de datos: `results/d3_validation.csv`, tests en `tests/test_d3_orchestrator_integration.py`.

### 11. Threshold θ de D3

**Valor actual:**
- `src/novelty_v2/types.py:130`:
  ```python
  umbral_theta: float = 0.5
  ```

**Cómo se usa:**
- `d3_premises.py:245-247`:
  ```python
  pruebas_distantes=(
      None if distancia is None else distancia > 0.5
  ),
  ```
- `jaccard > 0.5` → `pruebas_distantes = True` → `NOVEDAD_DEMOSTRACION`.
- `jaccard ≤ 0.5` → `pruebas_distantes = False` → `NO_NOVEDOSO_redundante`.

**Estado de calibración:**
- `paper/decisions.md:79`:
  > Valor inicial del umbral `θ` para D3. Empezar con 0.5 y calibrar contra T07/T08/T09.
- **No calibrado.** Es el valor inicial del diseño. Los resultados del eval set y wide study usan θ=0.5 sin recalibrar.
- El único punto de datos calibrado es T08 = 0.7222 (pruebas distintas, correctamente clasificado con θ=0.5). T07 (~0.0) y T09 (~1.0) son los extremos esperados.
