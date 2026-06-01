# rigorous shape

Plan a feature, change, or subsystem **before writing any code**. The output is a short plan the user signs off on. `craft` and `tdd` won't run without it for non-trivial work.

## When to invoke

- New feature larger than ~30 lines.
- Refactor that touches >2 files.
- Anything affecting external interface (API, schema, public function).
- The user says "I want to do X" without having decided how.

Skip shape for:
- One-line bug fixes.
- Typo / dependency bumps.
- Pure renames.

## Output: a one-page plan

The user must read this in <90 seconds. Aim for ~25 lines. Sections in this order:

```markdown
## Goal
<one sentence — the user-visible outcome>

## Approach
<2-4 sentences — the technical strategy, named at the right altitude>

## Files
- `path/a.ts` — <what changes>
- `path/b.ts` — <what changes>
- `path/c.test.ts` — <new tests>

## Schema / API changes
<empty if none, otherwise: column adds, route signatures, breaking changes>

## Test plan
<which tests prove this works — unit / integration / manual?>

## Tradeoffs / alternatives considered
<2-3 alternatives you rejected and why. If you didn't consider any, you didn't shape — go think harder>

## Open questions
<anything you need from the user before craft>
```

## Discipline

**Decide, don't list.** "We could use approach A or B" is not a plan. Pick A, say why, and note B as the rejected alternative.

**Name files specifically.** Not "the routing layer" — `apps/api/src/routes/bundles.ts`. If you don't know the file path, read the codebase first.

**Schema changes are not handwaves.** Spell the migration. If a column type or nullability is ambiguous, state your choice and the reason.

**Test plan is part of the design.** "I'll write tests" is not a test plan. Name the test cases. If you can't name them, the design is not concrete enough yet.

**Tradeoffs are mandatory.** Every non-trivial design has alternatives. List 2–3. If you can only think of one path, you didn't think about it.

**Open questions stay open.** Don't paper over uncertainty in the plan. List it. The user will answer or accept the risk.

## Confirmation gate

After writing the plan, **stop and wait for explicit user approval**. Do not start craft / tdd until you receive confirmation in a separate message.

If the user replies with adjustments, revise the plan and re-confirm. Do not silently absorb the adjustments and start coding.

If the user says "go" / "ok" / "do it" / "proceed", that's the green light. Then load `craft.md` or `tdd.md` and start.

## What shape is not

- Not a TODO list. The plan is a single document, not a series of bullet items to chip at.
- Not implementation. No code in the plan. Snippets only when they clarify the interface.
- Not commitment to detail. Names of internal helpers, exact phrasing of error messages, etc., are decided during craft. Shape is altitude, craft is detail.

## Multiple-iteration shapes

For very large features, split into 2–3 phases and shape each independently:
- Phase 1 — schema + ETL
- Phase 2 — API
- Phase 3 — UI

Each phase gets its own shape + craft cycle. Don't try to plan all three in one document; the surface area is too large to keep coherent.
