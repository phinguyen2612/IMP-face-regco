# Detection, Landmarks, Quality, and Samples

Read this reference for SCRFD, face detection, facial landmarks, face crops,
quality assessment, or best-sample selection.

## Face Detector Boundary

Use a framework-independent `FaceDetector` contract. An implementation such as
`ScrfdOnnxFaceDetector` or a future `ScrfdTensorRTFaceDetector` owns tensor layout,
strides/anchors, preprocessing, decoding, confidence filtering, coordinate
restoration, and NMS. It returns domain `FaceDetection` values, not runtime tensors.

Validate model output before decoding:

- output count, rank, dimensions, and dtype where relevant;
- finite numeric values and supported batch size;
- expected feature-map/stride assumptions;
- one landmark set per decoded detection.

Unexpected output is `MODEL_FAILURE` or `POSTPROCESSING_FAILURE`, not zero faces.

## Coordinates and Provenance

Each detection/sample preserves track provenance:

```text
camera_id + stream_session_id + track_id + frame_id + timestamp
```

Record each transformation between original frame, person crop, detector input,
and aligned face. A crop operation clamps bounds, rejects non-finite or zero-area
regions, preserves source metadata, and avoids a copy until an owning image is
actually required. Domain detections use the project's canonical coordinate space;
prefer original-frame coordinates for later overlays and state.

## Landmark Contract

Represent landmarks independently of SCRFD using named semantics:

```text
left_eye, right_eye, nose, left_mouth, right_mouth
```

Validate exact count, finite values, coordinate range, inverse mapping through
crop/resize/padding, and left/right semantic order. Reject duplicated, degenerate,
or malformed landmarks before alignment.

## Quality Contract

`FaceQualityEvaluator` consumes a detection/crop and produces:

```text
accepted + overall_score + metrics + rejection_reasons
```

Rejection reasons are structured values. Each metric declares one status:
`MEASURED`, `NOT_EVALUATED`, `UNSUPPORTED`, or `INVALID`.

Measure only available signals. Candidate metrics include face size, detection
confidence, sharpness/blur, brightness, landmark validity, pose, and occlusion.
Never infer pose or occlusion from missing output, and never encode missing as zero.

Validate configurable thresholds before activation: minimum face size/confidence,
blur, brightness range, maximum yaw/pitch/roll, and occlusion. Tests establish
threshold behavior, not that defaults are scientifically optimal.

## Bounded Sample Selection

Prefer useful samples rather than the latest frame blindly. A deterministic score
may combine accepted quality, confidence, face size, sharpness, brightness, pose,
and recency. Define tie-breaking explicitly. Keep a fixed per-track capacity and
replace the least useful sample; do not append indefinitely.

## Tests

CPU-only focused tests cover:

- preprocessing shape/layout and malformed payloads;
- confidence filtering, NMS, and coordinate restoration;
- landmark ordering, ranges, and transform inversion;
- face-size, brightness, sharpness, and structured rejection reasons;
- unsupported/not-evaluated metric states;
- clamped/zero-area crop handling and provenance;
- bounded deterministic sample replacement;
- malformed model outputs producing explicit failures.

A tiny, legally usable golden image set is acceptable when its purpose and source
are documented. Avoid large datasets and brittle exact-confidence assertions;
define numerical tolerances for model-dependent outputs.
