# rigorous debug

Find the **root cause** of a defect. Not a symptom-suppressing patch. Channeled from John Carmack's discipline (*"It is much more important to know the right thing to do than to do things faster"*) and obra/superpowers/systematic-debugging.

## When to invoke

- A test is flaky.
- A user-reported bug.
- A behavior that contradicts the model in your head.
- Something works locally but not in CI / production.
- A change in one place broke something seemingly unrelated.

## The discipline

Most bug fixes that ship "as a fix" actually paper over symptoms. Real debugging produces:

1. A reproducible test case.
2. A clear cause (not "fixed by adding `if (!x) return`").
3. A fix that addresses the cause.
4. A regression test that fails without the fix.

If any of those four is missing, you didn't debug — you patched.

## Process

### 1. Reproduce

Get the bug to fire on demand. Write a minimal test that exhibits it. The test fails — that's the starting line.

If you can't reproduce, you can't debug. Spend whatever time it takes to make it reproducible. Often this step alone reveals the cause.

For environment-dependent bugs (works locally, fails in prod): identify the differing variable. OS, env var, data shape, timing, concurrency, library version. Reproduce locally by simulating the difference.

### 2. Form a hypothesis

State explicitly: "I believe X is happening because Y." This is testable.

Avoid:
- "Something with the database" — too vague.
- "I'll just try adding a console.log everywhere" — shotgun.

Do:
- "I believe the function returns the wrong row because the SQL `ORDER BY` is missing a `DESC` qualifier" — specific, falsifiable.

### 3. Test the hypothesis

Don't fix yet. **Confirm the cause first.** Add a focused log, hit a breakpoint, query the DB at the failing time, inspect the network response.

If the hypothesis is confirmed → step 4. If not, refine and retest. Don't fix based on unconfirmed guesses.

### 4. Reach the root, not the proximate

A common trap: you find a `null` where there shouldn't be one. The proximate cause is "value is null". The fix would be "check for null". But the **root cause** is "why is the value null in the first place"?

Trace upstream:
- Where was the null introduced?
- Why didn't the type system catch it?
- What invariant did the producer violate?

Fix the producer. The consumer's null check is a bandaid that hides the next instance of the same class of bug.

The "Five Whys" works here. If you stop at the first why, you patched. If you trace 3–5 levels up, you fixed.

### 5. Implement the fix

The fix targets the root. Often it's smaller than the symptomatic patch.

Resist the urge to also "clean up while I'm here". Mix-ins make the change unreviewable.

### 6. Add the regression test

The test you wrote in step 1 (or a refined version) goes into the suite. It must:
- Fail without your fix.
- Pass with it.
- Have a name that future readers will associate with this exact bug class.

If the bug only manifests under specific conditions (timing, concurrency), the test must reproduce those conditions reliably. Flaky regression tests are worse than no test.

### 7. Verify the fix doesn't break adjacent behavior

Run the full test suite. Read the diff once more — am I sure I didn't change observable behavior elsewhere?

For high-stakes fixes: deploy to staging, observe.

## Common anti-patterns

**Defensive null check.** `if (!x) return;` to make the crash go away without understanding why `x` is null. Symptom suppression.

**Try/catch swallow.** Wrapping the failing block in try/catch and logging. The bug is now silent in production.

**Time-based sleep.** Adding `setTimeout` to "fix" a race. Will break under load.

**Reverting "to before it broke".** Sometimes correct, but only if you understand the regression. Otherwise you reintroduce whatever the original change was trying to fix.

**"Cargo cult fix".** Copying a fix from a similar bug elsewhere without understanding the local cause.

**Heisenbug rationalization.** "It works now, must have been a flake" → it'll come back, often worse.

## When the cause is genuinely external

Sometimes the root is in a library, the OS, a third-party API. You can't fix it. Then:

- Document what you found (link to upstream issue if exists).
- Choose mitigation: workaround, version pin, switch library, retry.
- Add a regression test that fails if the mitigation is removed.
- Set a calendar reminder to re-test when the upstream fix lands.

State the workaround openly in code:

```ts
// Workaround for upstream-lib#123: trims trailing CR which the library
// fails to handle on Windows. Re-test once #123 ships.
input = input.replace(/\r$/, "");
```

## Output

After debug:

- Reproducible test case (committed).
- Cause statement: "X happened because Y" (in commit message or PR description).
- Fix (the smallest one that addresses Y).
- Regression test (committed).
- Notes on what was ruled out, if it took multiple hypotheses.

## Discipline

**Time-box hypothesis testing.** If a hypothesis takes more than 30 minutes to confirm, you're probably hunting in the wrong area. Reset.

**Print statements are fine.** Don't get hung up on debugger setup. `console.log` / `print` / `eprintln` for 10 minutes beats configuring breakpoints for 30.

**Talk to the rubber duck.** If you can't articulate the bug to a hypothetical teammate, you don't yet understand it.

**Don't fix in haste.** A fix shipped without confirming the root cause is a future incident in waiting.

## What debug is not

- Not a guarantee of immediate resolution. Some bugs take days. The discipline is what converges on a solution; the time is what it takes.
- Not the same as feature work. Don't refactor while debugging — find the cause, fix it minimally, refactor as a separate task.
- Not optional. Patches that hide symptoms accumulate into legacy systems no one understands.
