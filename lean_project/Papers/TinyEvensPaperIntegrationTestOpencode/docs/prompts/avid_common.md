# AViD Common Rules

> **Purpose**: Shared rules and conventions for ALL AViD agents (coordinator, sketch, blueprint).
>
> AViD Journal automates the formalization of mathematical papers: each block
> (definition, lemma, theorem, proposition, corollary) is turned into verified
> Lean 4 code and accumulated into `Paper.lean`.

---

## 1. Search Order (MANDATORY)

**Every time you need to find a lemma, definition, or any result, search in this exact order:**

```
1. PAPER_INDEX.md           ← results already proven IN THIS paper
   ↓ (if not found)
2. lean_local_search        ← find it inside Paper.lean by name
   ↓ (if not found)
3. lean_leandex             ← semantic search in Mathlib (natural language)
   ↓ (if not found)
4. lean_loogle              ← type-pattern search in Mathlib
```

### Why this order

- **PAPER_INDEX.md**: the author of the paper already proved it here. Reusing
  previous blocks is always preferable to re-proving or importing from Mathlib.
- **lean_local_search**: confirms name and exact signature in the current
  project.
- **lean_leandex** / **lean_loogle**: only consult Mathlib after exhausting
  local results.

### CRITICAL: Don't skip PAPER_INDEX

A block named `thm:foo` proven earlier in the paper MUST be reused by subsequent
blocks. The orchestrator guarantees topological order, so any label visible in
`PAPER_INDEX.md` is already compiled in `Paper.lean` and available for `open`
and direct reference.

---

## 2. sorry / axiom Policy

**This is the strictest divergence from Numina.**

| Construct | Allowed? | Where |
|-----------|----------|-------|
| `sorry`   | ❌ NEVER in final output | Final `Paper.lean` MUST NOT contain `sorry` |
| `axiom`   | ⚠️ ONLY for external results | With mandatory source comment |

### sorry

- You MAY use `sorry` during intermediate attempts.
- Your session ends with `END_REASON:COMPLETE` ONLY when the block compiles
  and has no `sorry`.
- If you cannot remove a `sorry`, end with `END_REASON:LIMIT`. The orchestrator
  will mark the block as `failed` and move on.

### axiom

Used ONLY when:
1. The paper cites an external result without proof (`proof_latex` is `null`).
2. You searched Mathlib with `lean_leandex` AND `lean_loogle` and did NOT find it.

Declare it as:

```lean
/-- source: [Author, Year, "Paper title"] -/
axiom ext_result_name : <statement>
```

The `-- source:` comment is mandatory. The orchestrator will mark the block
as `axiom` in `PAPER_INDEX.md`.

### What NOT to do

- ❌ Adding `axiom` because the proof is hard.
- ❌ Adding `axiom` as a replacement for `sorry`.
- ❌ Leaving `sorry` in a block that ended with `COMPLETE`.

---

## 3. Windows Encoding Note

**The Lean code written to files runs on Windows + lean-lsp-mcp.**

Unicode math symbols break the diagnostic parser's column offsets. Avoid them:

| Don't write | Write instead |
|-------------|---------------|
| `ℕ`         | `Nat`         |
| `ℤ`         | `Int`         |
| `ℝ`         | `Real`        |
| `ℚ`         | `Rat`         |
| `ℂ`         | `Complex`     |

Operators like `→`, `∀`, `∃`, `≤`, `≥`, `∈`, `∧`, `∨`, `¬` are fine (they are
single-width in the parser); but identifiers with unicode letters should be
avoided. When in doubt, stick to ASCII.

---

## 4. Verification Tool

**Always verify with `lean_diagnostic_messages`. NEVER use `lake build` or
`lean_build`.**

```
lean_diagnostic_messages(file_path="Paper.lean")
```

- Severity 1 = error
- Severity 2 = warning

A block is verified when `lean_diagnostic_messages` returns no severity-1
errors for your target file.

---

## 5. Block Types and Treatment

| Block type                                    | Has proof? | Treatment |
|-----------------------------------------------|------------|-----------|
| `definition`                                  | No         | Direct Lean translation; verify it compiles. |
| `theorem` / `lemma` / `proposition` / `corollary` with `proof_latex` | Yes | Formalize statement AND proof using `proof_latex` as guide. |
| Any block with `proof_latex = null`           | No         | Search Mathlib → if found, use it; if not, declare as `axiom` with source. |

**Important**: AViD has NO separate proof agent. The Sketch Agent formalizes
the statement AND the proof in a single pass. The informal proof from the
paper is the primary guide.

---

## 6. TASK.md — Your Input for Each Block

Every session works on ONE block. The orchestrator writes `TASK.md` at the
root of the Lean project with:

```markdown
# Current Block

- **Label**: thm:foo
- **Type**: theorem
- **Title**: Main Identity
- **Target file**: Blocks/thm_foo.lean
- **Dependencies (already in PAPER_INDEX)**: def:bar, lem:baz

## Informal statement

<statement_latex>

## Informal proof

<proof_latex>

## Notes

<optional orchestrator notes>
```

Read `TASK.md` FIRST, then `PAPER_INDEX.md`, then open the target file.

---

## 7. Output Format

Each session MUST end with exactly one of:

```
END_REASON:COMPLETE
```
or
```
END_REASON:LIMIT
```

- `COMPLETE`: target block compiles, no `sorry`, no errors.
- `LIMIT`: progress made but compilation not achieved.

The line must be the LAST line of your response. No text after it.

---

## 8. Agent Tools Summary

| Tool                         | Purpose |
|------------------------------|---------|
| `lean_diagnostic_messages`   | Verify target file (use frequently) |
| `lean_goal`                  | Inspect proof state |
| `lean_local_search`          | Find declarations in current project |
| `lean_leandex`               | Natural-language Mathlib search |
| `lean_loogle`                | Type-pattern Mathlib search |
| `hint` / `grind` / `aesop`   | Automated tactics (try before manual) |

---

## 9. NOT TO DO | WHY | HOW

| NOT TO DO | WHY | HOW (instead) |
|-----------|-----|---------------|
| Use `sorry` in COMPLETE output | Final paper must be sound | End with LIMIT if stuck |
| Use `axiom` for hard proofs | Only for external results | Prove it or end with LIMIT |
| Skip PAPER_INDEX | Re-proving wastes effort | Always check PAPER_INDEX first |
| Use `ℕ`, `ℝ`, etc.           | Breaks Windows diagnostic parser | Use `Nat`, `Real`, etc. |
| `lake build`                 | Too slow, wrong tool | `lean_diagnostic_messages` |
| Forget `source:` on axiom    | Audit trail required | Always cite paper/author on axioms |
