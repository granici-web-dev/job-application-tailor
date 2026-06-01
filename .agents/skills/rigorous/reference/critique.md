# rigorous critique

Acid review. Pretend you're a skeptical staff engineer on a fast team — nothing gets in unless it earns its place. The point is to surface what's complicated, what's unjustified, and what can be cut.

This is not "polite feedback". It's honest, specific, and unsentimental.

## When to invoke

- After craft, before opening a PR.
- On someone else's code that you're about to merge into.
- On your own code from a few weeks ago.
- When something feels off but you can't articulate why.

## Process

### 1. Read everything once, no notes

First pass: just read. No opinions yet. You're calibrating context — what is this thing trying to do?

### 2. Re-read with five questions

For each function, file, or chunk being reviewed, ask:

**1. What problem does this solve?** If you can't say it in one sentence, the code is too tangled.

**2. Is the simplest version of this code?** If you can imagine a simpler one, that one should ship instead.

**3. What would break if this were deleted?** If the answer is "nothing observable" → delete it.

**4. Is this abstraction earning its keep?** Interfaces, factories, generic types, helpers — each costs cognitive overhead. If there's only one caller / one implementation, the abstraction is overhead, not value.

**5. Would I be embarrassed if a senior engineer outside the team read this?** If yes, fix it before merging.

### 3. Hunt for specific anti-patterns

These are the most common things to call out:

**Defensive cargo.** `if (!arg) throw` in a function whose caller is in the same file and obeys types. Strip it.

**Premature abstraction.** Interface with one impl. Abstract base with one subclass. `BaseHandler` / `BaseService` hierarchies. Replace with the concrete thing.

**Comment archaeology.** Comments restating the code, comments referencing JIRA tickets that no longer exist, "// TODO from 2022", commented-out code. Delete.

**Magic numbers.** `setTimeout(..., 30000)` — what is 30000? Make it a named constant if it's load-bearing, delete the timeout if it's not.

**Defensive nullables.** `string | null | undefined` on every field. Pick one or zero of them. Treating `null` and `undefined` as different states is almost always a bug.

**One-time helpers.** `function formatX(x) { return x.toUpperCase(); }` called once. Inline it.

**Stretched names.** `UserRepositoryServiceManagerFactory`. Each suffix doubles in pomp without halving the cognitive load. Rename to `UserStore` or just `users`.

**Half-finished features.** A function with three branches, two implemented, one returning `null` "for now". Fix or remove the branch.

**Dead code paths.** A try/catch where the catch can never fire. A switch with a default that never executes. Coverage tools can find these; eyeballs are faster.

**Synchronous "async".** A function declared `async` that doesn't await anything. Drop the keyword.

**Suspicious "configurability".** A function with 7 boolean parameters, of which 6 are always the same in every call. The "config" is fake.

**Double-state.** A piece of data stored in two places that have to be kept in sync. They will go out of sync. Pick one source of truth.

### 4. Output format

Don't write a wall of prose. Write a list. Each item:

- File + line range.
- The issue, in one sentence.
- The fix, in one sentence.
- Severity tag: `block`, `nice-to-have`, or `nit`.

Example:

```markdown
- `src/api.ts:120-125` — **block** — `SafeHandler` interface has only `RouteHandler` implementing it. Strip the interface, use the concrete class.
- `src/utils.ts:45` — **nice-to-have** — `formatNum(n)` is called once, inline it.
- `src/db.ts:8` — **nit** — the comment "// initialize the database" restates the code. Delete.
```

The user can act on each item independently.

### 5. End with an overall verdict

After the list, one paragraph: is the code shippable? If not, what's the load-bearing problem?

Be willing to say "ship it as-is" if it really is fine. The point of critique is calibration, not theater.

## Discipline

**Be specific.** "This is overengineered" is useless. "Lines 80–95 wrap a single fetch in three layers of indirection (Service → Adapter → Client) — collapse to a single async function" is useful.

**Be falsifiable.** Every claim should be checkable by reading the cited code. No "this feels off" without naming the line.

**Don't moralize.** Critique the code, not the author. "This function is too long" not "you wrote a too-long function".

**Don't gatekeep style.** Linter / formatter handles tabs vs spaces, brace placement, etc. Don't waste a critique on those — fix or note as `nit`.

**No copy-paste from a generic checklist.** Every project is different. A critique that could apply to any codebase isn't critique.

## What critique is not

- Not a rewrite. You're flagging issues, not solving them. Use `simplify` / `refactor` / `harden` to act.
- Not a personality test. Some code reads ugly but works fine. Don't conflate aesthetics with quality.
- Not approval theater. If everything is fine, say so in one sentence. Don't pad.
