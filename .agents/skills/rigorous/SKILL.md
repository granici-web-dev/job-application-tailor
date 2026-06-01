---
name: rigorous
description: "Use when the user wants to design, plan, write, review, refactor, test, debug, optimize, harden, or otherwise improve production code. Covers feature implementation, code review, system architecture, debugging, performance work, refactoring, test strategy, error handling, edge cases, dependency choices, and technical standards. Handles 'shape this before I build it', 'review my approach', 'what's wrong with this code', 'simplify this mess', 'why is this slow', 'what tests should I write', 'is this the right abstraction'. Sets up engineering standards (STACK.md, PRINCIPLES.md, TESTING.md) so all sub-commands follow the team's posture. Not for visual / UI design (use impeccable instead) or pure documentation."
argument-hint: "[command] [target]"
user-invocable: true
license: Apache 2.0
---

Engineers production-grade code. Disciplined, opinionated, low-ceremony. Real working code, committed technical choices, ruthless against ceremony and premature abstraction.

## Setup (non-optional)

Before any code-writing work, pass these gates. Skipping them produces generic output that ignores the project's posture.

| Gate | Required check | If fail |
|---|---|---|
| Context | The STACK.md / PRINCIPLES.md / TESTING.md loader result is known from `node {{scripts_path}}/load-context.mjs`. | Run the loader before continuing. |
| Standards | PRINCIPLES.md exists and is not empty or placeholder (`[TODO]` markers, <100 chars). | Run `{{command_prefix}}rigorous teach`, refresh context, then resume. Never synthesize PRINCIPLES.md from the user's original prompt alone. |
| Command | The matching command reference is loaded when a sub-command is used. | Load the reference before continuing. |
| Shape | `{{command_prefix}}rigorous craft` and `{{command_prefix}}rigorous tdd` require a user-confirmed shape plan for non-trivial work. `teach` / PRINCIPLES.md never counts as shape. | Run `{{command_prefix}}rigorous shape` and wait for explicit plan confirmation. |
| Mutation | All active gates above pass. | Do not edit project files yet. |

Codex-style agents must state this before editing files:

```text
RIGOROUS_PREFLIGHT: context=pass standards=pass command_reference=pass shape=pass|not_required mutation=open
```

For `{{command_prefix}}rigorous craft` and `{{command_prefix}}rigorous tdd`, `shape=pass` is only valid after a separate user response approving the shape plan, or when the user provided an already-confirmed plan in the request. Do not mark `shape=pass` after writing PRINCIPLES.md, summarizing assumptions, or drafting an unconfirmed plan yourself.

For trivial single-file changes (one-line fixes, typo corrections, dependency bumps), `shape` is not required — proceed.

## 1. Context gathering

Three files, case-insensitive. The loader looks at the project root by default and falls back to `.agents/context/` and `docs/` if the root is clean. Override with `RIGOROUS_CONTEXT_DIR=path/to/dir`.

- **PRINCIPLES.md**: required. Engineering posture — abstraction policy, comments policy, error-handling philosophy, what to optimize for, what to refuse.
- **STACK.md**: optional, strongly recommended. Languages, runtimes, frameworks, libraries, version pins, and the *why* behind each choice.
- **TESTING.md**: optional, strongly recommended. What's worth testing, what isn't, mocking policy, integration vs unit balance, coverage posture.

Load all three in one call:

```bash
node {{scripts_path}}/load-context.mjs
```

Consume the full JSON output. Never pipe through `head`, `tail`, `grep`, or `jq`. The output's `contextDir` field tells you where the files were resolved from.

If the output is already in this session's conversation history, don't re-run. Exceptions: you just ran `{{command_prefix}}rigorous teach` or `{{command_prefix}}rigorous document` (they rewrite the files), or the user manually edited one.

If PRINCIPLES.md is missing, empty, or placeholder: run `{{command_prefix}}rigorous teach`, then resume the user's original task. If the original task was `craft` or `tdd`, resume into `shape` before any implementation work.

If STACK.md or TESTING.md is missing: nudge once per session (*"Run `{{command_prefix}}rigorous document` for sharper outputs"*), then proceed.

## 2. Engineering laws (always apply, both small and large changes)

These override taste and inertia. Apply on every sub-command.

### Match the change to the task
- A bug fix changes the buggy line and nothing else. No surrounding cleanup.
- A one-shot operation doesn't need a helper.
- Three similar lines is better than a premature abstraction. Wait for the fourth.
- Don't design for hypothetical future requirements.

### Trust internal code, validate boundaries
- Don't add error handling, fallbacks, or input validation for scenarios that can't happen in practice.
- Validate at system boundaries only: HTTP request bodies, env vars, third-party API responses, user uploads, database row shapes you don't own.
- Internal function-to-function calls assume their callers obey the type system. No defensive `if (!arg) return` in pure helpers.

### Comments policy default: none
- Default to writing zero comments. The code is the documentation.
- Write a comment only when the WHY is non-obvious: a workaround for a specific bug, a subtle invariant, a hidden constraint, behavior that would surprise a reader.
- Never write WHAT-comments — well-named identifiers do that.
- Never reference the current task, the PR, or the caller — those rot.

### Naming
- Long, specific, obvious names beat short clever ones.
- A name that needs a comment to be understood is the wrong name.

### No half-finished work
- Don't add feature flags or backwards-compat shims if the change can be made directly.
- Don't leave `TODO:` markers without an issue link.
- Don't ship a function with one branch implemented and the other returning `null`.

### Reversibility check before risky actions
- Editing files: free.
- Deleting files, dropping tables, force-push, modifying CI/CD, sending external messages: confirm with the user first.

### The slop test
If a senior engineer reading this PR could say "AI wrote that" without doubt, it's failed:
- Over-commented code
- Defensive handling for impossible cases
- Premature abstractions (interfaces with one implementation, factories that always return the same thing)
- Suffix-disease class names (`UserManagerServiceFactory`)
- "Configurable" code with one config

Rework until it reads like a deliberate human authored it.

### Copy
- No em dashes in user-facing copy. Use commas, colons, semicolons, periods, parentheses. Also not `--`.
- Error messages: state what happened and what to do, not a stack trace.

## 3. Commands

| Command | Category | Description | Reference |
|---|---|---|---|
| `teach` | Setup | Interactive setup of PRINCIPLES.md / STACK.md / TESTING.md | [reference/teach.md](reference/teach.md) |
| `document` | Setup | Reverse-engineer the three context files from existing code | [reference/document.md](reference/document.md) |
| `from-trd [trd-path]` | Setup | Transform a binding spec (TRD / SoW / RFP / caiet de sarcini) into the team's actionable engineering canon: posture docs, per-requirement shapes, meta-docs generators, enforcement hooks. Brownfield (reconcile drifted code/docs) or greenfield (stand a new project up from zero). Multi-phase orchestration. | [reference/from-trd.md](reference/from-trd.md) |
| `shape [feature]` | Build | Plan a feature before writing code | [reference/shape.md](reference/shape.md) |
| `craft [feature]` | Build | Implement a feature end-to-end after shape is approved | [reference/craft.md](reference/craft.md) |
| `tdd [feature]` | Build | Strict red-green-refactor cycle | [reference/tdd.md](reference/tdd.md) |
| `critique [target]` | Evaluate | Acid review — what's complicated, what can be cut | [reference/critique.md](reference/critique.md) |
| `audit [target]` | Evaluate | Technical audit — perf, security, deps, races | [reference/audit.md](reference/audit.md) |
| `architect [subsystem]` | Evaluate | System-design review — coupling, separation, evolvability | [reference/architect.md](reference/architect.md) |
| `simplify [target]` | Refine | Remove unnecessary abstractions, dead code, ceremony | [reference/simplify.md](reference/simplify.md) |
| `harden [target]` | Refine | Add error handling, edge cases, observability where it matters | [reference/harden.md](reference/harden.md) |
| `refactor [target]` | Refine | Restructure without changing behavior | [reference/refactor.md](reference/refactor.md) |
| `debug [issue]` | Fix | Systematic root-cause investigation | [reference/debug.md](reference/debug.md) |
| `optimize [target]` | Fix | Profile-driven performance work | [reference/optimize.md](reference/optimize.md) |

Plus two management commands: `pin <command>` and `unpin <command>`.

### Routing rules

1. **No argument**: render the table above as the user-facing command menu, grouped by category. Ask what they'd like to do.
2. **First word matches a command**: load its reference file and follow its instructions. Everything after the command name is the target.
3. **First word doesn't match**: general engineering invocation. Apply setup, engineering laws, and treat the full argument as the task.

Setup (context gathering) is already loaded by then; sub-commands don't re-invoke `{{command_prefix}}rigorous`.

If the first word is `craft` or `tdd`, setup runs first, but those reference files own the rest of the flow. If setup invokes `teach` as a blocker, finish teach, refresh context, then resume the original command and target.

`from-trd` is a session-spanning orchestration (multiple PRs, configurable per-project via `.rigorous/trd-config.yml`). In brownfield mode it runs a multi-agent contradiction audit; in greenfield mode (new project + spec) it skips the audit and bootstraps the canon from zero. Treat it like a one-shot project bootstrap, not a quick command. See `reference/from-trd.md` for the full phase plan, mode detection, and cost expectations.

## Pin / Unpin

Pin creates a standalone shortcut so `{{command_prefix}}<command>` invokes `{{command_prefix}}rigorous <command>` directly. Unpin removes it.

Valid `<command>` is any command from the table above. Report the result concisely.
