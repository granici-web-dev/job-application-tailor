# PRINCIPLES.md — Job Application Tailor

Engineering posture for this project. These are durable opinions, not suggestions. Every change, small or large, follows them.

## Posture

- **Correctness is the thing to protect.** This tool feeds a real job hunt. A silently-wrong CV, a fabricated skill, or a corrupted tracker is the worst outcome there is. When in doubt, fail loudly rather than produce a plausible-but-wrong document.
- **Design the boundaries before coding the slice.** Think through the seams between pipeline steps (fetch, analyze, tailor, render, track) before implementing them. We'd rather get the contracts right once than hack a vertical slice and rewrite it.
- **Under time pressure, ship annotated TODOs.** Tests and self-review stay. When something has to give, leave a TODO that states what's missing and why, and ship the working part.

## Abstractions

- **Rule of three.** Don't extract a helper until the third duplication. Two near-identical blocks beat one premature abstraction.
- **No interface until a second implementation exists.** No Protocols, ABCs, or "pluggable" indirection for the pipeline steps until there's a real second implementation. Ship the concrete function or class. One fetcher, one renderer, one tracker until reality demands more.
- **Don't design for hypothetical futures.** Build for the SPEC in front of us, not the feature we might want.

## Comments and naming

- **Comments: WHY only.** Default to zero comments. Write one only when the reasoning is non-obvious: an ATS quirk, a workaround for a specific site or library bug, a subtle invariant. Never restate what the code does.
- **Long, explicit names.** `tailor_cv_for_job`, `sanitize_company_folder_name`, `extract_job_text`. No abbreviations (`cfg`, `ctx`, `usr`). A name that needs a comment to be understood is the wrong name.

## Error handling

- **Validate at boundaries only.** HTTP request bodies, env vars (`ANTHROPIC_API_KEY`), LLM responses, fetched HTML, and the user's `profile/` files get validated. Internal function-to-function calls trust the type system: no defensive `if not arg` in pure helpers.
- **Raise specific exceptions with clear messages.** On an unexpected failure, raise an exception that states what happened and what to do (see SPEC §8). The CLI and API layers translate exceptions into clean user-facing messages. Never swallow an error or return a silent `None` in place of a result.
- **Don't fabricate.** The LLM steps never invent experience, skills, titles, or dates. If the model returns content not grounded in `master_cv.md`, that's a bug, not a feature. Guardrails for this live in the prompts and in the assembly code, not in hope.

## Logging

- **Log at the orchestrator and external calls.** The pipeline orchestrator and each external boundary (fetch, Anthropic API, PDF render, Excel write) log what they're doing. Pure helpers stay quiet. A CLI run should read as a clear sequence of steps, not a firehose.

## Discipline

- **TODOs are allowed, but must say what and why.** No bare `TODO`. Write `TODO: add Playwright fallback for JS-rendered pages (LinkedIn returns empty body)`. A reader should know the gap and the reason without asking.
- **Refactor opportunistically, in scope.** Clean up code you're already touching when it helps the current change. Don't open unrelated cleanup inside a feature change.
- **No half-finished branches.** Don't ship a function with one path implemented and the other returning `None`. If a path isn't built yet, raise a clear "not implemented" error or gate it behind an explicit flag.

## Reversibility

- Editing files is free. Deleting files, rewriting the tracker schema, force-pushing, or changing Docker/CI requires a heads-up first.
