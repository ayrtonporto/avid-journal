# PAPER_INDEX — Paper

Base de datos local de bloques formalizados de este paper.
El Sketch Agent debe consultar este archivo ANTES de buscar en Mathlib.

---

## def:even — Even number
Type: definition
Status: ❌ failed
File: Paper.lean:8
Depends on: —
Statement: A natural number $n$ is even if there exists a natural number $k$ such that $n = 2k$.

---

## lem:even_sum — Sum of two evens
Type: lemma
Status: ❌ failed
File: Paper.lean:12
Depends on: def:even
Statement: If $a$ and $b$ are even natural numbers (Definition~\ref{def:even}), then $a + b$ is even.

---

## thm:four_evens — Sum of four evens
Type: theorem
Status: ❌ failed
File: Paper.lean:16
Depends on: lem:even_sum
Statement: If $a, b, c, d$ are even natural numbers, then $a + b + c + d$ is even.

---

## def:even — Even number
Type: definition
Status: ✅ verified
File: Paper.lean:20
Depends on: —
Statement: A natural number $n$ is even if there exists a natural number $k$ such that $n = 2k$.

---

## lem:even_sum — Sum of two evens
Type: lemma
Status: ✅ verified
File: Paper.lean:22
Depends on: def:even
Statement: If $a$ and $b$ are even natural numbers (Definition~\ref{def:even}), then $a + b$ is even.

---

## thm:four_evens — Sum of four evens
Type: theorem
Status: ✅ verified
File: Paper.lean:27
Depends on: lem:even_sum
Statement: If $a, b, c, d$ are even natural numbers, then $a + b + c + d$ is even.

---

