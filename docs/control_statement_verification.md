# Control Paper Statement Verification — Run 002

**Generated:** 2026-07-13  
**Sources:** All 5 controls downloaded from arXiv and cached in `cache/retracted_dataset/ctrl_src_*/`.

---

## Control 1 — 1501.01654v1 (paired with 1609.02090v1)

### YAML target (TRUNCATED — requires fix)
```latex
\label{main}
$H(x)$ is almost universal if and only if $N_p$ represents all of $\Z_p$
for every odd prime $p$, and one of the following holds:
\begin{enumerate}[(1)]
\item $\alpha=\beta+1$, and ...
\end{enumerate}
```

### Source (Haensch.tex, Theorem #1) — FULL TEXT
```latex
\begin{theorem}
$H(x)$ is almost universal if and only if $N_p$ represents all of $\Z_p$ 
for every odd prime $p$, and one of the following holds:
\begin{enumerate}[(1)]
\item $\alpha=\beta+1$, and
\begin{enumerate}[(a)]
\item $B(\nu,N_2)=2^{\beta-1}\Z_2$; or,
\item $B(\nu,N_2)\subseteq 2^{\beta}\Z_2$, and 
\begin{enumerate}[(i)]
\item $2\s(N)=\n(N)=2^{\beta+2}\Z$; or, 
\item $N_2$ diagonalizable and $\ord_2(dN)=3+3\beta$; or,
\item $N_2$ is diagonalizable, $\ord_2(dN)=5+3\beta$. 
  and $B(\nu,N_2)=2^{\beta+1}\Z$. 
\end{enumerate}
\end{enumerate}
\item $\alpha=\beta+2$, and
\begin{enumerate}[(a)]
\item $B(\nu,N_2)=2^{\beta}\Z_2$, and
\begin{enumerate}[(i)]
\item $\ord_2(dN)-3\beta$ is odd; or 
\item $\ord_2(dN)-3\beta=4$; or,
\item $\rad(dN)'$ is divisible by a prime $p$ for which 
  $\left(\frac{-\lambda}{p}\right)=-1$; or,
\item $N_2$ has a binary Jordan component with the square free part 
  of its discriminant congruent to $5\mod 8$; or,
\end{enumerate}
\item $B(\nu,N_2)=2^{\beta+1}\Z_2$, $\n(G_2)=2^{\beta+2}\Z_2$, 
  where $G_2$ is the orthogonal complement of $\nu$ in $N_2$, and 
\begin{enumerate}[(i)]
\item $\ord_2(dN)-3\beta$ is odd; or,
\item $\ord_2(dN)-3\beta=6$; or,
\item $\rad(dN)'$ is divisible by a prime $p$ for which 
  $\left(\frac{-\lambda}{p}\right)=-1$. 
\end{enumerate}
\end{enumerate}
\item $\alpha=\beta+3$, and
\begin{enumerate}[(a)]
\item $G_2$ is not diagonalizable; or,
\item $\n(G_2)=2^{\alpha}\Z_2$, and $\ord_2(dN)-3\beta$ is even, 
  or $\ord_2(dN)=9+3\beta$; or,
\item $\n(G_2)=2^{\alpha+1}\Z_2$ and $\ord_2(dN)-3\beta$ is odd; or,
\item $\rad(dN)'$ is divisible by a prime $p$ satisfying 
  $\left(\frac{-\lambda}{p}\right)=-1$; or,
\item $\rad(dN)'\not\equiv Q(\nu)'\mod 8$; or,
\item $\n(G_2)=2^{\alpha}\Z_2$ and $2^\alpha Q(\nu)$ is not represented by $G_2$. 
\end{enumerate}
\item $\alpha=\beta+2$ or $\beta+3$, and 
  $\frac{2^\beta\rad(dN)'-Q(\nu)}{2^{\alpha}}$ is represented by $H(x)$. 
\end{enumerate}
\end{theorem}
```

**Veredict:** 🔴 TRUNCADO — YAML debe reemplazarse con el texto completo.

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

### Source (Trop-Prog-Arxiv-V2.tex, Theorem)
```latex
\begin{theorem}[\cite{EM-79,GKK-88}] 
For the mean payoff game whose payments are given by the matrices 
$A,B\in (\R\cup\{-\infty\})^{m\times n}$, 
where $A,B$ satisfy Assumptions 1 and 2, 
there exists a vector $\chi\in\R^n$ and a pair of
positional strategies $\sigma^*$ and $\tau^*$ such that 
\begin{enumerate}[(i)]
\item $\Phi_{A,B}^{\sup}(j,\tau^*,\sigma)\leq \chi_j$ for
all (not necessarily positional) strategies $\sigma$,
\item $\Phi_{A,B}^{\inf}(j,\tau,\sigma^*)\geq \chi_j$
for all (not necessarily positional) strategies $\tau$, 
\end{enumerate}
for all nodes $j$ of Min. 
\end{theorem}
```

**Veredict:** 🔴 TRUNCADO — YAML dice "there exists..." sin completar. Debe reemplazarse con el texto completo.

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
\begin{theorem}
Let $B_{\varepsilon}(N)$ denote the set of binary $m<N$ for which 
$\theta_m<m^{1/2+\varepsilon}$. Then we have
$$B_{\varepsilon}(N) = \left\{ \begin{array}{ll}
\Omega(N^{1/2}) & \text{for } 0 < \varepsilon < 1/2, \\
O(N^{1/2+\varepsilon}) & \text{for } 0 < \varepsilon < 1/6, \\
O(N/\log^2 N) & \text{for } 0 < \varepsilon < 1/2,
\end{array}\right.$$
where we used the $O$ and $\Omega$ asymptotical notation.
\end{theorem}
```

**Veredict:** 🟡 TRUNCADO — Faltan dos ramas de la llave (O(N^{1/2+ε}) y O(N/log²N)) y la línea de notación.

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

### Source (ur.tex, Theorem)
```latex
\begin{theorem}
The set $\cP \sseq \Rset^n$ is a closed polyhedron if and only if
there exist finite sets $R, P \sseq \Rset^n$
of cardinality $r$ and $p$, respectively,
such that $\vect{0} \notin R$ and
\[
  \cP = \gen\bigl( (R, P) \bigr)
      \defeq
        \biggl\{\,
          R \vect{\rho} + P \vect{\sigma} \in \Rset^n
        \biggm|
          \vect{\rho} \in \nonnegRset^r,
          \vect{\sigma} \in \nonnegRset^p,
          \sum_{i=1}^p \sigma_i = 1
        \,\biggr\}.
\]
\end{theorem}
```

**Veredict:** 🔴 TRUNCADO y ERROR — YAML dice `\vect{0} \in \cP` (pertenece) pero la fuente dice `\vect{0} \notin R` (NO pertenece a R). La definición de P está truncada con "...".

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

### Source (s.tex, Proposition #1)
```latex
\begin{proposition} 
For any graph $G$ we have 
\begin{equation} \left\{ \begin{array}{ccl}
\bPsi_p(\, \calC_t \, \mbox{ occurs for every } \, t \, )=1  
  & \mbox{ if } & p>p_c(G) 
   \\[1ex]
\bPsi_p\bigl((\neg\, \calC_t) \mbox{ occurs for every } t\bigr)=1 
  & \mbox{ if } & p<p_c(G) \, .
\end{array} \right.
\nonumber
\end{equation} 
\end{proposition}
```

**Veredict:** 🟡 TRUNCADO — Falta la segunda rama de la llave (p < p_c(G)).

---

## Summary — ALL 5 CONTROLS REQUIRE YAML FIX

| # | Control | Severidad | Problema |
|---|---------|:---------:|----------|
| 1 | 1501.01654v1 | 🔴 | Truncado con "..." — enunciado enorme pero completo en fuente |
| 2 | 1101.3431v2 | 🔴 | "there exists..." — falta toda la conclusión del teorema |
| 3 | 1101.3720v1 | 🟡 | Faltan 2 ramas de la llave + notación |
| 4 | 0904.1783v3 | 🔴 | `\in \cP` vs `\notin R` (ERROR) + truncado |
| 5 | math/0504586v2 | 🟡 | Falta rama p < p_c(G) |

**Los 5 controles tienen el target_theorem truncado o con errores en el YAML.** Ninguno pasaría una verificación textual. Se requiere reemplazar los 5 con el texto completo de la fuente LaTeX.

**⏸️ FRENADO. Esperando tu confirmación para reemplazar los 5 targets en el YAML y proceder a Run 002.**
