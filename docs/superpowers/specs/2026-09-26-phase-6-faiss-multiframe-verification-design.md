# Phase 6: FAISS Search and Multi-frame Identity Verification Design

## Status and Approval Gate

This document is the Phase 6 design specification. It changes no product code
and does not authorize an implementation plan or implementation. Phase 6 starts
with a valid `FaceEmbedding` and stops at `IdentityDecision` in one of four
states: `PENDING`, `VERIFIED`, `UNCERTAIN`, or `UNKNOWN`.

Implementation planning may begin only after this design is approved with the
requested phrase and the prerequisite mismatch below is resolved.

## Scope

Phase 6 includes the `VectorStore` abstraction, an exact-search FAISS MVP,
identity-collection compatibility, immutable index revisions, enrollment-level
Top-K search, identity-level aggregation, centralized metric and threshold
semantics, bounded recognition observations, deterministic
`quality_weighted_vote`, identity state transitions, TrackState caching and
re-verification, metrics, and tests.

It excludes recognition policies, known/unknown/watchlist business events,
evidence snapshots or clips, notifications, and a React event dashboard.
`PENDING` is an internal runtime result, not a business event.

## Repository Audit and Prerequisite Gate

The repository is the implementation source of truth. It currently contains:

- the Phase 2 camera/sampling/mock-detection/mock-tracking runtime;
- a skeletal `VectorStore` exposing mutable `add` and `remove` and returning
  `person_id` directly;
- domain `RecognitionState`, `CandidateMatch`, `VerificationObservation`, and a
  partial `QualityWeightedVerifier` with focused unit tests;
- a recognition scheduler and `TrackState` identity-cache fields;
- configuration for collection ID, Top-K, thresholds, verification counts and
  timing;
- domain `Person` and multiple `FaceEnrollment` values;
- a PostgreSQL/Redis Compose file, but no database schema, migrations, or
  repositories;
- no FAISS dependency, adapter, index artifacts, identity collection model,
  compatibility key, index revision model, or recognition runtime integration.

The claimed Phase 3–5 runtime is not present: there is no real YOLO, BoT-SORT,
SCRFD, `FaceSample`, face-quality pipeline, alignment implementation, AdaFace
adapter, or `FaceEmbedding`. The Phase 5 design records the same blocker. The
project-local `vision-pipeline-engineering` skill is also absent; the available
`face-pipeline-engineering` and newly validated
`recognition-verification-engineering` skills were applied.

The existing verifier is useful as a behavioral seed but is not the Phase 6
implementation. It assumes higher-is-better scores, treats a lone candidate as
having margin `1.0`, does not aggregate enrollment hits, lacks collection/config
revisions, and can classify terminal conflicting evidence as `UNKNOWN`.
`TrackState.observations` is independently unbounded.

Phase 6 implementation planning is blocked until the checkout containing the
completed Phase 3–5 code is provided or those phases are implemented and
verified. Phase 6 must not absorb that missing work silently.

## Considered Approaches

### A. Exact immutable FAISS revisions with a separated verifier (recommended)

Use normalized embeddings in `IndexIDMap2(IndexFlatIP)`, explicit mapping,
immutable revision bundles, identity aggregation, and a pure deterministic
verifier. It is exact, training-free, easy to test, and appropriate before
collection scale and latency requirements are measured.

### B. Approximate IVF/HNSW index in the MVP

This may improve large-collection performance, but introduces training or index
parameters, approximate-score behavior, recall evaluation, and more complex
rebuild validation before the collection size is known. It is deferred.

### C. PostgreSQL or Python brute-force search only

This would simplify artifact management but would not prove the approved FAISS
adapter boundary and could encourage per-query database access. It remains a
test double or recovery diagnostic, not the Phase 6 runtime.

## Architecture

```text
Control/build path

PostgreSQL enrollments (authoritative)
  -> IndexBuildCoordinator
  -> compatible enrollment snapshot
  -> FaissIndexBuilder + ID mapping
  -> validate/checksum/persist revision bundle
  -> load/warm
  -> atomic runtime activation
  -> persist active revision / retire old revision
  -> publish revision-change signal

Realtime path

FaceEmbedding
  -> RecognitionScheduler
  -> compatibility validation
  -> VectorStore.search
  -> EnrollmentSearchHit[]
  -> IdentityCandidateAggregator
  -> RecognitionObservation
  -> MultiFrameVerifier
  -> IdentityDecision
  -> TrackState update/cache
```

The realtime path never queries PostgreSQL, loads an index, mutates an active
index, serializes vectors as JSON, or contains FAISS types. Index build and
activation are infrastructure operations separate from per-frame search.

## VectorStore Contract

The current mutable protocol is replaced by read-only runtime search plus a
separate lifecycle boundary:

```python
class VectorStore(Protocol):
    def search(
        self,
        query: FaceEmbedding,
        collection_id: str,
        top_k: int,
    ) -> VectorSearchResult: ...


class VectorIndexLifecycle(Protocol):
    def load(self, revision: VectorIndexRevision) -> LoadedIndex: ...
    def validate(self, loaded: LoadedIndex) -> None: ...
    def warm(self, loaded: LoadedIndex) -> None: ...
    def activate(self, loaded: LoadedIndex) -> ActivationResult: ...
    def close(self, revision_id: str) -> None: ...
```

`IndexBuildCoordinator` owns construction. Runtime `VectorStore` has no
`add/remove`; enrollment mutations go through PostgreSQL and request a rebuild.

`VectorSearchResult` contains collection/revision/compatibility metadata,
ordered `EnrollmentSearchHit` values, search latency, and a successful empty
result when an active compatible index has no vectors or matches. It never
exposes FAISS indexes, NumPy buffers, or row positions. Typed failures distinguish
`INDEX_NOT_READY`, `INDEX_INCOMPATIBLE`, `INVALID_QUERY_EMBEDDING`, and
`SEARCH_FAILURE`; `SEARCH_NO_MATCH` is a successful empty result, not an
exception.

## FAISS MVP Index Strategy

The MVP uses CPU `IndexIDMap2(IndexFlatIP(d))`:

- `IndexFlatIP` performs exact, training-free search. FAISS documents Flat IP/L2
  as the exact-search options in its
  [index-selection guidance](https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index).
- Both enrollment and query vectors must already be finite, dimensionally
  compatible, and L2-normalized. FAISS documents that inner product represents
  cosine similarity only for normalized vectors in its
  [metric guidance](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances).
- The embedder remains the only normalization owner. The vector store validates
  the `normalized` contract and norm tolerance but never normalizes again.
- `IndexIDMap2` receives a stable signed 64-bit `vector_id`; the mapping bundle
  resolves that ID to enrollment, face identity, and person. It is never exposed
  as a domain identity.
- `faiss-cpu` is an optional worker dependency. No GPU or TensorRT FAISS behavior
  is claimed in Phase 6.

An active collection with zero enrollments has a valid empty revision and
returns successful no-match results. A collection with no active revision yields
`INDEX_NOT_READY` and cannot contribute an observation.

`top_k` means the maximum number of identity candidates exposed downstream, not
the number of enrollment vectors. Because one person may occupy several leading
enrollment positions, the adapter retrieves enrollment hits adaptively: begin
with at least `max(top_k, 2)` results and double the requested count until it has
enough distinct people or reaches `ntotal`. Once K distinct people have appeared
in score order, their first appearances are the exact top K identity best scores.
The candidate aggregator then truncates to identity Top-K.

## Similarity, Threshold, and Margin Semantics

The Phase 6 MVP has one `MetricPolicy`:

```text
metric: cosine_similarity_via_inner_product
direction: higher_is_better
score range: [-1, 1]
qualification: score >= similarity_threshold
margin: best distinct-person score - runner-up distinct-person score
```

Threshold equality qualifies. Sorting is descending by score, then stable
enrollment ID; identity candidates tie-break by score, best enrollment score,
then stable person ID. If there is no runner-up identity, margin is `None` with
`margin_satisfied=true`; no artificial numeric margin is invented.

All comparisons flow through `MetricPolicy`; verifier and orchestration code do
not scatter raw `>=` assumptions. The threshold is a calibration parameter bound
to collection, embedding compatibility, metric, and active configuration/
calibration revision. Phase 6 implements mechanics only and does not claim that
the current `0.72` default is production-optimal.

## Compatibility Model

`EmbeddingCompatibilityKey` is an immutable value shared by `FaceEmbedding`,
`IdentityCollection`, and `VectorIndexRevision`. It contains:

- model definition and version plus artifact fingerprint;
- embedding dimension;
- normalization profile and normalized flag;
- alignment and preprocessing profile revisions;
- distance metric and score interpretation.

The active collection also binds a calibration/configuration revision. Before
FAISS is called, the vector store validates query finiteness, length, unit-norm
tolerance, and exact compatibility-key equality. Any mismatch is
`INDEX_INCOMPATIBLE`, leaves verification state unchanged, and updates technical
failure/health metrics. It never becomes `UNKNOWN`.

## Persistent Identity and Index Models

PostgreSQL remains authoritative. Phase 6 introduces repository contracts and
migrations for:

- `identity_collections`: collection ID, name, compatibility key, calibration
  revision, active revision pointer, and lifecycle metadata;
- `face_identities`: stable identity ID and owning person ID;
- `face_enrollments`: stable enrollment/vector ID, face identity, embedding,
  complete compatibility metadata, quality/provenance, and active flag;
- `vector_index_revisions`: revision ID, collection, state, compatibility,
  vector count, source-enrollment snapshot/revision, build timestamps, artifact
  references/checksums, failure reason, and activation/retirement timestamps.

The MVP uses PostgreSQL `real[]` for authoritative embedding values and does not
require pgvector search. Repository reads occur only in enrollment/build paths.
SQLAlchemy 2, psycopg 3, and Alembic are the selected persistence/migration
boundary because no repository framework currently exists.

The index revision bundle contains the FAISS artifact, stable-ID mapping, and a
canonical metadata manifest. All components have checksums and matching vector
counts. Before `faiss.read_index`, the loader verifies configured path
containment, expected file size, and checksum; after loading it validates
dimension, metric, `ntotal`, IDs, mapping cardinality, and compatibility. This is
required because FAISS warns that index loading does not validate file safety or
integrity in its [index I/O documentation](https://github.com/facebookresearch/faiss/wiki/Index-IO%2C-cloning-and-hyper-parameter-tuning).

## Index Revision Lifecycle and Atomicity

Allowed persisted states are `BUILDING`, `READY`, `ACTIVE`, `FAILED`, and
`RETIRED`:

```text
enrollment commit -> rebuild request -> BUILDING
-> repeatable-read enrollment snapshot
-> compatibility/cardinality validation
-> build index + mapping + manifest in temporary revision location
-> checksum and reload validation -> READY
-> load/warm staged runtime snapshot
-> activation lock
-> atomic runtime reference swap + PostgreSQL active-pointer transaction
-> ACTIVE new revision / RETIRED old revision
-> publish reset signal
-> release old snapshot after readers drain
```

Any pre-activation failure marks the new revision `FAILED` and leaves the old
active revision serving searches. Local artifact publication uses a temporary
file, flush/fsync, and same-filesystem atomic rename. Activation retains the old
loaded snapshot until both persistence and runtime steps succeed; a database
failure swaps the runtime pointer back before releasing the lock. On process
restart, PostgreSQL's active pointer is authoritative and the worker reloads and
validates that revision, reconciling any crash between memory and database
steps.

The MVP targets one vision-worker process. Multi-worker fleet-wide activation
would require readiness acknowledgements and rollout orchestration and is not
claimed as globally atomic in Phase 6.

## Concurrency

Each search acquires a short read lease on one immutable
`(index, mapping, metadata)` snapshot, releases the manager lock, and searches
that same snapshot for the entire call. Builders never mutate it. Activation
uses a short writer lock/reference swap; retirement waits for leases to drain.

FAISS documents CPU indexes as safe for concurrent searches when no operation
changes the index, while modifying operations need mutual exclusion
([threading guidance](https://github.com/facebookresearch/faiss/wiki/Threads-and-asynchronous-calls)).
Phase 6 relies only on concurrent reads and immutable replacement. Backend-only
OpenMP thread limits prevent oversubscription; batching is a future measured
optimization rather than part of the domain contract.

## Enrollment-to-Identity Mapping and Aggregation

Mapping is explicit:

```text
FAISS vector_id -> FaceEnrollment -> FaceIdentity -> Person
```

`EnrollmentSearchHit` contains stable vector/enrollment/identity/person IDs,
score, enrollment rank, collection, index revision, and compatibility key.
`IdentityCandidateAggregator` groups hits by person and emits:

- `person_id` and `face_identity_id`;
- `aggregated_score`, defined as that person's best enrollment score;
- best enrollment ID/score;
- number of supporting enrollment hits in the examined search prefix;
- identity rank and runner-up/margin metadata.

Using the best enrollment score prevents people with more enrollment images
from receiving extra votes. Supporting count is diagnostic and does not multiply
temporal vote weight. Candidate order is deterministic.

## RecognitionObservation

A frozen observation contains:

- camera, stream session, track, frame, source sample, and timestamp;
- accepted face-quality score;
- successful search outcome and ordered identity candidates;
- collection ID, index revision, embedding compatibility/model revision;
- configuration and calibration revision.

It contains no face/aligned image, embedding vector, FAISS object, or event
metadata. Observations are unique by source sample and frame within one
camera/session track. A verification window uses one exact collection,
compatibility key, index revision, and configuration/calibration revision.

## Deterministic `quality_weighted_vote`

Only accepted Phase 5 embeddings with successful compatible searches produce
observations. For each observation:

1. Aggregate enrollment hits into distinct-person candidates.
2. The top candidate is score-qualified when `score >= recognition.similarity_threshold`.
3. It is vote-qualified when score-qualified and either no runner-up exists or
   `top_score - runner_up_score >= verification.min_candidate_margin`.
4. A vote-qualified observation casts exactly one vote for its top person.
   A successful empty/below-threshold search is valid no-match evidence. A
   score-qualified candidate with insufficient margin is ambiguous evidence.
5. Vote weight is `clamp(quality_score, 0, 1)`. Accepted samples must have a
   positive weight.

For each identity `p` in a window of `N` valid observations:

```text
support(p) = number of vote-qualified observations voting for p
consistency(p) = support(p) / N
weighted_similarity(p) = sum(quality_i * score_i) / sum(quality_i)
minimum_margin(p) = minimum finite margin among p's supporting observations
```

An absent runner-up passes the margin check but contributes no numeric value to
`minimum_margin`. Deterministic winner ordering is support, consistency,
weighted similarity, minimum margin, then stable person ID.

`VERIFIED` requires all of:

- `N >= min_good_frames`;
- at least `min_good_frames` independent vote-qualified observations for the
  same person (and therefore never one frame);
- consistency `>= identity_consistency`;
- weighted similarity `>= recognition.similarity_threshold`;
- every supporting observation satisfies the configured margin;
- one compatible collection/model/index/configuration generation.

If no identity verifies, the window remains `PENDING` until it reaches
`max_frames` or `timeout_ms`. At that terminal point:

- `UNKNOWN` requires `N >= min_good_frames`, every search successful, and no
  observation containing a score-qualified identity candidate;
- `UNCERTAIN` applies when any score-qualified or margin-ambiguous identity
  evidence exists but no identity verifies, or when timeout occurs with some
  valid evidence but fewer than `min_good_frames` observations;
- zero valid observations caused by technical failures leave the state
  `PENDING` and surface a technical failure instead of an identity decision.

## IdentityDecision

`IdentityDecision` contains state, optional person/face-identity ID, optional
score, evidence count, deterministic reason code, collection/model/index/config
revisions, and decision timestamp.

- `VERIFIED` requires person ID and score.
- `UNKNOWN` has no person ID.
- `UNCERTAIN` normally has no public person ID; leading-candidate context may
  remain internal for diagnostics.
- `PENDING` has no person ID and is not emitted as a business event.

Reason codes include `INSUFFICIENT_EVIDENCE`, `CRITERIA_SATISFIED`,
`NO_QUALIFYING_CANDIDATE`, `CONFLICTING_CANDIDATES`, `INSUFFICIENT_MARGIN`, and
`WINDOW_TIMEOUT`. Technical search/index errors are separate result types.

## State Transition Table

| Current | Condition | Next | Window action |
|---|---|---|---|
| PENDING | Compatible valid evidence, window open, criteria unmet | PENDING | append bounded observation |
| PENDING | All verification criteria pass | VERIFIED | retain bounded decision summary; clear observation images/vectors (none exist) |
| PENDING | Terminal window, sufficient valid evidence, no score-qualified identity | UNKNOWN | close and retain summary only |
| PENDING | Terminal window with conflicting/ambiguous evidence | UNCERTAIN | close and retain summary only |
| PENDING | Technical/index/search failure | PENDING | append no observation; record failure/backoff |
| UNKNOWN | Retry time reached with eligible sample | PENDING | start fresh window |
| UNCERTAIN | Retry time reached with eligible sample | PENDING | start fresh window |
| VERIFIED | Cache valid and generation unchanged | VERIFIED | reuse cached identity; no search |
| VERIFIED | TTL/generation/tracking validity expires | PENDING | clear cached decision; start fresh window |
| Any live state | Model/index/collection/config generation changes | PENDING | reset window/cache before new observation |
| Any | Track expires | terminated | release all state |

State changes occur through one transition function so scheduler, verifier, and
TrackState cannot update fields independently.

## UNKNOWN, UNCERTAIN, and Failure Semantics

`UNKNOWN` means sufficient valid biometric observations were embedded and
searched successfully against a ready compatible index, but none reached the
score threshold. It never means low face quality, missing face, AdaFace failure,
invalid query, missing index, incompatibility, corrupt artifact, search failure,
or insufficient evidence.

`UNCERTAIN` means valid evidence exists but is conflicting or ambiguous:
alternating identities, a score-qualified candidate with inadequate margin,
insufficient consistency, or window timeout/max count before reliable
verification. It is not a general exception bucket.

Explicit operational outcomes are `SEARCH_NO_MATCH`, `SEARCH_FAILURE`,
`INDEX_NOT_READY`, `INDEX_INCOMPATIBLE`, and `INVALID_QUERY_EMBEDDING`. Explicit
verification results are `VERIFICATION_PENDING`, `VERIFICATION_VERIFIED`,
`VERIFICATION_UNKNOWN`, and `VERIFICATION_UNCERTAIN`.

## Re-verification and TrackState

`TrackState` is extended only with one bounded `VerificationWindow` and cached
decision metadata:

- recognition state and bounded observations (`deque(maxlen=max_frames)`);
- leading candidate internally while pending;
- verified person/face-identity, score, and verification time;
- verified compatibility, collection, index, configuration/calibration revisions;
- last/next recognition times and last reset reason;
- latest technical failure summary without biometric payloads.

The scheduler uses existing `recognition_interval_ms`, `recognition_retry_ms`,
and `verified_identity_ttl_ms`. Verified state avoids search until TTL expires or
track association becomes invalid. Collection, index, embedding, configuration,
or calibration generation changes reset before the next observation. Track
expiration removes the entire window/cache. Strong contradictory evidence is
not an MVP trigger because verified tracks are not continuously searched; the
state machine exposes an explicit reset hook for a future audited strategy.

Per-frame verification state remains in process memory and is not persisted to
PostgreSQL.

## Configuration

Phase 6 uses the existing UI-editable fields:

- `recognition.identity_collection_id`, `top_k`, and `similarity_threshold`;
- `verification.strategy`, `min_good_frames`, `max_frames`, `timeout_ms`,
  `identity_consistency`, and `min_candidate_margin`;
- `timing.recognition_interval_ms`, `recognition_retry_ms`,
  `verified_identity_ttl_ms`, and `track_cache_ttl_ms`.

`verification.similarity_threshold` is removed as a duplicate; the single owner
is `recognition.similarity_threshold`. Because the project has no persisted
configuration repository yet, the feature schema advances to version 2 and the
example/tests migrate directly. Cross-field validation requires
`track_cache_ttl_ms > verification.timeout_ms` and preserves
`min_good_frames <= max_frames`. Internally the adapter retrieves at least two
distinct identities when available so `top_k=1` does not disable margin
calculation.

Backend-only runtime settings add index artifact root, FAISS/OpenMP thread
limit, revision poll/activation settings, and safe artifact size limit. They are
not UI-editable.

## Metrics and Diagnostics

Runtime status gains aggregate fields:

- `vector_search_attempts`, `vector_search_failures`, last/rolling-average
  search latency, and successful no-match count;
- `verification_observations`, `verification_pending`,
  `verification_verified`, `verification_unknown`, `verification_uncertain`,
  and `verification_resets` by fixed reason enum;
- `active_identity_collection`, `active_index_revision`, active vector count,
  and index readiness/compatibility state.

Logs may include collection/revision, model compatibility fingerprint, metric,
result count, decision reason, evidence count, and latency. They exclude person
identity, enrollment IDs, embedding vectors, and face images from ordinary
metrics/logs.

## Testing Strategy

All normal tests are CPU-only and use deterministic vectors.

### Vector and compatibility

- exact nearest neighbor and deterministic Top-K order;
- threshold equality and metric-direction behavior;
- empty active index versus no active index;
- wrong dimension/model/version/alignment/preprocessing/normalization/metric;
- invalid, non-finite, and non-unit query vectors;
- index/map cardinality, duplicate/missing IDs, checksum and corrupt-artifact
  rejection;
- mock/in-memory and FAISS contract parity.

### Mapping and aggregation

- vector ID to enrollment to face identity to person;
- multiple enrollments for one person do not multiply temporal votes;
- adaptive over-fetch produces exact identity Top-K;
- distinct-person runner-up and no-runner-up margin behavior;
- deterministic tie-breaking.

### Verification and state

- one frame never verifies and insufficient evidence remains pending;
- stable high-quality candidate verifies at exact configured boundaries;
- low-quality accepted weighting, no-match observations, and weighted score;
- alternating identities, near/above-threshold inadequate margins, conflicting
  candidates, timeout, and max-frame terminal behavior;
- sufficient all-below-threshold evidence becomes unknown;
- ambiguous evidence becomes uncertain;
- every transition in the table, unknown/uncertain retry, verified cache/TTL,
  track expiry, and model/index/collection/config/calibration invalidation;
- technical failures create no observation and never become unknown.

### Lifecycle and integration

- PostgreSQL snapshot/revision state transitions and failed-build rollback;
- build/load/warm/atomic activation while searches continue on the old snapshot;
- concurrent CPU searches, reader leases, swap, and delayed old-index close;
- crash/restart reconciliation from PostgreSQL's active pointer;
- `FaceEmbedding -> search -> aggregation -> observation -> decision ->
  TrackState` using Phase 5 mocks once those contracts exist;
- all earlier camera, YOLO, tracking, ROI, SCRFD, quality, alignment, embedding,
  API/WebSocket, lint, typecheck, build, and startup suites.

No model or enrollment dataset is downloaded automatically. Performance and
accuracy claims require operator-supplied representative data.

## Performance and Resource Boundaries

- Build/load/warm once per revision and reuse; never rebuild or reload per query.
- Search only eligible scheduled embeddings; never every frame after verified.
- Query the already loaded snapshot; never PostgreSQL/Redis per attempt.
- Keep observations bounded by `max_frames` and `timeout_ms`.
- Build replacements in a background worker outside runtime search locks.
- Use exact Flat IP until measured collection size/latency justifies an
  approximate index and recall evaluation.
- Avoid internal JSON serialization of vectors and unnecessary copies.
- Put explicit limits on artifact size, vectors per MVP collection, build memory,
  and concurrent builders before production deployment.

## Expected Implementation Files

Paths must be reconciled after the completed Phase 3–5 checkout is available.
The expected product-code change surface is:

- `pyproject.toml` — optional FAISS, SQLAlchemy, psycopg, and Alembic groups;
- database migrations and repository implementations for persons, face
  identities, enrollments, collections, and index revisions;
- `packages/python/face-recognition-domain/src/fr_domain/entities.py` and
  `recognition.py` — compatibility, candidates, observations, decisions, metric
  policy, verifier, and transition contracts;
- `packages/python/face-recognition-config/src/fr_config/models.py` and runtime
  settings — schema v2 cleanup and backend index settings;
- `workers/vision-worker/src/vision_worker/vector_store/interfaces.py` —
  immutable search/lifecycle contracts;
- new vector-store FAISS adapter, artifact bundle, builder, registry/manager,
  identity aggregator, and recognition orchestrator modules;
- `workers/vision-worker/src/vision_worker/face_recognition/scheduler.py`,
  `runtime/track_store.py`, and `runtime/pipeline.py` — scheduling, bounded state,
  activation resets, and integration;
- runtime-status Python/TypeScript/API/WebSocket contracts and status-only UI;
- focused domain, adapter, lifecycle, concurrency, repository, integration, and
  regression tests.

No policy, event, evidence, notification, or event-dashboard file belongs in
the Phase 6 implementation.

## Remaining Unresolved Decisions

1. **Phase 3–5 implementation (blocking):** restore/provide the completed source
   or implement and verify those phases before Phase 6 planning.
2. **Embedding compatibility/artifact (blocking for integration):** the approved
   AdaFace artifact, compatibility key, and real `FaceEmbedding` contract remain
   absent, as recorded in the Phase 5 design.
3. **Calibration input (blocking for production automatic verification):** no
   representative validation data or approved calibration profile exists. The
   threshold mechanics can be implemented, but `0.72` cannot be presented as a
   production-validated threshold.
4. **Deployment sizing (non-blocking for the exact MVP):** collection size,
   enrollment distribution, latency target, available Jetson FAISS package, and
   memory budget must be measured before setting production limits or replacing
   Flat IP with an approximate index.

## Design Review Result

This design preserves the `VectorStore` boundary, PostgreSQL authority,
embedding compatibility, explicit metric direction, calibrated-threshold
boundary, identity-level aggregation, multi-frame-only verification, bounded
revision-consistent state, exact UNKNOWN/UNCERTAIN semantics, immutable atomic
index replacement, deterministic tests, and Phase 6 scope. It does not conceal
the missing Phase 3–5 prerequisites or introduce policy/event behavior.
