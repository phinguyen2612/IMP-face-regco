# Phase 3: Real YOLO Person Detection Design

## Scope

Phase 3 replaces the runtime's mock person detector with a configurable YOLO
implementation and replaces mock tracking in the configured camera path with a
BoT-SORT motion/IoU tracker. It ends at track state and runtime observability.

The phase does not implement SCRFD, face quality execution, face alignment,
AdaFace, ArcFace, FAISS, identity verification, or recognition events.

## Current State

The worker already provides:

- `VideoFrame` objects containing RGB payloads from GStreamer.
- Bounded frame history and per-camera frame sampling.
- `PersonDetector` and `Tracker` interfaces with deterministic mocks.
- Camera/session-scoped `TrackState` storage.
- Runtime status publication to FastAPI and WebSocket clients.
- Versioned UI configuration containing model references.

The repository does not contain a model deployment resolver, a real tracker,
an inference library, a YOLO artifact, or a sample video. The development host
does not have ONNX Runtime, TensorRT, PyTorch, OpenCV, or GStreamer installed.

## Architecture

```text
FaceRecognitionConfig
  person model reference + UI detection settings
                         |
ModelDeploymentRegistry |  backend-controlled manifests
                         v
PersonDetectorFactory -> YoloPersonDetector
                           |
                  YoloInferenceBackend
                    |              |
          OnnxRuntimeBackend   TensorRTBackend (future)

VideoFrame (RGB)
  -> letterbox preprocessing
  -> backend inference
  -> YOLO output normalization
  -> person filtering + confidence filtering + NMS
  -> coordinate restoration
  -> PersonDetection
  -> BotSortTracker (motion/IoU profile)
  -> TrackedPerson
  -> TrackState
  -> RuntimeStatus
```

`RuntimePipeline` depends only on `PersonDetector` and `Tracker`. It must not
import ONNX Runtime, TensorRT, or YOLO-specific output structures.

## Configuration Boundaries

### UI-editable feature configuration

The person detector selection retains:

- `model_definition_id`
- `model_version`
- `deployment_id`

It adds a person-detection settings section containing:

- `confidence_threshold`, constrained to `[0, 1]`
- `iou_threshold`, constrained to `[0, 1]`
- `input_size`, a positive width/height pair
- `processing_fps`, greater than zero
- `inference_profile`, a logical profile identifier such as `balanced`

The UI never receives artifact paths, CUDA device indices, TensorRT bindings,
ONNX input/output names, or provider-specific settings.

### Backend-controlled deployment manifests

A versioned deployment manifest resolves the three model-reference identifiers
to:

- model type (`PERSON_DETECTION`)
- runtime (`onnxruntime` initially; `tensorrt` reserved)
- artifact URI or local resolved path
- artifact checksum
- YOLO output layout/profile
- input tensor layout and normalization metadata
- runtime provider/profile settings

The resolver rejects missing artifacts, checksum mismatches, mismatched model
types/versions/deployment IDs, unsupported runtimes, and path escapes from the
configured artifact root.

## Domain Contract

`PersonDetector.detect()` returns one list of `PersonDetection` values per input
frame. Each detection contains:

- normalized bounding box in the original frame coordinate system
- confidence
- class ID (`0` for the supported person model profile)
- class name (`person`)
- source frame timestamp
- source frame width and height

No raw YOLO tensor or backend-specific object crosses the detector boundary.
The mock detector remains available and implements the same contract.

## ONNX Runtime Backend

The initial real backend uses an exported YOLO ONNX model. ONNX Runtime is an
optional local-inference dependency rather than a dependency of domain or
control-plane packages.

The backend:

1. Verifies the artifact exists before creating a session.
2. Loads the configured ONNX providers without silently claiming CUDA or
   TensorRT execution.
3. Validates the model input/output contract against the deployment profile.
4. Accepts a contiguous `float32` NCHW tensor.
5. Returns backend-neutral numeric output to the YOLO postprocessor.

The future TensorRT backend will implement the same `YoloInferenceBackend`
interface. TensorRT engine paths, CUDA context selection, binding indices, and
buffer management remain entirely inside that adapter and its deployment data.

## Preprocessing

The preprocessor validates that each `VideoFrame` has positive dimensions,
`RGB` pixel format, and a payload with exactly `width * height * 3` bytes.

For each frame it:

1. Creates a NumPy view over the bytes without an initial payload copy.
2. Resizes while preserving aspect ratio.
3. Applies symmetric letterbox padding to the configured input dimensions.
4. Converts pixels to `float32` and applies profile-defined normalization.
5. Transposes HWC RGB to contiguous NCHW.
6. Returns tensor data plus scale and padding metadata.

The metadata is retained only for postprocessing and is not exposed downstream.

## Postprocessing

The first supported model profile is a standard raw Ultralytics-style YOLO ONNX
output containing center-based boxes and class scores. Output-layout handling is
selected by the deployment profile rather than guessed from arbitrary tensors.

Postprocessing:

1. Validates tensor shape and finite numeric values.
2. Selects only the configured person class.
3. Applies the UI confidence threshold.
4. Converts `cx, cy, width, height` to corner coordinates.
5. Runs class-aware NMS using the UI IoU threshold.
6. Removes padding and reverses the letterbox scale.
7. Clips coordinates to the original frame.
8. Converts coordinates to normalized original-frame values.
9. Produces `PersonDetection` domain objects.

Malformed output is an explicit inference error and is never converted into an
empty successful detection result.

## BoT-SORT Tracking Profile

Phase 3 implements a BoT-SORT motion/IoU profile with:

- per-track Kalman motion state
- high- and low-confidence association stages
- IoU-based association cost
- linear assignment
- confirmed, lost, and removed track lifecycles
- configurable match thresholds and track buffer
- monotonically allocated camera/session-local track IDs

Appearance ReID is disabled and camera-motion compensation is not claimed for
this phase. Those are explicit future tracker profiles, not hidden no-op flags.
Tests verify stable IDs for continuously visible synthetic detections, track
loss, expiration, and new-ID allocation after removal.

## Runtime Metrics

`RuntimeStatus` is extended with:

- `person_inference_fps`
- last and rolling-average person inference latency in milliseconds
- detections in the latest processed frame
- cumulative person detections
- inference-skipped frames
- loaded person detector identifier/version/deployment
- inference backend/runtime name

Existing camera, input/processed FPS, dropped frames, active tracks, ring-buffer
usage, worker health, and config revision fields remain intact. Deliberately
sampled-out frames are counted as inference-skipped, not capture-dropped.

## Detector and Tracker Selection

The configured worker path uses factories:

1. Resolve the person model deployment.
2. Instantiate the backend declared by that deployment.
3. Construct `YoloPersonDetector` with UI thresholds and input size.
4. Construct the BoT-SORT motion/IoU tracker from validated tracker settings.
5. Inject both through the existing pipeline interfaces.

The dependency-free `--once` smoke path and unit tests can continue to select
mock adapters explicitly. Unsupported runtimes fail startup with a clear error;
the worker never silently falls back from real inference to mocks.

## Debug Visualization

Debug visualization is separate from inference and tracking. A renderer consumes
`VideoFrame` metadata plus `TrackedPerson` results and produces an annotated
development image containing:

- person bounding box
- confidence
- track ID

The renderer is enabled only by an explicit debug output option. It is not used
by tracking decisions and can later be replaced by a React-preview transport.

## Error Handling

Configuration and startup fail explicitly for:

- invalid thresholds, input size, processing FPS, or tracker settings
- absent deployment manifest
- unsupported backend
- missing or checksum-invalid model artifact
- unavailable ONNX Runtime provider
- incompatible model input/output signature

Individual invalid frames and malformed inference output produce typed runtime
errors and unhealthy/degraded status as appropriate. No exception is converted
to a successful empty detection response.

## Testing Strategy

Tests are written before their corresponding implementation and cover:

- RGB payload validation and tensor shape
- resize/letterbox scale and padding
- restoration to original normalized coordinates
- confidence and person-class filtering
- IoU and NMS behavior
- supported and malformed YOLO tensor layouts
- `PersonDetector` contract and batch cardinality
- model-reference/deployment resolution
- missing artifact, checksum failure, and unsupported runtime
- continuous detection to stable track ID
- track loss, expiration, and replacement
- detector/tracker factory selection without fallback
- new runtime metric calculations
- debug annotation content
- mock detector compatibility

The full Python test, Ruff, strict MyPy, React typecheck/build, API startup,
worker smoke startup, and available infrastructure checks run before completion.

## Verification Claims

No model is downloaded automatically. If no compatible user-supplied ONNX model
and video/RTSP source are available, completion will report that preprocessing,
postprocessing, backend construction, and synthetic detector/tracker integration
were tested, but real-image detection was not executed.

TensorRT and GPU performance are only reported after execution on the Jetson AGX
Orin. ONNX Runtime CPU results must not be presented as Jetson or TensorRT
performance.

## Phase Completion Boundary

Phase 3 is complete when the real ONNX YOLO adapter, deployment selection,
BoT-SORT motion/IoU tracking, metrics, debug mechanism, and prescribed tests are
implemented and verified. Work stops before SCRFD or any face-recognition stage.
