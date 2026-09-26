# Phase 5: Face Alignment and AdaFace Embedding Design

## Status and Approval Gate

This is the Phase 5 design specification. It changes no product code and does
not authorize an implementation plan or implementation. Phase 5 starts at an
accepted `FaceSample` and stops at a validated, L2-normalized `FaceEmbedding`.

Implementation planning may begin only after this design is approved with the
requested approval phrase and after the prerequisite mismatch described below
is resolved.

## Scope

Phase 5 adds:

- named-landmark validation and five-point face alignment;
- an independently testable `FaceAligner` and transient `AlignedFace`;
- manifest-driven AdaFace preprocessing;
- a backend-neutral `FaceEmbedder` with deterministic mock and ONNX Runtime
  implementations;
- model-output validation and exactly-once L2 normalization;
- a framework-independent `FaceEmbedding` compatibility contract;
- bounded, track-owned embedding observations;
- Phase 5 runtime metrics, safe diagnostics, and CPU-first tests.

Phase 5 does not add FAISS, vector collections, Top-K search, similarity
thresholding, person matching, identity states or decisions, multi-frame
identity verification, policy evaluation, or events. TensorRT remains a future
adapter boundary and must not be reported as implemented.

## Repository Audit and Prerequisite Gate

The source tree is the implementation source of truth. At the time of this
design, it contains the Phase 2 runtime foundation rather than the claimed
completed Phase 3 and Phase 4 runtime:

- `VideoFrame`, a bounded frame buffer, frame sampling, camera state, mock
  person detection/tracking, `TrackState`, runtime status, and the React status
  shell exist.
- `FaceDetection` is only a box plus an unnamed tuple of point tuples.
- `FaceDetector` and `FaceEmbedder` are skeletal protocols using `Any` or raw
  lists; only stubs exist.
- No `FaceSample`, `FaceQualityResult`, named landmark type, best-face store,
  SCRFD adapter, real YOLO adapter, BoT-SORT adapter, model-deployment registry,
  ONNX Runtime session adapter, or Phase 4 tests exist in source.
- `TrackState` contains identity-era fields and an unconstrained observations
  list, but no face samples or embeddings.
- The manifest schema is a generic envelope whose `metadata` is unconstrained;
  no concrete deployment manifest is present.
- The base Python dependencies do not include NumPy, Pillow, or ONNX Runtime.
- The only project-local skill currently present is
  `face-pipeline-engineering`; `vision-pipeline-engineering` is not present in
  this checkout.

This mismatch is a hard prerequisite, not permission to fold Phase 3 or Phase 4
into Phase 5. Before a Phase 5 implementation plan is written, the project must
either:

1. provide the checkout/worktree containing the completed Phase 3 and Phase 4
   implementation; or
2. complete and verify those phases first.

The Phase 5 contracts below define the required integration boundary so that
the prerequisite work does not have to be redesigned.

## Considered Approaches

### A. Explicit alignment and embedding stages (recommended)

Keep `FaceAligner`, AdaFace tensor preprocessing, inference, output validation,
and normalization as explicit, testable boundaries. Drive artifact-specific
behavior from backend-controlled versioned profiles. This is the clearest way
to preserve coordinate provenance and prevent incompatible embeddings from
reaching a future vector store.

### B. A single AdaFace service that accepts `FaceSample`

This has a smaller public surface, but it hides landmark conversion and affine
alignment inside the model adapter. Alignment becomes difficult to test or
replace independently, and preprocessing ownership becomes ambiguous. It is
rejected.

### C. A generic configurable stage graph

A general DAG could compose arbitrary preprocessors and models, but Phase 5 has
one known flow. The extra configuration and dynamic dispatch would make failure
semantics and compatibility harder to audit. It is rejected as premature.

## Proposed Architecture

```text
Accepted FaceSample
  -> EmbeddingScheduler
  -> FaceAligner
       validate named landmarks and coordinate transform
       estimate five-point similarity transform
       warp into the selected alignment profile
  -> AlignedFace (transient)
  -> FaceEmbedder
       AdaFacePreprocessor (profile-owned tensor preparation)
       AdaFaceInferenceBackend (ONNX Runtime initially)
       output validation
       L2 normalization (exactly once)
  -> FaceEmbedding
  -> BoundedEmbeddingBuffer on TrackState
  -> RuntimeStatus aggregates
```

`RuntimePipeline` composes these interfaces but does not import ONNX Runtime or
understand affine matrices, AdaFace tensors, or embedding math. SCRFD does not
align faces. `TrackState` does not align or embed. No Phase 5 component makes an
identity decision.

## Runtime Contracts

### Required Phase 4 Input

The accepted `FaceSample` contract must be supplied by Phase 4 and contain:

- `sample_id` unique within its camera stream session;
- `camera_id`, `stream_session_id`, `track_id`, `frame_id`, and `timestamp_ms`;
- an image view or owned crop with width, height, pixel format, and lifetime;
- the original-frame face box;
- five named landmarks: `left_eye`, `right_eye`, `nose`, `left_mouth`, and
  `right_mouth`;
- an explicit landmark coordinate space and the transform into sample-image
  coordinates;
- `FaceQualityResult`, including accepted status and overall score.

For this contract, `left_*` means image-left and `right_*` means image-right.
The Phase 4 SCRFD adapter must perform any model-output conversion into these
named semantics. Phase 5 never guesses or silently reorders an unknown tuple.

### FaceAligner

```python
class FaceAligner(Protocol):
    def align(
        self,
        face_sample: FaceSample,
        profile: AlignmentProfile,
    ) -> AlignedFace: ...
```

The aligner owns only geometric normalization. It validates the sample,
landmarks, coordinate transform, and alignment profile; converts landmarks to
sample-image coordinates explicitly; estimates the transform; and produces the
profile-sized image. It does not perform model tensor scaling, mean/std
normalization, inference, embedding normalization, or persistence.

`AlignedFace` contains:

- the complete provenance tuple and `sample_id`;
- an owned, contiguous HWC `uint8` image buffer with declared pixel format;
- output width and height;
- versioned `alignment_profile_id`;
- the forward affine matrix and non-image source metadata needed for debugging;
- source quality score.

The aligned image is transient. It is neither added to `TrackState` nor written
to disk by default.

### FaceEmbedder

```python
class FaceEmbedder(Protocol):
    adapter_kind: str
    deployment: EmbeddingDeploymentIdentity

    def embed(self, aligned_face: AlignedFace) -> FaceEmbedding: ...
```

Implementations are:

- `MockFaceEmbedder`: deterministic, configured dimension, unmistakable
  `mock` deployment identity, and no randomness;
- `AdaFaceOnnxEmbedder`: initial real local-development implementation;
- `AdaFaceTensorRTEmbedder`: interface boundary only, with construction failing
  explicitly as unsupported until genuinely implemented and tested.

The ONNX implementation owns AdaFace preprocessing, session inference, output
validation, and L2 normalization. ONNX sessions are constructed, validated,
warmed once, and reused. `OrtValue`, session objects, provider handles, and raw
backend outputs never cross the adapter.

## Alignment Strategy

The initial profile is versioned as `adaface-5pt-112-v1` and declares:

- semantic source order: `left_eye`, `right_eye`, `nose`, `left_mouth`,
  `right_mouth`;
- output size: 112 by 112 pixels;
- destination points, in that order:
  `(38.2946, 51.6963)`, `(73.5318, 51.5014)`, `(56.0252, 71.7366)`,
  `(41.5493, 92.3655)`, `(70.7299, 92.2041)`;
- a least-squares similarity transform with reflection disabled;
- bilinear interpolation;
- constant black border fill;
- pixel-center and forward/inverse matrix conventions fixed by the profile and
  golden tests.

The initial CPU implementation uses NumPy for a deterministic similarity
transform and Pillow for affine resampling, avoiding a mandatory OpenCV wheel
on Jetson. The interface permits a later optimized implementation only if it
matches the same golden output within documented tolerance.

Validation rejects missing/non-finite points, repeated or degenerate geometry,
an image-left eye or mouth point not left of its image-right peer, points outside
the configured tolerance around the sample image, non-invertible transforms,
wrong sample ownership, unsupported pixel formats, and non-positive images.
Points in original-frame coordinates are transformed using the explicit Phase 4
matrix before alignment; implicit subtraction of a crop origin is forbidden.

The numeric template is activated only for an AdaFace artifact whose documented
training/export profile is compatible with it. A different artifact requires a
different versioned alignment profile, not a silent constant change.

## Manifest and Configuration Strategy

The UI continues to select the existing logical `ModelReference` only:
`model_definition_id`, `model_version`, and `deployment_id`. Artifact paths,
checksums, tensor names, providers, and profiles remain backend-only.

Phase 5 extends the shared deployment-manifest model planned for Phase 3; it
must not create a second AdaFace-only registry. A face-embedding deployment
must define and validate:

- the exact model definition, version, deployment ID, and
  `FACE_RECOGNITION` model type;
- backend (`onnxruntime`; `tensorrt` reserved);
- artifact URI and SHA-256 checksum;
- input/output tensor names, batch policy, static input shape, layout, and dtype;
- provider order and startup requirements;
- versioned preprocessing and alignment profiles;
- expected output count, rank, and embedding dimension;
- normalization profile and epsilon;
- distance metric and score interpretation intended for future compatible
  indexes.

The resolver verifies path containment, artifact checksum, model-reference
identity, backend support, profile completeness, and model input/output
signatures before the worker becomes healthy. The current unconstrained
`metadata` object is insufficient and must be replaced or constrained by a
discriminated profile schema as part of the shared prerequisite infrastructure.

## AdaFace Preprocessing Ownership

There is exactly one owner: `AdaFaceOnnxEmbedder` delegates to an
`AdaFacePreprocessor` selected by the deployment profile.

- `FaceAligner` performs only the geometric warp and emits declared HWC
  `uint8` pixels.
- `AdaFacePreprocessor` validates dimensions/channels/pixel format, performs
  RGB/BGR conversion if required, converts dtype, applies pixel scaling and
  mean/std normalization, changes HWC to the configured tensor layout, adds the
  batch dimension, and returns a contiguous tensor.
- No downstream component preprocesses the tensor again.

The profile records every operation. The implementation does not infer channel
order or normalization from a filename or model ID.

Before inference, the adapter requires the exact alignment profile, positive
dimensions, three channels, supported input dtype/pixel format, finite converted
values, the configured static tensor shape, and a compatible preprocessing
profile. Failure produces `MODEL_INPUT_ERROR`; no fake vector is returned.

## Output Validation and L2 Normalization

`AdaFaceOnnxEmbedder` validates exactly one configured output, expected tensor
rank, batch size one, configured dimension, finite values, and a norm greater
than the profile epsilon. Unexpected output is `MODEL_OUTPUT_ERROR`.

The embedder adapter is the sole owner of L2 normalization:

```text
raw model vector -> validate dimension/finite values -> compute float64 norm
                 -> reject norm <= epsilon -> divide once -> validate norm ~= 1
                 -> FaceEmbedding(normalized=true)
```

NaN, infinity, zero/near-zero norm, or a post-normalization value outside the
documented tolerance produces `INVALID_EMBEDDING` or
`NORMALIZATION_FAILURE`. No orchestrator, `TrackState`, or future vector store
may normalize again.

## FaceEmbedding Schema and Compatibility

`FaceEmbedding` is a frozen, framework-independent value containing:

- `vector: tuple[float, ...]` and `dimension`;
- `normalized: Literal[True]` and `normalization_profile_id`;
- `model_definition_id`, `model_version`, `deployment_id`, and artifact
  SHA-256 fingerprint;
- `preprocessing_profile_id` and `alignment_profile_id`;
- `distance_metric` and score interpretation;
- `camera_id`, `stream_session_id`, `track_id`, `frame_id`, `timestamp_ms`, and
  `source_sample_id`;
- `source_quality_score`.

Construction validates vector length, finite values, unit norm tolerance, and
non-empty compatibility/provenance fields. It exposes neither a NumPy/ONNX
object nor JSON serialization in the internal hot path.

An immutable `EmbeddingCompatibilityKey` is derived from the model definition,
model version, deployment/artifact fingerprint, dimension, preprocessing
profile, alignment profile, normalization profile, distance metric, and score
interpretation. Phase 6 must bind each vector collection to exactly one such
key and reject mismatches. Equal dimension alone never implies compatibility.

## Scheduling and TrackState Integration

An `EmbeddingScheduler` consumes only newly accepted output from the Phase 4
best-face selector. It does not rescan every frame and does not use identity
state. A sample is eligible when:

- its track still exists;
- it is accepted and has a new `sample_id`;
- the existing `recognition_interval_ms` cadence has elapsed;
- Phase 4 identifies it as newly selected or as a deterministic improvement
  over a retained sample;
- it can improve the bounded embedding set.

Fixed skip reasons are: `no_accepted_face`, `insufficient_quality`,
`embedding_interval`, `duplicate_or_lower_quality`, `capacity_not_improved`, and
`track_expired`.

Each `TrackState` receives a `BoundedEmbeddingBuffer` whose capacity is
`verification.max_frames` (already constrained and UI-editable). It stores only
`FaceEmbedding` plus small observation metadata, never source/aligned images.
It deduplicates by `source_sample_id`. Until full, it adds eligible samples; at
capacity, it replaces the lowest `(quality_score, timestamp_ms, frame_id)` entry
only when the new deterministic ordering key is better. The whole buffer expires
with its camera/session-scoped `TrackState`. This prepares observations without
voting, matching, or assigning an identity.

The current unused, unconstrained `TrackState.observations` field is an
architectural issue. It must not be reused for embeddings. The implementation
plan should either remove it if still unused or separately bound it without
introducing Phase 6 behavior.

## Error Semantics

A typed Phase 5 error carries one stable code, stage, safe message, and optional
exception cause:

- `ALIGNMENT_FAILURE`
- `INVALID_LANDMARKS`
- `INVALID_ALIGNED_FACE`
- `MODEL_NOT_LOADED`
- `MODEL_INPUT_ERROR`
- `MODEL_INFERENCE_ERROR`
- `MODEL_OUTPUT_ERROR`
- `INVALID_EMBEDDING`
- `NORMALIZATION_FAILURE`
- `CONFIGURATION_ERROR`

Startup/configuration failures prevent a false healthy state. Per-sample errors
are caught once at the Phase 5 orchestration boundary, update metrics, and leave
the track eligible for later samples according to scheduling. They are never
translated into no face, no match, or unknown person.

## Metrics, Diagnostics, Privacy, and Performance

`RuntimeStatus` and its Python/TypeScript contracts gain aggregate fields:

- cumulative `alignment_attempts` and `alignment_failures`;
- last and rolling-average `alignment_latency_ms`;
- cumulative `embedding_attempts`, `embedding_success`,
  `embedding_failures`, `embeddings_skipped`, and `invalid_embedding_count`;
- last and rolling-average `embedding_latency_ms`;
- `active_face_embedder`, `active_embedding_model_version`, and
  `active_embedding_backend`.

Skip/error reason counters use a fixed enum and are not labeled by track,
camera-person identity, or arbitrary exception text. Logs may include stage,
error code, aligned dimensions, embedding dimension, norm, backend, and model
version. They must not include vector contents, person identity, raw/aligned
images, or biometric payloads.

Aligned faces and realtime embeddings remain process-memory-only. Debug image
dumping is disabled by default, development-only when enabled, requires an
explicit bounded destination/retention policy, and is not exposed through the
ordinary runtime-status API.

The hot path performs no model load, filesystem read, database/Redis call,
network call, vector JSON serialization, or unbounded queue append per face.
Sessions and profiles are loaded, validated, warmed, and reused. Image ownership
is explicit so alignment makes only the copy required for its output.

## Testing Strategy

All normal tests are CPU-only and artifact-independent.

### Alignment tests

- named order and image-left/right semantics;
- original-frame-to-sample coordinate conversion;
- exact output dimensions and deterministic output;
- known similarity/affine mapping and inverse warp convention;
- interpolation and border behavior using tiny golden fixtures;
- missing, repeated, collinear, NaN/Inf, out-of-range, and wrong-owner
  landmarks.

### Preprocessing tests

- RGB/BGR conversion, HWC/NCHW layout, channel count, dimensions, and dtype;
- scaling, mean/std normalization, contiguous output, and batch shape;
- incompatible alignment/preprocessing profiles and malformed input.

### Embedding tests

- deterministic mock vectors and explicit mock identity;
- fake ONNX-session input/output name and shape validation;
- output count/rank/dimension, NaN/Inf, zero, and near-zero rejection;
- exactly-once L2 normalization and numerical tolerance;
- complete provenance and compatibility metadata;
- compatibility-key changes for every relevant profile/version/fingerprint
  change.

### Integration and regression tests

- `FaceSample -> FaceAligner -> MockFaceEmbedder -> FaceEmbedding`;
- fake-session AdaFace path without an actual model;
- bounded selection, replacement, duplicate suppression, cadence, and track
  expiration;
- runtime metrics and API/WebSocket/React contract propagation;
- the complete earlier camera, sampling, detector, tracker, TrackState, ROI,
  SCRFD, quality, lint, typecheck, build, and startup suites once the prerequisite
  implementation is present.

A real AdaFace ONNX test is optional and enabled only when an operator supplies
the approved artifact and manifest. No model is downloaded automatically.
Jetson/TensorRT performance is not claimed from CPU or fake-session tests.

## Current Verification Baseline

During this design review:

- The first Python test run collected 52 tests: 50 passed and 2 failed during
  fixture setup because the host denied access to pytest's user temp directory.
  A fresh rerun using a workspace-local `--basetemp` and no cache provider
  passed all 52 tests with one third-party deprecation warning.
- Ruff reported all checks passed, with a host access warning while walking the
  workspace.
- Strict MyPy passed for all 38 discovered source files.
- Frontend typecheck/build could not run because `npm` is unavailable in this
  environment.

These are baseline facts, not Phase 5 completion claims.

## Expected Files to Change During Implementation

Exact paths must be reconciled against the restored Phase 3/4 source before the
implementation plan. The expected change surface is:

- `pyproject.toml` — optional CPU/ONNX inference dependencies;
- `model-manifests/schemas/model-manifest-v1.schema.json` and the shared model
  deployment models/registry supplied by Phase 3 — typed AdaFace profiles;
- `workers/vision-worker/src/vision_worker/face_recognition/contracts.py` —
  alignment, embedding, compatibility, and error values;
- `workers/vision-worker/src/vision_worker/face_recognition/alignment.py` —
  alignment profile and CPU aligner;
- `workers/vision-worker/src/vision_worker/face_recognition/preprocessing.py` —
  AdaFace tensor preprocessing;
- `workers/vision-worker/src/vision_worker/face_recognition/embedders.py` —
  protocol, deterministic mock, and ONNX adapter/factory;
- `workers/vision-worker/src/vision_worker/face_recognition/scheduler.py` —
  Phase 5 eligibility only, kept separate from identity verification;
- `workers/vision-worker/src/vision_worker/runtime/track_store.py` and
  `runtime/pipeline.py` — bounded storage and orchestration;
- `packages/python/face-recognition-contracts/src/fr_contracts/runtime_status.py`,
  control API status transport, and web contracts/view — aggregate metrics;
- focused worker unit/integration tests plus existing regression tests;
- a backend-only example AdaFace manifest only after a real artifact identity,
  checksum, and license are known.

No database, Redis, vector-store, enrollment persistence, policy, event, or
evidence file belongs in the Phase 5 change set.

## Remaining Unresolved Decisions

1. **Repository prerequisite (blocking):** the completed Phase 3/4 source must
   be restored/provided or implemented before Phase 5 planning. The current
   checkout cannot supply the accepted `FaceSample` or shared model/ONNX
   infrastructure that this design is required to integrate with.
2. **AdaFace artifact contract (blocking for the real adapter):** no approved
   ONNX artifact, export documentation, checksum, license, input/output tensor
   names, embedding dimension, or provider requirements exist in the repository.
   The artifact must be operator-supplied. Its documented training/export
   preprocessing must confirm the proposed 112x112 alignment template and
   tensor profile; otherwise a new versioned profile is required.

All other Phase 5 architecture decisions are resolved in this specification.

## Design Review Result

The design preserves the approved pipeline boundaries, named landmark semantics,
single preprocessing and normalization owners, explicit compatibility metadata,
bounded track memory, CPU testability, transient biometric data, reusable model
sessions, and the strict Phase 5 completion boundary. It does not conceal the
missing prerequisite implementation and does not introduce Phase 6 behavior.
