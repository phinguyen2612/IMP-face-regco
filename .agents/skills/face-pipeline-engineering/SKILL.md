---
name: face-pipeline-engineering
description: Use when implementing or reviewing SCRFD, face detection, facial landmarks, face bounding boxes or crops, face quality, face sample selection, alignment, AdaFace or ArcFace embeddings, embedding normalization, or vector-search compatibility.
---

# Face Pipeline Engineering

Engineer face-specific stages as explicit, testable boundaries:

```text
TrackedPerson -> FaceDetector -> FaceDetection -> FaceQualityEvaluator
-> FaceSample -> FaceAligner -> FaceEmbedder -> FaceEmbedding -> VectorStore
```

SCRFD must not own quality, alignment, embedding, or identity decisions. AdaFace
must not know FAISS, and the vector store must not know detector output formats.
Framework tensors and raw model arrays stop at their adapters.

## Required Context

Use `vision-pipeline-engineering` alongside this skill when available. That skill
owns ingestion, realtime scheduling, queues/backpressure, person detection,
tracking, general model lifecycle, Jetson/runtime boundaries, and worker resource
cleanup. This skill owns face contracts, coordinates, landmarks, quality,
alignment, embeddings, and compatibility; do not restate the general rules here.

Before changing code, inspect the repository's current contracts and architecture
documents. They remain authoritative over examples in this skill.

## Invariants

- Carry `camera_id`, `stream_session_id`, `track_id`, `frame_id`, and timestamp
  through every face sample and embedding. A `track_id` is never globally unique.
- Label coordinate space explicitly: original frame, person crop, detector input,
  or aligned face. Preserve crop/resize/padding/affine transforms for mapping.
- Prefer original-frame canonical coordinates for domain detections, visualization,
  and track state.
- Keep face crops transient and bounded. Persist only explicit enrollment artifacts
  or configured event evidence; debug output requires an explicit destination and
  retention decision.
- Keep quality evaluation separate from detection. Unsupported metrics are
  `UNSUPPORTED` or `NOT_EVALUATED`, never invented zeros.
- Treat thresholds as validated configuration/calibration values, not universal
  scientific constants.
- Distinguish `NO_FACE`, `LOW_QUALITY_FACE`, `INVALID_FACE_SAMPLE`,
  `MODEL_FAILURE`, `PREPROCESSING_FAILURE`, `POSTPROCESSING_FAILURE`, and
  `CONFIGURATION_FAILURE`. Infrastructure/model failures are not empty detections.
- Keep per-track samples bounded and use deterministic replacement; never retain
  every observed face.
- Run cheap ROI/scheduling checks before face inference, quality before embedding,
  and reuse verified track state rather than processing every frame.
- Do not use identity or person name as an observability label.

## Task-Specific References

- For SCRFD, face boxes, landmarks, crops, quality, and sample selection, read
  [references/detection-quality.md](references/detection-quality.md).
- For alignment, AdaFace/ArcFace, normalization, embedding metadata, and vector
  search compatibility, read
  [references/alignment-embeddings.md](references/alignment-embeddings.md).
- When a task spans both groups, read both references.

## Review Gate

Before completion, verify:

- provenance and coordinate spaces survive every boundary;
- detector output and landmark semantics are validated;
- crops and sample collections remain transient and bounded;
- quality is separate and unsupported metrics are not fabricated;
- alignment and embedding compatibility profiles are explicit;
- normalization has exactly one owner;
- incompatible embeddings cannot share a search operation;
- model/framework objects do not leak downstream;
- failures cannot masquerade as `NO_FACE`;
- mathematical tests run without GPU hardware;
- hot-path work and face persistence remain bounded.
