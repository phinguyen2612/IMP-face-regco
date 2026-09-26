from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

import httpx
from fr_domain.model_management import DeploymentBackend, ModelType

from vision_worker.model_runtime import (
    AtomicModelSet,
    InferenceRuntimeResolver,
    ModelArtifacts,
    PreparedModelRuntime,
    ResolvedModelRuntime,
    RuntimeCapabilities,
    RuntimeResolutionError,
)


class ModelDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PendingModelDeployment:
    deployment_id: str
    model_type: ModelType
    requested_backend: DeploymentBackend
    artifact_path: Path
    artifact_checksum: str
    version: str
    precision: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> PendingModelDeployment:
        deployment = payload["deployment"]
        definition = payload["definition"]
        version = payload["version"]
        artifact = payload["artifact"]
        return cls(
            deployment_id=str(deployment["id"]),
            model_type=ModelType(definition["model_type"]),
            requested_backend=DeploymentBackend(deployment["backend"]),
            artifact_path=Path(str(artifact["storage_key"])),
            artifact_checksum=str(artifact["checksum"]),
            version=str(version["version"]),
            precision=str(deployment["precision"]),
        )


class DeploymentProvider(Protocol):
    def pending(self) -> list[PendingModelDeployment]: ...

    def report(
        self,
        deployment_id: str,
        *,
        success: bool,
        resolved: ResolvedModelRuntime | None = None,
        error_category: str | None = None,
    ) -> None: ...


class ModelAdapterFactory(Protocol):
    def prepare(
        self,
        deployment: PendingModelDeployment,
        resolved: ResolvedModelRuntime,
    ) -> PreparedModelRuntime: ...


class UnavailableProductionAdapterFactory:
    """Truthful boundary until real YOLO/SCRFD/AdaFace adapters are installed."""

    def prepare(
        self,
        deployment: PendingModelDeployment,
        resolved: ResolvedModelRuntime,
    ) -> PreparedModelRuntime:
        del deployment, resolved
        raise ModelDeliveryError("REAL_MODEL_ADAPTER_NOT_IMPLEMENTED")


class HttpDeploymentProvider:
    def __init__(self, base_url: str, worker_token: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-Worker-Token": worker_token}
        self._timeout = timeout_seconds

    def pending(self) -> list[PendingModelDeployment]:
        response = httpx.get(
            f"{self._base_url}/api/v1/internal/model-deployments/pending",
            headers=self._headers,
            timeout=self._timeout,
        )
        response.raise_for_status()
        return [PendingModelDeployment.from_api(item) for item in response.json()["items"]]

    def report(
        self,
        deployment_id: str,
        *,
        success: bool,
        resolved: ResolvedModelRuntime | None = None,
        error_category: str | None = None,
    ) -> None:
        body: dict[str, object] = {"success": success, "error_category": error_category}
        if resolved is not None:
            body.update(
                resolved_backend=resolved.backend.value,
                execution_provider=resolved.execution_provider,
                fallback_reason=resolved.fallback_reason,
            )
        response = httpx.post(
            f"{self._base_url}/api/v1/internal/model-deployments/{deployment_id}/activation-result",
            headers=self._headers,
            json=body,
            timeout=self._timeout,
        )
        response.raise_for_status()


class ModelDeploymentSynchronizer:
    def __init__(
        self,
        provider: DeploymentProvider,
        capabilities: RuntimeCapabilities,
        adapter_factory: ModelAdapterFactory,
        active_models: AtomicModelSet | None = None,
        resolver: InferenceRuntimeResolver | None = None,
    ) -> None:
        self._provider = provider
        self._capabilities = capabilities
        self._factory = adapter_factory
        self.active_models = active_models or AtomicModelSet()
        self._resolver = resolver or InferenceRuntimeResolver()

    @staticmethod
    def _verify_artifact(deployment: PendingModelDeployment) -> None:
        try:
            payload = deployment.artifact_path.read_bytes()
        except OSError as error:
            raise ModelDeliveryError("ARTIFACT_MISSING") from error
        if sha256(payload).hexdigest() != deployment.artifact_checksum:
            raise ModelDeliveryError("CHECKSUM_MISMATCH")

    def sync_once(self) -> list[str]:
        processed: list[str] = []
        for deployment in self._provider.pending():
            resolved: ResolvedModelRuntime | None = None
            try:
                self._verify_artifact(deployment)
                resolved = self._resolver.resolve(
                    deployment.requested_backend,
                    ModelArtifacts(onnx=deployment.artifact_path.suffix.lower() == ".onnx"),
                    self._capabilities,
                )
                candidate = self._factory.prepare(deployment, resolved)
                self.active_models.activate(candidate)
            except (ModelDeliveryError, RuntimeResolutionError) as error:
                self._provider.report(
                    deployment.deployment_id,
                    success=False,
                    error_category=str(error),
                )
            except Exception:
                self._provider.report(
                    deployment.deployment_id,
                    success=False,
                    error_category="MODEL_LOAD_FAILED",
                )
            else:
                self._provider.report(
                    deployment.deployment_id,
                    success=True,
                    resolved=resolved,
                )
            processed.append(deployment.deployment_id)
        return processed


def discover_runtime_capabilities() -> RuntimeCapabilities:
    """Probe ONNX Runtime lazily; CPU-only startup never imports NVIDIA modules."""
    try:
        import onnxruntime as ort  # type: ignore[import-untyped]
    except ImportError:
        return RuntimeCapabilities(False, False, False)
    providers = tuple(ort.get_available_providers())
    return RuntimeCapabilities(
        onnx_cpu_available="CPUExecutionProvider" in providers,
        onnx_cuda_available="CUDAExecutionProvider" in providers,
        tensorrt_available="TensorrtExecutionProvider" in providers,
        execution_providers=providers,
    )
