# REVIEW — arXiv 2603.29961

Documento de seguimiento humano. El orchestrator anota aqui los bloques que
necesitan revisar manualmente: axiomas declarados (resultados externos sin
prueba en el paper) y bloques que no se pudieron formalizar (failed).

Los bloques `verified` NO aparecen aqui; vive el log limpio en `PAPER_INDEX.md`.

---

## Axiomas declarados


### `thm:basis-main` (theorem)
- **Paper.lean**: linea 16
- **Fuente**: external result (paper without proof)
- **Enunciado**:

```
There exists a set $A\subset \mb{N}$ such that $A$ is a basis of order $2$, and for every partition $A=A_1\sqcup A_2$, at least one of $A_1+A_1$ and $A_2+A_2$ does not have bounded gaps.
```

---

## Bloques fallidos





### `thm:binomial-main` (theorem)
- **Paper.lean**: linea 8
- **Enunciado**:

```
For $n$ sufficiently large, we have that
\[
f(n)\le \left(\frac{24}{\pi^2-6}+o(1)\right)(\log n)^2
\leq 6.20219 (\log n)^2.
\]
Furthermore, there exists a sequence $n_j\to \infty$ such that
\[
f(n_j)\ge \left(\frac12+o(1)\right)\log n_j.
\]
```

### `thm:binomial-main` (theorem)
- **Paper.lean**: linea 12
- **Enunciado**:

```
For $n$ sufficiently large, we have that
\[
f(n)\le \left(\frac{24}{\pi^2-6}+o(1)\right)(\log n)^2
\leq 6.20219 (\log n)^2.
\]
Furthermore, there exists a sequence $n_j\to \infty$ such that
\[
f(n_j)\ge \left(\frac12+o(1)\right)\log n_j.
\]
```

### `thm:binomial-main` (theorem)
- **Paper.lean**: linea 20
- **Enunciado**:

```
For $n$ sufficiently large, we have that
\[
f(n)\le \left(\frac{24}{\pi^2-6}+o(1)\right)(\log n)^2
\leq 6.20219 (\log n)^2.
\]
Furthermore, there exists a sequence $n_j\to \infty$ such that
\[
f(n_j)\ge \left(\frac12+o(1)\right)\log n_j.
\]
```

### `thm:binomial-main` (theorem)
- **Paper.lean**: linea 24
- **Enunciado**:

```
For $n$ sufficiently large, we have that
\[
f(n)\le \left(\frac{24}{\pi^2-6}+o(1)\right)(\log n)^2
\leq 6.20219 (\log n)^2.
\]
Furthermore, there exists a sequence $n_j\to \infty$ such that
\[
f(n_j)\ge \left(\frac12+o(1)\right)\log n_j.
\]
```

---

## Notas adicionales

