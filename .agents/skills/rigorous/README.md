# rigorous

> The engineering counterpart of [`impeccable`](https://github.com/anthropics/skills/tree/main/skill-creator).
> One skill, 13 commands, 3 standards files.

Disciplined code, low-ceremony, opinionated. Setup writes your team's engineering posture once (`PRINCIPLES.md`, `STACK.md`, `TESTING.md`). Every sub-command after that reads them so output never drifts from your team's standards.

## Install

```bash
npx skills add CoRLab-Tech/skills@rigorous
```

Part of the [`CoRLab-Tech/skills`](https://github.com/CoRLab-Tech/skills) monorepo. Browse adjacent skills there.

## Use

Inside Claude Code or any harness that supports skills:

```text
/rigorous                       Show the command menu
/rigorous teach                 Set up PRINCIPLES.md / STACK.md / TESTING.md
/rigorous shape <feature>       Plan a feature before writing any code
/rigorous craft <feature>       Implement after the shape is approved
/rigorous tdd <feature>         Strict red-green-refactor cycle
/rigorous critique <target>     Acid review — what's complicated, what can be cut
/rigorous audit <target>        Technical audit (perf, security, deps, races)
/rigorous architect <subsystem> System design review
/rigorous simplify <target>     Strip ceremony, dead code, premature abstraction
/rigorous harden <target>       Boundary validation, edge cases, observability
/rigorous refactor <target>     Restructure without changing behavior
/rigorous debug <issue>         Systematic root-cause investigation
/rigorous optimize <target>     Profile-driven performance work
```

## The three standards files

`teach` writes these at the root of your repo:

| File | Required | Holds |
|---|---|---|
| `PRINCIPLES.md` | yes | Engineering posture — abstraction policy, comments policy, error handling philosophy, what to optimize for, what to refuse |
| `STACK.md` | recommended | Languages, frameworks, libraries, version pins, and the why behind each choice |
| `TESTING.md` | recommended | What's worth testing, what isn't, mocking policy, coverage posture |

Every sub-command reads these on every run via `scripts/load-context.mjs`. If `PRINCIPLES.md` is missing, sub-commands refuse to run until `teach` is invoked.

## Engineering laws (always apply)

Six rules every command honors regardless of what's in your standards files:

1. **Match the change to the task.** A bug fix changes the buggy line and nothing else.
2. **Trust internal code, validate boundaries.** No defensive null checks where the type system already validated.
3. **Default to zero comments.** Code is the documentation. WHY-comments only.
4. **No half-finished work.** No feature flags / TODO without an issue link / functions with stubbed branches.
5. **The slop test.** If a senior engineer could say "AI wrote that" without doubt, rework it.
6. **Reversibility before risk.** Confirm before destructive operations.

## Landing page

<https://rigorous.corlab.tech> — full documentation, examples, and comparisons to other code-quality skills.

## Compared to

| | rigorous | other code skills |
|---|---|---|
| Install | one package, 13 commands | several packages across orgs |
| Standards | three durable files | global system prompts only |
| Gates | shape required for craft / tdd | optional or absent |
| Engineering laws | baked into every command | depends on which skill you invoke |

Honest take: [`obra/superpowers`](https://github.com/obra/superpowers) and [`mattpocock/skills`](https://github.com/mattpocock/skills) have excellent individual skills. Use them too. `rigorous` is for teams that want one cohesive frame over fourteen separate packages.

## License

Apache 2.0. See [`LICENSE`](./LICENSE).
