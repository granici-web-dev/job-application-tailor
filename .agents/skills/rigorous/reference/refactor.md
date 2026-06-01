# rigorous refactor

Restructure code without changing observable behavior. Different from `simplify` (which removes) and `craft` (which adds features) — refactor reorganizes.

Channeled from Martin Fowler's *Refactoring* discipline: small steps, tests after each, no behavior change.

## When to invoke

- The code works but its shape is impeding the next change.
- Two parallel features keep stepping on each other in one module.
- A module has grown past the size where it's readable in one sitting.
- A name no longer matches what the code does.
- An abstraction emerged after the third duplication appeared.

## When NOT to invoke

- "While I'm in here." Refactor opportunistically only if it's tightly scoped. Otherwise: separate task.
- "I think this would be cleaner." If the team isn't blocked by current structure, leave it.
- Right before a release. Refactor introduces risk; don't stack with deploy risk.

## The contract

**Behavior must not change.** Tests pass before refactor, pass after, and pass at every checkpoint in between. If they don't, you broke something — revert and try a smaller step.

If the existing tests don't cover behavior you'd be touching: write the tests first (a "characterization test" — captures current behavior so you'll notice if it changes). Only then refactor.

## The catalog (refactors that almost always pay off)

### Rename

A name that describes the old purpose is a tax on every future reader. Rename in one move (IDE-assisted is best). Tests must still pass.

### Extract function

When a 50-line function has 3 distinct steps, extract each into a named function. The original becomes a 5-line orchestrator. Names tell the story.

### Inline function

Inverse of extract. A function called once, named obscurely, just delegates. Inline it.

### Move function (or method)

Function lives in module A but only operates on data from module B. Move it to B. Reduces cross-module coupling.

### Split phase

A function does step 1, then step 2 with the output of step 1. Split into two functions; pipe explicit. Now each is testable on its own.

### Replace conditional with polymorphism

A switch over a type tag, repeated in 5 places. Replace with proper subclassing or tagged union dispatch. **Caution**: only after the third or fourth repetition. Earlier is premature.

### Replace primitive with object / type

A `string` that means "user role" gets a typed wrapper. Compiler catches misuse.

### Replace nested if with guard clause

```ts
function foo(x) {
  if (x.valid) {
    if (x.permitted) {
      // happy path
    }
  }
}
```

Becomes:

```ts
function foo(x) {
  if (!x.valid) return ...;
  if (!x.permitted) return ...;
  // happy path
}
```

Reduces nesting; reads top-to-bottom.

### Replace magic literal with named constant

`30000` becomes `RETRY_TIMEOUT_MS`. Loud at the call site, named in one place.

### Pull up / push down

A method shared by two subclasses moves to the parent. A method only one subclass uses moves to that subclass.

## Process

### 1. Pick the smallest refactor that addresses the pain

If you can fix the pain with a rename, do that. Don't skip to "extract base class" when "rename + move" gets it done.

### 2. Run the tests now

Get the green baseline. Note the count and timing.

### 3. Apply the change

Use the IDE if it has one. Manual is fine for small. Resist combining 4 refactors into 1 commit.

### 4. Run tests again

Same count green? Continue. Different? Revert.

### 5. Commit

Each commit a coherent refactor with a green-tests checkpoint. If you ever need to bisect later, this is what saves you.

### 6. Repeat for the next-smallest step

Big refactors are sequences of small ones. Don't try to land "rewrite the auth subsystem" in one go.

## Common mistakes

- **Mixing refactor with feature work.** A commit titled "refactor + add new endpoint" is two changes. Reviewers can't tell which broke if regression hits. Split.
- **Refactoring without tests.** "Trust me, this is equivalent" is the famous last words. Get coverage first or accept the risk explicitly.
- **Refactoring code that was about to be deleted.** Wasted work. Check whether the module is on the way out before polishing it.
- **Refactoring to a pattern instead of a problem.** "Let's introduce the Strategy pattern" is solution-shaped. The problem is "these 3 functions take a tag and dispatch differently". Apply the smallest fix that solves *that* — sometimes Strategy, often something simpler.

## Output

After a refactor session:

- List of refactors applied (rename / extract / move / split / etc).
- Tests-passed checkpoints (count + duration).
- One-line summary of what's now easier to do.
- One-line summary of what wasn't refactored and why.

## Discipline

**No behavior change.** If a behavior change is needed, that's a separate `craft`.

**Small steps.** Big-bang refactors land 60% on green and 40% in revert. Small steps land 100%.

**Run tests often.** Cost of running tests << cost of bisecting which of 8 changes broke things.

**Stop when the original pain is gone.** "While I'm here" is the path to scope creep.

## What refactor is not

- Not a rewrite. A rewrite is `craft` of a replacement; refactor is incremental.
- Not a style pass. Linter does style. Refactor is structure.
- Not negotiable on tests. No tests, no refactor — write them first or accept the risk.
