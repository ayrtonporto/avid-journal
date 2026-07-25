# REVIEW — Paper

Documento de seguimiento humano. El orchestrator anota aqui los bloques que
necesitan revisar manualmente: axiomas declarados (resultados externos sin
prueba en el paper) y bloques que no se pudieron formalizar (failed).

Los bloques `verified` NO aparecen aqui; vive el log limpio en `PAPER_INDEX.md`.

---

## Axiomas declarados

(ninguno todavia)

---

## Bloques fallidos




### `def:even` (definition) — Even number
- **Paper.lean**: linea 8
- **Enunciado**:

```
A natural number $n$ is even if there exists a natural number $k$
such that $n = 2k$.
```

### `lem:even_sum` (lemma) — Sum of two evens
- **Paper.lean**: linea 12
- **Enunciado**:

```
If $a$ and $b$ are even natural numbers (Definition~\ref{def:even}),
then $a + b$ is even.
```

### `thm:four_evens` (theorem) — Sum of four evens
- **Paper.lean**: linea 16
- **Enunciado**:

```
If $a, b, c, d$ are even natural numbers, then $a + b + c + d$ is even.
```

---

## Notas adicionales

