# Resolution and lifecycle

## Vocabulary

- **Installed**: a package or provider can be imported.
- **Available**: the provider can initialize on this host and see a usable device.
- **Compatible**: the chosen artifact and runtime satisfy model, provider, device, shape, precision, and plugin constraints.
- **Resolved**: the deterministic resolver selected the candidate for a model deployment.
- **Active**: load, warmup, and smoke inference completed successfully.

Never collapse these states into a single `gpu_available` boolean.

## Capability boundary

Collect an immutable `RuntimeCapabilities` snapshot in infrastructure. Include OS, architecture, usable ONNX Runtime providers, CUDA device class and compute capability when safely discoverable, TensorRT/runtime/plugin availability, and probe errors. Make the probe injectable so tests never depend on developer hardware.

Do not call CUDA, TensorRT, or PyTorch APIs from domain entities or model-independent contracts. Do not use package import or `nvidia-smi` output as proof that inference works.

## Deterministic per-model resolution

Resolve every deployment independently from:

1. requested mode;
2. deployment manifest and artifacts;
3. capability snapshot;
4. adapter support;
5. compatibility validation;
6. initialization and smoke inference.

Explicit modes (`onnx_cpu`, `onnx_cuda`, `tensorrt`) have one candidate and fail activation if it fails. `auto` evaluates its documented ordered candidates, normally TensorRT → ONNX CUDA → ONNX CPU. Record every rejected candidate and the exact fallback reason.

Manifest/configuration errors that invalidate model semantics are terminal. Candidate-local unavailability, incompatibility, load, or warmup failures may advance `auto` to the next candidate. Do not switch backends ad hoc after activation; mark the stage unready and require a deliberate supervised re-resolution policy.

## Lifecycle

Use explicit states such as `RESOLVING`, `VALIDATING`, `INITIALIZING`, `LOADING`, `WARMING`, `ACTIVE`, `FAILED`, and `CLOSED`.

The normal sequence is:

`resolve → validate artifact → initialize runtime → load once → allocate → warm up → smoke infer → health check → activate → infer repeatedly → close`

Readiness means all required stages are active. Liveness only means the worker control loop is functioning. A CPU resolution is not degraded merely because a GPU exists; degradation means requested/desired behavior could not be activated and a declared fallback was used.

Expose requested and resolved mode, actual providers, safe device class, precision, artifact fingerprint, lifecycle state, warmup result, fallback reason, last typed error, last successful inference, queue depth, and drops. Never expose credentials, local paths, device serials, or raw model inputs.
