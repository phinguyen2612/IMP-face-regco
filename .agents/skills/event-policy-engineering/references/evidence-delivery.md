# Evidence and Realtime Delivery

## Evidence Lifecycle

Create evidence requests only after the event engine accepts a candidate. Persist
evidence metadata linked to the committed event with explicit `PENDING`, `READY`,
or `FAILED` state. Capture/storage failure never deletes or rolls back the event;
record a bounded failure code, retry count, and timestamps instead.

Snapshot selection uses stable frame provenance or nearest timestamp from the
bounded source buffer. Render overlays on a copy so inference frames remain
unchanged. Store the configured evidence artifact, not every face crop, and keep
original-versus-rendered behavior explicit.

The vision pipeline owns frame production and the bounded camera buffer; evidence
orchestration owns only event-triggered frame selection, leases/copies, and work
admission. For clips, select a documented event-relative interval: buffered pre-event
frames plus future post-event frames from the same camera and stream session.
Validate buffer retention against the configured pre-window. Define timestamp
selection, incomplete prehistory, session change, track disappearance, camera
loss, encoder failure, and partial-clip policy. Track disappearance alone need
not stop camera-level post-event collection.

## Bounded Work and Storage

Snapshot rendering, post-event collection, encoding, and blob writes run outside
the inference path through capacity-limited work queues. Define admission
timeout, overflow status, per-event memory/frame limits, worker concurrency,
retry/backoff, graceful drain deadline, and stale-job recovery. Never create an
unbounded frame history or evidence queue.

Depend on `BlobStorage`, not filesystem APIs. Persist opaque keys and content
metadata; return controlled references or API download URLs rather than local
paths. Local storage must enforce containment and atomic writes. Future S3/MinIO
adapters preserve the same put/get/delete/reference contract. Define retention,
deletion, authorization boundary, and whether stored artifacts are encrypted;
never log bytes or secrets.

## Realtime and Tests

Publish versioned domain messages such as `event.created`, `evidence.ready`, and
`evidence.failed` only after their database state commits. Messages carry stable
event/evidence IDs and queryable metadata, not image bytes or UI component state.
Use durable publication intent when failures must be retried; disconnected
clients recover through REST and may deduplicate at-least-once messages by ID.

Tests use fake frames, clock, encoder, storage, repository, and publisher. Cover
snapshot selection, overlay immutability, pre/post windows, missing frames,
partial clips, storage/encoder failures, bounded queue saturation, shutdown,
blob-key containment and atomicity, state transitions, publication ordering,
retry/replay, contract versioning, and privacy/logging constraints. Metrics
include bounded queue depth/overflow, latency, success/failure codes, and
publication retries without person identifiers.
