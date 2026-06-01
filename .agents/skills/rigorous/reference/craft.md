# rigorous craft

Implement the feature end-to-end after `shape` is approved. This is where most code gets written.

## Preflight

State this before editing files:

```text
RIGOROUS_PREFLIGHT: context=pass standards=pass command_reference=pass shape=pass mutation=open
```

`shape=pass` is only valid after a separate user response approving the plan, or when the user provided a confirmed plan in the request. Do **not** mark `shape=pass` after writing PRINCIPLES.md, summarizing assumptions, or drafting an unconfirmed plan yourself.

For trivial changes (single-line fix, dependency bump, typo), `shape=not_required` is acceptable. State so explicitly.

## Process

### 1. Re-read the shape plan

Before editing, re-read the approved plan. Note the file list, schema changes, test plan, open-question answers. The plan is the contract.

### 2. Build in dependency order

If the plan touches schema → routes → UI, build in that order. Each layer compiles + tests before moving to the next.

Within each layer:
- Write the code.
- Run typecheck for that workspace immediately. Fix errors before moving on.
- Run the relevant tests if test-first wasn't the chosen approach (use `tdd` for that).

### 3. Match the standards

Reference PRINCIPLES.md / STACK.md / TESTING.md *while writing*, not after. If the project says "no comments," don't add them. If it says "interfaces only with ≥2 impls," don't add an interface for a single class.

When uncertain about a standard's application, ask the user **before** writing — it's faster than rewriting.

### 4. Tests are part of the change

Per the shape's test plan, write the tests. Don't punt them to later. If they're hard to write, the design is wrong — go back to shape.

### 5. Verify behavior

For backend changes: hit the endpoint with curl, query the DB, observe the result. Don't claim "it works" from typecheck alone.

For UI changes: open the page in a browser, click through the golden path, monitor console. State plainly if you couldn't test the UI.

For migrations: run the migration on a real DB, verify the schema, run a query that exercises the new column / index.

### 6. State what changed

End-of-task message: 1–2 sentences naming the files changed and what's verified.

## Discipline

**No drift from the plan.** If craft reveals a problem with the plan, stop, re-shape, get approval, then resume. Don't quietly redesign mid-craft.

**No surprise refactors.** A craft for feature X doesn't include "while I was here, I cleaned up Y." Y is a separate task.

**No comments unless WHY-grade.** See engineering laws in SKILL.md.

**No defensive cargo.** If the schema says NOT NULL, your TypeScript code reading it doesn't need `if (!val) return null` — the type system already knows.

**No dead code.** If a function you wrote isn't called, delete it. If a variable is unused, delete it. The compiler will tell you.

**No premature extraction.** Helpers come from observed duplication, not from "this might be useful elsewhere."

**No swallow-and-log.** Errors that bubble matter. Don't catch and `console.warn` an exception you can't recover from — let it propagate and be handled at the boundary.

## Verification checklist

Before declaring done:

- [ ] Typecheck passes for affected workspaces (`npm run typecheck` or equivalent).
- [ ] Tests pass — both new and existing.
- [ ] Linter / formatter clean.
- [ ] Behavior verified (browser / curl / SQL — pick the right one).
- [ ] No debug `console.log` left behind.
- [ ] No commented-out code.
- [ ] No `// eslint-disable` without a justification comment.
- [ ] Migration files (if any) ran cleanly.

If anything fails, fix it. Don't claim done with broken state.

## What craft is not

- Not exploration. Exploration belongs in shape. By craft, the design is decided.
- Not a place to revisit the brand of the project, the deployment model, or the test strategy. Those belong in PRINCIPLES.md / STACK.md / TESTING.md, edited by the user explicitly.
- Not a free-for-all. Every line written should map to something in the shape plan or be a near-zero-cost consequence of it.
