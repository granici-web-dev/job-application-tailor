# rigorous audit

Technical audit. Surface concrete defects, not stylistic preferences. Different from `critique` (which targets readability + abstraction) — this is for: performance, security, dependency health, concurrency, data integrity, and observability.

## When to invoke

- Before a release.
- When something has been running for a while without scrutiny.
- After a security-sensitive change.
- On a dependency upgrade.
- On regression that defies easy reproduction.

## The categories

### 1. Performance

Look for:

- **N+1 queries.** A list endpoint that queries one row per item in a loop. Fix with a single join or `IN` clause.
- **Missing indexes.** Slow `WHERE` / `ORDER BY` / `JOIN` on a column without an index. Run `EXPLAIN ANALYZE` on hot queries.
- **Over-fetching.** `SELECT *` returning 50 columns when 5 are used. List the columns.
- **Unbounded result sets.** Pagination missing on endpoints that can grow.
- **Synchronous network in a hot loop.** A `fetch` per row in a render path. Batch or parallelize.
- **Cache misuse.** A cache that's invalidated on every write makes the endpoint slower than no cache.
- **Premature optimization.** A clever loop that saves microseconds in code that runs once a day. Revert to the simple version.

Profile before optimizing. State the metric you measured, not "it feels slow".

### 2. Security

Walk through OWASP top 10 in the project's context:

- **Injection.** SQL: parameterized queries everywhere? Search for string concatenation against user input. Same for shell commands, LDAP, XPath.
- **Broken auth.** Session tokens stored where? Refresh / expiry policy? `httpOnly` + `Secure` flags? CSRF protection if cookie-based?
- **Sensitive data.** PII / credentials in logs, URLs, or error messages? `.env` committed accidentally? Secrets in client-side code?
- **XSS.** User input rendered into HTML without escaping? Frameworks usually handle this — verify the unsafe-inner-html escape hatches aren't used.
- **Authorization.** Are routes that should be admin-only actually checking? Is row-level access enforced (user X can only see user X's data)?
- **Dependency CVEs.** `npm audit` / `pip audit` / `cargo audit` clean? Address criticals.
- **Open redirects, SSRF.** Anywhere we follow a user-supplied URL?
- **Rate limiting.** Public endpoints — is there a ceiling? Login endpoint especially.

Document each finding: location, severity (CVSS-ish — informational / low / medium / high / critical), proof of concept if relevant, fix.

### 3. Dependencies

- **Stale.** Dependencies older than ~12 months for actively maintained projects. List which.
- **Unmaintained.** Last commit > 2 years ago + open issues > 100. Plan a replacement.
- **Bloated.** A dependency for a 5-line function (`leftpad`-style). Inline.
- **Duplicate.** Two libraries doing the same job. Pick one.
- **Lock file out of sync** with manifest.

### 4. Concurrency / data integrity

- **Race conditions.** Read-modify-write without a transaction or lock. Two requests can corrupt the row.
- **Missing transactions.** A multi-statement update that should be atomic but isn't.
- **Idempotency.** A retry-able endpoint that double-charges / double-sends if called twice.
- **Foreign keys.** Cascade behavior intentional? An `ON DELETE CASCADE` that wipes more than expected?
- **Unique constraints.** Should-be-unique columns without a unique index — silent duplicates accumulate.
- **Time zone bugs.** Timestamps stored as `TIMESTAMP` without time zone, compared across regions.

### 5. Observability

- **Errors swallowed.** Catch blocks that log but don't re-throw and don't surface anywhere actionable.
- **Missing structured logs** at boundaries (request start/end, external API calls, background job state transitions).
- **No correlation IDs** — tracing a single user request through services is impossible.
- **Health endpoints absent or fake** (return 200 even when the DB is down).
- **Metrics absent** for the things you'd page on (error rate, p95 latency, queue depth).

## Output format

Same shape as `critique`: list of findings with file/line, severity, fix.

Severity scale here is sharper:

- `critical` — exploitable today, data loss possible, or production outage imminent. Fix before next merge.
- `high` — exploitable / breakable in plausible scenarios.
- `medium` — defensive — would bite at scale or under attack.
- `low` — best-practice deviation, no immediate impact.
- `info` — observation, no action required.

End with a one-paragraph posture summary: roughly how healthy is this codebase on the audit dimensions checked? Where is the technical debt accumulating?

## Discipline

**Reproducible findings.** Every issue stated must be checkable. "Probably has a SQL injection somewhere" is not a finding. "Line 42 in `routes/foo.ts` interpolates `req.query.name` into a SQL string" is.

**Run the tools.** Before opining: `npm audit`, `EXPLAIN ANALYZE` for slow queries, `git log --grep=secret`. Don't speculate when a tool gives a definitive answer.

**Skip the cargo cult.** Don't flag "using `console.log` instead of a structured logger" if the project is small and console is fine. Match severity to actual risk.

**Cite sources.** OWASP, CVE numbers, framework changelogs, language docs — link or quote. Vague "best practice says" doesn't justify action.
