# prompts — LLM agent prompts

The prompts that drive the formalization agent. The formalizer copies the agent docs
under `docs/prompts/` into each paper's Lean project at runtime, so **this folder is the
single source of truth** — do not edit the per-paper copies (they are gitignored).

## Layout

```
prompts/
├── prompt_avid.txt              # SIMPLE-mode block prompt
├── prompt_medium_mode_avid.txt  # MEDIUM-mode block prompt
├── prompt_hard_mode_avid.txt    # HARD-mode block prompt
└── docs/prompts/
    ├── avid_common.md           # shared conventions for every agent
    ├── avid_coordinator.md      # coordinator agent
    ├── avid_blueprint_agent.md  # proof blueprint agent
    └── avid_sketch_agent.md     # proof sketch agent
```

Which top-level prompt is used is chosen by `src/formalization/complexity.py` from the
block's `SIMPLE` / `MEDIUM` / `HARD` classification.
