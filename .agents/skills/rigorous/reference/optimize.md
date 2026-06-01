# rigorous optimize

Profile-driven performance work. Channeled from Knuth (*"premature optimization is the root of all evil"*) and Carmack (*"measure everything"*).

## When to invoke

- A user-reported "this is slow" with a specific trigger.
- A measurement (p95 latency, throughput, response time) that crossed a threshold.
- A resource (memory, CPU, IO) hitting a hard ceiling.
- A planned scale-up where the current numbers won't survive.

## When NOT to invoke

- "I think this could be faster." Without a measurement, you don't know if it matters.
- Code that runs once at startup. Optimizing it saves microseconds invisible to anyone.
- Code that hasn't shipped yet. Profile real production load before guessing.

## Process

### 1. Define the metric

What's being optimized? Pick one number:

- Endpoint latency (p50, p95, p99).
- Throughput (requests/sec).
- Memory usage (RSS, heap).
- Database query time.
- Cold start.
- Bundle size.

Vague "speed" / "performance" without a number leads to optimization theater.

### 2. Set the target

What's good enough? "p95 < 200ms" / "fits in 512MB" / "under 100ms cold start". With a target, you know when to stop. Without one, you optimize forever.

### 3. Measure baseline

Reproducible benchmark. Run it 5 times, report median + spread. Single-run "it took 3.5s" is noise.

For backend: load test with realistic concurrency. `k6` / `wrk` / `vegeta` — pick one.
For frontend: Lighthouse / WebPageTest with 3 runs.
For DB: `EXPLAIN ANALYZE` with realistic data volume.
For memory: heap snapshot at peak.

### 4. Profile

Find where the time goes. Don't guess.

- Backend code: profiler (Node `--prof`, Python `cProfile`, Go `pprof`, Rust `flamegraph`).
- DB: `EXPLAIN (ANALYZE, BUFFERS)` for the slow query. Note rows returned vs scanned.
- Frontend: DevTools Performance tab. Render flame graph, paint, layout.
- Network: throttle to realistic conditions.

The profile shows the hot spots. **Almost always**, 80% of time is in <20% of code (and often a single function).

### 5. Hypothesize

For each hot spot, state the cause. Examples:

- `dbQuery` takes 60% of request time. Looking at the query: full table scan on a column without an index.
- `renderList` takes 40%. Computing 1000 sort comparisons each render.
- `parseJSON` takes 25%. Re-parsing a static config on every request.

### 6. Apply minimum viable fix

The smallest change that addresses the bottleneck. Standard moves:

**Database**
- Add an index. Verify with `EXPLAIN`.
- Replace `SELECT *` with named columns.
- Convert N+1 into a single query (batch IDs, JOIN, IN clause).
- Move expensive aggregates to a materialized view.
- Pagination on result-set-grows endpoints.

**Backend**
- Cache. Pin TTL. Validate hit rate.
- Batch async operations (`Promise.all` for parallelizable work).
- Don't await inside loops if the work is independent.
- Stream large results instead of buffering.

**Frontend**
- Code-split routes (`React.lazy` / dynamic import).
- Memoize expensive renders / computations.
- Debounce event handlers in hot paths.
- Lighten images (next-gen formats, dimensions matching display).

**Memory**
- Don't keep references to objects past their need (event listener cleanup).
- Stream / chunk large file IO.
- Watch for closures capturing large objects.

### 7. Re-measure

Run the same baseline benchmark. Report new number. Calculate improvement.

If the improvement is small relative to your target, the bottleneck wasn't where you thought. Profile again, hypothesize again.

If the improvement is large, ship it. Don't keep optimizing past your target — diminishing returns kill maintainability.

### 8. Add a regression test or monitor

Performance regressions are silent. Either:
- Add a benchmark to CI that flags slowdowns above a threshold.
- Add a metric / alert on the production signal you optimized.

Without one, the next refactor will quietly undo the win.

## Common false-economy optimizations

- **Manual loop unrolling.** The compiler does this; you make the code unreadable.
- **Bit-twiddling for clarity-cost.** A `% 2` is fast enough; `& 1` doesn't earn its obscurity.
- **Replacing one library with another for "speed"** without measuring.
- **Premature concurrency.** Adding async/parallelism where the bottleneck was IO and now both are bottlenecks.
- **Caching everything.** Every cache adds invalidation complexity. Cache hot paths, not by reflex.
- **Removing safety checks "for speed".** Bounds checks and similar cost almost nothing in modern JITs/optimizers.

## When to stop

- Target reached.
- Diminishing returns: each new optimization < 5% improvement.
- Complexity cost > performance gain.
- The bottleneck moved to something you can't easily change (network RTT, third-party API).

State plainly when you've stopped and why. Don't let an open optimization task linger.

## Output

After optimize:

- Metric optimized + baseline + target.
- Profile findings (where the time was).
- Changes applied (the actual diff).
- New measurement.
- Regression guard (test, metric, or alert).

## Discipline

**Measure first, fix second.** No exceptions.

**One change per measurement.** If you change three things, you can't attribute the win.

**Don't optimize the wrong layer.** A slow function called once a day is not a problem. A fast function called 1M times a second is.

**Resist the urge to over-engineer.** A single index can solve what was about to become a queue+cache+CDN architecture.

**Stop on diminishing returns.** Optimization is exponentially hard. Don't pursue 5% wins at the cost of 50% added complexity.

## What optimize is not

- Not refactoring. If the code is faster but unreadable, you didn't optimize, you regressed.
- Not architectural. If you need a new layer (queue, cache, separate service), that's `architect` first, then targeted craft.
- Not a substitute for capacity planning. At some scale, vertical/horizontal scaling is the right answer.
