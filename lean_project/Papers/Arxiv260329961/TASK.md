# Current Block

- **Label**: thm:binomial-main
- **Type**: theorem
- **Title**: 
- **Lean name**: `thm_binomial_main`
- **Target file (EDIT THIS, AND ONLY THIS)**: `Blocks/thm_binomial_main.lean`
- **Paper module imported by the target**: `Papers.Arxiv260329961.Paper`

## File editing rules (CRITICAL)

You MUST follow these rules. Violating them silently drops your work.

1. Edit ONLY `Blocks/thm_binomial_main.lean`. This is YOUR file for this session.
2. NEVER edit `Paper.lean`. It is read-only context with the blocks
   already proven in this paper. The orchestrator will append your
   declaration to `Paper.lean` automatically AFTER this session.
3. NEVER edit `PAPER_INDEX.md`. The orchestrator updates it.
4. Keep the existing `import Papers.Arxiv260329961.Paper` line at the top of the
   target file. That import gives you access to all dependencies
   listed below by their Lean names.
5. The body of `Blocks/thm_binomial_main.lean` should be ONE main declaration
   (`thm_binomial_main`) plus optional helper lemmas above it.

## Dependencies you can call (already in `Paper.lean`)

(none)

## Informal statement

For $n$ sufficiently large, we have that
\[
f(n)\le \left(\frac{24}{\pi^2-6}+o(1)\right)(\log n)^2
\leq 6.20219 (\log n)^2.
\]
Furthermore, there exists a sequence $n_j\to \infty$ such that
\[
f(n_j)\ge \left(\frac12+o(1)\right)\log n_j.
\]

## Informal proof

By Legendre's formula,
\[
v_p\bigg(\binom{n}{k}\bigg)
= \sum_{t=1}^{\infty}\bigg\lfloor \frac{n}{p^{t}}\bigg\rfloor-\bigg\lfloor \frac{n-k}{p^{t}}\bigg\rfloor-\bigg\lfloor \frac{k}{p^{t}}\bigg\rfloor
\ge \bigg\lfloor \frac{n}{p}\bigg\rfloor-\bigg\lfloor \frac{n-k}{p}\bigg\rfloor-\bigg\lfloor \frac{k}{p}\bigg\rfloor
= \one_{n\pmod p< k\pmod p}.
\]

Fix $\varepsilon>0$, and set
\[
C=\frac{24}{\pi^2-6}+\varepsilon,\qquad Y=\lfloor C(\log n)^2\rfloor.
\]
For each integer $j\ge 2$, let
\[
\mc{P}_j=\{p\text{ prime and }p\le Y/j\}.
\]
Define $r_p\equiv n\pmod p\in [0,p)$, $a_p=p-r_p$, and
\[
T_j=\sum_{p\in \mc{P}_j}\log p,\qquad
R_j=\sum_{p\in \mc{P}_j}a_p\log p,\qquad
M_j=\bigg\lfloor \frac{Y}{j\log n}\bigg\rfloor.
\]

The crucial observation is that for $1\le A\le M_j$ we have
\[
\sum_{\substack{p\in \mc{P}_j\\a_p\le A}}\log p
\le \log\Big(\prod_{m=1}^{A}(n+m)\Big)
\le A\log(n+A)
\le A(\log n + \log M_j);
\]
indeed, if $a_p\le A$ then $p$ divides one of $n+1,\ldots,n+A$. Now note that
\begin{align*}
R_j
= \sum_{A\ge 0}\Big(\sum_{p\in \mc{P}_j}\log p\cdot (1-\one_{a_p\le A})\Big)
&\ge M_jT_j-\sum_{A=0}^{M_j-1}A(\log n + \log M_j)\\
&\ge M_jT_j-\frac{M_j^2(\log n + \log M_j)}{2}\\
&= \left(\frac{C^2}{2j^2}-o(1)\right)(\log n)^3.
\end{align*}
Here we have used that $T_j=(1+o(1))Y/j$ by the prime number theorem.

Now fix $J\ge 2$. For each prime $p\le Y$, the interval $[p,Y]$ contains exactly $\lfloor Y/p\rfloor-1$ disjoint blocks of the form
\[
[mp,(m+1)p-1]\qquad (1\le m\le \lfloor Y/p\rfloor-1),
\]
and on each such block the residue classes modulo $p$ run through all of $[0,p)$ once. Hence
\begin{align*}
\sum_{k=1}^{Y}\log(u(n,k))
&\ge \sum_{k=1}^{Y}\sum_{p\le k}\log(p)\cdot \one_{n\pmod p< k\pmod p}\\
&\ge \sum_{p\le Y}\Big(\Big\lfloor \frac{Y}{p}\Big\rfloor-1\Big)(a_p-1)\log p\\
&\ge \sum_{j=2}^{J}\sum_{p\in \mc{P}_j}(a_p-1)\log p\\
&= \sum_{j=2}^{J}(R_j-T_j)\\
&\ge \left(\frac{C^2}{2}\sum_{j=2}^{J}\frac1{j^2}-o(1)\right)(\log n)^3.
\end{align*}
Therefore
\[
\frac{\sum_{k=1}^{Y}\log(u(n,k))}{Y}
\ge \left(\frac{C}{2}\sum_{j=2}^{J}\frac1{j^2}-o(1)\right)\log n.
\]
Since
\[
\sum_{j=2}^{\infty}\frac1{j^2}=\frac{\pi^2}{6}-1
\]
and
\[
C>\frac{4}{\sum_{j=2}^{\infty}j^{-2}}=\frac{24}{\pi^2-6},
\]
we may choose $J$ so that
\[
\frac{C}{2}\sum_{j=2}^{J}\frac1{j^2}>2.
\]
Thus for $n$ sufficiently large at least one $1\le k\le Y$ satisfies $u(n,k)>n^2$, proving the upper bound.

For the lower bound, for $K\ge 2$ define 
\[M_K = \prod_{p\le K}p^{\lfloor \log_p K\rfloor + 1}.\]
We prove that $f(M_K - 1)>K$. Observe that for every $0\le k\le K$ and every prime power $p^a$, we have
\[M_K - 1 \pmod {p^a} \ge k\pmod{p^a}.\]
For $a\le \lfloor \log_p K\rfloor + 1$ this is immediate, since $M_K - 1 \equiv p^{a}-1 \pmod {p^a}$. For larger $a$, we have $M_K - 1 \pmod {p^a}\ge p^{\lfloor \log_p K\rfloor + 1} - 1>K\ge k \pmod{p^a}$, as desired.

Via \[v_p\bigg(\binom{n}{k}\bigg) = \sum_{t=1}^{\infty}\bigg\lfloor \frac{n}{p^{t}}\bigg\rfloor-\bigg\lfloor \frac{n-k}{p^{t}}\bigg\rfloor-\bigg\lfloor \frac{k}{p^{t}}\bigg\rfloor = \sum_{t=1}^{\infty}\one_{n\pmod{p^t}<k\pmod{p^t}},\]
we have that $v_p(\binom{M_K-1}{k}) = 0$ for $p\le K$ and $k\le K$. Noting that $\log(M_K) = \sum_{p\le K}(\lfloor \log_p K\rfloor + 1)\log p = 2K + o(K)$ via the prime number theorem, we immediately obtain the desired result.

## Workflow

1. (HARD mode only) Read `docs/prompts/avid_common.md` and `docs/prompts/avid_sketch_agent.md`.
2. Open `Blocks/thm_binomial_main.lean` and add your declaration(s).
3. Verify with `lean_diagnostic_messages(file_path="Blocks/thm_binomial_main.lean")`.
4. Iterate until there are no severity-1 errors and no `sorry`.
5. End your response with `END_REASON:COMPLETE` (success) or `END_REASON:LIMIT`.
