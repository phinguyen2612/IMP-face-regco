# Deployment boundary

The initial target is NVIDIA Jetson AGX Orin 32GB. Deployment manifests are deferred until
the TensorRT/GStreamer integration profile, camera resolution, and model artifacts are
selected. The control API must remain deployable separately from the GPU vision worker.
