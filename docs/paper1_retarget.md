# Paper 1 Retarget — 1609.02090v1 (Waring's problem for Z_n)

**Source:** `cache/retracted_dataset/src_6589a00c8ffbb195/WaringZn.tex`  
**Current YAML target:** Theorem `SquaresZn` (lines 105-107) — **atribuido a [HJL], NO es contribución original del paper**  
**Withdrawal comment:** "Main results originally proved in Some Problems of Partitio Numerorum (VIII) by Hardy & Littlewood"

---

## Contexto

El paper estudia la función γ(k) = mínimo m tal que todo Z_n se cubre con m k-ésimas potencias. Los autores calculan γ(k) para k ≤ 10 con métodos elementales.

- **Theorem `SquaresZn`** (target actual del YAML): caso k=2 con 2 cuadrados, atribuido explícitamente a [HJL] 2014 (línea 104: "The first nontrivial case of squares was obtained in [HJL]"). **NO es propio del paper.**
- **Theorem `Squares`**: Z_n ⊂ 3R_2 iff 8 ∤ n. Caso intermedio de cuadrados.
- Los **resultados propios** (no atribuidos) son los de potencias superiores: cubos, cuárticas, k-ésimas para k≥3.

## Duplicador conocido

Hardy & Littlewood, *Some Problems of 'Partitio Numerorum' (VIII)* — probaron γ(4) = 15 (citado en el propio paper como [HL], línea 55). El paper retirado da pruebas "elementales" de los mismos valores.

---

## Teoremas de potencias superiores (candidatos para el nuevo target)

### Opción A — Theorem `Cubes` (líneas 114-125)

Potencias impares. **Resultado propio del paper** (no atribuido).

```latex
\begin{theorem} \label{Cubes}
$\mathbb{Z}_n$ can always be covered by four cubes, by five quintics, 
four septics, and thirteen nonics, and these results are all best possible 
that work for all $n$. That is
\[
\mathbb{Z}_n \subset 4R_3, \mathbb{Z}_n \subset 5R_5, 
\mathbb{Z}_n \subset 4R_7, \text{ and } \mathbb{Z}_n \subset 13R_9.
\]
Furthermore, we have the following intermediary results for cubes.
\begin{enumerate}
\item \label{twocubes} $\mathbb{Z}_n \subset 2R_3$ if and only if 
  $7 \nmid n$ or $9 \nmid n$.
\item \label{threecubes} $\mathbb{Z}_n \subset 3R_3$ if and only if 
  $9 \nmid n$.
\end{enumerate}
\end{theorem}
```

**Qué caracteriza:** γ(3)=4, γ(5)=5, γ(7)=4, γ(9)=13 óptimos + casos intermedios de cubos.

### Opción B — Theorem `EvenPowers` (líneas 149-161)

Potencias pares. **Resultado propio del paper** (no atribuido).

```latex
\begin{theorem} \label{EvenPowers}
$\mathbb{Z}_n$ can be covered by fifteen quartics, nine sextics, 
thirty-two octics, and twelve decics, and these are all best possible. 
That is, for all $n \geq 2$, we have
\[
\mathbb{Z}_n \subset 15 R_4, \mathbb{Z}_n \subset 9R_6,  
\mathbb{Z}_n \subset 32R_8, \text{ and } \mathbb{Z}_n \subset 12R_{10}.
\]
Furthermore, 
\begin{enumerate}
\item \label{five4ths} $\mathbb{Z}_n \subset 5R_4$ if and only if 
  $8 \nmid n$.
\item \label{seven4ths} $\mathbb{Z}_n \subset 7R_4$ if and only if 
  $16 \nmid n$.
\end{enumerate}
\end{theorem}
```

**Qué caracteriza:** γ(4)=15, γ(6)=9, γ(8)=32, γ(10)=12 óptimos + casos intermedios de cuárticas.

### Opción C — Tabla resumen γ(k) para k≤10 (líneas 163-191)

Resultado global del paper: la función γ(k) completa para k=2,...,10.

| k | γ(k) | k | γ(k) |
|---|------|---|------|
| 2 | 4 | 7 | 4 |
| 3 | 4 | 8 | 32 |
| 4 | 15 | 9 | 13 |
| 5 | 5 | 10 | 12 |
| 6 | 9 | | |

**Qué caracteriza:** Tabla completa de γ(k) para k≤10 (el objetivo declarado del paper).

### Opción D — El par más limpio: `Cubes` + `EvenPowers` juntos

Los dos teoremas centrales que cubren todos los exponentes k≤10. Es lo que el paper anuncia como "Main Results".

---

## ¿Qué probó Hardy-Littlewood?

Según el propio paper (línea 55): **G_1(4) = 15** ([HL]), que es exactamente γ(4) = 15 (Theorem `EvenPowers`, primer ítem). El paper de Hardy-Littlewood de 1925 (*Partitio Numerorum VIII*) establece G_1(k) para varios valores mediante el método del círculo. El paper de Covert et al. reproduce estos valores con métodos elementales.

---

## Selección

> [ ] **Opción A** — Theorem `Cubes` (γ(3)=4, γ(5)=5, γ(7)=4, γ(9)=13)
> [ ] **Opción B** — Theorem `EvenPowers` (γ(4)=15, γ(6)=9, γ(8)=32, γ(10)=12)
> [ ] **Opción C** — Tabla γ(k) completa para k≤10
> [ ] **Opción D** — Ambos teoremas (`Cubes` + `EvenPowers`)
> [ ] **Otra** — (especificar)

**Instrucción:** Marcar UNA opción. Al confirmar, el `target_theorem` del YAML se reemplaza por el texto LaTeX exacto de arriba.
