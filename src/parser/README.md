# src/parser — LaTeX → blocks

Turns a `.tex` paper into an ordered list of **blocks** (theorems, lemmas,
definitions, corollaries) plus the **dependency graph** between them, so the
formalizer can process them in topological order.

## Files

| File | Role |
|---|---|
| `latex_parser.py` | The parser: extracts `\begin{theorem}…` environments, labels, statements and `\ref`/`\cref` dependencies. |
| `parse_tex.py` | CLI wrapper around the parser. |

## Usage

```bash
python -m src.parser.parse_tex path/to/paper.tex --stats
```

`--stats` prints a summary (block counts by type, dependency edges) instead of the
full block dump.
