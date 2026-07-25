---
title: AViD Journal Demo
emoji: 🔬
colorFrom: red
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# 🔬 AViD Journal — Demo

**Automated Verification in Demonstrations**

A system that checks whether mathematical theorems are genuinely novel by
searching formal libraries (Mathlib) and informal literature (arXiv +
TheoremSearch).

## What this demo does

For each theorem in your `.tex` file the pipeline runs:
- **Formalization** — `.tex` → Lean 4 (a formalizer provider; verified by Lean).
- **D2 (triviality)** — tactic budget `{decide, norm_num, simp, omega, tauto, aesop}`.
- **D1 (existence)** — Mathlib (Leandex) as formal corpus C_F; arXiv +
  TheoremSearch as informal corpus C_I (MiniLM coarse filter + DeepSeek judge).

Verdicts you may see:
- 🟢 `NOVEDAD_ENUNCIADO` — genuinely new statement
- 🟡 `MATCH_ENCONTRADO_PENDIENTE_D3` — found in Mathlib, proof novelty unknown
- 🟠 `CONOCIDO_LITERATURA` — found in informal literature
- ⚪ `ZONA_GRIS` — related but different (generalization/specialization)
- 🔴 `NO_NOVEDOSO_trivial` — closed by a D2 tactic

Formalization and D2 need Lean 4 + Mathlib. The Docker image (`deploy/Dockerfile`)
bundles them plus a **resident Lean REPL pool** (Mathlib preloaded) so checks are
sub-second; a lightweight deploy without Lean falls back to D1-only.
**D3 (proof distance)** runs offline (LeanDojo + premise extraction), not in the demo.

For the full pipeline, clone the repo and run locally:
```
git clone https://github.com/ayrtonporto/avid-journal
cd avid-journal
pip install -r requirements.txt
python app.py
```

## Author

**Ayrton Porto** — UNICEN, Argentina
- [GitHub](https://github.com/ayrtonporto/avid-journal)
- [Landing Page](https://avid-journal.github.io)
- [Paper (arXiv)](https://arxiv.org) (forthcoming)
