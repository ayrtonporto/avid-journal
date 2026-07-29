# tests

Pytest suite for the pipeline. Fixtures (sample `.tex` papers, a Mathlib smoke file)
live in [`fixtures/`](fixtures/).

## Running

```bash
pytest tests/              # everything
pytest -m "not live"       # skip tests that hit Leandex / arXiv / TheoremSearch / the LLM
pytest tests/test_jaccard.py -q   # a single module
```

Tests marked `live` make real network / LLM calls and need the relevant keys in `.env`.
Everything else runs offline.

## Rough map

| Area | Tests |
|---|---|
| Parsing | `test_error_parser`, `test_fetch_abstract`, `test_paper_extractor_local` |
| Novelty D1 | `test_novelty`, `test_arxiv_backoff`, `test_theoremsearch_exclusion`, `test_ss_api_key` |
| Novelty D3 | `test_jaccard`, `test_filters`, `test_premise_extraction`, `test_autolocation`, `test_d3_integration`, `test_d3_orchestrator_integration` |
| Formalization / Lean | `test_lean_repl`, `test_orchestrator`, `test_informal_match` |
| End-to-end | `test_pipeline_integration`, `test_e2e_real` |
