# rigorous architect

System-design review at the subsystem or whole-app level. The altitude is layers, modules, boundaries — not lines.

## When to invoke

- Considering a major rewrite.
- Adding a new layer (queue, cache, separate service).
- Onboarding a teammate who needs the mental model.
- A subsystem that has accumulated > 6 months of patches and feels off.

## The five questions

For the subsystem under review, answer:

### 1. What are the modules and their dependencies?

Draw the graph (mentally — actual diagrams optional). Each box is a module. Arrows are imports / calls.

Look for:
- **Cycles.** A → B → A is a smell. Either A and B are the same module, or one of them is in the wrong place.
- **God modules.** One module imported by everyone. Likely doing too much.
- **Spaghetti.** Every module imports every other. The boundaries aren't real.

### 2. Where do data and control flow?

Trace one common operation end to end. For an HTTP endpoint:
- Request arrives → which module handles auth?
- Which validates input?
- Which queries the DB?
- Which formats the response?

If the answer is "one big function," the layers aren't enforced — and that may be fine for a small app. State the choice openly.

If the answer is "the request goes through 7 layers, each one passing the same data downward," the layering is theatrical. Collapse.

### 3. Where do the abstraction lines fall?

Good lines:
- Process boundaries (HTTP, queue, file).
- Persistence (DB schema is the contract).
- Third-party integration (we mock the SDK at the seam).
- Cross-team contract (other team consumes our API; spec is the line).

Bad lines:
- "Manager" / "service" / "helper" classes that don't correspond to a real boundary.
- Layers added because a tutorial said so (Hexagonal / Clean / Onion architecture cargo).
- Interfaces with one impl.

### 4. What's the consistency story?

- **Single source of truth** — for each piece of state, what owns it? DB row? In-memory cache? Frontend state? Multiple sources will diverge.
- **Eventual vs strong** — if you have a queue or async pipeline, what's eventually consistent? Document the staleness window.
- **Schema as contract** — does the DB schema match the language types? Drift is a bug factory.

### 5. What's the failure model?

For each external dependency:
- What happens if it's down? Retry? Fail open? Fail closed? Queue and reprocess?
- What happens if it's slow? Timeout? Hedged request? Circuit breaker?
- What happens if it returns garbage? Validate? Pass through? Reject loudly?

Most "architecture" reviews die without ever asking these questions, and most production incidents come from the answers being implicit.

## Output format

A short doc, ~1–2 pages, with sections for each of the five questions. Diagrams optional but a tree of `apps/<app>/src/<module>` notation works.

End with **3 strengths** and **3 weaknesses**. Be willing to say a system is well-architected. Equally willing to say it's tangled. The goal is honest assessment, not balanced theater.

## Common findings to look out for

- **Premature microservices.** App split into 5 services on day 1, each owning a slice the team is still figuring out.
- **Late microservices.** Monolith with three teams stepping on each other.
- **Half-events.** A queue used for some flows but not others. Pick one.
- **DTO explosion.** Three nearly-identical types (`User`, `UserDTO`, `UserResponse`) for one entity. Collapse.
- **Implicit ordering.** Code that breaks if module A's import doesn't run before module B's. Make ordering explicit.
- **Singleton mutable state.** A module-level `let store` that everything reads/writes. Replace with explicit dependency or accept it openly as the architecture.

## Discipline

**No "best practice" appeals without reason.** "Use Clean Architecture" is not an argument. "The DB schema has 3 places to change for one logical update because we duplicated the model 3 times" — that's an argument.

**Cost the changes.** A migration plan is part of architecture review. "Refactor everything" is not a plan. "Move X module behind a queue, taking ~3 days, here are the risks" is.

**Don't over-engineer the recommendation.** If the system is fine, say so. The most common failure of architecture reviews is recommending grand restructures for systems that work.

**Match advice to scale.** A 3-person team with 50k LOC has different leverage than a 100-person team with 5M LOC. The same advice doesn't apply.

## What architect is not

- Not a green-field design exercise. The system exists. Work with what's there.
- Not a moral judgment on past decisions. Past decisions were made under different constraints. Move forward.
- Not implementation. The output is a doc. Use `craft` / `refactor` to act on it.
