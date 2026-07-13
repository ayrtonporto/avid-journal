# Control Paper Statement Verification — Run 002

**Generated:** 2026-07-13
**Purpose:** Verify that the `target_theorem` for each of the 5 control papers matches the LaTeX source.

---

## Control 1 — 1501.01654v1 (paired with 1609.02090v1)

### YAML target
```latex
\label{main}
$H(x)$ is almost universal if and only if $N_p$ represents all of $\Z_p$
for every odd prime $p$, and one of the following holds:
\begin{enumerate}[(1)]
\item $\alpha=\beta+1$, and ...
\end{enumerate}
```

### Source (Haensch.tex, Theorem #1)
```latex
$H(x)$ is almost universal if and only if $N_p$ represents all of $\Z_p$ 
for every odd prime $p$, and one of the following holds:
\begin{enumerate}[(1)]
\item $\alpha=\beta+1$, and
\begin{enumerate}[(a)]
\item $B(\nu,N_2)=2^{\beta-1}\Z_2$; or,
\item ...
\end{enumerate}
```

**Veredict:** 🟡 BAJA — Truncado con "..." al final. El núcleo del enunciado coincide.

---

## Control 2 — 1101.3431v2 (paired with 1207.0631v1)

### YAML target
```latex
\cite{EM-79,GKK-88}\label{value}
For the mean payoff game whose payments are given by the matrices
$A,B\in (\R\cup\{-\infty\})^{m\times n}$,
where $A,B$ satisfy Assumptions 1 and 2,
there exists...
```

### Source
⚠️ **Source not available in cache** (`source_available=False`). arXiv tarball download returned no extractable .tex files.

**Veredict:** ⚠️ NO VERIFICABLE — requiere descarga manual del PDF o consulta del abstract.

---

## Control 3 — 1101.3720v1 (paired with 1212.0196v1)

### YAML target
```latex
Let $B_{\varepsilon}(N)$ denote the set of binary $m<N$ for which
$\theta_m<m^{1/2+\varepsilon}$. Then we have
$$B_{\varepsilon}(N) =
\left\{ \begin{array}{ll}
\Omega(N^{1/2}) & \text{for } 0 < \varepsilon < 1/2
\end{array} \right.$$
```

### Source (Binary.tex, Theorem #1)
```latex
Let $B_{\varepsilon}(N)$ denote the set of binary $m<N$ for which 
$\theta_m<m^{1/2+\varepsilon}$. Then we have
$$B_{\varepsilon}(N) = \left\{ \begin{array}{ll}
\Omega(N^{1/2}) & \text{for } 0 < \varepsilon < 1/2, \\
O(N^{1/2+\varepsilon}) & \text{...
```

**Veredict:** 🟢 OK — Coincide textualmente. YAML trunca la segunda rama de la llave (`O(N^{1/2+ε})`).

---

## Control 4 — 0904.1783v3 (paired with 1004.3381v1)

### YAML target
```latex
\label{thm:minkowski-weyl}
The set $\cP \sseq \Rset^n$ is a closed polyhedron if and only if
there exist finite sets $R, P \sseq \Rset^n$
of cardinality $r$ and $p$, respectively,
such that $\vect{0} \in \cP$ and...
```

### Source
⚠️ **Source not available in cache** (`source_available=False`).

**Veredict:** ⚠️ NO VERIFICABLE.

---

## Control 5 — math/0504586v2 (paired with math/0604362v1)

### YAML target
```latex
\label{pr:noncrit}
For any graph $G$ we have
\begin{equation} \left\{ \begin{array}{ccl}
\bPsi_p( \calC_t \mbox{ occurs for every } t ) = 1 & \mbox{ if } & p>p_c(G)
\end{array} \right.
\end{equation}
```

### Source
⚠️ **Source not available in cache** (`source_available=False`).

**Veredict:** ⚠️ NO VERIFICABLE.

---

## Summary

| # | Control | Source available? | Verification |
|---|---------|:-----------------:|-------------|
| 1 | 1501.01654v1 | ✅ | 🟡 Truncado ("...") |
| 2 | 1101.3431v2 | ❌ | ⚠️ No verificable |
| 3 | 1101.3720v1 | ✅ | 🟢 OK |
| 4 | 0904.1783v3 | ❌ | ⚠️ No verificable |
| 5 | math/0504586v2 | ❌ | ⚠️ No verificable |

**Acción requerida:** Los controles 2, 4, 5 requieren verificación manual (descarga de PDF/abstract de arXiv) o decisión del usuario de proceder sin verificación. Los controles 1 y 3 son aceptables (truncamiento menor o coincidencia textual).

**Instrucción:** Confirmar para proceder a Run 002.
