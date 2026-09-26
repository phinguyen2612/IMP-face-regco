# Policy and Event Mechanics

## Deterministic Policy Boundary

Evaluate an immutable domain result plus explicit `PolicyContext`. Context may
contain camera/session/track provenance, ROI membership, authoritative or cached
person/group data, a schedule result produced by an injected `ScheduleEvaluator`,
dwell duration, configuration revision, and evidence settings. Given equal
inputs, configuration, and time value, evaluation
must produce the same output. A clock, resolver, or state store is injected and
owned outside individual rules.

Recognition failures, insufficient evidence, and `UNCERTAIN` must not silently
become unknown-person events. Define the allowed recognition states for every
event type and validate impossible policy combinations. Resolve multiple matches
with one documented total order, including a stable tie-breaker and whether one
or many candidates may result. A matching suppress action must also have explicit
precedence.

An `EventCandidate` carries stable event type, severity, provenance, optional
person/ROI, recognition summary, policy/config/model/index revisions, occurrence
time, resolved evidence request, and deduplication context. It is transient and
has no persistent event ID.

## Temporal Mechanics

Define dwell start, continuation, and reset conditions. Scope unknown dwell at
least by camera, stream session, track, policy, ROI when relevant, and
configuration revision. Use monotonic elapsed time for runtime durations and UTC
instants plus configured IANA timezone for schedule decisions.

Choose deduplication keys per event type. Unknown events normally include the
session-scoped track; known/watchlist events normally include stable person
identity. Include camera, policy, event type, ROI where material, and revision
semantics. Cooldown suppresses emission only; it never pauses tracking,
recognition, or track-state updates.

Document whether temporal state is in memory or durable, concurrency ownership,
cleanup, and restart behavior. Use database uniqueness or an equivalent durable
idempotency boundary when retries can otherwise create duplicate persisted
events. Persistent event IDs are independently generated and never reused as
deduplication keys.

## Persistence and Delivery

The event engine accepts candidates and either returns a suppression outcome or
persists an immutable `DomainEvent` through a repository boundary. Hot-path
domain services contain no SQL. Persist event, requested evidence metadata/job
intent, and publication intent in one acceptance transaction. Publish only
committed events. Emitted domain updates require crash-recoverable publication
intent; state end-to-end client delivery limits explicitly and give consumers
immutable IDs for deduplication.

Database failure creates no event and no evidence. Retry has a bounded queue,
backoff, deadline, and observable terminal outcome. Publication failure leaves
the committed event queryable and retries independently. Corrections or
enrichment use separate records or explicit versioned semantics; never rewrite
the original occurrence silently.

Use bounded metric labels. Cover deterministic matching, priority ties,
schedule/DST boundaries, dwell/reset, all dedup scopes, cooldown isolation,
idempotent persistence, concurrent candidates, restart semantics, configuration
revision changes, and every suppression/failure outcome without camera or GPU.
