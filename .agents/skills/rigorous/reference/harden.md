# rigorous harden

Add error handling, edge cases, observability, idempotency — but only **where it earns its place**. Not blanket defensive code.

The opposite of harden is "shipping the happy path and hoping". The pathology of harden done badly is "validating every argument in every function until the code is 60% defensive cargo".

## When to invoke

- Before promoting a system from internal-only to user-facing.
- After an incident — fix the class of bug, not just the instance.
- Before a high-stakes deploy.
- When introducing a new external dependency.

## The three layers

Hardening targets exactly three things, in this order:

### 1. Boundaries

Inputs from outside the trust domain. Harden every one.

- **HTTP request bodies.** Schema validation (Zod / Pydantic / equivalent). Reject malformed early; type the parsed shape downstream.
- **Query string + URL params.** Same.
- **Env vars.** Validated at startup, not lazily on first use. Crash loud at boot rather than silently fail at request 1.
- **Third-party API responses.** Don't trust the SDK's types — runtime validate the fields you depend on.
- **Database rows you don't own.** If the schema is shared with another service, treat it as untrusted.
- **User uploads.** Size limit, content-type sniffing, scan if applicable.

For each boundary, you should have:
- A strict input schema.
- A path for "valid but unexpected".
- A rejection path that's safe (no leak of internal errors).

### 2. Failure modes for external dependencies

For each external service (DB, HTTP API, queue, cache, file system), answer:

- **Down**: timeout, retry policy, circuit breaker, fallback (or fail fast).
- **Slow**: timeout (with sensible value, not 30s default).
- **Wrong**: validation of response — what if it returns garbage?
- **Disagrees with us**: idempotency — what if we retry a write that already succeeded?

A function that calls 3 services and ignores any of these for any of them is a 3× landmine.

### 3. Observability where it pays off

The minimum that makes incidents tractable:

- **Structured logs at boundaries** — request start/end with method+path+status+latency, external API calls with target+latency+result, background job state transitions.
- **Correlation ID** propagated through the request — usually a header, threaded through async work.
- **Metric for the things you'd page on** — error rate, p95 latency, queue depth.
- **Health endpoint that's honest** — actually checks DB connectivity, not just `return 200`.

Don't go further unless there's a specific need. Tracing every function entry/exit is observability theater.

## What NOT to harden

This is half the discipline.

- **Internal pure helpers.** A function called by 3 other internal functions doesn't need defensive arg checks — the type system covered it.
- **Initialization order.** If module A must load before B, just import them in the right order. Don't add runtime guards "just in case".
- **Cases the type system already prevents.** TypeScript narrowed it to `string`? Stop checking for `null`.
- **"Future-proofing".** Don't add error handling for an API that doesn't exist yet.
- **Logs that only fire in normal operation.** A log line per successful request × 10k req/sec = ungreppable spam. Sample, or log only deviations.

## Idempotency specifically

When a request can be retried (network error, queue redelivery, user double-click), the second execution should be a no-op or produce the same result.

Patterns:
- **Idempotency keys** — the client supplies a unique ID; server stores and dedupes.
- **Conditional updates** — `UPDATE … WHERE status='pending'` — only one of two retries hits the row.
- **Upserts** — `INSERT … ON CONFLICT DO NOTHING/UPDATE`.
- **Compensating actions** — for actions that can't be undone (charges, sent emails), log + manually reconcile.

State which pattern is in use and where. "Idempotent" with no detail is not a hardening claim.

## Process

### 1. Map the boundaries

Make a list of every place data crosses from outside the trust domain. This is the work surface.

### 2. Decide threat model

Distinguish:
- **Adversarial inputs** — malicious user, attacker. Stricter validation, rate limits, sanitization.
- **Faulty integrations** — well-meaning third party that returns garbage. Schema-validate, fall back gracefully.
- **Intermittent failures** — network blip, slow DB. Retries with backoff.

### 3. Add the protection — minimum viable

For each boundary, add the smallest piece of code that addresses the actual risk. Don't add three layers when one suffices.

### 4. Add the test

Hardening that isn't tested isn't hardening. Write a test that fails without your fix.

### 5. Add the observability — only what helps incidents

Logs / metrics / traces only where they would change the resolution time of a real incident.

## Output

After harden:

- List of risks addressed (each with a one-line description).
- List of risks **not** addressed and why (out of scope, low likelihood, deferred).
- Tests added.
- Observability added.

The "not addressed" list is as important as "addressed". It signals where the user is now exposed by design choice, not oversight.

## Discipline

**Don't add `try/catch` to look responsible.** A try/catch you can't act on (just rethrows or logs and continues) is noise.

**Don't validate twice.** If the HTTP layer already enforced a schema, don't re-check at the service layer.

**Don't make "hardening" a euphemism for adding tests after the fact.** Tests are part of craft. Harden is about runtime resilience.

**Don't ship "TODO: handle this case".** Either handle it or document the explicit decision not to.
