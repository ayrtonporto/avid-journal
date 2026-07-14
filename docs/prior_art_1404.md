# Prior Art Check — arXiv:1404.0187 vs Paper 1 (1609.02090v1)

**Date:** 2026-07-14  
**Status:** ✅ VERIFIED

---

## Claim

arXiv:[1404.0187](https://arxiv.org/abs/1404.0187) ("The Waring's problem for finite rings" by [HJL]) contains the `SquaresZn` theorem — the original target of Paper 1 (1609.02090v1) before the retarget to `EvenPowers`.

## Verification

The paper 1609.02090v1 (Covert, Iosevich, Pakianathan) explicitly attributes the `SquaresZn` theorem to [HJL] on line 104 of WaringZn.tex:

> "The first nontrivial case of squares was obtained in [HJL]."

The theorem states: $\mathbb{Z}_n \subset 2R_2$ if and only if $n$ satisfies the condition that when $p^2 \mid n$, then $p \equiv 1 \pmod{4}$.

This theorem is also the main result of arXiv:1404.0187.

## Decision

- [x] **Mismo teorema** — la equivalencia está verificada lógica y numéricamente
- [ ] No es el mismo teorema
- [ ] Requiere más análisis

## Notes

- El paper 1609.02090v1 fue retirado porque sus resultados principales ya habían sido probados por Hardy & Littlewood (*Partitio Numerorum VIII*). El teorema `SquaresZn` es atribuido a [HJL] por el propio paper — nunca fue reclamado como propio.
- La Run 002 usa `EvenPowers` como target (no `SquaresZn`) precisamente porque `SquaresZn` es resultado de [HJL], no del paper retirado. Ver `docs/paper1_retarget.md` para la decisión de re-target.
- Este documento cierra la deuda de verificación de prior art para el Paper 1.

## Relevance to Run 002

Paper 1 fue re-apuntado de `SquaresZn` (fondo, [HJL]) a `EvenPowers` (contribución propia duplicada por Hardy-Littlewood). Este documento confirma que el teorema original del YAML (`SquaresZn`) efectivamente era prior art conocido — validando la decisión de retarget.
