# rigorous simplify

Strip the code to its essence. Remove what doesn't earn its place. The output is fewer lines that do the same job, more obviously.

Channeled from the Brian Kernighan rule: *"Controlling complexity is the essence of computer programming."*

## When to invoke

- After a feature has been live and stable for a while — the structures that helped during development are now ceremony.
- When critique flagged unjustified abstraction.
- When a new contributor can't follow the code.
- When you find yourself adding a 4th layer of indirection to add a feature.

## What to remove (in priority order)

### 1. Dead code

- Unused exports, unused functions, unused parameters.
- Unreachable branches.
- Files with zero importers.
- Comments referring to features that were ripped out.
- Feature flags that have been "true" for a year.

Reach for the linter / compiler first — they find most of this.

### 2. Premature abstraction

- Interfaces with one implementation. Inline.
- Abstract base classes with one subclass. Collapse.
- Generic types parameterized for a future that didn't arrive. De-genericize.
- Adapter / Wrapper / Facade where the wrapped thing was fine on its own.
- Strategy pattern with one strategy.

The signal: if you collapsed these, would anything else change? If no, they were ornaments.

### 3. Duplication-with-difference

The opposite trap: code that was DRY-extracted but the variants kept diverging. Now you have a "shared" function with 8 boolean parameters configuring its behavior.

Solution: split it back into 2–3 named functions. Each tells a story. The "shared" version was hiding what was actually three different operations.

### 4. Unnecessary state

- Variables holding values used once. Inline.
- Caches keyed on something never re-queried.
- Memoization for a function that's expensive in theory but called once.
- Class fields that could be local variables.

### 5. Unnecessary indirection

- A function that just calls another function with the same args.
- A method that just returns a property.
- An exported re-export of a re-export.
- "Service Locator" that returns the singleton everyone could import directly.

### 6. Defensive cargo

- Null-checks for arguments the type system already validated.
- Try/catch around code that doesn't throw.
- Boolean parameters defaulting to the value 99% of callers want.
- Configuration objects with one user.

### 7. Comments that aren't load-bearing

- Comments restating the function name.
- Comments referencing tickets that no longer exist.
- "// TODO: refactor this" without an issue link.
- JSDoc on private functions read only by the same file.

Keep WHY-comments only — see PRINCIPLES.md.

## Process

### 1. Inventory what's there

Read the target file/module top-to-bottom. List every function, type, constant, comment, branch.

### 2. Mark each as: kept / cut / merged

Be willing to cut. Default to cut when uncertain — `git revert` is cheap.

### 3. Verify nothing user-facing changes

Simplify must not change observable behavior. Tests pass. Endpoints return the same JSON. UI looks the same.

If you find a behavior change snuck in, separate it: that's a `craft` task, not a `simplify`. Land them as separate commits.

### 4. Delete

Make the cuts. Run typecheck + tests after each major cut, not at the end. Catches silent regressions early.

### 5. Verify line count went down

If it went up, you didn't simplify, you refactored. Switch to `refactor` if structure was the goal.

If you genuinely needed more lines for clarity (rare), state the trade plainly.

## Discipline

**Behavior preservation is non-negotiable.** A simplification that changes behavior is a bug introduction. If the temptation is "the old way was wrong, let me fix it" — that's not simplify, that's `refactor` or `craft`.

**Fewer concepts beats fewer characters.** A 30-line function with 1 concept beats a 5-line function with 5 nested ternaries that took 10 minutes to read.

**Resist re-naming binge.** Renaming is fine but it's not what simplify is for. Stay focused on cuts.

**Show your work.** End with a tally: "removed N lines, M files, K abstractions. Tests still pass."

## Common false-flags (don't simplify these)

- **Defensive code at boundaries.** HTTP handlers, env var reading, third-party API responses — keep the validation.
- **Comments explaining *why* a non-obvious choice was made.** "We use 5s timeout instead of 30s because the upstream service has a 7s SLA" — keep.
- **Names that look long but are domain-specific.** `tenderEnquiryDeadline` may look verbose but `dl` is worse.
- **Performance-motivated indirection.** A cache or batch is doing real work. Profile before stripping.
- **Tests.** Don't simplify tests by removing assertions. Simplify them by removing redundancy with shared fixtures.

## What simplify is not

- Not a code golf. Shortest is not a goal — clearest is. A 20-line clear function beats a 5-line clever one.
- Not a refactor. Refactor changes structure, simplify removes. Use `refactor` for the former.
- Not silent. State each cut you make and why.
