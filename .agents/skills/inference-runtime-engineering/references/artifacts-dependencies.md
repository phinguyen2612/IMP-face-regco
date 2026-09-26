# Artifacts and dependencies

## Portable source of truth

Preserve an approved ONNX artifact as the portable source for each model deployment. Record its checksum, byte size, opset, input/output names, shapes, dtypes, dynamic axes, and model-semantic compatibility metadata.

Keep preprocessing and postprocessing in model-specific components shared across execution backends. ONNX CPU and CUDA should use the same adapter with provider injection. A TensorRT adapter may own engine bindings and buffers but must reuse the same semantic preprocessing/postprocessing contract.

## TensorRT engines

Treat an engine as a derived, device-constrained artifact—not a portable model. Its manifest should bind at least:

- source ONNX checksum;
- TensorRT, CUDA, and relevant platform/JetPack versions;
- GPU architecture or compute capability;
- precision;
- optimization profiles and binding contract;
- required plugins;
- builder version and build-configuration fingerprint.

Build engines offline or during an explicit provisioning command. Do not build them implicitly during normal worker startup. Do not copy an engine between a laptop and Jetson unless the complete compatibility contract has been demonstrated and recorded.

Reduced precision is opt-in. FP16 or INT8 activation requires model-specific correctness evidence and declared tolerances. INT8 additionally requires a reproducible calibration dataset definition and calibration artifact.

## Dependency profiles

The base/control-plane install must not import NVIDIA libraries. Keep CPU inference and NVIDIA inference in separate, mutually exclusive environment profiles because `onnxruntime` and `onnxruntime-gpu` conflict in one Python environment.

Use a CPU profile for local development and normal CI. Use a version-locked NVIDIA profile/image for CUDA hosts. Package TensorRT according to the target platform; Jetson commonly receives it from the JetPack stack rather than a universal Python dependency.

Optional imports belong behind the infrastructure adapter boundary and produce typed availability errors. Never catch a broad import or initialization failure and silently execute another backend; only the resolver may perform an observable `auto` fallback.
