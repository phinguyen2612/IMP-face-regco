# Realtime Operations UX

## Managed connection

One client per realtime endpoint/context parses the versioned envelope into typed domain
messages. It owns connect/disconnect, lifecycle state, exponential backoff with
jitter and a maximum delay, cleanup, and subscriber
fan-out. React Strict Mode mount cycles must not leave duplicate sockets or
listeners. Unsupported or malformed messages are observable contract errors, not
partially trusted payloads.

WebSocket signals freshness; durable snapshot/history APIs own current/history truth. After the first
connection and every reconnection, invalidate/refetch affected runtime, recent
event, and evidence resources. If a backend later exposes a replay cursor, use it
behind the same adapter; do not assume replay exists. Domain IDs deduplicate
at-least-once updates. Cap in-memory live items and use latest-by-track/camera
maps; throttle rendering independently from message parsing. Server-assigned IDs
deduplicate client delivery/rendering only, never event candidates, cooldown, or
identity decisions.

## Operational presentation

Do not collapse connection, camera, worker, model, index, configuration, event,
and evidence status into one health boolean. Unknown/stale data is distinct from
healthy. Show last update time when supplied, and avoid inventing model/index
status from selected configuration.

Event lists use server filters and cursor/page limits. `event.created` invalidates
or prepends one bounded typed summary; it never grows an unbounded history.
`evidence.ready` and `evidence.failed` update or refetch the referenced event.
PENDING shows progress without a broken media element; READY uses the controlled
backend access URL; FAILED shows the safe backend reason and only a supported
retry action. Revoke object URLs and avoid caching large media in global state.

Preview/live tracking uses the existing safe transport and latest-state semantics.
Drop superseded visual frames/overlays rather than queueing them. Track IDs are
development diagnostics only when the backend intentionally exposes them.

Tests use fake timers and mocked network boundaries for single-socket ownership,
cleanup, capped backoff, reconnect reconciliation, duplicate messages, malformed
envelopes, bounded collections, throttled live updates, event/evidence transitions,
stale/unknown runtime data, pagination, cancellation, and media cleanup.
