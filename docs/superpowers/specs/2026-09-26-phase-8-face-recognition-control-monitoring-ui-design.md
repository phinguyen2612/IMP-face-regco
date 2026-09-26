# Phase 8: Face Recognition Control and Monitoring UI Design

## Status and approval gate

This document is the Phase 8 design specification. It changes no product code
and does not authorize an implementation plan or implementation. Phase 8 makes
the Face Recognition system operable through a React control and monitoring UI;
it adds no recognition logic, AI model, general IOC feature, or Phase 9 work.

Implementation planning may begin only after the user replies exactly:

`APPROVE PHASE 8 DESIGN`

The prerequisite and backend-capability gates below must also be resolved before
the affected UI slices can be implemented honestly.

## Scope and repository audit

Phase 8 includes navigation/layout, overview, camera management, face-recognition
configuration and revision lifecycle, ROI editor, safe model status, people and
multiple enrollments, index status presentation, live operations, events and
evidence, runtime diagnostics, typed HTTP/WebSocket clients, reconciliation,
accessibility, frontend tests, a mocked end-to-end workflow, and only the minimal
backend gaps required by those pages.

It excludes new AI algorithms/models, TensorRT work, training/calibration,
analytics, cross-camera tracking, notifications, general IOC dashboards,
Gathering, Restricted Area, Uniform/PPE, and full authentication/RBAC.

The repository is the implementation source of truth. It currently has:

- React 19.3, ReactDOM 19.3, Vite 8.3, TypeScript 7 strict mode, and React Strict
  Mode;
- one `App` component, one global stylesheet, no routes/pages, no component
  library, and no design system beyond a small dark scaffold;
- one `fetch` health call and one direct WebSocket helper;
- handwritten TypeScript contracts only for the envelope and runtime status;
- no router, server-state/query library, global-state library, form library,
  frontend tests, test script, or E2E framework;
- only backend health, static stub model list, camera/config validation,
  in-memory runtime-status GET/PUT, and a WebSocket that publishes
  `system.ready` and changed `runtime.status` messages;
- configuration Pydantic models for camera/RTSP/ROIs, model selections, quality,
  recognition, verification, timing, schedule, policies, and evidence;
- no persistent camera/config revision endpoints, people/enrollment APIs,
  collection/index lifecycle API, events/evidence API, browser preview, or live
  recognition contract;
- Phase 5-7 design documents but not their claimed product implementations. The
  checkout remains the Phase 2 mock runtime with partial recognition scaffolding.

Phase 8 implementation is therefore blocked as an end-to-end phase until the
completed Phase 3-7 checkout is supplied or those phases are implemented and
verified. UI code must not manufacture missing server behavior.

## Considered approaches

### A. Domain-sliced SPA with small, justified infrastructure (recommended)

Add React Router for navigation, TanStack Query for authoritative REST state and
reconciliation, a single custom typed WebSocket service, generated OpenAPI types,
native controlled forms/reducers, SVG ROI editing, and the existing CSS approach
with tokens and feature-scoped styles. Add Vitest, React Testing Library, MSW,
and Playwright for behavior/E2E tests. This introduces dependencies only where
the current scaffold demonstrably lacks required infrastructure.

### B. Zero-dependency custom router and resource cache

This keeps production dependencies minimal but recreates routing, cancellation,
cache invalidation, retry, stale-state, and navigation behavior. Phase 8 has too
many authoritative resources for this to remain simpler or safer.

### C. Expand the current single page with tabs and manual fetch effects

This appears fastest but produces the exact giant-component, duplicated-server-
state, socket-lifecycle, and error-state problems the UI skill prevents. It is
rejected.

Approach A is selected. No Redux/Zustand, form framework, canvas framework,
Tailwind, or large component library is added. Those have no demonstrated need.

## 1. Existing frontend stack

The implementation preserves Vite, React, strict TypeScript, React Strict Mode,
the current dev proxy, and CSS. `npm run dev`, `build`, and `typecheck` remain.
Add:

- React Router for URL-addressable pages and details;
- TanStack Query for REST server state, cancellation, pagination, invalidation,
  and reconnect reconciliation;
- `openapi-typescript` as a development generator from a checked-in FastAPI
  OpenAPI artifact, wrapped by project-specific clients;
- Vitest + React Testing Library + user-event + MSW for component/integration
  behavior;
- Playwright for one mocked-network E2E workflow.

Forms use React state/reducers and shared field primitives. ROI uses SVG. Styling
extends the existing dark operational language through CSS custom properties,
layout utilities, and feature styles instead of importing a component library.

## 2. Information architecture

The Face Recognition UI contains only:

```text
Overview
Cameras
  Camera detail
  ROI editor
Recognition Configuration
Models
People & Enrollment
  Person detail / enrollment samples
Live Recognition
Events
  Event detail / evidence
Runtime Status
```

Configuration and ROI remain distinct tasks but share the selected camera and
revision context. People owns enrollment; Enrollment is not a top-level person
substitute. Event history stays separate from transient live state.

## 3. Navigation

A desktop-first application shell uses a left navigation rail, top context bar,
and main content landmark. Routes are:

```text
/
/cameras
/cameras/:cameraId
/cameras/:cameraId/roi
/configuration/:cameraId
/models
/people
/people/:personId
/live
/events
/events/:eventId
/runtime
```

Routes preserve shareable filters in query parameters only when values are not
sensitive. Unknown resources render a typed not-found state. The shell owns one
WebSocket provider/client; pages never open independent sockets. At narrower
widths the rail collapses to a labeled menu while operational tables scroll or
adapt rather than becoming low-information mobile cards.

## 4. Overview

Overview is a bounded operational summary, not analytics. It queries server
resources for:

- configured and connected camera counts;
- enabled face-recognition configurations and active/applied revisions;
- worker health;
- selected/loaded model deployments and active FAISS index revision;
- a small server-limited recent-event list;
- count/list of recent evidence failures.

Each tile links to its authoritative detail page and states `Unavailable` when
the backend lacks data. Configured cameras are not counted as online; selected
models are not shown loaded; enabled configuration is not shown applied. Empty,
partial-error, loading, and stale/disconnected states are independent so one
failed resource does not blank the page.

## 5. Camera UX

Camera list shows name, enabled state, feature association, connection state, and
last backend update. Create/edit uses name, RTSP URL, codec, transport, enabled,
and ROIs supported by `CameraConfig`.

RTSP credentials are write-only. List/detail responses return safe display data
such as host label and `credentials_configured`, never the full URI/password.
Leaving the secret field blank retains the current secret; replacing it is an
explicit action. Disable and remove require confirmation. Remove explains that
associated configuration must be disabled/reassigned according to backend
constraints; the UI never cascades silently.

Connection status comes from runtime data and may be unknown/stale even when the
camera exists. Form checks provide immediate syntax help, while backend
validation and save errors remain authoritative and field-specific.

## 6. Configuration UX

The editor exposes only current `FaceRecognitionConfig` product fields:

- model references for person detector, face detector, and face embedder;
- recognition ROI IDs and track/face anchors;
- face quality size, detector confidence, blur, brightness, supported pose,
  occlusion, and landmark requirements;
- identity collection, Top-K, and similarity threshold;
- verification strategy, frame bounds, timeout, consistency, and margin;
- recognition/retry intervals, verified/cache TTL, unknown dwell, event cooldown,
  and duplicate suppression;
- timezone/week windows;
- ordered UNKNOWN_PERSON, optional KNOWN_PERSON, and WATCHLIST_PERSON policies;
- snapshot/video, pre/post duration, and overlay flags.

Settings are grouped into Models, ROI, Quality, Recognition, Verification,
Timing, Schedule, Policies, and Evidence. The primary interface is structured
forms, not JSON. No backend-only DSN, storage root, decoder/encoder path, model
artifact path, CUDA/TensorRT setting, Redis detail, checksum, or secret appears.

## 7. Draft, validation, and activation lifecycle

The screen always displays four separate facts when available: editing base
revision, saved draft revision, validation result, and active/runtime-applied
revision.

```text
load active/draft -> edit locally -> Save Draft
-> Validate saved revision -> Activate validated revision
-> wait for activation result -> compare runtime applied revision
```

Save never activates. Local changes invalidate the displayed validation result.
Activate names an immutable validated revision and is disabled for unsaved,
invalid, stale, or already-pending drafts. API success means the activation
request was accepted; only backend activation state and worker runtime status may
show ACTIVE/APPLIED. Activation failure retains the draft and errors.

Optimistic concurrency uses revision/ETag. A conflict prompts reload/compare; no
last-write-wins overwrite. Navigation with unsaved local changes prompts. Backend
field errors map to controls; unmatched errors remain in a focusable summary.

## 8. ROI editor

The editor uses a safe backend preview image and an SVG overlay. Domain points
remain normalized `(x,y)` values in the backend-defined canonical frame. Display
applies the supplied canonical-to-preview transform, then the actual media content
rectangle after letterboxing; edits apply the inverse before normalization.
Resize always reprojects from normalized source data.

Operations are click/add, pointer or keyboard move, selected-point delete, clear,
reset to loaded draft, preview, and Save Draft. It validates at least three
distinct finite points, `[0,1]` range, nonzero area, and all backend polygon
rules. Client validation assists; server validation decides acceptance.

The editor shows purpose and current `track_anchor`/`face_anchor`. It never
activates configuration. Preview unavailability leaves editing possible against
the last explicitly fetched snapshot only when the user chooses; it never falls
back to RTSP in the browser or reveals camera credentials.

## 9. Model management

Models is a read-oriented operational page backed by safe deployment DTOs. It
shows model definition, version, role (`PERSON_DETECTOR`, `FACE_DETECTOR`, or
`FACE_EMBEDDER`), backend family, deployment state, loaded state, activation
state, compatibility summary, and last failure when supplied.

The current static `/models` stub is insufficient and must not be presented as
loaded. Filesystem/engine paths, CUDA devices, TensorRT internals, credentials,
and irrelevant checksums remain hidden. Configuration model selectors use only
compatible backend-returned choices. Phase 8 does not upload, convert, train, or
optimize models.

## 10. People

People provides server-paginated search/list, create, detail, editable allowed
metadata, and confirmed delete/deactivate. The current domain exposes
`display_name`, active state, group IDs, and multiple enrollments; the UI does
not invent demographic fields.

Rows show safe person identity, active state, enrollment count, identity groups
when exposed, and related collection/index readiness. Person detail owns the
enrollment list. No embedding, FAISS row/vector ID, internal path, or face-search
candidate data is rendered, logged, stored in URLs, or persisted in browser
storage.

Delete behavior is entirely backend-defined. Until hard-delete versus deactivate
and event-history constraints are specified, the UI labels the operation from
the returned capability and explains known index consequences in a confirmation.

## 11. Enrollment

One person may own multiple enrollment samples. The flow is:

```text
select image -> transient preview -> multipart upload
-> PROCESSING -> backend face/quality/embedding result
-> enrollment READY or FAILED
-> index rebuild lifecycle -> searchable only when relevant revision ACTIVE
```

Client checks file size and content type for fast feedback; backend performs face
detection, multiple-face policy, quality, alignment, embedding, compatibility,
and enrollment creation. Stable backend reasons are mapped to specific messages:
`NO_FACE`, `MULTIPLE_FACES`, `LOW_QUALITY`, `INVALID_IMAGE`,
`INCOMPATIBLE_MODEL`, and `PROCESSING_FAILURE`. Unknown codes remain visible as
safe generic processing errors with correlation information.

The UI shows enrollment ID, created time, safe thumbnail/evidence reference,
model version, quality summary when exposed, active/compatible state, and index
impact. Object URLs are revoked. Removing a sample is confirmed and never
optimistically claims the index is rebuilt.

## 12. Index rebuild and status UX

Enrollment mutations may return an index-operation/revision reference. The UI
shows only authoritative states: `REBUILD_REQUESTED`, `BUILDING`, `READY`,
`ACTIVE`, or `FAILED`, plus active revision and vector/enrollment count when safe.

`READY` is not `ACTIVE`; an enrollment is not labeled searchable until its
collection's active revision contains the relevant source-enrollment revision.
WebSocket signals invalidate the collection/index query, while REST returns the
truth after reconnect. Phase 8 has no manual FAISS manipulation and never derives
index state from elapsed time.

## 13. Live Recognition

The MVP live page is capability-driven:

- per-camera connection/worker metrics and active configuration revision;
- the latest bounded backend-supplied recognition state when such a contract
  exists (`PENDING`, `VERIFIED`, `UNKNOWN`, `UNCERTAIN`);
- backend-supplied person display for VERIFIED only;
- safe preview snapshot/stream when the preview capability exists;
- a small recent-event lane linked to persisted event detail.

The actual backend has no live recognition or preview contract, so the initial
page must show those capabilities as unavailable rather than inferring recognition
from tracks or events. Bounding boxes and track IDs appear only when an intentional
backend preview/overlay DTO supplies canonical coordinates; track IDs are hidden
outside an explicit diagnostic mode.

Latest-by-camera/track maps are capped and time-expired. Rendering is throttled to
a useful UI rate; superseded overlay/preview updates are dropped. Persisted event
history is queried separately and no historical frames/detections accumulate in
browser memory. React performs no recognition or identity decision.

## 14. Event list

Events uses the Phase 7 server contract: camera, event type, person, recognition
status, and UTC time-range filters with cursor pagination and a bounded page size.
Filters are encoded in safe query parameters and debounced; stale requests are
cancelled. The browser never downloads the complete table.

Each row shows occurred time in the selected display timezone, camera, stable
event type, recognition status, backend-provided person when applicable,
severity, and aggregate evidence state. `event.created` invalidates the first
page or inserts one deduplicated summary only when it matches current filters.
The server query remains authoritative after reconnect.

## 15. Event detail

Event detail renders the immutable Phase 7 DTO: type, severity, occurrence and
creation times, camera, optional ROI, track context, recognition status, optional
person and score, policy, configuration/model/index revisions, and evidence.

Operational revisions are collapsed under a technical-details disclosure rather
than dominating the primary incident view. The UI never displays embeddings,
candidate lists, FAISS positions, local paths, or a new identity inferred from
the score. Missing optional person/score fields are intentionally absent, not
shown as errors.

## 16. Evidence

`EvidenceViewer` handles each artifact independently:

- `PENDING`: processing status and metadata, no broken media element;
- `READY`: render snapshot or video/download from the controlled backend access
  URL, with type and accessible fallback;
- `FAILED`: safe backend failure status, with Retry only if the API explicitly
  advertises that capability.

`evidence.ready` and `evidence.failed` invalidate the event/evidence query;
messages do not carry media bytes. Local filesystem paths never reach the DOM.
Large blobs are not placed in query/global state; object URLs are scoped and
revoked. Event validity never depends on evidence success.

## 17. Runtime Status

Runtime Status displays only supplied subsystems:

- current schema: camera connection, input/processed FPS, dropped frames, active
  tracks, ring-buffer usage, worker health, and applied config revision;
- required future safe extensions: model load states, index lifecycle/revision,
  worker lifecycle, and freshness timestamp.

It separately shows WebSocket client state. `healthy`, `degraded`, `unhealthy`,
`unknown`, and `stale` use text/icons as well as color. A configured camera with
no recent runtime sample is `unknown` or `stale`, never connected. A selected
model with no load telemetry is `unknown`, never loaded. Staleness is determined
from a backend timestamp and a documented UI threshold, not from configuration.

## 18. HTTP client

`api/http.ts` owns base URL, JSON/multipart serialization, abort signals,
response decoding, and a typed `ApiError` containing HTTP status, stable code,
field errors, safe message, and optional correlation ID. Feature clients expose
domain operations for cameras, configurations, models, people/enrollments,
indexes, events/evidence, runtime, and preview.

OpenAPI generation centralizes DTO shapes; handwritten adapters may refine
discriminated unions but cannot scatter duplicate versions across components.
Runtime parsing validates untrusted boundary data before it reaches views. Calls
accept `AbortSignal`; query changes and unmount cancel stale work. Mutation
idempotency/revision headers are supplied where backend contracts require them.

No client logs response bodies by default. Errors remain classified as field
validation, conflict, activation, unavailable, or unexpected rather than one
generic toast.

## 19. WebSocket architecture

One `RealtimeClient` instance per configured `/api/v1/ws` endpoint/context owns:

- `CONNECTING`, `CONNECTED`, `RECONNECTING`, `DISCONNECTED`, and `ERROR`;
- envelope version/type parsing and typed domain payload validation;
- exponential backoff with jitter and a maximum delay;
- subscriber registration/cleanup and Strict Mode-safe connection ownership;
- bounded latest-state dispatch and contract/publication diagnostics.

Supported messages initially include actual `runtime.status`, then Phase 7
`event.created`, `evidence.ready`, and `evidence.failed` when implemented. Unknown
types are ignored with bounded diagnostics; malformed known types are contract
errors and are not partially consumed. Server-assigned message/entity IDs only
deduplicate client delivery/rendering—they never perform event-engine dedup,
cooldown, identity merging, or policy work.

The service dispatches typed domain notifications to query invalidation and
small latest-state stores. Components subscribe through hooks and never parse
raw JSON or open sockets directly.

## 20. Reconnection and reconciliation

Durable REST snapshot/history endpoints remain authoritative. On initial connect
and every reconnect, the coordinator invalidates/refetches runtime status, recent
events, visible event evidence, model/index state, and any visible activation
status. This handles all messages missed while disconnected.

The current backend has no replay cursor; Phase 8 does not invent one. A future
cursor can be hidden behind `RealtimeClient` without changing pages. Repeated
at-least-once messages are harmless because cache updates use stable backend IDs.
Backoff is bounded in delay and resets after a stable connection. Terminal
contract/auth errors stop automatic retry when the backend can identify them;
ordinary network loss continues retrying while the app is active.

## 21. State management

TanStack Query owns authoritative REST resources and pagination. Query keys are
centralized by domain. Mutations invalidate the smallest affected sets and use
optimistic updates only for reversible presentation where server semantics are
unambiguous; activation, enrollment/index, evidence, and runtime state are never
optimistically declared successful.

Local React state/reducers own filters, selection, dialogs, unsaved forms, upload
preview, and ROI drawing. A narrow configuration-draft context may span the
configuration/ROI routes for one camera and revision. `RealtimeClient` owns only
connection state and bounded transient latest-state maps. No Redux/Zustand or
generic mirror of all server entities is added.

## 22. Error, loading, and empty states

Every data surface has deliberate loading, empty, success, and typed error UI.
Realtime surfaces add disconnected/reconnecting and stale states. Patterns are:

- field error plus focusable form summary for validation;
- inline activation panel for activation conflict/failure;
- connection banner for WebSocket state without hiding REST content;
- runtime subsystem warning for camera/worker/model/index failures;
- per-artifact evidence failure;
- retryable page error with retained safe filters;
- specific empty copy and next action when authorized by backend capability.

Toasts acknowledge short-lived mutation results; they are not the only location
for actionable errors. Background refetch preserves existing data with a visible
refresh indicator. A failed Overview tile does not fail unrelated tiles.

## 23. Security and privacy boundary

Authentication/RBAC implementation remains out of scope, but all clients and
routes are future-auth-compatible. Phase 8:

- never stores RTSP/database/Redis credentials, tokens, images, embeddings, or
  sensitive API payloads in localStorage/sessionStorage/URLs/logs/analytics;
- never receives full saved camera secrets or internal filesystem/model paths;
- never exposes FAISS IDs or embedding vectors;
- uses controlled evidence/preview references and revokes temporary object URLs;
- does not embed raw RTSP in browser elements;
- treats server-provided display strings as text and never unsafe HTML;
- keeps destructive operations explicit and backend-authoritative.

Non-sensitive UI preferences such as compact layout may use localStorage under a
namespaced schema. No Phase 8 page implements roles, permissions administration,
or an authentication platform.

## 24. Accessibility and responsive behavior

Navigation, headings, landmarks, forms, tables, dialogs, status announcements,
and media controls use semantic elements and programmatic labels. Validation
summaries receive focus; dialogs trap focus and restore it to their trigger;
uploads and activation announce progress; every status has text/icon meaning
beyond color.

ROI vertices are keyboard selectable/movable/deletable with visible focus and an
equivalent coordinate list for precise adjustment. Pointer targets meet usable
size expectations. Evidence images have contextual alternative text; decorative
overlays do not pollute the accessibility tree. Reduced-motion preferences apply
to animation.

Desktop operations is primary. At smaller sizes, navigation collapses, forms
stack, and tables gain controlled horizontal scroll or priority columns. Dense
diagnostic data remains accessible rather than being removed for a mobile-card
aesthetic.

## 25. Tests

Vitest + Testing Library + user-event + MSW tests behavior, not component
internals. Coverage includes:

- camera list/create/edit, masked secret behavior, API failures, and runtime
  status versus configuration;
- configuration load/edit/save, stale validation, field errors, activate,
  activation conflict/failure, and active versus applied revision;
- ROI normalized/screen round trips, resize/letterbox/transform preservation,
  pointer/keyboard editing, reset, invalid polygons, and save-only behavior;
- people CRUD presentation, multiple enrollments, upload/progress, each stable
  rejection reason, success, delete confirmation, and index lifecycle;
- one Strict Mode-safe socket, connect/disconnect/reconnect/backoff, malformed
  messages, runtime/event/evidence dispatch, deduped rendering, cleanup, and
  reconciliation;
- event filters/pagination/detail plus PENDING/READY/FAILED evidence and media
  cleanup;
- healthy/degraded/stale/unknown camera, worker, model, index, configuration, and
  WebSocket states without fabricated status;
- loading/empty/partial-error states, cancellation, focus management, labels,
  dialog semantics, and non-color status.

Contract tests regenerate/check OpenAPI TypeScript types and parse representative
WebSocket fixtures. Frontend CI runs typecheck, unit/integration tests, production
build, and E2E; no camera, GPU, or Jetson is required.

## 26. E2E workflow

Playwright runs against the built frontend with deterministic mocked HTTP and
WebSocket boundaries:

```text
create/edit camera with write-only secret
-> draw normalized ROI -> Save Draft
-> Validate -> Activate -> observe applied revision
-> create Person -> upload two enrollment samples
-> observe index BUILDING -> ACTIVE
-> receive event.created -> open event
-> observe evidence PENDING -> READY -> inspect snapshot
```

The test also exercises one reconnect and authoritative refetch. Mock fixtures
obey the shared contracts and never include embeddings or credentials. A future
system E2E against real services is separate from normal frontend CI.

## 27. PHASE 8 BACKEND GAP

The UI cannot work around these gaps. Minimal backend changes are allowed only
after this design and a later implementation plan are approved.

| Required capability | Current limitation | Minimal backend contract/change | Why the UI needs it |
|---|---|---|---|
| Completed Phase 3-7 runtime | Claimed implementations are absent; only mock/partial runtime exists | Restore or implement and verify approved upstream contracts before Phase 8 slices rely on them | Prevents a UI for fictional state |
| Persistent, secret-safe cameras | Only `POST /cameras/validate`; no persistence and `CameraConfig` returns full RTSP URI | `GET/POST /cameras`, `GET/PATCH/DELETE /cameras/{id}` with write-only secret input, masked safe output, ETag/revision, structured errors | Camera management without credential exposure |
| Configuration revisions | Only stateless `POST /face-recognition/configs/validate` | list/get active+draft; create/update draft; validate immutable revision; activate revision; query activation status; ETag/conflict and field-error contracts | Honest Draft/Validated/Active/Applied UX |
| Safe model/deployment status | `/models` is a static stub with ID/type/status only | safe model-definition/deployment DTOs with role, version, backend family, compatibility, selected/loaded/active state, failure code; no paths | Model selectors and truthful operations status |
| ROI preview and transform | No browser preview/snapshot or canonical-frame metadata | `GET /cameras/{id}/preview` descriptor containing controlled snapshot URL, capture time, canonical dimensions, and canonical↔preview rotation/crop transform | Draw normalized ROI without RTSP credentials or coordinate drift |
| People persistence | Domain dataclasses only; no repositories/routes | paginated `GET/POST /people`, `GET/PATCH/DELETE /people/{id}` with explicit deactivate/delete capability and conflict rules | People list/detail and safe destructive UX |
| Enrollment processing | No upload, validation, job, or sample API | multipart `POST /people/{id}/enrollments`; list/get/delete sample; async status/reason codes; safe thumbnail reference; model/collection revision | Multiple samples per person and specific feedback |
| Collection/index lifecycle | Phase 6 design only | list identity collections; query rebuild operation and active index revision/state/source enrollment revision; optional typed index status messages | Never claim enrollment is searchable before ACTIVE |
| Events and evidence | Phase 7 design only; no schema/routes/messages | implement Phase 7 event/evidence query, controlled content access, cursor filters, and `event.created`/`evidence.ready`/`evidence.failed` | Event list/detail/evidence lifecycle |
| Runtime freshness and subsystem states | Current status lacks emitted/received timestamp, model/index state, and explicit worker lifecycle | extend safe runtime DTO with `updated_at`, worker lifecycle, model deployment states, active index state/revision; preserve current metrics | Distinguish stale/unknown from healthy and selected from loaded |
| Typed realtime contracts | Envelope payload is `dict[str, Any]`; only ready/runtime messages exist | discriminated payload schemas/JSON Schema/OpenAPI artifacts, stable IDs, documented at-least-once behavior, safe contract-error observability | Typed parsing, reconnection, and cache invalidation |
| Structured errors | Pydantic/default errors are not normalized across future endpoints | common error envelope with stable code, field path/message list, safe message, correlation ID, and conflict metadata | Specific form/API/activation/enrollment error UX |
| Versioned OpenAPI artifact | FastAPI can generate OpenAPI but no checked-in/generated frontend workflow exists | deterministic OpenAPI export plus CI drift check; exclude secrets/internal schemas | Central TypeScript contracts without handwritten drift |

Two capabilities are optional rather than silently assumed:

- Continuous browser video is not required for initial Phase 8. The preview
  descriptor may provide a still snapshot. A future HLS/WebRTC adapter can use
  the same safe boundary.
- Per-track live-recognition messages are not currently required. Until an
  approved bounded DTO exists, Live Recognition combines runtime truth, safe
  preview capability, and recent persisted events and labels track state
  unavailable.

## 28. Expected files and components

The later implementation plan should minimally add/change:

```text
apps/web/
  package.json
  vite.config.ts
  src/
    app/
      App.tsx
      router.tsx
      providers.tsx
      layout/AppShell.tsx
    api/
      generated/schema.ts
      http.ts
      errors.ts
      cameras.ts
      configurations.ts
      models.ts
      people.ts
      enrollments.ts
      indexes.ts
      events.ts
      runtime.ts
      preview.ts
    realtime/
      contracts.ts
      RealtimeClient.ts
      RealtimeProvider.tsx
      useRealtime.ts
    components/
      StatusBadge.tsx
      LoadingState.tsx
      EmptyState.tsx
      ErrorState.tsx
      ConfirmDialog.tsx
      RevisionStatus.tsx
      EvidenceViewer.tsx
    features/
      overview/
      cameras/
      configuration/
      roi/
      models/
      people/
      enrollment/
      live/
      events/
      runtime/
    styles/
      tokens.css
      layout.css
      components.css
    test/
      setup.ts
      server.ts
      fixtures/
  e2e/face-recognition-operations.spec.ts
  playwright.config.ts

packages/contracts/
  openapi/control-api-v1.json
  websocket/*.schema.json

apps/control-api/src/control_api/
  cameras.py
  configurations.py
  models_api.py
  people.py
  enrollments.py
  indexes.py
  events.py
  preview.py
  errors.py
  main.py

apps/control-api/tests/
  test_camera_api.py
  test_configuration_lifecycle_api.py
  test_people_enrollment_api.py
  test_model_index_status_api.py
  test_event_evidence_api.py
  test_preview_api.py
  test_contract_export.py
```

Feature folders contain focused pages, components, hooks, and tests rather than
one file per directory by rule. Shared primitives are created only after repeated
behavior appears. Exact backend files must follow the restored Phase 3-7
architecture and repository boundaries; this list does not authorize recreating
those phases inside control-api.

## 29. Unresolved decisions and prerequisite gates

Only these decisions remain genuinely unresolved:

1. **Missing upstream implementation:** supply or implement and verify Phase 3-7
   before Phase 8 implementation planning can bind to real DTOs and behavior.
2. **Preview MVP:** confirm that a safe still-snapshot descriptor is sufficient
   for ROI and initial live operations, or approve a browser streaming adapter as
   separate backend scope. Raw RTSP is never an option.
3. **Canonical preview geometry:** define the backend canonical frame after
   rotation/crop and the exact transform metadata used by ROI and optional
   overlays.
4. **Person/enrollment deletion semantics:** choose deactivate versus hard-delete,
   historical-event retention, and index rebuild behavior. The UI follows the
   capability; it cannot decide business deletion rules.
5. **Enrollment constraints:** define accepted file types/size, whether multiple
   faces are rejected, processing timeout, and safe thumbnail retention.
6. **Biometric media access in the unauthenticated MVP:** define the trusted
   deployment boundary and evidence/preview access controls. Full RBAC remains
   out of scope, but production cannot expose unrestricted biometric media.

Resolved by this design: domain-sliced SPA; React Router; TanStack Query rather
than a generic global store; native forms/SVG ROI; no component framework;
generated centralized contracts; one managed socket per endpoint/context;
authoritative reconciliation after reconnect; server pagination; bounded live
state; strict Draft/Active/Applied separation; Person versus Enrollment; exact
evidence lifecycle; and no frontend recognition logic.

## Self-review

- Authority: every identity, event, enrollment, activation, index, and health
  decision comes from backend contracts; frontend checks are presentation aids.
- Draft/Active: save, validate, activate, and runtime applied revision are never
  conflated or optimistically promoted.
- ROI: persistence is normalized against a backend-defined canonical frame;
  letterbox/crop/rotation and inverse transforms are explicit.
- Secrets/internal state: RTSP credentials, paths, infrastructure, embeddings,
  and FAISS IDs never enter browser output or persistence.
- WebSocket: one managed client per endpoint/context, Strict Mode-safe cleanup,
  typed parsing, bounded backoff/state, and authoritative refetch are defined.
- Realtime memory: server pagination, capped latest maps, throttled rendering,
  cancellation, dropped superseded visuals, and media cleanup are explicit.
- Enrollment: one Person owns many samples; React does no biometric processing
  and waits for ACTIVE index truth.
- States: all pages cover loading/empty/error; realtime adds reconnect/stale;
  evidence handles PENDING/READY/FAILED independently.
- Accessibility: semantic structure, focus, keyboard ROI, dialogs, progress, and
  non-color status are testable requirements.
- Scope: no AI, TensorRT, analytics, notification, RBAC platform, other IOC
  feature, or Phase 9 work appears.
- Testability: mocked boundaries cover CI without Jetson/camera/GPU; contract
  drift and the complete operator journey have explicit tests.

## Stop condition

No product implementation, dependency installation, implementation plan, backend
endpoint, or React component is authorized by this document. Stop and wait for
exactly:

`APPROVE PHASE 8 DESIGN`
