# Phase 9 — Cross-platform Inference Runtime & Hardware Acceleration

**Status:** Proposed design only
**Scope:** Face Recognition only
**Gate:** No product implementation before `APPROVE PHASE 9 DESIGN`.

## Decision

Use ONNX Runtime CPU as the mandatory portable baseline. Resolve a backend independently for YOLO, SCRFD, and AdaFace. In `auto`, try a compatible TensorRT engine, then ONNX Runtime CUDA, then ONNX Runtime CPU. Explicit backends are strict and never fall back. Hardware selection belongs below the existing detector/embedder interfaces; model preprocessing, postprocessing, and recognition semantics remain backend-independent.

The repository currently has interfaces and mock/stub adapters, not real YOLO, SCRFD, AdaFace, ONNX Runtime, CUDA, TensorRT, or FAISS integrations. Its manifest schema also lacks executable tensor/artifact contracts. This design therefore defines the boundary and acceptance gates; it does not claim any real backend is already supported.

Alternatives considered:

1. Shared model adapters with injected ONNX providers and optional model-specific TensorRT executors — selected, because it prevents CPU/CUDA semantic drift.
2. ORT CPU/CUDA only — safest first implementation milestone, but insufficient for the eventual Jetson optimization goal.
3. Separate CPU/GPU pipelines — rejected because it duplicates preprocessing/postprocessing and makes correctness difficult to compare.

## 1. Current runtime architecture

- `PersonDetector`, `FaceDetector`, and `FaceEmbedder` are hardware-neutral interfaces with lightweight Python payloads.
- `VisionWorker.with_runtime_config` currently wires `MockPersonDetector` and `MockTracker`; the live worker is not an end-to-end face-recognition inference pipeline.
- Only mock/stub model adapters exist. No real execution provider, runtime resolver, model registry, or warmup lifecycle exists.
- `ModelSelection` references definition/version/deployment IDs, but backend is not modeled. `RuntimeSettings` contains no inference-runtime choice.
- Manifest v1 has identity/runtime/artifact placeholders but no concrete manifests, tensor contracts, compatibility data, or approved checksums.
- The frame ring buffer is bounded, but there is no separate bounded inference queue. Runtime status has camera/worker counters but no per-model runtime state.
- Base dependencies contain no NumPy, image runtime, ONNX Runtime, CUDA, or TensorRT package.

Phase 9 must not hide missing Phase 3–7 product implementations inside a generic executor.

## 2. Supported runtime matrix

| Tier | Environment | Required resolution | Evidence required |
|---|---|---|---|
| A | CPU-only laptop/server | ORT CPU, full functionality | Mandatory CPU CI and end-to-end acceptance |
| B | NVIDIA laptop/server | TensorRT → ORT CUDA → ORT CPU in `auto` | Target-specific CUDA/TensorRT runs |
| C | Jetson AGX Orin 32 GB | TensorRT preferred; only deliberately validated fallback | Native JetPack/ARM64 acceptance |
| D | CI without GPU | ORT CPU plus mocks/fakes | Core tests never skipped for missing GPU |

Windows/Linux x86-64 and Jetson Linux ARM64 are distinct targets. Desktop success never proves Jetson support. Other CPU platforms are supported only where pinned dependencies and acceptance tests pass.

## 3. CPU baseline

ORT CPU must run approved ONNX exports of YOLO, SCRFD, and AdaFace with the same semantics as accelerated variants. A clean CPU install must not install or import NVIDIA packages. Lower throughput is acceptable; incorrect outputs, weaker thresholds, or startup failure because NVIDIA is absent are not. Workload is controlled using sampling, ROI/quality gates, recognition intervals, verified-track cache reuse, and bounded queues.

## 4. ONNX Runtime architecture

Add one infrastructure `OnnxSessionFactory` receiving a validated artifact, provider choice, and backend-only session options. Model adapters own preprocessing, tensor contracts, decoding, alignment/normalization, and domain conversion. The factory owns session creation and tensor execution only.

The same `YoloOnnxDetector`, `ScrfdOnnxDetector`, and `AdaFaceOnnxEmbedder` serve CPU and CUDA via provider injection. Sessions load once during activation. Provider/session/binding/output errors become typed runtime failures, never empty detections or `UNKNOWN`.

## 5. CUDA provider strategy

`onnx_cuda` requires the NVIDIA environment profile, discoverable `CUDAExecutionProvider`, successful session creation with CUDA primary, successful warmup/smoke inference, and confirmation that CUDA is active. Package import or `nvidia-smi` is insufficient.

ORT may use CPU for unsupported individual nodes when configured, but this must not be misreported as a healthy CUDA session after whole-provider failure. Actual providers and warnings are observable. Provider options, device index, arenas, and threading are backend-only configuration.

## 6. TensorRT strategy

TensorRT is an optional model-specific executor sharing model semantic preprocessing/postprocessing. Engines are built by an explicit offline/provisioning command, never implicitly during normal worker startup.

Every engine is bound to source ONNX checksum, adapter contract, TensorRT/CUDA/platform versions, GPU compute capability, precision, optimization profiles, plugins, and builder configuration. Laptop engines are not assumed portable to Jetson. FP16 needs correctness evidence; INT8 is outside Phase 9 unless calibration and acceptance are separately approved. Interfaces may exist without hardware, but no mock can justify a TensorRT support claim.

## 7. `RuntimeCapabilities`

Create an immutable, injectable infrastructure snapshot containing OS/architecture, usable ORT providers, successful CPU probe, safe CUDA device class/compute capability and probe errors, TensorRT runtime/device/plugin availability, and supported precision. Keep `INSTALLED`, `AVAILABLE`, `COMPATIBLE`, `RESOLVED`, `ACTIVE`, and `FAILED` distinct. Exclude credentials, hostnames, serials, local paths, and RTSP data.

## 8. `InferenceRuntimeResolver`

Input is one deployment, requested backend, versioned artifacts, capability snapshot, adapter factories, and allowed policy. Output is either a fully activated `ResolvedModelRuntime` or a typed report of all rejected candidates. Resolution is deterministic and per model. Only the resolver may fall back; adapters and domain services may not.

`ResolvedModelRuntime` records definition/version/deployment, requested/resolved backend, actual provider, safe device class, artifact fingerprint, precision, lifecycle state, and fallback trail.

## 9. `AUTO` algorithm

1. Validate the deployment and model-semantic contract; semantic/configuration invalidity is terminal.
2. Build the ordered candidate list `tensorrt`, `onnx_cuda`, `onnx_cpu`.
3. Record and skip candidates disallowed by deployment or lacking required adapters/artifacts.
4. Validate host capability and artifact compatibility.
5. Initialize, load once, allocate, warm up, and smoke-infer.
6. Select the first candidate reaching `ACTIVE`; retain every prior failure code/reason.
7. If none activates, fail that model and keep the recognition pipeline unready.

Candidate-local unavailability, incompatibility, load, or warmup failure may advance `auto`. Runtime failure after activation does not cause an ad hoc mid-track switch; it makes the stage unready until a supervised re-resolution.

## 10. Explicit backend behavior

`onnx_cpu`, `onnx_cuda`, and `tensorrt` each have exactly one candidate. Missing dependencies/devices/artifacts, incompatibility, or failed initialization/warmup/smoke inference fails activation with a typed error. No explicit request is rewritten to `auto`; liveness can remain true for diagnostics while readiness is false.

## 11. Per-model deployment resolution

Resolve `person_detector` (YOLO), `face_detector` (SCRFD), and `face_embedder` (AdaFace) independently. Mixed backends are valid when every contract passes. Overall readiness requires all required roles and cross-model contracts to be active/compatible.

The normal UI continues selecting deployments. Requested backend, provider options, device index, engine profile, and artifact location are operator/backend-only deployment fields. The UI may display safe resolved status without exposing low-level mutation controls.

## 12. Artifact compatibility

Manifest v2 adds to model identity:

- role/family, adapter-contract version, deployment ID;
- artifact kind/URI/checksum/size/source relationship;
- ONNX opset, tensor names/shapes/dtypes/dynamic axes and batch/profile bounds;
- preprocessing, postprocessing, alignment, and normalization contract IDs;
- embedding dimension and compatibility-space version;
- supported backends/precision and correctness-profile reference;
- all TensorRT compatibility fields from section 6.

Validate checksum and semantics before initialization. AdaFace remains compatible with an index only when model/weights, preprocessing/alignment, dimension, normalization, and compatibility space match; equal vector dimensions alone are insufficient.

## 13. Dependency/install profiles

- `base`: API/config/contracts; no NVIDIA imports.
- `inference-cpu`: common numerical/image packages plus `onnxruntime`.
- `inference-nvidia`: common inference packages plus `onnxruntime-gpu`.
- `tensorrt-target`: bindings/runtime from a pinned target image/platform stack, including JetPack where applicable.
- `dev/test`: CPU inference dependencies plus lint/type/test tools.

CPU and GPU ORT wheels conflict, so CPU/NVIDIA are mutually exclusive clean-environment profiles, not extras installed together. Lock target versions. Lazy NVIDIA imports live only in infrastructure adapters and raise typed availability errors.

## 14. Model lifecycle/warmup

Lifecycle is `RESOLVING → VALIDATING → INITIALIZING → LOADING → WARMING → ACTIVE → CLOSED`, with any error transitioning to `FAILED`. Activation validates the contract/checksum, creates the runtime, allocates resources, runs representative non-private warmup, smoke inference, and output validation. `infer()` is legal only in `ACTIVE` and never loads/builds/resolves. `close()` is idempotent and releases sessions/buffers/handles.

## 15. Backpressure under CPU load

Keep the evidence ring buffer, but add a bounded latest-frame inference queue. On overflow drop the oldest unprocessed frame, enqueue the newest eligible frame, and increment a reason-labelled counter. Start with batch size 1 and one ordered consumer. Queue capacity, sampling, and ORT thread counts are bounded backend settings. Preserve frame IDs/timestamps for latency and evidence integrity. Concurrency/batching require benchmark proof and explicit session ownership.

## 16. Runtime health/status

Add safe per-model status: role/deployment/version, requested/resolved backend, actual providers, device class, precision, artifact fingerprint, lifecycle, load/warmup/smoke results, fallback trail, last typed error, last successful inference, latency, queue depth/capacity, and drops.

Liveness means the worker control loop/status publisher runs. Readiness means required camera/pipeline conditions and all models are active. Intentionally selected CPU is healthy, not degraded. Existing API/WebSocket delivery carries this schema. Metrics use bounded labels: role, backend, provider, result, and error code.

## 17. Benchmark methodology

A versioned `benchmark-inference` CLI supports each model and the full pipeline, with deployment/backend/input/iterations/warmup/batch/concurrency/output arguments. Record safe OS/architecture, generalized CPU/GPU class, Python/package/provider versions, artifact fingerprints, precision, tensor/input profile, and queue policy.

Measure cold start, capability resolution/load, warmup, preprocessing, execution, postprocessing, end-to-end mean/median/p95/p99 (when sample size permits), sustained FPS, memory, optional utilization/thermal state, and drops. Synchronize GPU work around timings. Random tensors may measure executor overhead but never product throughput. Emit human-readable and schema-versioned JSON without secrets or identifying paths.

## 18. Correctness comparison

Use ORT CPU FP32 as portable reference unless an approved model release says otherwise. Feed identical decoded inputs through shared semantics:

- YOLO: matched boxes, confidence drift, IoU, recall/precision.
- SCRFD: boxes, confidence, landmark assignment and coordinate drift.
- AdaFace: shape, finiteness, norm, cosine drift, neighbor ordering, and decisions near thresholds.
- Pipeline: recognition state transitions and event decisions on deterministic labeled fixtures.

Version tolerances by model and precision before acceleration is enabled. A faster candidate outside tolerance is incompatible, not healthy.

## 19. Testing matrix

Mandatory CPU tests cover injected capability probes, deterministic resolver ordering, strict modes, every fallback path, schemas/artifact compatibility, lifecycle/resource cleanup, provider factories, bounded queue/drop accounting, status/redaction, benchmark statistics/schema, and unchanged semantics. Real ORT CPU smoke/integration and end-to-end tests are mandatory once approved artifacts exist.

CUDA/TensorRT/Jetson tests are separately tagged and optional in ordinary CI, but mandatory for a release claiming that target. GPU absence may skip optional profiles; it never skips core CPU/domain tests.

## 20. CPU acceptance test

In a clean machine/container without NVIDIA packages: install CPU profile; prove NVIDIA modules are not imported; validate/load all three approved ONNX models; start required services; process deterministic video through ingestion, YOLO, tracking, SCRFD, alignment/quality, AdaFace, FAISS, verification, policy/event, and evidence; assert all model statuses are `onnx_cpu/ACTIVE`; verify known/unknown/events/evidence; prove overload remains bounded and recent frames progress; restart and verify deterministic activation/cleanup.

This cannot pass until real upstream adapters/artifacts and missing live pipeline stages exist. A tiny generic ONNX test validates only the runtime layer and must be labelled accordingly.

## 21. NVIDIA acceptance test

For each claimed target class: install a pinned clean profile; record safe capabilities; run explicit ORT CUDA for every model; provision and run TensorRT where claimed; compare against CPU tolerances; assert expected `auto` selection/fallback trail; run sustained full-pipeline latency/FPS/memory/queue/drop/utilization tests; and test restart/resource release. Desktop results never validate Jetson. Unsupported current hardware is reported as `NOT TESTED`, without fabricated numbers.

## 22. Fallback tests

Cover: TensorRT success; absent/incompatible/failed-warmup TensorRT → CUDA; absent/non-active/failed-smoke CUDA → CPU; all candidates fail; semantic manifest failure is terminal; every explicit backend fails without fallback; mixed per-model resolution; post-activation failure causes unready without live switching; and ordered sanitized trails reach API/WebSocket. At least one claimed CUDA fallback path must run on real NVIDIA hardware, not only fakes.

## 23. Documentation changes

Update quick-start/install profiles, runtime architecture/lifecycle, manifest-v2 migration, operator status/error runbook, offline TensorRT provisioning, benchmark schema/usage, target support matrix (`DESIGNED`/`TESTED`/`SUPPORTED`), privacy rules for fixtures/status, and provider/wheel/JetPack troubleshooting. Keep future Jetson instructions separate from validated laptop instructions and include no credentials, RTSP URLs, private evidence, machine paths, or invented performance.

## 24. Expected implementation files

```text
model-manifests/schemas/model-manifest-v2.schema.json
packages/config/src/fr_config/{models,runtime}.py
packages/contracts/src/fr_contracts/runtime_status.py
apps/vision-worker/src/vision_worker/inference/runtime/
  {types,errors,capabilities,resolver,lifecycle,onnx_session,tensorrt_executor}.py
apps/vision-worker/src/vision_worker/inference/{yolo,scrfd,adaface}/
  {preprocessing,postprocessing,adapter}.py
apps/vision-worker/src/vision_worker/runtime/inference_queue.py
apps/vision-worker/src/vision_worker/tools/{benchmark_inference,build_tensorrt}.py
tests/unit/inference_runtime/
tests/integration/{inference_cpu,inference_cuda,inference_tensorrt}/
tests/acceptance/face_recognition/
docs/runtime/
docs/benchmarks/
```

Exact paths follow current package conventions. Real adapter files wait for approved artifacts/contracts. TensorRT code must not pretend to work where it cannot be exercised.

## 25. Remaining unresolved decisions

1. Exact licensed YOLO/SCRFD/AdaFace releases, ONNX artifacts/checksums, and tensor/pre/post contracts.
2. Whether missing real Phase 3–7 runtime pieces arrive first or are explicit prerequisites in Phase 9 planning.
3. Pinned Python/ORT/CUDA/cuDNN/TensorRT/JetPack matrices for Windows x86-64, Linux x86-64, and Jetson ARM64.
4. TensorRT profiles, plugins, workspace limits, and target build/provisioning environment.
5. Versioned numerical/domain tolerances, labeled corpus, and AdaFace/index compatibility evidence.
6. Hardware-profile acceptance budgets for resolution, sustained processed FPS, p95/p99 latency, memory, overload duration, and drop rate.

These do not block implementing resolver/CPU foundations, but they block claims of full model/hardware support.

## Self-review

- No NVIDIA dependency enters the base/CPU startup path.
- Domain interfaces remain hardware agnostic; resolution is per deployment.
- Only `auto` falls back, and every attempt is observable.
- CPU/CUDA share model preprocessing/postprocessing.
- TensorRT is compatibility-bound, built offline, and never faked.
- ORT dependency conflicts and Jetson portability are explicit.
- Slow CPU work is bounded and freshness-oriented.
- Health distinguishes liveness, readiness, compatibility, and activation.
- Benchmarks separate cold/warm behavior and require correctness evidence.
- No unrelated IOC feature, retraining, INT8, distributed inference, Kubernetes, or autoscaling is introduced.

---

**STOP:** Await exactly `APPROVE PHASE 9 DESIGN` before Phase 9 product code.
