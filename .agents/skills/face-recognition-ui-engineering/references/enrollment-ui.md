# Enrollment, Privacy, and Frontend Structure

## People and enrollment

Person is the business entity; Enrollment is one biometric sample owned by a
person. Person pages show metadata, enrollment count, sample lifecycle, and
authoritative collection/index state without vectors or backend row IDs.

The upload flow is `select file -> upload -> backend processing -> validation
result -> enrollment created -> index rebuild/activation status`. React may check
file size/type for fast feedback but does not perform face detection, quality
gating, alignment, embedding, compatibility, or searchability decisions. Present
stable backend reasons such as no face, multiple faces, low quality, invalid
image, incompatible model, and processing failure. Do not claim an enrollment is
searchable until the relevant index revision is ACTIVE.

Keep image previews transient, revoke object URLs, and never place images,
credentials, embeddings, or sensitive API payloads in localStorage, URLs,
analytics, or console logs. Destructive person/enrollment actions require an
accessible confirmation that describes known index-rebuild consequences.

## Structure and state

Use server-state query/cache tooling when the project has it or the number of
authoritative resources justifies it. Keep form drafts, filters, selected IDs,
dialogs, and ROI drawing state local or narrowly contextual. Do not introduce a
general global store solely because the application has multiple routes.

Organize vertical feature slices behind centralized clients/contracts. Pages
compose smaller list/detail/form/status components; geometry, WebSocket parsing,
and API calls do not live in page rendering. Shared primitives are earned by
repeated behavior: loading, empty, error, confirmation, status, revision, and
evidence presentation. Avoid a speculative component framework.

Every workflow supports keyboard use, programmatic labels, predictable focus,
dialog semantics, and status text beyond color. Tests assert user-visible
behavior for person CRUD, multi-sample enrollment, upload progress/failures,
index lifecycle, destructive confirmations, privacy-safe rendering/logging,
loading/empty/error states, focus restoration, and contract parsing. A mocked
end-to-end path may cover camera/config/ROI activation, person enrollment, event
arrival, and evidence inspection without Jetson, camera, or GPU hardware.
