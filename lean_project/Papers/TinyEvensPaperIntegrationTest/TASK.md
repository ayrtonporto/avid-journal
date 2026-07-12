# Current Block

- **Label**: thm:four_evens
- **Type**: theorem
- **Title**: Sum of four evens
- **Lean name**: `thm_four_evens`
- **Target file (EDIT THIS, AND ONLY THIS)**: `Blocks/thm_four_evens.lean`
- **Paper module imported by the target**: `Papers.TinyEvensPaperIntegrationTest.Paper`

## File editing rules (CRITICAL)

You MUST follow these rules. Violating them silently drops your work.

1. Edit ONLY `Blocks/thm_four_evens.lean`. This is YOUR file for this session.
2. NEVER edit `Paper.lean`. It is read-only context with the blocks
   already proven in this paper. The orchestrator will append your
   declaration to `Paper.lean` automatically AFTER this session.
3. NEVER edit `PAPER_INDEX.md`. The orchestrator updates it.
4. Keep the existing `import Papers.TinyEvensPaperIntegrationTest.Paper` line at the top of the
   target file. That import gives you access to all dependencies
   listed below by their Lean names.
5. The body of `Blocks/thm_four_evens.lean` should be ONE main declaration
   (`thm_four_evens`) plus optional helper lemmas above it.

## Dependencies you can call (already in `Paper.lean`)

- `lem:even_sum` -> Lean name: `lem_even_sum` (type: lemma)

## Informal statement

If $a, b, c, d$ are even natural numbers, then $a + b + c + d$ is even.

## Informal proof

By Lemma~\ref{lem:even_sum}, $a + b$ is even and $c + d$ is even.
Applying Lemma~\ref{lem:even_sum} once more to $a + b$ and $c + d$
yields that $(a + b) + (c + d) = a + b + c + d$ is even.

## Workflow

1. (HARD mode only) Read `docs/prompts/avid_common.md` and `docs/prompts/avid_sketch_agent.md`.
2. Open `Blocks/thm_four_evens.lean` and add your declaration(s).
3. Verify with the Lean compiler.
4. Iterate until there are no errors and no `sorry`.
5. End your response with `END_REASON:COMPLETE` (success) or `END_REASON:LIMIT`.
