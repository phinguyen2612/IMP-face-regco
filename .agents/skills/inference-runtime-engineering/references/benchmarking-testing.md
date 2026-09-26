# Benchmarking and testing

## Correctness before speed

Choose ONNX Runtime CPU FP32 as the portable reference unless a validated model-specific reference is documented. Run representative, legally usable inputs through identical preprocessing and postprocessing.

Compare model semantics, not only raw tensor closeness:

- detectors: matched boxes, class/confidence drift, recall/precision, IoU, and landmarks where applicable;
- embedders: shape, finite values, norm, cosine drift, and downstream verification decisions near thresholds;
- pipeline: track/recognition/event outcomes and failure behavior.

Set model- and precision-specific tolerances before enabling an accelerated artifact. Never invent tolerances or benchmark numbers.

## Reproducible benchmark

Capture safe environment metadata: OS, architecture, Python and package versions, generalized CPU/GPU model, provider versions, CUDA/TensorRT versions, artifact fingerprints, backend, precision, input shape, batch size, concurrency, queue policy, warmup count, and measured iteration count. Exclude usernames, hostnames, absolute paths, credentials, device serials, and images.

Separate cold startup, model load, warmup, and steady-state inference. Synchronize asynchronous GPU work around timing. Report mean, median/p50, p95, p99 when sample size is adequate, sustained throughput, memory, optional utilization/thermal observations, and queue drops. Include preprocessing/postprocessing and an end-to-end pipeline mode; do not report random-tensor kernel timing as product throughput.

Write machine-readable results with a schema version. A result is evidence only for its recorded host/runtime/artifact combination.

## Test matrix

Mandatory CPU CI:

- resolver and typed failure unit tests with injected capabilities;
- manifest/artifact compatibility contracts;
- lifecycle, warmup, close, and health transitions;
- bounded queue/drop policy;
- benchmark statistics/schema;
- real ONNX Runtime CPU smoke tests and end-to-end acceptance when approved model artifacts are available.

Optional tagged GPU jobs:

- CUDA provider initialization and smoke inference;
- TensorRT engine compatibility and smoke inference;
- explicit-mode failure and `auto` fallback paths;
- correctness comparison against the CPU reference;
- lifecycle/resource-release repetition.

GPU tests may skip only when the job does not claim GPU support. A release claiming a target must run its required acceptance job. Mock providers verify orchestration, never hardware support.
