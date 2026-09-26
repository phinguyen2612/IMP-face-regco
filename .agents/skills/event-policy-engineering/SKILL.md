---
name: event-policy-engineering
description: Use when designing, implementing, or reviewing recognition policies, event candidates, event deduplication or cooldown, evidence capture/storage, event persistence, or realtime event delivery.
---

# Event Policy Engineering

Protect the boundary between recognition and business events:

```text
AI/Recognition -> Domain Result -> Policy -> EventCandidate
-> Event Engine -> DomainEvent -> Evidence
```

Recognition components never choose event type/severity, persist business
events, capture evidence, publish notifications, or shape frontend payloads. A
recognition state is policy input, not an event.

## Ownership

Use `recognition-verification-engineering` for `IdentityDecision` semantics. Use
the general vision-pipeline skill when available for frame buffers, scheduling,
backpressure, and worker lifecycle. This skill owns deterministic business
policy evaluation, event mechanics, persistence ordering, evidence orchestration,
and domain-level realtime delivery.

## Invariants

- Give policy an explicit immutable context; resolve identity groups, ROI,
  schedule, dwell, configuration revision, and provenance before evaluation.
  Policy rules do not query databases or hide temporal state.
- Policy returns `EventCandidate` or no event. The event engine alone owns
  conflict resolution, deduplication, cooldown, event identity, and final
  emission. Never persist a candidate directly.
- Scope dwell and suppression with camera/session/track or person as appropriate;
  `track_id` alone is never globally unique. Keep persistent event IDs separate
  from deduplication keys and never use embeddings as keys.
- Make schedule timezone and interval boundaries explicit. Configuration changes
  have defined dwell, deduplication, cooldown, and pending-evidence semantics.
- A committed `DomainEvent` is immutable history. Persist before realtime
  publication; specify idempotency, retry, replay, and delivery guarantees.
- Trigger evidence only from an emitted event. Evidence failure updates evidence
  status but never erases a valid event.
- Use bounded asynchronous evidence work and bounded ring-buffer history. Define
  overload, missing-frame, partial-clip, storage, encoder, and shutdown behavior.
- Persist opaque `BlobStorage` keys/references, never local paths. Do not log image
  bytes, store every face crop, or expose biometric data through metrics.
- Keep WebSocket messages versioned and domain-oriented; normal event transport
  never streams frames or couples to React component shapes.
- Distinguish policy no-match/configuration error, duplicate/cooldown suppression,
  persistence failure, evidence capture/storage failure, and publication failure.

## Task References

- For policy contracts, priority, temporal state, event identity, persistence,
  failures, and tests, read [references/policy-events.md](references/policy-events.md).
- For snapshot/clip capture, storage, evidence lifecycle, realtime delivery,
  privacy, and backpressure, read
  [references/evidence-delivery.md](references/evidence-delivery.md).

## Review Checklist

- [ ] Recognition result separated from business event
- [ ] Inference does not emit business events directly
- [ ] Policy deterministic
- [ ] `EventCandidate` separate from `DomainEvent`
- [ ] Deduplication explicit
- [ ] Cooldown explicit
- [ ] Schedule timezone explicit
- [ ] Dwell state correctly scoped
- [ ] Event immutable after emission
- [ ] Evidence only created for emitted events
- [ ] Evidence failure does not erase event
- [ ] `BlobStorage` abstraction preserved
- [ ] No uncontrolled biometric persistence
- [ ] Persistence precedes or coordinates realtime publication
- [ ] WebSocket domain-oriented and versioned
- [ ] Tests cover suppression and failure paths
