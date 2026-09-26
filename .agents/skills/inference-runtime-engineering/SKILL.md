---
name: inference-runtime-engineering
description: Use when designing, implementing, or reviewing ONNX Runtime execution providers, CPU/GPU inference selection, CUDA or TensorRT backends, runtime capability detection, model artifact compatibility, warmup, fallback, inference benchmarking, or hardware-aware runtime health.
---

# Inference Runtime Engineering

## Scope

Own the infrastructure boundary between model-specific tensor semantics and the machine that executes them. Keep domain interfaces hardware-agnostic. Use face-pipeline-engineering for face preprocessing, outputs, and embedding compatibility; use recognition-verification-engineering for search and identity semantics.

Read the relevant references before deciding:

- [Resolution and lifecycle](references/resolution-lifecycle.md)
- [Artifacts and dependencies](references/artifacts-dependencies.md)
- [Benchmarking and testing](references/benchmarking-testing.md)

## Workflow

1. Inventory actual adapters, artifacts, package profiles, runtime status, and test coverage. Do not design from phase labels alone.
2. Define supported OS/architecture/device combinations and separate installed, available, compatible, resolved, and active states.
3. Resolve a backend independently for every model deployment. Explicit requests are strict; only `auto` may try an ordered fallback.
4. Validate artifacts before model activation. Initialize, load, warm up, smoke-test, then expose readiness.
5. Inject execution providers into shared ONNX adapters so preprocessing and postprocessing remain model-owned and backend-independent.
6. Keep TensorRT model-specific and evidence-driven. Build engines offline; never assume portability across devices or runtime stacks.
7. Bound queues, prefer fresh frames under overload, and expose drops and queue depth.
8. Establish CPU correctness first, then compare accelerated outputs before accepting speed gains.

## Invariants

- ONNX Runtime CPU is the portable baseline; NVIDIA support is additive and optional.
- Capability probing is centralized, deterministic, injectable in tests, and based on real initialization—not package presence or `nvidia-smi` alone.
- A requested backend, resolved backend, provider, device, precision, artifact fingerprint, fallback reason, and lifecycle state are observable per model.
- Models and sessions are loaded once per lifecycle, never per frame.
- Backend errors are typed; they must not become “no detection,” “unknown identity,” or silent CPU fallback.
- Runtime choice must not change ROI, quality, similarity, or verification semantics.
- Production readiness requires reproducible correctness and performance evidence on the claimed hardware.

## Review Checklist

- [ ] CPU portable baseline
- [ ] NVIDIA dependencies optional
- [ ] Domain hardware agnostic
- [ ] Runtime detection centralized
- [ ] AUTO fallback observable
- [ ] Explicit backend strict
- [ ] ONNX portable artifact preserved
- [ ] TensorRT compatibility validated
- [ ] No per-frame runtime/model loading
- [ ] Bounded queues
- [ ] Benchmark reproducible
- [ ] Correctness checked
- [ ] CPU CI works without GPU
- [ ] GPU tests optional
- [ ] Runtime health truthful
