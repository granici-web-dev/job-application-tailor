# rigorous tdd

Strict red → green → refactor cycle. Use when the project's `TESTING.md` or `PRINCIPLES.md` says TDD, or when the user explicitly invokes it.

## Preflight

Same as craft. `shape` is required for non-trivial work. `tdd` extends `craft` discipline by enforcing test-first ordering.

## The cycle, per behavior

For each piece of behavior to add (one assertion at a time):

### 1. Red

Write **one** failing test that names the behavior. Just one. Not five.

Run it. Confirm it fails for the *right reason* — not because the file doesn't compile, not because of a missing import. Fail because the assertion is unmet.

If the test compiles but the production code doesn't yet exist: that's fine, write the minimal stub (`throw new Error("not implemented")` or equivalent) so the test fails meaningfully.

### 2. Green

Write the **simplest** code that makes the test pass. Resist the urge to add the "while I'm here" code.

Hard-coded return values are acceptable here. They'll be generalized by subsequent test cases. This is the point of TDD — the next failing test forces real logic.

Run the test. Confirm green.

### 3. Refactor

Now look at the code with fresh eyes. Improve naming, remove duplication, extract helpers (if extraction is justified by ≥2 sites — see PRINCIPLES rule of three).

Run the tests. Confirm still green.

### 4. Commit (logical)

The cycle should produce a logical commit-sized change. Move on to the next behavior.

## Discipline

**One assertion per cycle.** If your test has 5 assertions, split it into 5 cycles.

**Don't write code that isn't required by a test.** No "I'll need this later" branches. No defensive paths the tests don't exercise. The test suite is the spec — if behavior isn't tested, it isn't required.

**Don't write tests after.** Writing the implementation first then tests is not TDD; it's regression coverage. Both are valuable, but `tdd` means test-first.

**Don't re-test the framework.** A test that asserts `Array.map` works is wasted. Test the behavior unique to your code.

**Don't snapshot trivially.** Snapshots that "look right and we'll fix when they break" become noise. Use sparingly, only where the structure is genuinely the contract.

## Test naming

Follow `TESTING.md`. If the project hasn't pinned a convention, default to:

- File: `<source>.test.ts` co-located with the source (or matching `tests/` tree if that's the convention).
- Test name: full sentence describing the behavior, not the function. `"returns 404 when the tender ocid does not exist"` beats `"test getTender error case"`.

## Mocking posture

Read `TESTING.md`. If it says "real DB", use a real test DB; spinning up Postgres in CI is solved.

If you need to mock something, mock at boundaries the project already mocks (HTTP clients, time, randomness). Don't introduce mocks at boundaries that aren't already mocked elsewhere — it creates inconsistency and tests that pass while production breaks.

## When TDD doesn't fit

- **Spike code / exploration** — write throwaway code first, then if it survives, redo with tests.
- **Pure UI tweaks** — visual regression isn't test-driven; eyeballs are the spec.
- **Migration scripts** — usually one-shot; tests don't add value proportional to cost.
- **Bug fixes for which a regression test is overkill** — judgment call. State the choice openly.

In all of these cases, switch to `craft`. State why TDD is being skipped so the user can disagree.

## What tdd is not

- Not 100% coverage as a goal. Coverage is a side effect. The goal is design feedback — tests force you to confront ergonomics before users do.
- Not a slow process. A trained TDD cycle takes 2–5 minutes per behavior. If a cycle takes 30 minutes, the design is too coupled — go back to shape.
- Not religion. If pure TDD doesn't fit a particular task, switch to craft. Be honest about it.
