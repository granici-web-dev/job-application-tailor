# rigorous from-trd

Take an externally-authored binding specification (a "caiet de sarcini", TRD, SoW, RFP, or similar) and transform it into the team's actionable engineering canon: posture docs, per-UC shapes, meta-docs generators, and enforcement hooks. The output is a repo where every requirement in the spec has a traceable home, every rule lives in exactly one place, and stale-ness becomes structurally impossible.

This is an orchestration command. It runs an audit, asks for one architectural decision (the Constitutional Map), then drives a series of focused PRs that each go through the standard shape → craft → critique loop.

It runs in one of two modes — **brownfield** (the default: existing code and docs drifted from the spec, reconcile them) or **greenfield** (a binding spec for a project that doesn't exist yet, stand the canon up from zero). Phase 0 detects which; see [Two modes](#two-modes-brownfield-and-greenfield).

## When to invoke

- You inherited a project where a binding spec is sitting beside code that drifted from it.
- A new tender / contract drops a multi-hundred-page TRD and you need to turn it into shape-able work.
- A new tender / contract drops a TRD for a project that doesn't exist yet, and you need to stand up the repo's engineering canon from zero (greenfield track).
- A repo's docs grew organically and contradict each other (e.g., the same rule stated three ways across three files).
- The team uses CLAUDE.md / AGENTS.md / ARCHITECTURE.md but nobody knows which one owns a given rule.

## Skip for

- Single-page specs that fit in one shape.
- Projects where the team is happy with existing docs.
- Greenfield with *no* binding spec yet — use `teach` + `shape` instead. (Greenfield *with* a spec is in scope: see the greenfield track.)

## Pre-flight (gates)

Same as the rest of rigorous: `PRINCIPLES.md` must exist (run `teach` first if it doesn't). The other context files (`STACK.md`, `TESTING.md`) help but don't block.

Additionally, `from-trd` reads a per-project config at `.rigorous/trd-config.yml`:

```yaml
trd_path: docs/<spec-filename>.md
trd_language: ro           # ro | en | ru — binding spec stays in this language verbatim
uc_header_regex: '^### (UC\d{2,3}) — (.+)$'   # how to find requirements in the spec
shape_filename_pattern: 'shape-uc-{nn}-{slug}.md'
posture_docs:
  workflow: AGENTS.md         # "how we work"
  architecture: ARCHITECTURE.md  # "how the system looks"
  stack: STACK.md
  testing: TESTING.md
  principles: PRINCIPLES.md
  design: DESIGN.md           # optional, FE-heavy projects
informational_marker: 'în scopuri informative'   # spec-specific phrase marking out-of-scope UCs
docs_generator_outputs:
  - docs/status.md
  - docs/shapes-index.md
  - docs/roadmap.md
pr_gate:
  app_src_prefix: apps/        # a change under here = "app functionality delivered" → requires an e2e test, no mocks
  frontend_prefix: apps/web/   # a change under here → requires a screenshot in the PR description
  main_branch: main
```

If the config is absent, the command interviews the user for these fields and writes it. Re-running with the file present skips that interview.

## Two modes: brownfield and greenfield

`from-trd` runs in one of two modes. Phase 0 detects which; the user can override.

**Brownfield (default)** — the repo already has code and docs that drifted from the spec. This is the reconciliation case the eight-phase plan below was written for: audit contradictions, sync the architecture doc to live code, consolidate duplicated rules, clean an existing shape catalog. Detect when any of these hold: a posture doc (`PRINCIPLES.md` or equivalent) exists, the repo contains app code under `apps/` / `src/` / `libs/`, or `docs/` holds more than the binding spec.

**Greenfield** — a binding spec for a project that doesn't exist yet: an empty or freshly `git init`-ed repo, no posture docs, the spec as the only substantive document. There is nothing to reconcile. The contradiction audit has one clean spec to chew on, there is no live code to sync a doc against, and there is no existing shape catalog to clean — so the full eight-phase plan would burn the ~500k–1M-token audit on empty phases. Detect when all hold: no posture docs, no app code, and the only docs are the spec(s). When detected, run the **greenfield track** below in place of Phases 1, 3, 5, 7, 8.

This supersedes the old "pure greenfield → use `teach` + `shape`" guidance, which now applies only to greenfield with *no* spec. Greenfield *with* a binding spec is exactly what the greenfield track is for: hand it the TRD and it lays down the full engineering canon from zero.

### Greenfield track

Each step is still one focused PR through shape → craft → critique. Steps G2 and G5 reuse the brownfield phases verbatim; the rest replace reconciliation work with from-scratch authoring.

- **G0 — Bootstrap.** `git init` if needed. Convert the binding spec(s) to markdown under `docs/` (`textutil` or `pandoc` for `.docx`). Write `.rigorous/trd-config.yml`, setting `uc_header_regex` to the spec's *actual* requirement numbering — a TRD that codes requirements `CF-1.1`, `CF-2.3` needs `^CF-\d+\.\d+`, not the `UC` default, and named user flows (`4.1 …`) map to use cases. Extract the requirements inventory (count, IDs, titles) and the spec's own open-questions / assumptions list (e.g. an `OQ-1…OQ-n` annex). Output: a one-page inventory + open-questions summary the user signs off on. Replaces Phase 0 and the Phase 1 audit.
- **G1 — Posture from spec, then teach the gaps.** Derive `STACK.md` from the spec's recommended-stack section, marking each choice `[from spec]` vs `[team default]`. Seed `PRINCIPLES.md` and `TESTING.md` from the spec's non-functional and acceptance sections. Run `teach` only for what the spec leaves open. Never invent posture the spec already states. Satisfies the `PRINCIPLES.md` pre-flight gate.
- **G2 — Constitutional Map.** Same as brownfield Phase 2, but each concern's owner doc is authored fresh, not reconciled. Spec concerns (data model, RBAC matrix, state machines, API contract, NFR values) each get a single canonical owner.
- **G3 — Architecture skeleton (docs, not code).** Write `ARCHITECTURE.md` from the spec's component / deployment description and lay down the directory skeleton the spec implies — one folder per logical service / module, plus the data model and API surface. Docs and structure only; `from-trd` never writes production code.
- **G4 — Per-requirement shapes.** Create one shape stub per requirement group / use case, pre-filled with the spec's acceptance criteria (Given/When/Then where provided) and the open questions that block it. These are the planning docs the engineer completes during `craft`. Replaces Phase 5; Phase 8 JIT does not apply (no phase-style shapes exist yet).
- **G5 — Meta-docs generator + enforcement hooks.** Identical to brownfield Phases 6 and 9 — the generator and the pre-PR / communication hooks apply unchanged.

Skipped in greenfield: Phase 1 (audit — replaced by G0's inventory + open-questions pass), Phase 3 (no live code to sync), Phase 7 (no existing prose to translate; the spec stays in its `trd_language`), Phase 8 (JIT extraction).

## Process

The phases below are the **brownfield** plan. In greenfield mode they collapse to the greenfield track above.

Eight phases. Each completes a focused PR. Each PR follows the full rigorous loop (shape → craft → critique → review-ready) and posts a Telegram / equivalent ping at PR open if hooks are wired.

### Phase 0 — Bootstrap

1. Verify pre-flight gates. **Detect mode (brownfield vs greenfield) per [Two modes](#two-modes-brownfield-and-greenfield); if greenfield, switch to the greenfield track and skip the brownfield phases below.**
2. Load or create `.rigorous/trd-config.yml`.
3. Read the binding spec; extract the requirements inventory using `uc_header_regex` (count, IDs, titles).
4. Detect any informational-only requirements via `informational_marker` (these get an `ℹ external` status downstream, no shape required).
5. Survey existing docs: list what's already in the repo, classify by candidate ownership (workflow / architecture / stack / etc.).

Output: a single-page summary the user signs off on. No file edits yet.

### Phase 1 — Audit (multi-agent)

6. Dispatch a Workflow with seven parallel agents, each on a distinct dimension. The agents read the docs in scope and return findings as structured JSON. After the fan-out, every finding is passed through an adversarial verifier (a second agent that reads the cited files and confirms the contradiction is real).

The seven dimensions:

| Dimension | What it looks for |
|---|---|
| `tech-contradictions` | Conflicting tech choices, port numbers, service counts, schema names, auth flows across STACK / ARCHITECTURE / shapes |
| `process-strictness` | Rules stated as suggestions where they should be mandatory; duplicated workflow definitions; missing strictness in commit/PR/test gates |
| `frontend-coherence` | DESIGN.md vs PRODUCT.md vs ui-shape.md contradictions; design system reuse vs local wrapper; token/font/spacing drift |
| `cross-ref-integrity` | Broken file refs, dead section pointers, UC IDs cited that don't exist in spec |
| `spec-vs-shape` | Shape declares X, spec requires Y; UCs missing from shape catalog; UC numbering renamed inconsistently |
| `structure-hygiene` | Scratch files at repo root; duplicate paragraphs across files; two parallel organization schemes; stale meta-docs |
| `ambiguity-gaps` | Terms used with multiple meanings; "see X" without a concrete link; conventions implicit but not written; missing answers for common edge cases |

The Workflow uses `model: opus` for both finder and verifier agents — anything weaker produces noise. Verifier is biased toward keeping a finding (better one false positive than missing a real contradiction).

7. Present the prioritized findings (P0 / P1 / P2) to the user. P0s are contradictions that produce wrong code or behavior; P1s are ambiguities a reader will trip on; P2s are hygiene.

Output: a written audit report committed to `docs/audit-<date>.md` (optional, controlled by user) or just consumed inline.

### Phase 2 — Constitutional Map

8. Propose a single-owner-per-concern table based on the audit + the posture_docs from the config. Each row is `concern → canonical owner doc → other docs treat by link-only`. Standard rows include:

- "How we work" → workflow doc (commit discipline, naming, shape→craft→critique cycle, LOC thresholds, slash commands).
- "How the system looks" → architecture doc (services, ports, schemas, flows).
- "Tech pinned + rationale" → stack doc (no version overrides in shapes).
- "Read-order at session start" → workflow doc §0.
- "Project state" → generated meta-docs (status / shapes-index / roadmap).
- "Terminology glossary" → workflow doc §Glossary.
- "Canonical design system" → design doc; STACK/ARCHITECTURE only refer.
- "Canonical shape catalog" → per-UC + per-ops filename pattern; phase-style shapes deprecated.

9. User ratifies, edits, or rejects. The map is committed as `docs/shape-ops-docs-consolidation.md` (the master shape) and becomes the contract for the remaining phases.

### Phase 3 — Sync architecture with live code (PR-1)

10. Read all code that backs the posture doc claims: app entrypoints, env schemas, migration filenames, auth implementation, design-system linkage. Compute the diff between architecture-doc claims and code reality. Fix the doc to match code. Resolve every P0 from the audit that lives in the architecture doc.

Each architecture mismatch becomes a one-line edit, cited in the commit message body.

### Phase 4 — Posture single-owner (PR-2)

11. Move every duplicated rule into its canonical owner per the Constitutional Map. Convert duplicate sections in CLAUDE.md / session-bootstrap.md / pr-verification-checklist.md (or equivalents) into pointers-with-link. Reduce CLAUDE.md to a thin entry-point.

12. Resolve numeric divergences (LOC thresholds, retention windows, cap values) to a single canonical value. Update any enforcing hooks to match.

### Phase 5 — Shape catalog cleanup (PR-3)

13. For each shape file:
    - If it's per-UC and matches the canonical pattern: keep.
    - If it's per-phase or per-iteration and covers UCs that overlap with per-UC shapes: absorb the overlapping content into the per-UC shape, add `> Superseded by: <canonical>` at the start of the absorbed section, and mark the phase shape `PARTIALLY SUPERSEDED` in its header.
    - If a phase shape covers UCs with no per-UC shape: leave it in place (JIT extraction, see Phase 8).

14. Move clearly-scratch files (root-level dumps, snapshots, debug output) into `docs/.archive/` with a README explaining what each is. Rename misnamed files (e.g., a tender metadata file misnamed `overview.md`).

### Phase 6 — Meta-docs generator (PR-4)

15. Generate `tools/scripts/refresh-docs-status.mjs` from the embedded template (below). The script reads:
    - Binding spec (per `trd_path` + `uc_header_regex`)
    - Shape files (filename glob)
    - GitHub PR state (`gh pr list --json ...`)
    - Caiet-informational marker (skips out-of-scope requirements)

Outputs three markdown files per `docs_generator_outputs`. Each output carries a SHA1(body) header so manual edits are detected on next run. The script supports `--check`, `--force`, and a `pnpm docs:refresh` wrapper.

16. Add the three generated files to `.prettierignore` so prettier doesn't reformat tables and invalidate the SHA1 on commit.

### Phase 7 — Translation pass (PR-6, optional, split into 3 sub-PRs)

If the team's policy is "code AND prose docs in English" but the repo has prose in another language, run a translation pass. Three sub-PRs to keep diffs reviewable:

17a. Root posture docs + ops docs (PRINCIPLES / STACK / TESTING / DESIGN / PRODUCT / PR-checklist / session-bootstrap). Update `R3` rule in the workflow doc to explicitly state "code AND prose docs in target language".

17b. All shape docs in bulk (mechanical batch). Run in parallel via 2–3 sub-agents partitioned by file count. Each agent applies the same preservation rules:

- Code samples, identifiers, file paths, fenced blocks: verbatim.
- Binding-spec citations: keep original language in italics + brief gloss in target language right after.
- UI copy strings (the literal strings that will appear in the product UI): verbatim — they're i18n source.
- Proper names of external systems: verbatim.

17c. The largest single FE shape doc (e.g., `ui-shape.md`). Light-touch only — UI mockups stay verbatim; only narrative prose translates. Optional screenshot spot-check after.

Each sub-PR uses a 1:1 translation glossary committed to the sub-shape to enforce consistency across files.

### Phase 8 — JIT extraction policy (PR-5)

18. The remaining phase-style shapes still cover requirements without dedicated per-UC shapes. Don't pre-emptively split them. Codify the rule in the workflow doc §Shape naming:

> A per-requirement shape is created the first time an engineer plans implementation work on that requirement. Until then, the existing phase shape is canonical. When extracting: copy the section into the new shape, link back with `> Superseded by: <canonical>` from the phase shape's section header.

Phase shapes move to `.archive/` only after every requirement they cover has a per-requirement shape — not before.

### Phase 9 — Enforcement hooks (PR alongside Phase 6)

19. Install the **PR gate** in two layers, concretized from the templates and committed as project tooling. The gate blocks a PR unless all of these hold:

- **`rigorous critique` ran** on the diff (ticked in the PR description).
- **App functionality delivered** (any `pr_gate.app_src_prefix` source change) ships an **e2e test of that functionality, with no mocks** — a real-services test. The gate requires an e2e file in the branch and statically scans it for mock APIs (`vi.mock`, `jest.mock`, `nock`, `sinon`, `mockDeep`, …); finding any fails the gate.
- **Frontend touched** (any `pr_gate.frontend_prefix` change) includes a **screenshot in the PR description**, so the visual result is visible on the PR.
- The generated docs canon is up to date (`pnpm docs:check`).

Two layers, because a written rule isn't enforcement:

- **GitHub Action** (`.github/workflows/pr-gate.yml`, from `pr-gate.yml.tmpl`) — authoritative and unbypassable; runs on every PR open/edit/sync, reads the PR body + changed files via `check-pr-gate.mjs`. Pair it with a `pull_request_template.md` (from `pull-request-template.md.tmpl`) holding the checklist + screenshot section, and require the check in branch protection.
- **Local Claude Code hook** (`.claude/settings.json`, from `claude-settings.json.tmpl`) — a committed `PreToolUse` hook (`hook-block-pr.sh`) that intercepts `gh pr create` and runs `check-pre-pr.sh` (the file-based half) before the PR is even created. Exit 2 blocks the call.

The rule engine (`check-pr-gate.mjs`) is shared by both layers, so they never diverge. Scope = since last `git checkout -b`; diffs limited to `tools/` / `docs/` / `.github/` / `.claude/` are exempt from the e2e/screenshot rules.

20. **Communication trigger** (optional): at Stop event, if the assistant's final turn contains attention-needed phrases ("waiting for approval", "go ahead?", explicit ask) AND no notification has been sent, block the stop. Forces the user-notification discipline mechanically. Wire this into per-user `.claude/settings.local.json` (not committed) so contributors without notification credentials aren't blocked. Document the wire-up in `tools/scripts/HOOKS.md`.

## Output discipline

Each phase produces exactly one focused PR. Each PR:

1. Has a sub-shape committed under `docs/shape-ops-docs-consolidation-prN.md` listing files modified + test plan + tradeoffs + open questions.
2. Runs `/rigorous critique` on the staged diff before commit. Block-level findings fixed pre-commit; nice-to-haves listed in PR description.
3. Cites the sub-shape in the commit body per the shape-ref hook.
4. Posts a notification at PR open if the trigger hook is configured.

The series typically lands as ~8 PRs over the working session.

## Cost discipline

The Phase 1 audit costs ~500k-1M output tokens (seven Opus auditors + verifiers). Run it once per project. Don't re-run on small follow-ups — for incremental work, manually invoke `audit` on a specific dimension.

Greenfield mode skips the Phase 1 audit entirely (G0 does a cheap inventory + open-questions pass instead), so a greenfield bootstrap costs a fraction of a brownfield run — typically well under 200k tokens unless the optional translation pass is run.

The translation pass (Phase 7) costs another ~300-500k tokens. Optional and one-time.

Tooling install (Phases 6, 9) and JIT policy (Phase 8) are cheap.

## What from-trd is not

- Not a code rewrite. It edits docs, generates tooling, and adds enforcement. It never modifies production code in `apps/` or `libs/`.
- Not interactive code generation. The per-requirement shapes it creates are *planning* documents the engineer fills in during their `craft` cycle, not finished implementation specs.
- Not a one-shot. It's a session-spanning command — typically 4–8 hours of orchestration in brownfield mode, with explicit user check-ins at Phase 0 (inventory), Phase 1 (audit findings), Phase 2 (Constitutional Map), and at each PR review. The greenfield track is shorter (no audit) but keeps the same check-ins at G0 (inventory + open questions), G1 (posture), and G2 (Constitutional Map).
- Not a substitute for the engineer's own thinking. The Constitutional Map is *proposed* by the command but *ratified* by the user. The per-UC shapes have open questions the engineer answers during craft.

## Embedded templates

The skill ships ten parameterized templates under `templates/`:

Shapes & meta-docs:
- `master-shape.md.tmpl` — the Constitutional Map header used in Phase 2.
- `sub-shape.md.tmpl` — the per-PR sub-shape used in every phase.
- `per-uc-shape.md.tmpl` — the per-requirement planning shape used in Phase 8 / JIT / greenfield G4.
- `refresh-docs-status.mjs.tmpl` — the meta-docs generator used in Phase 6 / G5.

PR gate (Phase 9 / G5):
- `check-pr-gate.mjs.tmpl` — the shared rule engine (critique + e2e-no-mocks + screenshot).
- `pr-gate.yml.tmpl` — the GitHub Action (server-side, unbypassable).
- `pull-request-template.md.tmpl` — the PR checklist + screenshot section the Action parses.
- `check-pre-pr.sh.tmpl` — the local pre-flight that mirrors the file-based checks.
- `hook-block-pr.sh.tmpl` — the Claude Code `PreToolUse` wrapper that blocks `gh pr create`.
- `claude-settings.json.tmpl` — the committed project hook wiring.

Each template uses `{{var}}` placeholders bound to fields in `.rigorous/trd-config.yml` (including the `pr_gate` block). The command writes them out concretized after the user confirms config in Phase 0.

## When to escalate

- If the audit returns >20 P0 findings: stop and surface to the user. The repo may need a bigger restructure than `from-trd` is designed for.
- If the Constitutional Map needs more than the eight standard rows: the project is unusual; the command falls back to interactive per-row decision rather than pre-set defaults.
- If the binding spec is in a language with no Romanian / English mapping in the translation glossary: ask the user to provide a 1:1 glossary of the 20–30 most common terms before running Phase 7.
