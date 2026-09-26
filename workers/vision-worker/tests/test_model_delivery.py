from hashlib import sha256
from pathlib import Path

from fr_domain.model_management import DeploymentBackend, ModelType
from vision_worker.model_delivery import (
    ModelDeploymentSynchronizer,
    PendingModelDeployment,
    UnavailableProductionAdapterFactory,
)
from vision_worker.model_runtime import RuntimeCapabilities


class Provider:
    def __init__(self, item: PendingModelDeployment) -> None:
        self.item = item
        self.results: list[dict[str, object]] = []

    def pending(self) -> list[PendingModelDeployment]:
        return [self.item]

    def report(self, deployment_id: str, **result: object) -> None:
        self.results.append({"deployment_id": deployment_id, **result})


class Runtime:
    def __init__(self, deployment_id: str, warmup_ok: bool = True) -> None:
        self.deployment_id = deployment_id
        self.model_type = ModelType.PERSON_DETECTOR
        self.warmup_ok = warmup_ok
        self.closed = False

    def warmup(self) -> None:
        if not self.warmup_ok:
            raise RuntimeError("MODEL_WARMUP_FAILED")

    def health_check(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class Factory:
    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    def prepare(self, deployment: PendingModelDeployment, resolved: object) -> Runtime:
        del deployment, resolved
        return self.runtime


def pending(path: Path, checksum: str | None = None) -> PendingModelDeployment:
    return PendingModelDeployment(
        "deployment-1",
        ModelType.PERSON_DETECTOR,
        DeploymentBackend.AUTO,
        path,
        checksum or sha256(path.read_bytes()).hexdigest(),
        "v1",
        "FP32",
    )


def test_valid_artifact_is_resolved_warmed_and_activated(tmp_path: Path) -> None:
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"controlled")
    provider = Provider(pending(artifact))
    runtime = Runtime("deployment-1")
    synchronizer = ModelDeploymentSynchronizer(
        provider, RuntimeCapabilities.cpu_only(), Factory(runtime)
    )
    assert synchronizer.sync_once() == ["deployment-1"]
    assert synchronizer.active_models.active(ModelType.PERSON_DETECTOR) is runtime
    assert provider.results[0]["success"] is True


def test_checksum_mismatch_never_reaches_factory(tmp_path: Path) -> None:
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"tampered")
    provider = Provider(pending(artifact, "0" * 64))
    synchronizer = ModelDeploymentSynchronizer(
        provider, RuntimeCapabilities.cpu_only(), UnavailableProductionAdapterFactory()
    )
    synchronizer.sync_once()
    assert provider.results[0]["success"] is False
    assert provider.results[0]["error_category"] == "CHECKSUM_MISMATCH"


def test_production_boundary_does_not_fall_back_to_mock(tmp_path: Path) -> None:
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"controlled")
    provider = Provider(pending(artifact))
    synchronizer = ModelDeploymentSynchronizer(
        provider, RuntimeCapabilities.cpu_only(), UnavailableProductionAdapterFactory()
    )
    synchronizer.sync_once()
    assert synchronizer.active_models.active(ModelType.PERSON_DETECTOR) is None
    assert provider.results[0]["error_category"] == "REAL_MODEL_ADAPTER_NOT_IMPLEMENTED"


def test_failed_replacement_keeps_previous_runtime(tmp_path: Path) -> None:
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"controlled")
    first_provider = Provider(pending(artifact))
    first = Runtime("deployment-old")
    synchronizer = ModelDeploymentSynchronizer(
        first_provider, RuntimeCapabilities.cpu_only(), Factory(first)
    )
    synchronizer.sync_once()
    replacement_provider = Provider(pending(artifact))
    synchronizer._provider = replacement_provider
    synchronizer._factory = Factory(Runtime("deployment-1", warmup_ok=False))
    synchronizer.sync_once()
    assert synchronizer.active_models.active(ModelType.PERSON_DETECTOR) is first
    assert replacement_provider.results[0]["success"] is False
