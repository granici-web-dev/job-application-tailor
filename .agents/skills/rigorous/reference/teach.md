# rigorous teach

Interactive setup of `PRINCIPLES.md`, `STACK.md`, `TESTING.md`. **Don't synthesize these from the user's prompt alone — ask the questions, get answers, then write the files.**

Three documents, written in this order. Each is the seed of how all future code on this project will be written. Treat the answers as durable opinions, not suggestions.

## File 1 — PRINCIPLES.md (required)

Ask all of the following. Cluster questions sensibly so the user isn't bombarded — 4–5 batches of 2–3 questions each is the right cadence.

**A. Engineering posture**
1. What's the project's main risk: shipping too slow, shipping broken, or losing maintainability? Pick one and explain why.
2. Are you closer to "move fast, refactor later" or "design properly the first time"?
3. When tight on time: do you cut tests, skip code review, or ship with TODOs?

**B. Abstractions**
4. When do you extract a helper? After the second duplication, third, or never until pain forces it?
5. Are interfaces / typeclasses / abstract base classes welcome, or only after you have ≥2 concrete implementations?
6. Do you prefer composition or inheritance when a choice exists?

**C. Comments and naming**
7. Comments policy: zero by default / WHY only / liberal? (See engineering laws — default is zero, but the project may differ.)
8. Long descriptive names vs short familiar ones?
9. Are abbreviations (`usr`, `cfg`, `ctx`) acceptable?

**D. Error handling**
10. Where does validation belong: every function, public boundaries only, or only at user input?
11. On unexpected error: throw, return Result/Either, or log-and-continue?
12. Is logging part of business code, or only at infrastructure boundaries?

**E. Discipline**
13. Refactor as you go, in a separate PR, or only when explicitly scheduled?
14. Are TODOs allowed in committed code? With what discipline (issue link required, expiry date, etc.)?
15. Is generated code (codegen, scaffolding) ever modified by hand?

After collecting answers, write `PRINCIPLES.md` with one section per cluster. Each item is one or two crisp sentences stating the rule and the why. Example:

```markdown
## Abstractions

- **Rule of three.** Don't extract a helper until the third duplication. Two near-identical blocks beat one premature abstraction.
- **No interfaces with one impl.** Add an interface only when ≥2 concrete implementations exist. Until then, ship the concrete class.
```

## File 2 — STACK.md (recommended)

Optional but pushes future code toward the right defaults.

1. Languages and runtimes (with version pins).
2. Primary framework(s). Why this one over the obvious alternatives.
3. Database / persistence layer. Migrations tool.
4. Test runner. Assertion style. Snapshot testing posture.
5. Linter / formatter. Strictness level.
6. Build / bundler / package manager.
7. Deployment target.
8. Notable libraries you've committed to (e.g. `pg-boss` instead of Redis Bull) and the why.
9. Notable libraries you've REJECTED (e.g. "no GraphQL", "no ORMs unless we hit pain") and the why.

Write `STACK.md` as a short table for the choices and a "Decisions" section for the why-paragraphs. Anti-choices matter as much as choices — they prevent agent drift.

## File 3 — TESTING.md (recommended)

1. What's worth testing here? (Pure logic, integration with DB, HTTP endpoints, UI flows, all of the above?)
2. What's NOT worth testing? (Trivial getters, framework code, third-party SDKs, generated code?)
3. Mocking policy: real DB / mocks / hybrid? When does each apply?
4. Coverage target: a number, or "covered where it matters"?
5. How long should the full test suite take? What's the upper bound for an acceptable test?
6. Snapshot tests: yes / no / sparingly / forbidden?
7. Test layout: co-located with source, parallel `tests/` tree, or both?
8. Naming convention for test files / test cases.
9. Fixture / factory strategy.
10. End-to-end testing tool, if any.

Write `TESTING.md` with sections matching these answers. Include 1–2 example test names from the project that exemplify the conventions.

## How to run the conversation

1. **Read existing files first** if any of the three already exist — don't overwrite without reviewing what's there.
2. **Ask in clusters**, not 35 questions at once. Use 4–5 messages.
3. **Confirm your draft** before writing — paraphrase the user's answers and ask "did I get this right?"
4. **Write all three files in one final commit-style message**, ready for them to skim.

## After teach

1. Tell the user the three files are written and where.
2. Suggest they edit them directly any time the rules drift.
3. Suggest they commit them. They are durable engineering policy — meaningful diffs over time.
4. If the user invoked teach because another sub-command (e.g. `craft`) blocked on missing context, resume that command now.
