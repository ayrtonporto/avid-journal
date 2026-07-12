# Statement Verification — Experiment Run 001 (POST-CORRECCIÓN)

**Generado:** 2026-07-12 (segunda verificación)  
**Propósito:** Verificar que los `target_theorem` corregidos en `config/experiment_run_001.yaml` coinciden TEXTUALMENTE con las fuentes LaTeX cacheadas.  
**Resultado esperado:** CERO divergencias no declaradas.

---

## Paper 1 — 1609.02090v1 ✅

### YAML (corregido)
```latex
\label{SquaresZn}
$\mathbb{Z}_n \subset 2R_2$ if and only if $n$ satisfies the condition
that when $p^2 \mid n$, then $p \equiv 1 \pmod{4}$.
```

### Fuente LaTeX (WaringZn.tex:105-107)
```latex
\begin{theorem} \label{SquaresZn}
$\mathbb{Z}_n \subset 2R_2$ if and only if $n$ satisfies the condition 
that when $p^2 \mid n$, then $p \equiv 1 \pmod{4}$.
\end{theorem}
```

**Veredicto:** ✅ TEXTO IDÉNTICO. Eliminados "for every odd prime p" y "n≢0(mod 16)".

---

## Paper 2 — 1207.0631v1 ✅

### YAML (corregido)
```latex
\label{maintheo}
Let $A$ be a non-scalar matrix of $\Mat_n(\K)$, and $c_1,\dots,c_n$ be scalars.
Then the following conditions are equivalent:
\begin{enumerate}[(i)]
\item $c_1+\cdots+c_n=\tr A$;
\item $A$ is similar to a matrix with diagonal entries $c_1,\dots,c_n$.
\end{enumerate}
```

### Fuente LaTeX (diagonalarxiv.tex:162-169)
```latex
\begin{theo}\label{maintheo}
Let $A$ be a non-scalar matrix of $\Mat_n(\K)$, and $c_1,\dots,c_n$ be scalars.
Then the following conditions are equivalent:
\begin{enumerate}[(i)]
\item $c_1+\cdots+c_n=\tr A$;
\item $A$ is similar to a matrix with diagonal entries $c_1,\dots,c_n$.
\end{enumerate}
\end{theo}
```

**Veredicto:** ✅ TEXTO IDÉNTICO. Label corregido de `keylemma` a `maintheo`. Comentario en YAML documenta la decisión.

---

## Paper 3 — 1212.0196v1 ✅ (truncamiento declarado)

### YAML (sin cambios en el texto)
```latex
\label{cor:main}
Suppose $m=p_1\cdots p_k$ and $p_i\equiv 3\pmod 8$.
If $\leg{p_i}{p_j}=1$ for all $1\leq i<j\leq k$,
then $m$ is a non-congruent number.
```

### Fuente LaTeX (noncong.tex:84-86)
```latex
\begin{cor}\label{cor:main}
Suppose $m=p_1\cdots p_k\ \text{and}\ p_i\equiv 3\pmod 8$. 
If $\leg{p_i}{p_j}=1$ for all $1\leq i<j\leq k$, 
then $m$ is a non-congruent number. 
If moreover $k$ is even, then $2m$ is also a non-congruent number. 
In particular, we can construct an infinite set $S$...
\end{cor}
```

**Veredicto:** ✅ Núcleo idéntico. **Truncamiento declarado:** extensiones a 2m y conjunto S excluidas por decisión del usuario (comentario en YAML).

---

## Paper 4 — 1004.3381v1 ✅

### YAML (corregido)
```latex
Let $R$ be a set of rectangles such that the largest independent
set is of size $m$, then the rectangles can be sliced by
$f(m) \leq c\cdot(2m+1)^2$ axis-parallel lines.
```

### Fuente LaTeX (stab.tex:36-38)
```latex
\begin{lemma} Let $R$ be a set of rectangles such that the largest independent 
set is of size $m$, then the rectangles can be sliced by 
$f(m) \leq c\cdot(2m+1)^2$ axis-parallel lines.
\end{lemma}
```

**Veredicto:** ✅ TEXTO IDÉNTICO. Cota corregida de O(m log m) a c·(2m+1)².

---

## Paper 5 — math/0604362v1 ✅ (truncamiento declarado)

### YAML (corregido)
```latex
\label{thm:spectral_lowerbound}
The eigenvalues $\lambda_i\neq 1$ of a finite, irreducible Markov chain satisfy
$$d(n) \geq \frac 12\,|\lambda_i|^n.$$
```

### Fuente LaTeX (cheeger.tex:141-147)
```latex
\begin{theorem} \label{thm:spectral_lowerbound}
The eigenvalues $\lambda_i\neq 1$ of a finite, irreducible Markov chain satisfy
$$d(n) \geq \frac 12\,|\lambda_i|^n \quad\textrm{and}\quad
d(t) \geq \frac 12\,e^{-(1-\Ree\lambda_i)t}\,.$$
\end{theorem}
```

**Veredicto:** ✅ Parte discreta TEXTO IDÉNTICO (desigualdad ≥, exponente n, factor ½, sin max). **Truncamiento declarado:** parte de tiempo continuo d(t) excluida por decisión del usuario. Nota en YAML: la cota vale para cada λ_i≠1.

---

## Resumen final

| # | Paper | Estado | Divergencias |
|---|-------|--------|-------------|
| 1 | 1609.02090v1 | ✅ CORRECTO | 0 |
| 2 | 1207.0631v1 | ✅ CORRECTO | 0 (label cambiado a maintheo) |
| 3 | 1212.0196v1 | ✅ CORRECTO | 0 (truncamiento declarado) |
| 4 | 1004.3381v1 | ✅ CORRECTO | 0 |
| 5 | math/0604362v1 | ✅ CORRECTO | 0 (truncamiento declarado) |

**⏸️ DETENIDO. Esperando confirmación explícita del usuario para pasar a FASE 1 (Run 001-b).**
