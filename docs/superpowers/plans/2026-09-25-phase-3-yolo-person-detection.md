# Phase 3 YOLO Person Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run configurable ONNX YOLO person detection through a BoT-SORT motion/IoU tracker, TrackState, runtime metrics, and optional debug rendering without adding any face-recognition inference.

**Architecture:** Preserve dependency injection through `PersonDetector` and `Tracker`. Resolve UI model references through backend-only deployment manifests, run a backend-neutral `YoloPersonDetector` over an ONNX Runtime adapter, normalize results into `PersonDetection`, and inject a BoT-SORT motion/IoU tracker into the existing synchronous camera pipeline.

**Tech Stack:** Python 3.11+, Pydantic 2, NumPy 2, SciPy 1.14+, Pillow 11+, ONNX Runtime 1.23+, FastAPI, pytest, strict MyPy, Ruff, React/TypeScript.

**Spec:** `docs/superpowers/specs/2026-09-25-phase-3-yolo-person-detection-design.md`

## Global Constraints

- Scope ends at Camera -> YOLO -> BoT-SORT -> TrackState -> Runtime Status.
- Do not implement SCRFD, face quality execution, alignment, AdaFace, ArcFace, FAISS, identity verification, or face-recognition events.
- Only the `person` class may cross the `PersonDetector` boundary.
- UI configuration may reference logical models and thresholds but must never expose artifact paths, CUDA indices, TensorRT bindings, or provider internals.
- ONNX Runtime is the executable local backend; TensorRT is an explicit future adapter and must not be reported as implemented or tested.
- Do not download a model or video automatically.
- Keep `MockPersonDetector` and the dependency-free worker smoke path.
- No silent fallback from a configured real backend to a mock.
- The workspace currently has no Git metadata; run every verification checkpoint, but skip commit commands unless a repository is initialized before execution.

## Review Focus

- Truncated or oversized RGB payloads must raise a typed frame-validation error, covered in Task 3.
- NaN/Inf and unexpected YOLO tensor shapes must fail explicitly rather than appear as zero detections, covered in Task 4.
- A manifest path escaping the configured artifact root must be rejected before file access, covered in Task 2.
- A detection exactly on confidence/IoU thresholds must have deterministic inclusive behavior, covered in Task 4.
- A track returning after its removal buffer expires must get a new ID rather than revive stale state, covered in Task 6.

---

## File Structure

### Create

- `packages/python/face-recognition-config/src/fr_config/deployments.py` — versioned deployment manifest models and safe registry resolution.
- `workers/vision-worker/src/vision_worker/inference/errors.py` — typed deployment, frame, backend, and output errors.
- `workers/vision-worker/src/vision_worker/inference/yolo_preprocess.py` — RGB validation and letterbox tensor conversion.
- `workers/vision-worker/src/vision_worker/inference/yolo_postprocess.py` — YOLO output decoding, filtering, NMS, and coordinate restoration.
- `workers/vision-worker/src/vision_worker/inference/yolo_backend.py` — backend protocol and ONNX Runtime implementation.
- `workers/vision-worker/src/vision_worker/inference/yolo_detector.py` — production `PersonDetector` adapter.
- `workers/vision-worker/src/vision_worker/inference/factory.py` — deployment-driven detector selection.
- `workers/vision-worker/src/vision_worker/tracking/bot_sort.py` — BoT-SORT motion/IoU tracker and lifecycle.
- `workers/vision-worker/src/vision_worker/debug/annotations.py` — backend-neutral debug annotation values.
- `workers/vision-worker/src/vision_worker/debug/pillow_sink.py` — opt-in annotated PNG sink.
- `workers/vision-worker/tests/test_model_deployments.py`
- `workers/vision-worker/tests/test_yolo_preprocess.py`
- `workers/vision-worker/tests/test_yolo_postprocess.py`
- `workers/vision-worker/tests/test_yolo_detector.py`
- `workers/vision-worker/tests/test_bot_sort.py`
- `workers/vision-worker/tests/test_debug_visualization.py`
- `workers/vision-worker/tests/test_detector_factory.py`

### Modify

- `pyproject.toml` — add inference extras without forcing them into control-plane-only installs.
- `packages/python/face-recognition-config/src/fr_config/models.py` — UI-safe person detection configuration.
- `packages/python/face-recognition-contracts/src/fr_contracts/runtime_status.py` — person inference metrics.
- `model-manifests/schemas/model-manifest-v1.schema.json` — add deployment identity and validated inference profile.
- `configuration/examples/face-recognition.example.json` — show UI-safe person detection settings.
- `workers/vision-worker/src/vision_worker/inference/interfaces.py` — `PersonDetection` contract and detector metadata.
- `workers/vision-worker/src/vision_worker/inference/stubs.py` — preserve mocks under the richer contract.
- `workers/vision-worker/src/vision_worker/tracking/interfaces.py` — consume `PersonDetection` and retain class/frame metadata.
- `workers/vision-worker/src/vision_worker/runtime/pipeline.py` — measure inference and skipped-frame metrics.
- `workers/vision-worker/src/vision_worker/runtime/runner.py` — optional debug sink.
- `workers/vision-worker/src/vision_worker/app.py` — inject resolved real adapters in configured mode.
- `workers/vision-worker/src/vision_worker/main.py` — deployment-root and debug-output CLI options.
- `apps/web/src/api/contracts.ts` and `apps/web/src/app/App.tsx` — display new runtime metrics.
- Existing unit and contract tests whose constructors use `BoundingBox` directly.
- `README.md` — exact real-detector install and run commands.

---

### Task 1: UI Configuration and Person Detection Domain Contract

**Files:**
- Modify: `pyproject.toml`
- Modify: `packages/python/face-recognition-config/src/fr_config/models.py`
- Modify: `configuration/examples/face-recognition.example.json`
- Modify: `workers/vision-worker/src/vision_worker/inference/interfaces.py`
- Modify: `workers/vision-worker/src/vision_worker/inference/stubs.py`
- Modify: `workers/vision-worker/src/vision_worker/tracking/interfaces.py`
- Modify: `tests/unit/test_config_flow.py`
- Modify: `tests/contract/test_example_config.py`
- Modify: `workers/vision-worker/tests/test_worker.py`

**Interfaces:**
- Produces: `PersonDetectionConfig`, `InputSize`, `PersonDetection`, and `PersonDetector.detector_id/backend_name`.
- Produces: `PersonDetector.detect(frames: Sequence[VideoFrame]) -> list[list[PersonDetection]]`.
- Consumes: existing `VideoFrame`, `ModelReference`, and `BoundingBox`.

- [ ] **Step 1: Write failing configuration tests**

Add tests that parse:

```python
"person_detection": {
    "confidence_threshold": 0.35,
    "iou_threshold": 0.5,
    "input_size": {"width": 640, "height": 640},
    "processing_fps": 8.0,
    "inference_profile": "balanced",
}
```

Assert all values load, `processing_fps=0`, thresholds outside `[0, 1]`, non-positive dimensions, and an empty profile raise `ValidationError`, and backend-only keys such as `artifact_path` remain forbidden.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -I -m pytest tests\unit\test_config_flow.py tests\contract\test_example_config.py -q
```

Expected: failures because `person_detection` is rejected as an extra field.

- [ ] **Step 3: Implement the configuration models**

Add:

```python
class InputSize(StrictModel):
    width: int = Field(default=640, gt=0)
    height: int = Field(default=640, gt=0)


class PersonDetectionConfig(StrictModel):
    confidence_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    input_size: InputSize = Field(default_factory=InputSize)
    processing_fps: float = Field(default=5.0, gt=0.0)
    inference_profile: str = Field(default="balanced", min_length=1)
```

Add `person_detection: PersonDetectionConfig` to `FaceRecognitionConfig` with a default factory, and update the checked-in example.

- [ ] **Step 4: Write failing detector contract tests**

Specify the new result:

```python
detection = PersonDetection(
    box=BoundingBox(0.1, 0.2, 0.5, 0.9),
    confidence=0.91,
    class_id=0,
    class_name="person",
    frame_timestamp_ms=1234,
    source_width=1920,
    source_height=1080,
)
assert MockPersonDetector([detection]).detect([frame]) == [[detection]]
```

Also assert the mock exposes its logical detector ID and backend name and the tracker accepts `PersonDetection` rather than raw boxes.

- [ ] **Step 5: Run detector contract tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -I -m pytest workers\vision-worker\tests\test_worker.py workers\vision-worker\tests\test_runtime_pipeline.py -q
```

Expected: import or constructor failure because `PersonDetection` does not exist.

- [ ] **Step 6: Implement the normalized domain contract**

Use:

```python
@dataclass(frozen=True, slots=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True, slots=True)
class PersonDetection:
    box: BoundingBox
    confidence: float
    class_id: int
    class_name: str
    frame_timestamp_ms: int
    source_width: int
    source_height: int
```

Move confidence from `BoundingBox` into `PersonDetection`, update `TrackedPerson` to retain `confidence`, `class_id`, and `class_name`, and update all mocks/tests without changing face contracts.

- [ ] **Step 7: Add install extras and verify Task 1**

Add:

```toml
[project.optional-dependencies]
inference-onnx = [
  "numpy>=2.0,<3",
  "scipy>=1.14,<2",
  "onnxruntime>=1.23,<2",
  "Pillow>=11,<13",
]
```

Keep existing `dev` dependencies. Run the two focused test commands until green, then run `pytest -q` to catch constructor regressions.

---

### Task 2: Backend-Controlled Model Deployment Registry

**Files:**
- Create: `packages/python/face-recognition-config/src/fr_config/deployments.py`
- Create: `workers/vision-worker/src/vision_worker/inference/errors.py`
- Create: `workers/vision-worker/tests/test_model_deployments.py`
- Modify: `model-manifests/schemas/model-manifest-v1.schema.json`

**Interfaces:**
- Consumes: `ModelReference`.
- Produces: `ModelDeploymentRegistry.resolve(reference: ModelReference) -> ResolvedModelDeployment`.
- Produces: `DeploymentResolutionError` for all rejected deployment inputs.

- [ ] **Step 1: Write registry failure and success tests**

Create temporary artifact and manifest files. Test exact resolution by ID/version/deployment, SHA-256 verification, and these explicit failures:

```python
with pytest.raises(DeploymentResolutionError, match="not found"):
    registry.resolve(missing_reference)

with pytest.raises(DeploymentResolutionError, match="checksum"):
    registry.resolve(reference_with_bad_checksum)

with pytest.raises(DeploymentResolutionError, match="escapes artifact root"):
    registry.resolve(reference_to_parent_path)
```

Also reject `FACE_DETECTION` manifests when resolving a person detector and reject unknown runtime names.

- [ ] **Step 2: Run registry tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -I -m pytest workers\vision-worker\tests\test_model_deployments.py -q
```

Expected: collection failure because `fr_config.deployments` is absent.

- [ ] **Step 3: Implement manifest models and safe resolution**

Define strict models:

```python
class ArtifactManifest(StrictModel):
    uri: str = Field(min_length=1)
    checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ModelDeploymentManifest(StrictModel):
    schema_version: Literal[1]
    id: str
    type: Literal["PERSON_DETECTION", "FACE_DETECTION", "FACE_RECOGNITION"]
    version: str
    deployment_id: str
    runtime: Literal["onnxruntime", "tensorrt"]
    artifact: ArtifactManifest
    profile: YoloDeploymentProfile | None = None
```

`YoloDeploymentProfile` contains logical output layout, class count, person class ID, normalization scale, tensor layout, and provider list. Resolve artifact paths with `Path.resolve()`, require they remain below the configured root, stream SHA-256 verification, and return an immutable `ResolvedModelDeployment`.

The resolution core is:

```python
def resolve(self, reference: ModelReference) -> ResolvedModelDeployment:
    key = (
        reference.model_definition_id,
        reference.model_version,
        reference.deployment_id,
    )
    manifest = self._manifests.get(key)
    if manifest is None:
        raise DeploymentResolutionError(f"model deployment not found: {key}")
    if manifest.type != "PERSON_DETECTION" or manifest.profile is None:
        raise DeploymentResolutionError("deployment is not a YOLO person detector")
    artifact = (self._artifact_root / manifest.artifact.uri).resolve()
    if not artifact.is_relative_to(self._artifact_root):
        raise DeploymentResolutionError("model artifact escapes artifact root")
    if not artifact.is_file():
        raise DeploymentResolutionError(f"model artifact not found: {artifact}")
    self._verify_sha256(artifact, manifest.artifact.checksum)
    return ResolvedModelDeployment(manifest=manifest, artifact_path=artifact)
```

- [ ] **Step 4: Update JSON Schema and verify Task 2**

Make `deployment_id` and `profile` valid schema properties, restrict `runtime` to the two declared values, and set profile fields equivalent to the Pydantic model. Run the focused test, then `pytest tests/contract -q`.

---

### Task 3: RGB Letterbox Preprocessing

**Files:**
- Create: `workers/vision-worker/src/vision_worker/inference/yolo_preprocess.py`
- Create: `workers/vision-worker/tests/test_yolo_preprocess.py`

**Interfaces:**
- Consumes: `VideoFrame`, `InputSize`, and profile normalization scale.
- Produces: `PreprocessedFrame(tensor: NDArray[np.float32], transform: LetterboxTransform)`.

- [ ] **Step 1: Write preprocessing tests**

Use a 4x2 RGB byte payload and a 4x4 target. Assert:

```python
prepared.tensor.shape == (1, 3, 4, 4)
prepared.tensor.dtype == np.float32
prepared.transform.scale == 1.0
prepared.transform.pad_x == 0.0
prepared.transform.pad_y == 1.0
```

Assert the original RGB values occupy the center rows, padding uses value 114, normalization is `/255`, and input payload remains unchanged. Add parameterized failures for `UNKNOWN`/`BGR`, zero dimensions, truncated payload, and oversized payload.

- [ ] **Step 2: Run preprocessing tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -I -m pytest workers\vision-worker\tests\test_yolo_preprocess.py -q
```

Expected: import failure for `yolo_preprocess`.

- [ ] **Step 3: Implement validation and letterbox conversion**

Implement `preprocess_frame(frame, input_size, normalization_scale=1/255)`. Begin with:

```python
expected = frame.width * frame.height * 3
payload = memoryview(frame.payload)
if frame.pixel_format != "RGB" or len(payload) != expected:
    raise FramePreparationError(
        f"expected {expected} RGB bytes for {frame.width}x{frame.height}, got {len(payload)}"
    )
source = np.frombuffer(payload, dtype=np.uint8).reshape(frame.height, frame.width, 3)
```

Calculate `scale = min(target_width/source_width, target_height/source_height)`, use Pillow bilinear resizing, split odd padding deterministically with floor on top/left, construct the padded array, transpose to NCHW, and call `np.ascontiguousarray` only for the final tensor.

- [ ] **Step 4: Verify Task 3**

Run the focused test. Then add portrait, landscape, exact-size, and odd-padding cases and keep the suite green.

---

### Task 4: YOLO Postprocessing and NMS

**Files:**
- Create: `workers/vision-worker/src/vision_worker/inference/yolo_postprocess.py`
- Create: `workers/vision-worker/tests/test_yolo_postprocess.py`

**Interfaces:**
- Consumes: one `ultralytics_detect_v8` array, `LetterboxTransform`, frame metadata, confidence/IoU thresholds, and person class ID.
- Produces: `list[PersonDetection]` in normalized original-frame coordinates.

- [ ] **Step 1: Write filtering and restoration tests**

Build deterministic NumPy tensors for:

- a qualifying person box restored through non-zero padding;
- a high-confidence non-person class;
- a person below and exactly equal to the confidence threshold;
- two overlapping person boxes above and exactly at the IoU threshold;
- boxes partially outside the source frame.

Assert only person detections survive, threshold equality is inclusive, NMS ordering is deterministic by descending confidence then source index, and restored boxes are clipped and normalized.

- [ ] **Step 2: Add malformed-output tests and verify RED**

Reject arrays with wrong rank/channel count, NaN, Inf, negative width/height, or a batch size inconsistent with transforms. Run:

```powershell
.venv\Scripts\python.exe -I -m pytest workers\vision-worker\tests\test_yolo_postprocess.py -q
```

Expected: import failure for `yolo_postprocess`.

- [ ] **Step 3: Implement IoU and deterministic NMS**

Implement:

```python
def box_iou(left: NDArray[np.float32], right: NDArray[np.float32]) -> float:
    x1 = max(float(left[0]), float(right[0]))
    y1 = max(float(left[1]), float(right[1]))
    x2 = min(float(left[2]), float(right[2]))
    y2 = min(float(left[3]), float(right[3]))
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, float(left[2] - left[0])) * max(0.0, float(left[3] - left[1]))
    right_area = max(0.0, float(right[2] - right[0])) * max(0.0, float(right[3] - right[1]))
    union = left_area + right_area - intersection
    return intersection / union if union > 0.0 else 0.0


def nms(boxes: NDArray[np.float32], scores: NDArray[np.float32], threshold: float) -> list[int]:
    source_indices = np.arange(len(scores))
    pending = list(np.lexsort((source_indices, -scores)))
    kept: list[int] = []
    while pending:
        selected = pending.pop(0)
        kept.append(int(selected))
        pending = [
            index for index in pending if box_iou(boxes[selected], boxes[index]) <= threshold
        ]
    return kept
```

Use inclusive confidence (`score >= threshold`) and suppress when `IoU > threshold`, so a box exactly at the IoU threshold remains.

- [ ] **Step 4: Implement output decoding and coordinate restoration**

Accept only `(1, 4 + class_count, candidates)` for the first profile. Transpose candidates, choose `argmax` class and score, filter person class, convert center boxes to corners, run NMS, reverse padding/scale, clip to the original frame, normalize, and create `PersonDetection` values containing original timestamp/dimensions.

The decoder starts with:

```python
if output.ndim != 3 or output.shape[:2] != (1, 4 + class_count):
    raise YoloOutputError(f"unexpected output shape: {output.shape}")
if not np.isfinite(output).all():
    raise YoloOutputError("YOLO output contains NaN or Inf")
candidates = output[0].T
class_ids = np.argmax(candidates[:, 4:], axis=1)
scores = candidates[np.arange(len(candidates)), 4 + class_ids]
selected = (class_ids == person_class_id) & (scores >= confidence_threshold)
```

- [ ] **Step 5: Verify Task 4**

Run the focused test and the preprocessing test together. Confirm malformed tensors raise `YoloOutputError` rather than returning `[]`.

---

### Task 5: ONNX Runtime Backend, YOLO Detector, and Factory

**Files:**
- Create: `workers/vision-worker/src/vision_worker/inference/yolo_backend.py`
- Create: `workers/vision-worker/src/vision_worker/inference/yolo_detector.py`
- Create: `workers/vision-worker/src/vision_worker/inference/factory.py`
- Create: `workers/vision-worker/tests/test_yolo_detector.py`
- Create: `workers/vision-worker/tests/test_detector_factory.py`

**Interfaces:**
- Consumes: `ResolvedModelDeployment`, `PersonDetectionConfig`, and `VideoFrame` sequences.
- Produces: `YoloInferenceBackend.infer(tensor) -> NDArray[np.float32]`.
- Produces: `YoloPersonDetector.detect(frames: Sequence[VideoFrame]) -> list[list[PersonDetection]]`.
- Produces: `create_person_detector(reference, settings, registry) -> PersonDetector`.

- [ ] **Step 1: Write detector tests against a recording backend**

Create a test backend implementing:

```python
class RecordingBackend:
    runtime_name = "recording"

    def infer(self, tensor: NDArray[np.float32]) -> NDArray[np.float32]:
        self.seen.append(tensor)
        return self.output
```

Assert one result list per frame, preprocessing is invoked with configured size, frame metadata is preserved, batch cardinality is enforced, `detector_id` contains model/version/deployment, and `backend_name` is exposed.

- [ ] **Step 2: Run detector tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -I -m pytest workers\vision-worker\tests\test_yolo_detector.py -q
```

Expected: import failure for `yolo_detector`.

- [ ] **Step 3: Implement the backend protocol and detector orchestration**

Define:

```python
class YoloInferenceBackend(Protocol):
    runtime_name: str

    def infer(self, tensor: NDArray[np.float32]) -> NDArray[np.float32]:
        raise NotImplementedError
```

`YoloPersonDetector.detect()` preprocesses each frame, invokes the backend, postprocesses the output, and returns exactly one list per input. Empty input returns `[]` without backend invocation.

Use this orchestration shape:

```python
def detect(self, frames: Sequence[VideoFrame]) -> list[list[PersonDetection]]:
    results: list[list[PersonDetection]] = []
    for frame in frames:
        prepared = preprocess_frame(frame, self._settings.input_size, self._normalization)
        output = self._backend.infer(prepared.tensor)
        results.append(
            decode_person_detections(
                output=output,
                frame=frame,
                transform=prepared.transform,
                class_count=self._class_count,
                person_class_id=self._person_class_id,
                confidence_threshold=self._settings.confidence_threshold,
                iou_threshold=self._settings.iou_threshold,
            )
        )
    return results
```

- [ ] **Step 4: Write ONNX backend construction tests**

Inject a fake ONNX module/session factory. Assert configured providers and artifact path are passed, one input/output is required, NCHW float input is checked, unavailable requested providers raise `BackendUnavailableError`, and session inference returns a copied/owned `float32` array.

- [ ] **Step 5: Implement `OnnxRuntimeYoloBackend`**

Import ONNX Runtime lazily with `importlib.import_module`. Validate requested providers against `get_available_providers()`, create an `InferenceSession`, inspect configured input/output names and shapes, and call:

```python
outputs = session.run([output_name], {input_name: tensor})
```

Never report CUDA/TensorRT unless that exact requested provider is returned as available and configured.

- [ ] **Step 6: Write factory selection/error tests and verify RED**

Assert `onnxruntime` yields `YoloPersonDetector`, `tensorrt` raises `BackendUnavailableError("TensorRT backend is not implemented")`, a missing artifact propagates the deployment error, and no branch returns `MockPersonDetector`.

- [ ] **Step 7: Implement factory and verify Task 5**

Resolve the deployment, require its type/profile, select only declared runtimes, and construct the detector. Run both focused files and Tasks 2–4 tests.

---

### Task 6: BoT-SORT Motion/IoU Tracking

**Files:**
- Create: `workers/vision-worker/src/vision_worker/tracking/bot_sort.py`
- Create: `workers/vision-worker/tests/test_bot_sort.py`
- Modify: `workers/vision-worker/src/vision_worker/tracking/__init__.py`

**Interfaces:**
- Consumes: `VideoFrame` and `Sequence[PersonDetection]`.
- Produces: existing `Tracker.update(frame: VideoFrame, detections: Sequence[PersonDetection]) -> list[TrackedPerson]` with stable camera/session-local IDs.

- [ ] **Step 1: Write lifecycle and stable-ID tests**

Feed one moving person across ten frames and assert a single stable ID. Test two crossing non-overlapping trajectories, a one-frame miss followed by recovery, low-confidence second-stage association, removal after `track_buffer_frames`, and a new ID when the person returns after removal.

- [ ] **Step 2: Run tracker tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -I -m pytest workers\vision-worker\tests\test_bot_sort.py -q
```

Expected: import failure for `tracking.bot_sort`.

- [ ] **Step 3: Implement validated settings and Kalman state**

Define `BotSortSettings` with high/low/new-track thresholds, first/second match IoU thresholds, and positive track buffer. Represent internal track state as center-x, center-y, aspect, height plus velocities and covariance. Use an eight-dimensional constant-velocity transition:

```python
transition = np.eye(8, dtype=np.float64)
transition[0, 4] = 1.0
transition[1, 5] = 1.0
transition[2, 6] = 1.0
transition[3, 7] = 1.0
measurement = np.zeros((4, 8), dtype=np.float64)
measurement[:4, :4] = np.eye(4, dtype=np.float64)
```

`BotTrack.predict()` applies `mean = transition @ mean` and propagates covariance. `update()` performs the standard Kalman innovation/update using `np.linalg.solve`, records the latest `PersonDetection`, resets missed frames, and marks the track confirmed.

- [ ] **Step 4: Implement assignment and two-stage association**

Build IoU cost matrices over predicted boxes and use SciPy's Hungarian assignment, rejecting pairs below the configured IoU match:

```python
def associate(
    tracks: Sequence[BotTrack],
    detections: Sequence[PersonDetection],
    minimum_iou: float,
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    if not tracks or not detections:
        return [], list(range(len(tracks))), list(range(len(detections)))
    ious = np.array(
        [
            [normalized_iou(track.predicted_box, detection.box) for detection in detections]
            for track in tracks
        ],
        dtype=np.float64,
    )
    rows, columns = linear_sum_assignment(1.0 - ious)
    matches = [
        (int(row), int(column))
        for row, column in zip(rows, columns, strict=True)
        if ious[row, column] >= minimum_iou
    ]
    matched_tracks = {row for row, _ in matches}
    matched_detections = {column for _, column in matches}
    return (
        matches,
        [index for index in range(len(tracks)) if index not in matched_tracks],
        [index for index in range(len(detections)) if index not in matched_detections],
    )
```

Associate high-confidence detections first, then remaining tracks against low-confidence detections. Start tracks only above the new-track threshold.

- [ ] **Step 5: Implement session isolation and output**

Reset internal tracks and ID allocation when `(camera_id, stream_session_id)` changes. Return only currently matched/confirmed `TrackedPerson` objects with the original detection confidence/class metadata. Do not create or mutate face-recognition state inside the tracker.

- [ ] **Step 6: Verify Task 6**

Run the focused test, then `test_runtime_pipeline.py` and `test_runtime_runner.py` to prove detection -> tracking -> TrackState compatibility.

---

### Task 7: Runtime Metrics and Debug Visualization

**Files:**
- Modify: `packages/python/face-recognition-contracts/src/fr_contracts/runtime_status.py`
- Modify: `workers/vision-worker/src/vision_worker/runtime/pipeline.py`
- Create: `workers/vision-worker/src/vision_worker/debug/__init__.py`
- Create: `workers/vision-worker/src/vision_worker/debug/annotations.py`
- Create: `workers/vision-worker/src/vision_worker/debug/pillow_sink.py`
- Modify: `workers/vision-worker/src/vision_worker/runtime/runner.py`
- Modify: `workers/vision-worker/tests/test_runtime_pipeline.py`
- Create: `workers/vision-worker/tests/test_debug_visualization.py`

**Interfaces:**
- Consumes: detector metadata, inference timing, `VideoFrame`, and `FrameProcessingResult`.
- Produces: extended `RuntimeStatus` and `DebugFrameSink.write(frame, result)`.

- [ ] **Step 1: Write runtime metric tests**

Inject a deterministic inference clock and process sampled and skipped frames. Assert:

```python
status.person_inference_fps == 2.0
status.person_inference_latency_ms == 12.0
status.person_inference_latency_average_ms == 10.0
status.person_detections_latest == 1
status.person_detections_total == 2
status.inference_skipped_frames == 3
status.person_detector == "yolo-person:1.0:jetson-default"
status.person_backend == "onnxruntime:CPUExecutionProvider"
```

- [ ] **Step 2: Run metric tests and verify RED**

Run `pytest workers/vision-worker/tests/test_runtime_pipeline.py -q`. Expected: `RuntimeStatus` rejects the new fields or lacks their attributes.

- [ ] **Step 3: Implement metric accumulation**

Measure only the `PersonDetector.detect()` call with a dedicated monotonic clock. Count processed inference frames, detection totals, latest detections, latency total/latest, and sampler skips. Add backward-compatible defaults to `RuntimeStatus` so an older worker status payload remains readable during rolling deployment.

The measurement block is:

```python
started_at = self._inference_clock()
detections = self._person_detector.detect([frame])[0]
latency_ms = (self._inference_clock() - started_at) * 1000.0
self._person_inference_frames += 1
self._person_inference_latency_ms = latency_ms
self._person_inference_latency_total_ms += latency_ms
self._person_detections_latest = len(detections)
self._person_detections_total += len(detections)
```

- [ ] **Step 4: Write debug annotation/rendering tests**

Create a 100x50 RGB frame and one normalized tracked person. Assert annotations map to `(10, 10, 50, 45)` and label exactly `Person 0.91 Track #17`. Render to a temporary PNG and verify it exists, has the original dimensions, and input payload bytes are unchanged.

- [ ] **Step 5: Implement decoupled annotations and Pillow sink**

Define immutable `DebugAnnotation` values and `annotations_for_tracks(frame, tracks)`. The sink creates a Pillow image from the payload, draws boxes/text, and writes collision-free names containing camera/session/sequence. It must not be imported by inference or tracking modules.

Use:

```python
label = f"Person {track.confidence:.2f} Track #{track.track_id}"
box = (
    round(track.box.x1 * frame.width),
    round(track.box.y1 * frame.height),
    round(track.box.x2 * frame.width),
    round(track.box.y2 * frame.height),
)
```

The sink validates RGB payload length, copies only for drawing, calls `ImageDraw.rectangle` and `ImageDraw.text`, creates the configured output directory, and saves `<camera>-<session>-<sequence>.png`.

- [ ] **Step 6: Connect optional debug sink and verify Task 7**

Add an optional `DebugFrameSink` to `RuntimeRunner`. Call it only for processed frames with non-`None` results. Run both focused tests plus API runtime status tests.

---

### Task 8: Configured Worker Wiring, Web Status, and Commands

**Files:**
- Modify: `workers/vision-worker/src/vision_worker/app.py`
- Modify: `workers/vision-worker/src/vision_worker/main.py`
- Modify: `workers/vision-worker/tests/test_worker.py`
- Modify: `packages/python/face-recognition-contracts/src/fr_contracts/runtime_status.py`
- Modify: `apps/web/src/api/contracts.ts`
- Modify: `apps/web/src/app/App.tsx`
- Modify: `README.md`

**Interfaces:**
- Consumes: camera/feature JSON, deployment/artifact roots, factory, BoT-SORT settings, and optional debug directory.
- Produces: configured real worker path and documented execution command.

- [ ] **Step 1: Write configured selection tests**

Inject a fake registry/backend factory and assert `VisionWorker.with_runtime_config` receives the resolved `YoloPersonDetector` and `BotSortTracker`. Assert missing `--model-deployments` for configured mode is a parser error, unsupported runtime exits non-zero, and dependency-free `--once` still uses explicit stubs.

- [ ] **Step 2: Run worker tests and verify RED**

Run `pytest workers/vision-worker/tests/test_worker.py -q`. Expected: configured worker still constructs `MockPersonDetector` and `MockTracker`.

- [ ] **Step 3: Replace configured mocks with factories**

Change the configured factory signature to accept the detector and tracker as injected interface implementations. In CLI configured mode:

1. Load feature/camera config.
2. Create registry from `--model-deployments` and `--model-artifacts`.
3. Resolve and create the real detector.
4. Create `BotSortTracker` from validated runtime defaults/profile.
5. Use `feature.person_detection.processing_fps` for `FrameSampler`.
6. Optionally create a Pillow debug sink for `--debug-output-dir`.
7. Run the existing GStreamer camera source and status publisher.

- [ ] **Step 4: Update frontend runtime contract/display**

Add all Task 7 fields to TypeScript `RuntimeStatus`. Display detector/backend, inference FPS/latency, latest/total detections, and skipped inference frames without removing existing camera/track/buffer information.

- [ ] **Step 5: Document install and run commands**

Document:

```powershell
python -m pip install -e ".[dev,inference-onnx]"
python -m vision_worker.main `
  --camera-config path\to\camera.json `
  --feature-config path\to\face-recognition.json `
  --model-deployments path\to\deployment-manifests `
  --model-artifacts path\to\model-artifacts `
  --status-url http://127.0.0.1:8000/api/v1/runtime/status `
  --debug-output-dir data\debug
```

State that manifests and artifacts are operator-supplied and TensorRT is not implemented.

- [ ] **Step 6: Run Phase 3 verification**

Run, read, and record every exit code:

```powershell
.venv\Scripts\python.exe -I -m pytest
.venv\Scripts\python.exe -I -m ruff check .
.venv\Scripts\python.exe -I -m mypy apps\control-api\src workers\vision-worker\src packages\python\face-recognition-domain\src packages\python\face-recognition-config\src packages\python\face-recognition-contracts\src
.venv\Scripts\python.exe -I -m pip check
.venv\Scripts\python.exe -I -m vision_worker.main --once
```

Then run:

```powershell
cd apps\web
npm run typecheck
npm run build
npm run dev -- --host 127.0.0.1 --port 5177
```

Verify the frontend returns HTTP 200. Start the API, verify `/health`, publish a complete extended runtime status, and verify both REST and WebSocket delivery.

- [ ] **Step 7: Perform only evidence-supported real inference checks**

Search for an operator-supplied ONNX artifact and sample video/real RTSP configuration. If both exist, execute the documented command and retain detection/tracking output. If either is absent, do not download one and report real detection as not executed. Check `tensorrt` availability; if absent, report GPU/TensorRT as not executed.

- [ ] **Step 8: Final scope audit**

Run:

```powershell
rg -n "SCRFD|AdaFace|ArcFace|FAISS" workers packages apps --glob "!**/README.md"
```

Confirm Phase 3 introduced no face detector, embedder, vector search, recognition decision, or recognition event implementation. Report the exact files changed, commands/results, real-model status, GPU status, limitations, run command, and next recommended step, then stop.
