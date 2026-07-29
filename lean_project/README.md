# lean_project

Shared Lean 4 project that hosts every paper AViD formalizes as a sub-module. Mathlib is built **once** here; each paper reuses the cached oleans instead of getting its own Mathlib.

## Layout

```
lean_project/
├── lakefile.toml          # toolchain + Mathlib + library declarations
├── lean-toolchain         # pinned Lean version
├── LeanProject.lean       # default library entry point
└── Papers/
    └── <ModuleName>/      # one sub-module per formalized paper
        ├── Paper.lean              # cumulative module (orchestrator-owned)
        └── Blocks/<lean_name>.lean # per-block file (edited by the LLM agent)
```

The Lean module path for a paper is `Papers.<ModuleName>.Paper`.

> The orchestrator also writes per-paper working files at runtime — `PAPER_INDEX.md`
> (block log), `REVIEW.md` (human-review notes), `TASK.md` (current block context) and
> a copied `docs/prompts/`. These are **gitignored**: they are AI-workflow scaffolding,
> not part of the tracked source.

## Checked-in Papers

| Sub-module | Purpose |
|---|---|
| `Papers/Paper/` | Small worked example (`def_even`, `lem_even_sum`, …). One module is built in the Docker image to register the `Papers` root for D3. |
| `Papers/D3_Calibration/` | Calibration theorems referenced by `src/novelty/d3_extraction_map.yaml`. |
| `Papers/AyrtonPortoTesis/` | Author's thesis blocks (topology/algebra), kept as extra formalized material. |

## Setup

Install Lean via [elan](https://leanprover-community.github.io/get_started.html). The toolchain pinned in [lean-toolchain](lean-toolchain) takes precedence over any system Lean.

One-time Mathlib build (slow the first time, fast afterwards):

```bash
cd lean_project
lake update
lake build
```

`.lake/` (build artifacts, including Mathlib's `.olean` files) is gitignored.

## Working with a paper

A paper at `Papers/<ModuleName>/` is built like any other Lean library target:

```bash
lake build Papers.<ModuleName>.Paper
```

The orchestrator runs this automatically after every verified block so the next block's verification reads cached oleans.

## Pointers

- [docs/GUIA_INSTALACION_Y_USO.md](../docs/GUIA_INSTALACION_Y_USO.md) — full install + usage walkthrough (Spanish)
- [src/lean_repl/README.md](../src/lean_repl/README.md) — the resident Mathlib pool that reuses these oleans at runtime
