from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from fr_domain.model_management import DeploymentBackend, ModelType


class RuntimeResolutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimeCapabilities:
    onnx_cpu_available: bool
    onnx_cuda_available: bool
    tensorrt_available: bool
    execution_providers: tuple[str, ...] = ()

    @classmethod
    def cpu_only(cls) -> "RuntimeCapabilities":
        return cls(True, False, False, ("CPUExecutionProvider",))


@dataclass(frozen=True, slots=True)
class ModelArtifacts:
    onnx: bool = False
    compatible_tensorrt: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedModelRuntime:
    requested_backend: DeploymentBackend
    backend: DeploymentBackend
    execution_provider: str
    fallback_reason: str | None = None


class InferenceRuntimeResolver:
    def resolve(
        self,
        requested: DeploymentBackend,
        artifacts: ModelArtifacts,
        capabilities: RuntimeCapabilities,
    ) -> ResolvedModelRuntime:
        if requested is DeploymentBackend.ONNX_CPU:
            if not artifacts.onnx:
                raise RuntimeResolutionError("ARTIFACT_MISSING")
            if not capabilities.onnx_cpu_available:
                raise RuntimeResolutionError("RUNTIME_UNAVAILABLE")
            return ResolvedModelRuntime(requested, requested, "CPUExecutionProvider")
        if requested is DeploymentBackend.ONNX_CUDA:
            if not capabilities.onnx_cuda_available:
                raise RuntimeResolutionError("CUDA_UNAVAILABLE")
            if not artifacts.onnx:
                raise RuntimeResolutionError("ARTIFACT_MISSING")
            return ResolvedModelRuntime(requested, requested, "CUDAExecutionProvider")
        if requested is DeploymentBackend.TENSORRT:
            if not capabilities.tensorrt_available:
                raise RuntimeResolutionError("TENSORRT_UNAVAILABLE")
            if not artifacts.compatible_tensorrt:
                raise RuntimeResolutionError("ENGINE_INCOMPATIBLE")
            return ResolvedModelRuntime(requested, requested, "TensorRT")

        fallback_reason: str | None = None
        if capabilities.tensorrt_available and artifacts.compatible_tensorrt:
            return ResolvedModelRuntime(requested, DeploymentBackend.TENSORRT, "TensorRT")
        fallback_reason = (
            "TENSORRT_ARTIFACT_UNAVAILABLE"
            if capabilities.tensorrt_available
            else "TENSORRT_UNAVAILABLE"
        )
        if capabilities.onnx_cuda_available and artifacts.onnx:
            return ResolvedModelRuntime(
                requested,
                DeploymentBackend.ONNX_CUDA,
                "CUDAExecutionProvider",
                fallback_reason,
            )
        if not capabilities.onnx_cuda_available:
            fallback_reason = "CUDA_PROVIDER_UNAVAILABLE"
        if capabilities.onnx_cpu_available and artifacts.onnx:
            return ResolvedModelRuntime(
                requested,
                DeploymentBackend.ONNX_CPU,
                "CPUExecutionProvider",
                fallback_reason,
            )
        raise RuntimeResolutionError("NO_COMPATIBLE_RUNTIME")


class PreparedModelRuntime(Protocol):
    deployment_id: str
    model_type: ModelType

    def warmup(self) -> None: ...
    def health_check(self) -> None: ...
    def close(self) -> None: ...


class AtomicModelSet:
    def __init__(self) -> None:
        self._lock = Lock()
        self._active: dict[ModelType, PreparedModelRuntime] = {}

    def active(self, model_type: ModelType) -> PreparedModelRuntime | None:
        with self._lock:
            return self._active.get(model_type)

    def activate(self, candidate: PreparedModelRuntime) -> None:
        try:
            candidate.warmup()
            candidate.health_check()
        except Exception:
            candidate.close()
            raise
        with self._lock:
            previous = self._active.get(candidate.model_type)
            self._active[candidate.model_type] = candidate
        if previous is not None and previous is not candidate:
            previous.close()
