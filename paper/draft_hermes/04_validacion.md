# Validación de instrumentos

Antes de evaluar el sistema completo contra papers reales (sección 5), esta sección valida cada instrumento por separado contra ground truth conocido: D3 contra pares de calibración con juicio humano, D2 contra el eval set de 24 teoremas, y D1 contra la cobertura del mismo eval set.

<!-- fuente: paper/PAPER_BRIEF.md §4, scripts/eval/eval_full_20260628_143702.csv, results/d3_validation.csv, results/pair_judgments.json -->

## 4.1 D3: escalera de calibración

La distancia de Jaccard se validó sobre cinco pares de teoremas para los cuales un juez humano (el primer autor) determinó la relación esperada entre sus demostraciones y firmó cada etiqueta. Los pares cubren el espectro completo: misma prueba (control self), pruebas genuinamente distintas, pruebas disfrazadas de distintas que resultaron idénticas tras la formalización, y teoremas completamente no relacionados (control cruzado).

<!-- fuente: results/pair_judgments.json (3 pares con etiqueta firmada por Ayrton Porto, 2026-07-12), results/d3_validation.csv -->

| Par | Tipo (juez) | Jaccard (similitud) | Distancia | Intersección | Unión |
|---|---|---|---|---|---|
| T08a vs T08a (self) | Control: misma prueba | 1.0 | 0.0 | 9 | 9 |
| T07a vs T07b | same_disguised | 0.50 | 0.50 | 1 | 2 |
| T08a vs T08b | genuinely_different | 0.2778 | 0.7222 | 5 | 18 |
| T09a vs T09b | genuinely_different | 0.0 | 1.0 | 0 | 6 |
| T07 vs T08 (cross-pair) | Control: no relacionados | 0.0 | 1.0 | 0 | 10 |

<!-- fuente: results/d3_validation.csv (5 filas), results/pair_judgments.json (3 pares calibrados con etiqueta firmada) -->

**Interpretación de la escalera.**

**T08 (distancia = 0.7222).** Dos pruebas genuinamente distintas de la irracionalidad de raíz de 2 producen una distancia alta. Las 5 premisas compartidas son lemas fundacionales (aritmética de `Nat`, `mul_comm`, `eq_of_sub_eq_zero`); las 13 premisas exclusivas de cada lado capturan las estrategias divergentes (divisibilidad por primos vs. valuación 2-adica). El umbral theta = 0.5 clasifica correctamente este par como "pruebas distantes".

**T07 (distancia = 0.50).** Las dos pruebas de la infinitud de primos (Euclides y Euler) quedan exactamente en el umbral. Tras la formalización en Lean, ambas colapsaron a la misma invocación del lema `Nat.exists_infinite_primes`. Con solo 2 premisas totales tras los filtros y 1 compartida, el Jaccard es frágil: pequeños cambios en el comportamiento de los filtros invertirian el veredicto. El juez humano las etiqueto como `same_disguised`: enunciados distintos en la fuente LaTeX, idénticos en el proof term elaborado. Este par ilustra un fenómeno recurrente en D3: la autoformalizacion tiende a colapsar pruebas conceptualmente distintas hacia el lema de Mathlib mas cercano.

<!-- fuente: results/pair_judgments.json entrada T07_euclid_vs_factorial: verdict=same_disguised, justification="Both proofs are identical, consisting solely of the line Nat.exists_infinite_primes n" -->

**T09 (distancia = 1.0, intersección = 0).** Las dos pruebas de la suma de Gauss (inducción con `sum_range_succ` + `ring` vs. formula cerrada con `Finset.sum_range_id`) no comparten ninguna premisa tras los filtros. Cada lado tiene 6 premisas, todas exclusivas de su estrategia. El juez humano las etiqueto como `genuinely_different`, y la distancia máxima refleja correctamente esa diferencia. Este es el resultado esperado tras la reescritura de T09a con inducción (la versión anterior usaba el mismo lema `sum_range_id` que T09b y colapsaba).

<!-- fuente: results/pair_judgments.json entrada T09_induction_vs_gauss: verdict=genuinely_different, approved_by="Ayrton Porto", results/d3_validation.csv: T09_induction_vs_gauss distance=1.0 intersection=0 union=6 -->

**Control negativo (T07 vs. T08).** La distancia entre un teorema de teoría de numeros (infinitud de primos) y uno de análisis (irracionalidad de raíz de 2) es 1.0 con intersección vacia. Esto confirma que D3 no produce similitud espuria entre teoremas de dominios matemáticos distintos.

<!-- fuente: results/d3_validation.csv control_unrelated_T07xT08: distance=1.0 intersection=0 union=10 -->

**Hallazgo de convergencia.** Mathlib, en su versión actual (v4.29.0), contiene típicamente una sola prueba canónica para cada teorema clásico. El caso T07 lo ilustra de forma extrema: dos estrategias de prueba que un matemático consideraría distintas (factorial de Euclides, divergencia de Euler) colapsan al mismo lema `Nat.exists_infinite_primes` al ser formalizadas. Esto revela algo más fuerte que la relatividad al corpus: D3 mide distancia entre FORMALIZACIONES, y la relación entre esa distancia y la distancia entre las ideas informales originales queda sin establecer. Dos pruebas pueden producir distancia 1.0 porque el formalizador eligió lemas distintos, no porque las ideas subyacentes lo sean. Complementariamente, T07 muestra que pruebas con ideas distintas pueden colapsar a distancia 0.5 (o menor) cuando el formalizador converge al mismo lema de Mathlib. Reportamos D3 como "relativo a la formalización en Mathlib v4.29.0".

<!-- fuente: paper/PAPER_BRIEF.md:117-118 (convergence finding), results/pair_judgments.json T07 -->

## 4.2 D2: filtro de trivialidad

El filtro de trivialidad se evaluo sobre 24 de los 26 teoremas del eval set (T20 y T21 no fueron formalizados en esta corrida: T20 requeria una salida especifica de LLM no recolectada, y T21 dependia de seleccionar un caso del ConjecturingProvingLoop de Kasaura et al. que quedo pendiente de implementación). Los 24 teoremas evaluados cubren triviales por diseno, clásicos en Mathlib, pares con distinta prueba, enunciados cercanos, casos generados por IA, y casos de falla.

<!-- fuente: scripts/eval/eval_full_20260628_143702.csv (24 filas), paper/eval_set.csv (T20 y T21 son los 2 ausentes) -->

### Resultados completos

**D2 detecto correctamente la trivialidad en 6 teoremas:**

| Teorema | Descripcion | Tactica | Tiempo (s) | Expectativa |
|---|---|---|---|---|
| T14 | Suma de 4 pares es par | `aesop` | 13.6 | Trivial |
| T15 | 2 + 2 = 4 | `decide` | 13.1 | Trivial |
| T16 | n + 0 = n | `norm_num` | 13.0 | Trivial |
| T17 | n <= n + 1 | `norm_num` | 13.0 | Trivial |
| T19 | Teorema generado por LLM sobre pares | `aesop` | 13.3 | Trivial (probable) |
| T22 | n par entonces n+0 es par | `norm_num` | 13.5 | Caso de falla para D1 |

<!-- fuente: scripts/eval/eval_full_20260628_143702.csv -->

T19 y T22 merecen comentario. T19 fue generado por un LLM con la instruccion "enuncia y prueba un teorema original sobre numeros pares"; D2 lo cerro con `aesop`, confirmando la hipotesis de que los LLM tienden a producir enunciados triviales. T22 ("si n es par entonces n+0 es par") es logicamente equivalente a "si n es par entonces n es par"; D2 lo cerro con `norm_num` en 13.5s, lo cual es correcto (el teorema es trivial) aunque T22 fue disenado para testear D1 (equivalencia sintactica), no D2. Ambos casos se clasifican como aciertos de D2 con expectativa ambigua.

**D2 clasifico correctamente como no triviales los 18 teoremas restantes:**

| Teoremas | Categoria | Resultado D2 |
|---|---|---|
| T01, T02, T03, T04, T05, T06 | Clasicos en Mathlib | No trivial (correcto) |
| T07a, T08a, T09a | Pares con distinta prueba | No trivial (correcto) |
| T10, T11, T12, T13 | Enunciados cercanos | No trivial (correcto) |
| T18 | Suma de impares = n^2 (trampa de control) | No trivial (correcto) |
| T23 | Grafo conexo y aciclico es árbol | No trivial (correcto) |
| T24 | Haces coherentes en esquema noetheriano | No trivial (correcto) |
| T25 | n par sii 2 divide a n | No trivial (correcto) |
| T26 | Suma de n pares es par | No trivial (correcto) |

<!-- fuente: scripts/eval/eval_full_20260628_143702.csv -->

**Casos notables.** T18 (suma de los primeros n impares es n^2) es una trampa de control: no es trivial (requiere inducción), y D2 correctamente no la cerro. T23 (definición de árbol como conexo + aciclico) en esta corrida tampoco fue cerrado por D2, a diferencia de corridas anteriores donde `tauto` lo cerraba sobre una definición conjuntiva; el enunciado Lean efectivamente usado en esta evaluación difiere del que producia el falso positivo. T14 (suma de 4 pares) fue cerrado por `aesop` en 13.6s, a diferencia del falso negativo documentado en la seccion 3.4.2 donde `aesop` requeria ~215s: la diferencia se debe al enunciado Lean concreto generado en esta corrida, que resulto mas simple de cerrar.

### Agregado

Sobre los 24 teoremas evaluados, D2 acierta en 22 casos (91.7%). Los 2 casos restantes (T19 y T22) quedan excluidos: T19 fue generado por un LLM y su expectativa en el eval set era "NO_NOVEDOSO (probable)", sin una clasificación binaria contra la cual medir acierto; T22 fue diseñado para testear D1 (equivalencia sintáctica), no D2, y el veredicto de D2 no es informativo sobre la dimensión que el caso fue construido para evaluar. No se registran falsos positivos ni falsos negativos de D2 en los 22 casos con expectativa definida.

<!-- fuente: calculo directo sobre scripts/eval/eval_full_20260628_143702.csv: 22/24 con expectativa clara, 2 con expectativa ambigua -->

## 4.3 D1: cobertura del corpus formal

La rama C_F de D1 (Leandex sobre Mathlib) encontro match para los 18 teoremas no triviales que alcanzaron esa etapa (100% de cobertura sobre no triviales). Los 6 teoremas que aparecen sin match en C_F (T14, T15, T16, T17, T19, T22) son exactamente los 6 que D2 detecto como triviales y sobre los cuales el pipeline aplico cortocircuito: D1 nunca se ejecuto para ellos porque el árbol de decision se detuvo en D2. La columna `d1_existe_en_C_F = False` en el CSV refleja esta no-ejecución, no un fallo de Leandex.

<!-- fuente: scripts/eval/eval_full_20260628_143702.csv: 18 teoremas con d1_existe_en_C_F=True, 6 con d1_existe_en_C_F=False (todos con stage_detenido=2, es decir, detenidos en D2) -->

**No hubo falsos positivos de D1 C_F en esta corrida.** Todos los matches de Leandex corresponden a teoremas que efectivamente estan en Mathlib. Los 18 matches encontrados cubren: teoremas clásicos (T01-T06: Pitagoras, Fermat pequeno, teorema fundamental del calculo, infinitud de primos, irracionalidad de raíz de 2, suma de Gauss), pares de prueba (T07a, T08a, T09a), enunciados cercanos (T10-T13: primos impares, AM-GM), y casos de falla (T18, T23, T24, T25, T26).

La rama C_I (busqueda en literatura informal via TheoremSearch, Semantic Scholar, arXiv y LLM judge) no se activo para ningun teorema de esta corrida. El motivo no es que los candidatos no superaran el threshold MiniLM de 0.40, sino que la condicion de entrada a C_I (D2 = False y C_F sin match) nunca se cumplio: todos los teoremas no triviales tenian match en C_F, y todos los que no tenian match en C_F eran triviales y fueron detenidos en D2. C_I es una rama del árbol que el eval set actual, por su composición (dominado por teoremas ya presentes en Mathlib), no ejercita.

<!-- fuente: análisis del árbol de decision en src/novelty_v2/orchestrator.py:60-307 y del CSV de eval -->

## 4.4 Resumen de instrumentos

| Instrumento | Validado contra | Resultado | Estado |
|---|---|---|---|
| D3 | 5 pares de calibración (juicio humano firmado) | 2/3 pares calibrados consistentes con el juez: T08 y T09 (genuinely_different). T07 (same_disguised) es un punto degenerado (unión = 2 premisas, intersección = 1), insuficiente para sostener calibración. 2 controles correctos (self, unrelated). | Funcional, umbral θ=0.5 sin calibrar, T07 no informativo |
| D2 | Eval set (24 teoremas) | 22/24 = 91.7% de acierto sobre casos con expectativa definida; 2 excluidos (T19, T22) por expectativa no binaria. | Funcional |
| D1 C_F | Eval set (18 teoremas no triviales) | 18/18 = 100% de cobertura sobre no triviales. Los 6 sin match son triviales detenidos en D2. | Funcional |
| D1 C_I | No evaluada (rama no alcanzada en esta corrida) | Sin datos. El eval set no contiene teoremas que activen la condicion de entrada a C_I. | No evaluada |

<!-- fuente: compilacion de secciones 4.1-4.3, scripts/eval/eval_full_20260628_143702.csv, results/d3_validation.csv, results/pair_judgments.json -->
