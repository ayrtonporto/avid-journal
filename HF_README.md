---
title: AViD Journal Demo
emoji: 🔬
colorFrom: red
colorTo: gray
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
---

# 🔬 AViD Journal — Demo

**Automated Verification in Demonstrations**

A system that checks whether mathematical theorems are genuinely novel by
searching formal libraries (Mathlib) and informal literature (arXiv).

## What this demo does

This is a **D1-only** demo: it checks whether a theorem already exists in:
- **Mathlib** (via Leandex semantic search) — formal corpus
- **arXiv / Semantic Scholar** (via embeddings + LLM judge) — informal corpus

For each theorem in your `.tex` file, you get a verdict:
- 🟢 `NOVEDAD_ENUNCIADO` — genuinely new statement
- 🟡 `MATCH_ENCONTRADO_PENDIENTE_D3` — found in Mathlib, proof novelty unknown
- 🟠 `CONOCIDO_LITERATURA` — found in arXiv literature
- ⚪ `ZONA_GRIS` — related but different (generalization/specialization)

## What's NOT included

- **D2 (triviality filter):** requires Lean 4 + Mathlib locally
- **D3 (proof distance):** requires LeanDojo + premise extraction

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
