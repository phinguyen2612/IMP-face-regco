# Phase 7: Recognition Policy, Event Engine, and Evidence Design

## Status and approval gate

This document is the Phase 7 design specification. It changes no product code
and does not authorize an implementation plan or implementation. Phase 7 begins
with the approved Phase 6 `IdentityDecision` and stops after persisted recognition
events, configured evidence, REST query access, and versioned WebSocket updates.

Implementation planning may begin only after the user replies exactly:

`APPROVE PHASE 7 DESIGN`

The prerequisite mismatch below must also be resolved before implementation.

## Scope and repository audit

Phase 7 includes only face-recognition policy, `UNKNOWN_PERSON`, optional
`KNOWN_PERSON`, `WATCHLIST_PERSON`, schedule, dwell, deterministic priority,
`EventCandidate`, event deduplication/cooldown, immutable `DomainEvent`,
PostgreSQL persistence, snapshot and optional clip evidence, `BlobStorage`, local
storage, evidence lifecycle, REST event queries, domain WebSocket updates,
metrics, and tests.

It excludes the full React management/live dashboard, ROI/model/enrollment UI,
analytics, notification integrations, email/SMS, unrelated IOC features, and
TensorRT optimization.

The repository is the implementation source of truth. The audit found:

- the Phase 2 synchronous camera, frame sampling, mock person detector/tracker,
  bounded frame-count buffer, and in-memory `TrackState` runtime;
- the Phase 6 design, but only a skeletal mutable `VectorStore` and partial
  `QualityWeightedVerifier`/`VerificationDecision` implementation;
- existing UI-editable policy, timing, schedule, and evidence models;
- `MessageEnvelope` v1 and runtime-status REST/WebSocket support only;
- a basic `BlobStorage`/`LocalBlobStorage` with `put/get/delete`, but no atomic
  write, public reference contract, evidence coordinator, or metadata model;
- PostgreSQL and Redis Compose services, but no schema, migrations, database
  client, repositories, events, evidence records, or outbox;
- no real YOLO, BoT-SORT, SCRFD, face-quality, alignment, AdaFace, FAISS index,
  Phase 3-6 orchestration, or implemented `IdentityDecision` contract described
  by the approved Phase 6 design;
- no project-local `vision-pipeline-engineering` skill. The available
  `face-pipeline-engineering`, `recognition-verification-engineering`, and newly
  validated `event-policy-engineering` skills were applied.

Therefore Phase 7 implementation is blocked until the checkout containing the
completed and verified Phase 3-6 implementation is supplied, or those phases
are implemented. Phase 7 must not silently absorb that work. The remainder of
this document defines the boundary to implement once its input contracts exist.

## 1. Runtime architecture

```text
Sampled tracked frame + cached Phase 6 IdentityDecision
  -> PolicyContextResolver
       -> cached authoritative person/group data
       -> ROI membership
       -> ScheduleEvaluator
       -> DwellStateStore
  -> RecognitionPolicyEvaluator (pure)
  -> EventCandidate | NoEvent
  -> bounded EventCommandQueue
  -> EventEngine
       -> PostgreSQL admission transaction
          - idempotency/dedup/cooldown decision
          - immutable DomainEvent
          - Evidence PENDING rows + job intents
          - event.created outbox message
  -> EvidenceCoordinator (bounded background work)
       -> camera ring-buffer selection/lease
       -> snapshot renderer / ClipEncoder
       -> BlobStorage
       -> Evidence READY|FAILED + outbox message
  -> Control API OutboxDispatcher
  -> WebSocketHub

PostgreSQL -> EventQueryRepository -> REST
```

The policy path is invoked on processed track updates using the cached decision;
it does not require face recognition to run again for dwell to advance. Inference
never emits an event, selects severity, captures evidence, writes SQL, or sends a
WebSocket message.

`EventCommandQueue` decouples bounded database latency from frame processing.
Admission uses a short configured timeout. Queue rejection is an observable
`EVENT_PERSISTENCE_FAILURE(queue_full)`, not a `DomainEvent`. In-memory candidates
not yet committed can be lost on process death; crash-durable pre-admission is an
explicit unresolved product decision, not an exactly-once claim.

## 2. Policy contract

```python
class RecognitionPolicyEvaluator(Protocol):
    def evaluate(
        self,
        decision: IdentityDecision,
        context: PolicyContext,
        policies: tuple[RecognitionPolicy, ...],
    ) -> PolicyEvaluationResult: ...
```

`PolicyEvaluationResult` is one of `CandidateCreated`, `PolicySuppressed`, or
`PolicyNoMatch`, and includes bounded reason codes. The evaluator has no FastAPI,
React, SQL, FAISS, storage, WebSocket, system-clock, or mutable-state dependency.
The same decision, context, and ordered configuration always produce the same
result.

An application-level `PolicyCoordinator` owns context resolution, state updates,
and the clock. `DwellStateStore` owns temporal state. `ScheduleEvaluator` owns
timezone conversion. Person/group lookup uses an authoritative revisioned cache
populated off the frame hot path.

## 3. Policy context

`PolicyContext` is immutable and contains:

- `camera_id`, `stream_session_id`, `track_id`, decision/frame timestamps;
- active recognition ROI IDs and a representative evidence source frame ID;
- copied person/face geometry required for configured overlays;
- optional verified `person_id` and authoritative identity-group IDs;
- resolved `schedule_active` plus configured IANA timezone;
- `dwell_ms_by_policy_id` and monotonic evaluation time;
- active configuration revision and Phase 6 collection/model/index revisions;
- resolved global evidence request and policy configuration snapshot.

It contains no image bytes, embeddings, FAISS positions, database session, or
framework objects. Group-cache misses are explicit technical/context failures;
they do not silently make a verified person non-watchlisted.

## 4. UNKNOWN_PERSON policy

An unknown policy matches only when all are true:

- `IdentityDecision.state == UNKNOWN` with Phase 6 sufficient-valid-evidence
  semantics;
- the configured ROI condition is empty or intersects the active recognition
  ROI set;
- the resolved schedule is active;
- the policy-scoped continuous unknown dwell reaches `minimum_dwell_ms`;
- the policy is enabled and its action names `UNKNOWN_PERSON`.

Model/search/index failure, no face, low quality, insufficient evidence,
`PENDING`, `UNCERTAIN`, and cache/context failure never create
`UNKNOWN_PERSON`. `timing.unknown_dwell_ms` remains the feature default; a
policy's existing `minimum_dwell_ms` overrides it when nonzero.

## 5. KNOWN_PERSON policy

`KNOWN_PERSON` requires `VERIFIED`, a non-null verified person, matching ROI and
schedule, and an explicitly enabled matching policy whose action has
`emit_event=true` and type `KNOWN_PERSON`. No built-in policy is synthesized from
the existence of `VERIFIED`; with no such configuration, known recognition emits
no event. Optional configured identity-group conditions must match the resolved
authoritative group set.

## 6. WATCHLIST_PERSON policy

`WATCHLIST_PERSON` requires `VERIFIED`, a non-null verified person, matching
ROI/schedule, and intersection with a non-empty configured
`identity_group_ids`. Membership comes from authoritative PostgreSQL-derived
business data held in a revisioned runtime cache, never from FAISS row position
or unverified candidate metadata. Missing/stale required membership context is a
configuration/context failure and emits nothing.

Configuration semantic validation enforces:

- `UNKNOWN_PERSON` accepts only `UNKNOWN` and no identity-group condition;
- `KNOWN_PERSON` and `WATCHLIST_PERSON` accept only `VERIFIED`;
- `WATCHLIST_PERSON` has at least one identity group;
- policy IDs are unique and referenced ROI IDs exist for the camera.

`PENDING` and `UNCERTAIN` have no Phase 7 event types and always produce no
event. Supporting them later requires an explicit event type and policy contract.

## 7. Priority and conflict resolution

MVP produces at most one `EventCandidate` per policy evaluation. Enabled policies
are ordered by descending `priority`, then ascending stable policy ID. The first
fully matching policy wins across all three event types. This lets a higher
priority watchlist rule override a broad known-person rule without duplicates.

If the winning rule has `emit_event=false`, evaluation returns
`PolicySuppressed` and lower-priority rules are not considered; this is an
explicit suppress rule. Tied priorities remain deterministic through policy ID,
but configuration validation reports a warning when overlapping policies share
a priority. Persist the winning policy ID and revision for auditability.

## 8. EventCandidate

`EventCandidate` is a frozen transient domain value containing:

- event type, severity, camera/session/track and optional ROI/person;
- recognition state and optional score;
- policy ID, occurred-at UTC instant, configuration/model/index revisions;
- representative frame and overlay geometry references;
- resolved immutable `EvidenceRequest`;
- exact idempotency fingerprint, semantic dedup key, and cooldown key.

The exact fingerprint is SHA-256 over a versioned canonical tuple of policy ID,
event type, camera/session/track, person when present, decision timestamp,
configuration revision, and decision revisions. It contains no embedding or
display name. A candidate has no persistent event ID and is never inserted as an
event directly.

## 9. DomainEvent

`DomainEvent` is frozen and contains:

- UUID event ID independent of track ID;
- stable event type and severity enums;
- camera ID, stream-session ID, track ID, optional ROI ID and person ID;
- recognition status and optional score;
- policy ID, `occurred_at`, database `created_at`;
- configuration, face-embedding model, and vector-index revisions;
- bounded schema-versioned metadata with reason code and evidence summary.

It contains no embedding, raw image, local path, UI display string, FAISS ID, or
mutable current track status. Later recognition changes do not rewrite history.
Corrections/enrichment require separate explicit records outside MVP.

## 10. Deduplication keys

Three concepts remain separate:

1. Exact idempotency fingerprint prevents the same candidate retry from creating
   multiple rows and has a unique database constraint.
2. Semantic deduplication suppresses rapid equivalent situations for
   `duplicate_suppression_ms`.
3. Cooldown suppresses later valid repeats for `event_cooldown_ms`.

MVP semantic keys are:

| Event | Dedup key | Cooldown key |
|---|---|---|
| UNKNOWN_PERSON | event, policy, config revision, camera, stream session, track, ROI | same scope |
| KNOWN_PERSON | event, policy, config revision, camera, stream session, track, person, ROI | event, policy, config revision, camera, person, ROI |
| WATCHLIST_PERSON | event, policy, config revision, camera, stream session, track, person, ROI | event, policy, config revision, camera, person, ROI |

Thus a new track for the same verified person bypasses same-track deduplication
but remains subject to identity-scoped cooldown. Different cameras, policies,
event types, identities, sessions for unknown tracks, and material ROIs do not
collide. Keys are versioned hashes of canonical fields, never raw embeddings.

## 11. Cooldown semantics

`EventRepository.admit` is the authoritative cross-thread/process owner. In one
PostgreSQL transaction it locks/creates the suppression-key row, checks exact
idempotency, then semantic dedup window, then cooldown, and finally inserts the
event and updates the last-emitted instant. Outcomes are
`EVENT_EMITTED`, `EVENT_SUPPRESSED_DUPLICATE`, or
`EVENT_SUPPRESSED_COOLDOWN`.

Durable database state is chosen over process-only state because multiple camera
workers and restart correctness are already architectural requirements. This is
one database operation per candidate, never per frame. A bounded in-memory
negative/last-seen cache may optimize obvious duplicates, but PostgreSQL remains
authoritative and tests cannot depend on the cache. Cooldown affects only event
emission; tracking, recognition, dwell updates, and TrackState continue.

## 12. Dwell semantics

`DwellStateStore` is in-process and keyed by camera, stream session, track,
policy, relevant ROI, and configuration revision. It begins when an `UNKNOWN`
decision is cached and the policy's ROI and schedule preconditions first hold.
It advances from monotonic time on subsequent processed track updates without
rerunning recognition.

Dwell resets on recognition leaving `UNKNOWN`, ROI exit, schedule becoming
inactive, track expiry/discontinuity, stream-session change, or configuration
revision change. A missed sampled frame does not reset dwell while TrackState is
live; expiry does. Dwell is never reconstructed after worker restart, so the
person must satisfy the full dwell again. Wall-clock changes cannot advance it.

## 13. Schedule and timezone

`ScheduleEvaluator` converts the decision's UTC instant to the configured IANA
timezone and returns an explicit boolean in `PolicyContext`. Empty `weekly`
means always active; an absent weekday means inactive. Ranges are start-inclusive
and end-exclusive: `[start, end)`.

The existing `TimeRange` validator rejects `start >= end`, so overnight windows
are not supported in MVP and must be split across two weekdays. This behavior is
documented and tested rather than inferred. UTC instants disambiguate DST folds;
nonexistent local times cannot occur because evaluation starts from UTC. Server
local timezone is never consulted.

## 14. Persistence flow

`EventRepository` is a domain-facing protocol; a PostgreSQL adapter owns SQL and
transactions. `EventEngine` passes one candidate to `admit`.

For an accepted candidate, one transaction inserts:

- `recognition_events` with unique idempotency fingerprint;
- updated `event_suppression_state` under a row/advisory lock;
- one `event_evidence` PENDING row per requested artifact;
- durable evidence job intent(s);
- one `event_delivery_outbox` row for `event.created`.

Only after commit does `DomainEvent` exist. A database failure returns
`EVENT_PERSISTENCE_FAILURE`; it creates no evidence artifact or WebSocket update.
The bounded event worker retries transient failures with capped exponential
backoff and deadline while keeping one stable fingerprint. Constraint conflict
loads and returns the already committed event as idempotent success.

Tables use `timestamptz`, foreign keys from evidence to event, bounded enums/check
constraints, indexes for supported filters, and append-only event permissions.
TrackState, frames, detections, observations, candidates, and embeddings are not
persisted.

## 15. Evidence request

`EvidenceRequest` is resolved from the existing active `EvidenceConfig` at
candidate creation and copied into the acceptance transaction. It contains
snapshot/video flags, pre/post seconds, overlay flags, source camera/session,
event timestamp/frame reference, and revision. Pending evidence continues using
this snapshot even after hot reload.

No PENDING evidence row is created for a disabled artifact. With both artifact
types disabled, the event remains valid and has no evidence rows.

## 16. Snapshot flow

After event commit, `EvidenceCoordinator` selects the exact referenced source
frame when present; otherwise it selects the nearest frame in the same camera and
stream session within a small backend-only tolerance. No qualifying frame marks
the evidence `FAILED` with `EVIDENCE_CAPTURE_FAILURE(frame_missing)`.

The renderer copies pixel data before drawing configured person/face boxes, ROI,
identity/status, or similarity. It never mutates a buffered/inference frame.
The stored snapshot is rendered event evidence; original unrendered frames are
not retained unless a future separately approved setting is introduced.

## 17. Video clip flow

The clip window is `[occurred_at - pre_event_seconds,
occurred_at + post_event_seconds]` within the event's camera and stream session.
The buffer gains timestamp-range selection and bounded evidence leases/copies;
it remains capacity-limited and owned by the vision runtime. Pre-event capacity
is validated against configured retention and expected input FPS at activation.

At event commit, available pre-event frames are leased/copied into the bounded
job. Future frames are collected until the post deadline. Track disappearance
does not stop collection because clips are camera-level. A stream-session change
or camera stop closes collection early. Missing prehistory or an interrupted
post-window yields a `READY` partial MP4 only if at least one encodable frame
exists; metadata records requested/actual bounds and `partial=true`. Zero frames
or encoder failure produces `FAILED`.

`ClipEncoder` is an adapter; the Jetson MVP may use a configured GStreamer H.264
MP4 pipeline, with a fake encoder in normal tests. Encoding/storage runs outside
the inference thread. No raw video travels through WebSocket.

## 18. BlobStorage

The existing abstraction is extended, not bypassed:

```python
put(key, content, content_type) -> BlobObject
get(key) -> bytes | stream
delete(key) -> None
create_read_reference(key, expires_in) -> StorageReadReference
```

`LocalBlobStorage` uses opaque keys, containment checks, temporary same-directory
writes plus atomic replace, and never returns an absolute path. The control API
exposes a controlled evidence-content URL; future S3/MinIO adapters may return a
short-lived signed URL. Domain events store only evidence IDs; evidence metadata
stores the opaque key internally.

Phase 7 adds retention/deletion hooks but no automated retention policy because
retention duration is unresolved. API boundaries remain authentication-ready;
production deployment must add authorization and encryption-at-rest policy
before exposing biometric artifacts beyond the trusted MVP environment.

## 19. Evidence lifecycle

`Evidence` contains UUID ID, event ID, type (`SNAPSHOT`/`VIDEO_CLIP`), status
(`PENDING`/`READY`/`FAILED`), optional opaque storage key, content type, created
and completed timestamps, attempt count, bounded metadata, and optional stable
failure code.

Allowed transitions are `PENDING -> READY` or `PENDING -> FAILED`. They are
idempotent and terminal in MVP. Retry happens while PENDING. Storage succeeds
before the READY transaction; if that transaction fails, retry detects the same
deterministic blob key. Final evidence failure never deletes or changes the
event. A later manual retry would create a new attempt record in a future phase.

## 20. WebSocket delivery

The existing `MessageEnvelope` v1 is retained. Typed payloads are added for:

- `event.created` with queryable event summary and immutable event ID;
- `evidence.ready` with event/evidence IDs, type, metadata, and controlled content
  reference;
- `evidence.failed` with event/evidence IDs, type, and bounded failure code.

Every message corresponds to committed database state. The worker writes outbox
intent; a single-control-API MVP `OutboxDispatcher` leases rows, broadcasts via a
`WebSocketHub`, and marks success. Failed dispatch is retried with backoff and a
lease timeout. Crash between broadcast and acknowledgement may duplicate a
message, so delivery is at-least-once from outbox to hub and clients deduplicate
by `message_id`/entity ID. Per-client delivery is best effort: disconnected or
failed clients recover through REST. The event engine never knows React shapes.

Multiple control-API replicas require a future shared fan-out layer such as Redis
Pub/Sub; the MVP explicitly supports one API process.

## 21. REST endpoints

- `GET /api/v1/events`: cursor-paginated by `(occurred_at, id)` with bounded
  limit and filters for camera ID, event type, person ID, recognition status,
  and inclusive UTC from/exclusive UTC to.
- `GET /api/v1/events/{event_id}`: immutable event detail or 404.
- `GET /api/v1/events/{event_id}/evidence`: evidence metadata list, never local
  paths or bytes.
- `GET /api/v1/evidence/{evidence_id}/content`: streams local content or redirects
  to a future short-lived signed reference after evidence access checks.

DTOs live in shared contracts and are independent of ORM/database rows. Queries
use `EventQueryRepository`; endpoints contain no SQL. This is retrieval, not an
analytics/reporting API.

## 22. Failure and retry semantics

| Scenario | Required behavior |
|---|---|
| Candidate queue full | reject within bounded admission timeout; metric/degraded health; no event claim |
| Database unavailable | bounded retry; no event/evidence/message until commit; terminal persistence failure observable |
| Exact retry races | unique fingerprint returns one event; no duplicate evidence/outbox rows |
| Event committed, WebSocket fails | event remains queryable; outbox retry; publication failure metric |
| Snapshot capture/render fails | evidence becomes FAILED after bounded retry; event unchanged |
| Blob storage unavailable | retry PENDING with backoff; then FAILED; event unchanged |
| Clip encoder fails | clip evidence FAILED; snapshot may independently succeed |
| Incomplete ring history | READY partial clip with actual coverage when frames exist; otherwise FAILED |
| Track disappears post-event | continue camera/session collection to deadline |
| Stream/camera stops | close early and apply partial/zero-frame rule |
| Worker shutdown | stop admission, drain to deadline; persist unfinished jobs for recovery; release frame leases |
| Stale PENDING job after restart | retry if source artifacts still exist; otherwise mark FAILED with restart/source-lost code |
| Policy config changes during dwell | old dwell discarded; new revision starts at zero |

Failures use distinct codes: `POLICY_NO_MATCH`,
`POLICY_CONFIGURATION_ERROR`, `EVENT_SUPPRESSED_DUPLICATE`,
`EVENT_SUPPRESSED_COOLDOWN`, `EVENT_PERSISTENCE_FAILURE`,
`EVIDENCE_CAPTURE_FAILURE`, `EVIDENCE_STORAGE_FAILURE`, and
`REALTIME_PUBLICATION_FAILURE`. They never become recognition states.

## 23. Concurrency and backpressure

Use a capacity-limited event command queue and a separate capacity-limited
evidence job queue. Backend-only runtime settings define capacities, event/evidence
worker counts, enqueue timeouts, retry limits, drain timeout, maximum frames/bytes
per job, and outbox batch/lease sizes. They are not UI-editable feature settings.

PostgreSQL serialization on suppression keys resolves concurrent candidates.
Evidence workers atomically claim durable job intents; only one owns a job lease.
Frame lease/copy memory is accounted against a fixed byte/frame budget. On
evidence queue overload, the already committed PENDING row is marked FAILED with
`queue_full` rather than growing memory or crashing inference. No queue is
unbounded, and health/metrics expose saturation.

Shutdown order is: stop new camera/policy admission, drain event commands,
persist/hand off evidence jobs, drain outbox within timeout, release leases and
storage/database resources. Forced termination may duplicate retried work but
must remain idempotent.

## 24. Metrics

Add bounded-label metrics for:

- policy evaluations/latency, match/no-match/configuration-error counts;
- active dwell state count and dwell resets by fixed reason;
- event command queue depth/rejections;
- events emitted and suppressed by event type/reason;
- persistence latency/failures;
- evidence requested, queue depth/rejections, latency, READY/FAILED by artifact
  type and fixed failure code;
- outbox backlog/oldest age/retries and WebSocket publication failures.

Labels may include camera, event/evidence type, state, and bounded reason. Never
label by person, track, event ID, storage key, path, embedding, or raw policy ID
if policy cardinality is not administratively bounded. Logs contain identifiers
needed for correlation but never image bytes, embeddings, credentials, or local
paths.

## 25. Tests

Normal tests use fake decisions, clock, schedule resolver, group cache, frames,
repository, blob store, encoder, and publisher; no camera or GPU is required.

Policy tests cover deterministic UNKNOWN, known, watchlist, PENDING, UNCERTAIN,
technical failures, ROI mismatch, schedule mismatch/boundaries/timezone/DST,
unsupported overnight ranges, dwell start/continue/reset, priority ties,
watchlist override, and suppress precedence.

Event-engine tests cover first emission, exact idempotency, duplicate window,
cooldown, different unknown tracks/sessions, different identities/cameras/ROIs,
concurrent admission, database failure/retry, and configuration revision change.

Evidence tests cover exact/nearest snapshot, copy-on-render overlays, timestamped
pre/post selection, partial/missing windows, track disappearance, session change,
failed storage/encoder, deterministic blob retries, bounded queue/memory,
restart/shutdown, LocalBlobStorage containment/atomicity/reference behavior, and
privacy-safe logs.

PostgreSQL integration tests cover migrations, transactional event/evidence/
outbox creation, unique constraints, suppression locking, retrieval, filters,
cursor pagination, relations, and failure rollback. Realtime contract tests cover
all three message types, versioned schemas, persistence-before-publication,
duplicate replay, and publisher failure. All earlier available tests, lint,
mypy, and frontend build remain required; no earlier test is weakened.

## 26. Configuration and hot reload

Reuse existing UI-editable `policies`, `timing.unknown_dwell_ms`,
`event_cooldown_ms`, `duplicate_suppression_ms`, `schedule`, and `evidence` fields.
Add semantic/cross-resource validation, not parallel settings. `config_revision`
remains backend-generated activation metadata rather than a user field.

On an atomic revision activation:

- new policy evaluations use the complete new immutable snapshot;
- dwell state resets and old-revision entries are purged;
- in-memory dedup/cooldown hints reset, while database suppression is naturally
  revision-namespaced;
- queued candidates retain the revision and request snapshot that created them;
- persisted events remain unchanged;
- PENDING evidence completes using its captured request, not new settings.

Invalid policy/schedule/evidence configuration is rejected before activation;
the previous active revision continues. Queue sizes, retry/backoff, database,
storage root, encoder, outbox, and shutdown controls belong only to backend
`RuntimeSettings`.

## 27. Expected implementation files

The implementation plan should minimally add or change:

```text
packages/python/face-recognition-domain/src/fr_domain/
  policy.py                 # PolicyContext/results and pure evaluator
  events.py                 # EventCandidate, DomainEvent, Evidence, outcomes

packages/python/face-recognition-contracts/src/fr_contracts/
  events.py                 # REST DTOs and typed WebSocket payloads
  messages.py               # retain envelope; typed integration only

packages/python/face-recognition-config/src/fr_config/
  models.py                 # semantic policy validation
  runtime.py                # backend queue/retry/outbox/encoder settings

packages/python/face-recognition-persistence/src/fr_persistence/
  events.py                 # repository protocols/records
  postgres.py               # PostgreSQL event/query/evidence/outbox adapter

workers/vision-worker/src/vision_worker/
  eventing/policy.py        # context coordinator and dwell store
  eventing/engine.py        # bounded submission and EventEngine
  eventing/worker.py        # persistence worker lifecycle
  evidence/coordinator.py   # durable job coordination
  evidence/rendering.py     # copy-on-render snapshot overlays
  evidence/encoding.py      # ClipEncoder protocol/GStreamer adapter
  evidence/storage.py       # enhanced BlobStorage/local implementation
  video/buffer.py           # timestamp query and bounded evidence lease/copy
  runtime/pipeline.py       # Phase 6 decision -> policy handoff only

apps/control-api/src/control_api/
  events.py                 # query/content routes
  outbox.py                 # dispatcher lifecycle
  realtime.py               # WebSocketHub
  main.py                   # router/lifespan wiring

infrastructure/database/migrations/
  0001_phase7_events.sql

tests/unit/
  test_policy.py
  test_event_engine.py
  test_dwell_schedule.py
  test_evidence.py
  test_event_contracts.py

tests/integration/
  test_event_repository.py
  test_event_outbox.py
  test_event_api.py
```

Exact module splits may follow the restored Phase 3-6 checkout, but ownership and
dependency direction may not change. No Phase 8 UI or other IOC feature files are
part of this plan.

## 28. Unresolved decisions and prerequisite gates

Only these decisions remain genuinely unresolved:

1. **Missing implementation input:** obtain/implement and verify actual Phase
   3-6 code, especially the approved `IdentityDecision`, revision provenance,
   representative frame/geometry reference, authoritative group cache, and real
   timestamped buffer integration. Phase 7 cannot be implemented against the
   current mock-only checkout without expanding scope.
2. **Pre-commit crash tolerance:** approve the documented bounded in-memory event
   command window, or require a durable candidate transport (for example a Redis
   Stream) before PostgreSQL admission. The latter adds operational scope.
3. **Biometric evidence governance:** choose retention duration, deletion policy,
   deployment encryption-at-rest requirement, and authorization rules before
   production exposure. No invented defaults belong in code.
4. **MVP clip encoder availability:** confirm the Jetson GStreamer H.264/MP4
   encoder pipeline and licensing/runtime packages. The adapter boundary and fake
   tests do not depend on that choice.
5. **Multi-instance control API:** confirm the Phase 7 deployment remains one
   control-api process. Multiple replicas require shared WebSocket fan-out and
   are not covered by an in-process hub.

The following are resolved by this design: highest-priority single winner;
explicit suppress precedence; no PENDING/UNCERTAIN events; PostgreSQL-authoritative
dedup/cooldown; dwell reset on restart/revision; start-inclusive/end-exclusive
IANA schedules with split overnight windows; event/evidence/outbox intent in one
transaction; at-least-once outbox-to-hub and best-effort per-client delivery;
partial clip rules; immutable events; and evidence failure isolation.

## Self-review

- Recognition/event boundary: verifier and inference expose only domain results;
  policy, event, evidence, and delivery responsibilities are separated.
- UNKNOWN handling: only a successful Phase 6 `UNKNOWN` with sufficient evidence
  can match; operational and ambiguous states cannot fall through.
- Policy determinism/conflicts: explicit immutable context, pure evaluation,
  total ordering, single winner, and suppress precedence are defined.
- Collision risk: keys differ by unknown track versus verified identity and
  include camera/policy/type/ROI/revision/session where material.
- Time: monotonic dwell and UTC-to-IANA schedule evaluation avoid server-local
  and wall-clock-duration errors.
- Bounded work: event/evidence queues, frame budgets, retries, and shutdown are
  bounded with observable overload behavior.
- Persistence/publication race: event, evidence/job intent, and outbox commit
  atomically; only committed state is published.
- Privacy: no embeddings, raw paths, image logs, per-face persistence, or identity
  metric labels; evidence uses opaque storage references.
- Failure semantics: every requested failure scenario preserves the valid event
  and has an explicit retry or terminal result.
- Testability: pure domain logic and fakes cover normal tests without GPU/camera;
  PostgreSQL behavior is isolated to integration tests.
- Scope: no Phase 8 UI, analytics, notifications, other IOC features, or TensorRT
  work is included.

## Stop condition

No product implementation, implementation plan, migration, dependency addition,
or React work is authorized by this document. Stop and wait for exactly:

`APPROVE PHASE 7 DESIGN`
