# Configuration and ROI UX

## Revision lifecycle

Display backend-returned draft, validation, activation, and runtime-applied
revisions as separate facts. Save Draft persists editable product configuration;
Validate returns structured field/global errors; Activate targets one validated
revision; runtime status confirms whether workers applied it. Disable Activate
while validation is stale, an activation is pending, or the target revision is
not activatable. Do not optimistically label activation successful.

Keep the local form draft separate from cached server DTOs. Warn before navigation
with unsaved changes. Map backend error paths to fields and retain unmatched
errors in a summary with correlation data when safely supplied. Configuration
conflicts require reload/compare behavior; never overwrite a newer revision
silently.

Expose only schema-backed UI-editable values. Backend-only runtime settings,
credentials, artifact paths, infrastructure endpoints, checksums, and internal
engine details do not enter forms or browser persistence.

## ROI geometry

Store domain polygons as normalized points in the backend-defined canonical
source frame. The backend supplies rotation/crop/transform metadata when that
frame differs from the preview. Conversion is pure:

```text
screen = media offset + normalized * displayed media size
normalized = (screen - media offset) / displayed media size
```

Account for letterboxing/cropping and device-pixel ratio through the actual media
content rectangle, not the surrounding element. Apply the backend canonical-to-
preview transform before content-rectangle mapping and its inverse before
normalizing edits. Clamp only transient pointer input; report invalid persisted
values rather than silently repairing them.

The editor supports add, drag, keyboard move, delete, clear, reset-to-loaded, and
save-to-draft. Validate at least three distinct points, finite values, range,
nonzero area, and backend-reported polygon rules. Resizing reprojects from the
normalized source of truth. Use SVG or another lightweight accessible overlay;
do not add a canvas framework without demonstrated need.

A browser preview comes only from an explicit backend adapter returning a safe
snapshot or browser-compatible stream reference. Empty preview capability yields
an intentional unavailable state; React never receives or parses RTSP secrets.

Tests cover conversion round trips, resize/letterbox behavior, pointer and
keyboard editing, reset, invalid polygons, structured backend errors, stale
validation, revision conflicts, save-versus-activate, activation failure, and
runtime-applied mismatch.
