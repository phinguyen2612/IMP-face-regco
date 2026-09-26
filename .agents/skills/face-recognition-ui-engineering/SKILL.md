---
name: face-recognition-ui-engineering
description: Use when designing, implementing, or reviewing React control-plane, realtime monitoring, ROI editing, enrollment, event/evidence, configuration lifecycle, or runtime-status UX for a face-recognition system.
---

# Face Recognition UI Engineering

Treat the UI as a typed control and observation plane. Backend/domain services
remain authoritative for recognition, policy, validation, activation, runtime,
events, evidence, and enrollment.

## Ownership

Use `recognition-verification-engineering` for identity semantics and
`event-policy-engineering` for event/evidence lifecycle. Do not duplicate their
backend rules in React.

## Invariants

- Separate server resources from local selections, drafts, dialogs, filters, and
  temporary ROI vertices. Avoid unrelated global copies of server state.
- Model configuration as `edit -> validate -> save draft -> activate -> applied
  runtime revision`. A saved draft is never displayed as active. Frontend checks
  aid users; backend validation remains authoritative and errors stay specific.
- Expose only API-approved product fields. Never store credentials, internal
  paths, infrastructure details, FAISS IDs, or embeddings.
- Persist ROI vertices only as normalized coordinates in `[0,1]` for the
  backend-defined canonical source frame. Drawing never activates config.
- Use one managed, typed WebSocket per realtime endpoint/context with explicit
  lifecycle, bounded backoff, cleanup, and no duplicate subscriptions. Durable
  snapshot/history APIs remain authoritative; reconnect reconciles resources.
- Use a backend-supported browser preview adapter. Never send RTSP credentials to
  the browser or invent a parallel video architecture.
- Keep Person distinct from Enrollment. React presents backend results; it never
  validates faces, computes embeddings, or claims index activation.
- Render event identity exactly as supplied by the backend. Handle evidence
  `PENDING`, `READY`, and `FAILED` independently of event creation.
- Distinguish configured from runtime states. Never infer healthy or searchable
  from configuration alone.
- Resource views handle loading, empty, success, and typed errors; realtime adds
  disconnected/reconnecting. Destructive actions use accessible confirmation.
- Centralize API/WebSocket types and parsing; avoid `any`. Separate page
  composition, feature components, clients, forms, geometry, presentation, and
  generic primitives.
- Bound realtime collections, throttle visual updates, cancel stale requests,
  release listeners/object URLs, and keep large media out of global state.
- Provide labels, keyboard/focus behavior, semantic controls, and non-color status.
- If an API/contract is missing, record a backend gap with the minimal required
  capability. Do not fabricate server state or hide the gap in frontend logic.

## Task References

- Configuration and ROI: [references/configuration-roi.md](references/configuration-roi.md)
- Realtime operations: [references/realtime-operations.md](references/realtime-operations.md)
- Enrollment and structure: [references/enrollment-ui.md](references/enrollment-ui.md)

## Review Checklist

- [ ] Backend remains authoritative
- [ ] Draft is distinct from active
- [ ] Backend-only configuration hidden
- [ ] API types centralized
- [ ] WebSocket lifecycle explicit
- [ ] Reconnect reconciles state
- [ ] ROI persisted normalized
- [ ] Person distinct from Enrollment
- [ ] Embeddings never exposed
- [ ] Evidence PENDING/READY/FAILED handled
- [ ] Runtime health distinct from configured state
- [ ] Loading/empty/error states implemented
- [ ] Destructive actions confirmed
- [ ] No giant page components
- [ ] Realtime memory bounded
- [ ] Critical workflows tested
