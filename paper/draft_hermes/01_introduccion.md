# Introducción

En febrero de 2026, el sistema Axiom Math presentó como propia una conjetura que ya había sido formulada y nombrada por el matemático André Fel dos años antes. El incidente, cubierto por Scientific American, no fue un caso aislado: ilustra un modo de falla sistemático de los sistemas de inteligencia artificial aplicados a la matemática. Los modelos de lenguaje pueden generar enunciados que compilan, que son correctos, y que sin embargo no son nuevos.

<!-- fuente: paper/PAPER_BRIEF.md §1 (caso Axiom Math / Fel) -->

Abouzaid et al., en su examen *First Proof* para inteligencia artificial matemática, lo enunciaron con precisión: "lo que nos falta es una manera sistemática de evaluar si esos lemas pueden ensamblarse en una prueba novedosa" (arXiv:2602.05192). El problema es doble. Por un lado, los sistemas actuales de AI matemática (Axiom, Harmonic, DeepSeek-Prover) verifican corrección pero no novedad. Por otro, el criterio ingenuo que equipara novedad con ausencia en Mathlib (Kasaura et al., arXiv:2509.14274) falla en dos direcciones: marca como nuevos teoremas triviales que ninguna táctica automatizada resolvería en 2026 pero que no requieren idea matemática genuina, y omite resultados que no están formalizados pero sí publicados en la literatura informal.

<!-- fuente: paper/bibliography_merged.md (First Proof, Kasaura), paper/PAPER_BRIEF.md §1 (problema en una oración) -->

Tao, en sus notas sobre *Machine-Assisted Proof* (Notices of the AMS, 2025), planteó la pregunta en términos de escala: si la generación automática de teoremas se acelera, hace falta filtrar novedad automáticamente. La verificación humana, que ya es el cuello de botella del peer review tradicional, se vuelve inviable cuando quien propone teoremas es un modelo.

<!-- fuente: paper/bibliography_merged.md §9 (Tao 2025) -->

Este artículo presenta AViD Journal (Automated Verification in Demonstrations), un sistema que aborda exactamente esa pregunta: ¿se puede arbitrar novedad de teoremas de manera automática, con grounding formal? La respuesta que ofrecemos no es un sí rotundo sino la construcción y evaluación temprana de un pipeline que recorre el camino completo, desde el LaTeX de un paper hasta un veredicto de novedad, y cuyos límites quedan tan documentados como sus aciertos.

<!-- fuente: paper/PAPER_BRIEF.md (espina narrativa) -->

## 1.1 Contribuciones

1. **Una taxonomía de novedad como cruce de dos ejes.** La novedad de un teorema no se reduce a "está o no está en Mathlib". Proponemos dos ejes: el tipo del enunciado (idéntico, generalización, especialización, diferente) y las premisas de la demostración (idénticas, cercanas, distantes). El producto cartesiano produce cuatro casos netos más una zona gris para generalizaciones y especializaciones, que requieren revisión humana.

<!-- fuente: paper/PAPER_BRIEF.md §1 (taxonomía) -->

2. **Una métrica operacional de tres dimensiones.** D1 verifica la existencia previa del enunciado en un corpus formal (Mathlib, vía Leandex) y en un corpus informal (arXiv, Semantic Scholar, TheoremSearch, con un juez LLM). D2 filtra la trivialidad: si una táctica automatizada estándar cierra el enunciado, el teorema no es novedoso. D3 mide la distancia estructural entre demostraciones como la distancia de Jaccard sobre los conjuntos de premisas utilizados.

<!-- fuente: paper/PAPER_BRIEF.md §1 (métrica de 3 dimensiones) -->

3. **Una implementación funcional del ciclo completo.** El pipeline integra parseo de LaTeX, formalización en Lean 4 mediante una abstracción multi-modelo (8 backends), y el árbol de decisión D2-D1-D3, corriendo sobre Windows nativo con Lean 4.29.0 y Mathlib.

<!-- fuente: docs/PROJECT_STATE.md, paper/PAPER_BRIEF.md §1 -->

4. **Evaluación preliminar contra ground truth real.** El sistema se evaluó en tres frentes: (a) un conjunto de 26 teoremas hand-curated que cubren casos de trivialidad, coincidencia exacta, pruebas alternativas y ruido deliberado (24 evaluados en la corrida de validación de instrumentos, sección 4); (b) un experimento con 10 papers retirados de arXiv por duplicación de resultados previos; y (c) un estudio ancho de 52 papers (26 retirados + 26 controles emparejados) usando similitud semántica de enunciados. Los resultados son preliminares en todos los casos, y el artículo dedica tanto espacio a los límites encontrados como a los aciertos.

<!-- fuente: paper/PAPER_BRIEF.md §1 (4 contribuciones), docs/PROJECT_STATE.md (eval set, experimentos) -->

## 1.2 Estructura del artículo

La sección 2 sitúa este trabajo en la intersección de cuatro frentes de investigación. La sección 3 describe el pipeline completo: parser, formalización, corpus de referencia, las tres dimensiones y el árbol de veredictos. La sección 4 valida cada instrumento por separado (D2 contra el eval set, D3 contra pares de calibración). La sección 5 reporta los experimentos con papers retirados y el estudio ancho, ambos como evidencia preliminar. La sección 6 enumera las limitaciones del framework, la implementación y el diseño experimental. La sección 7 cierra con lo construido y lo pendiente.
