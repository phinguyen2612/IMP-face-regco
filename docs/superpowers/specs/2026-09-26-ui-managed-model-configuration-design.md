# UI-Managed Model Configuration Design

## Scope

Face-recognition inference models only: person detector, face detector, and face embedder. The control plane owns immutable model metadata, artifacts, deployments, activation state, assignment, and safe health. Training, marketplaces, arbitrary Python execution, and unrelated IOC features remain out of scope.

## Boundaries

- ModelDefinition is logical identity; ModelVersion is immutable ONNX plus manifest and checksum; ModelDeployment is execution intent.
- LocalModelArtifactStorage writes generated paths under one configured root and never accepts client paths. PostgreSQL stores metadata only.
- RuntimeCapabilities and InferenceRuntimeResolver resolve each deployment independently. Explicit backends are strict; AUTO may fall back observably.
- Activation is prepare/validate/load/warm/health before an atomic swap. Failure retains the prior active deployment.
- Worker production construction consumes resolved deployment adapters. Missing real adapters fail activation; mocks are test/dev only.
- Face embedder compatibility includes artifact fingerprint, dimension, normalization, metric, preprocessing, and alignment. Incompatible changes mark the vector index as requiring rebuild.
- UI displays configured, validated, deployed, loaded, healthy, and active as distinct facts and never receives internal storage paths.

## Persistence and delivery

Normalized PostgreSQL tables store definitions, artifacts, versions, deployments, runtime status, and active role assignments. Workers consume authenticated internal deployment snapshots by revision, cache artifacts by checksum in a bounded cache, prepare replacements off-path, and publish safe activation/runtime results.

## Validation

Uploads are size bounded, ONNX-only, SHA-256 checked server-side, inspected through an injectable ONNX inspector, and stored immutably only after the manifest/tensor contract is valid. Invalid versions cannot deploy or activate.

## Current implementation constraint

The repository has no real YOLO, SCRFD, AdaFace, ONNX Runtime, BoT-SORT, or FAISS adapters. This implementation creates truthful management/resolution/activation boundaries and removes production mock fallback; real inference remains a separate artifact/adapter acceptance gate.
