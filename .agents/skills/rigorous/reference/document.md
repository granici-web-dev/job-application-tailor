# rigorous document

Reverse-engineer `PRINCIPLES.md`, `STACK.md`, `TESTING.md` from an existing codebase. Use when the project is already mature and you don't want to interrogate the user — read the code.

## When to use

- Codebase is non-trivial (>~5 source files).
- The user wants standards documents but doesn't want a 30-question interview.
- Existing `PRINCIPLES.md` etc. are stale and need a refresh from the current code.

## Process

### 1. Map the codebase

Read these signals before writing anything:
- `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` for stack and pinned versions
- `tsconfig.json` / `.eslintrc` / `pyproject.toml` strictness flags for posture
- `README.md` if present
- 8–15 representative source files across modules (not just one)
- Test files (file names, framework imports, average length, presence of mocks)
- CI config (`.github/workflows/`, `.gitlab-ci.yml`) for test/lint/deploy commands
- Migration files for DB conventions
- Recent commit messages — look for the style and scope of changes

### 2. Infer STACK.md

Direct from manifests + `tsconfig` / equivalent. Pin versions exactly as found. Note libraries with explicit comments or non-default config — they're committed choices.

For "decisions" / "anti-choices", look for:
- Libraries you'd expect but don't see (no Redis with a queue → likely a "no Redis" decision; no ORM with a DB → likely a "no ORM" decision)
- Comments in source explaining choices
- README sections justifying tooling

### 3. Infer PRINCIPLES.md

Read carefully. Look at:

**Comments density.** Sample 10 files. Are they comment-heavy or comment-sparse? Default to whatever's actually in the code.

**Abstractions used.** Count interfaces / abstract classes / generics. If they're rare and concrete classes dominate, the rule is "concrete first". If interfaces with one implementation exist, the project tolerates them.

**Error handling.** Find 3–5 places that handle errors. Is it `try/catch` everywhere or only at boundaries? Are errors thrown, returned as values, or logged-and-swallowed?

**Validation.** Search for input validation — Zod, manual `if (!x)`, or none. If only at HTTP boundaries, that's the policy.

**File length.** Are files small and many, or few and large? That's a decision.

**Naming.** Look at variable names. Long? Short? Abbreviations? Greek-letter-style (`i`, `j`, `n`)?

**TODOs.** Count `TODO` / `FIXME` / `XXX`. Density tells you the discipline.

**Test posture.** Is there a `tests/` dir? Co-located? Both? Mocks heavy or absent? Real DB used?

Write `PRINCIPLES.md` quoting the patterns you observed. Where the codebase is internally inconsistent (very common), pick the dominant pattern and note the minority as the exception.

### 4. Infer TESTING.md

From actual test files:
- Framework (Vitest, Jest, pytest, Go test, …)
- Average test length
- Mock-vs-real-DB ratio (look for test setup using actual `pool` / Testcontainers)
- Coverage of business logic vs handlers vs utility functions
- Snapshot test count
- Suite total runtime if reported in CI

If there are no tests at all, write a short `TESTING.md` saying so plainly and noting "default to: <reasonable defaults given the stack>" rather than inventing imagined conventions.

### 5. Confirm with the user

Before writing the files: produce a one-page summary of what you observed and intend to write. Ask "anything wrong here?" and let them correct before committing.

After confirmation, write all three files. Date the header so future runs know when the snapshot was taken. Suggest the user re-runs `document` whenever the codebase posture shifts materially.

## What document is not

- Not a code review. Don't critique the project — just describe it.
- Not aspirational. Document what is, not what should be. The user can edit toward what they want.
- Not silent. State your inferences openly so the user can correct them.

## Output format

The three files have the same structure as `teach` produces — reuse those templates so a project that runs `teach` once and `document` later doesn't end up with two incompatible formats.
