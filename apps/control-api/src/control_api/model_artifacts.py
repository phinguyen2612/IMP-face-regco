import re
from dataclasses import dataclass
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from fr_domain.model_management import ModelManifest, ModelType


class ArtifactValidationError(ValueError):
    pass


class ArtifactInspector(Protocol):
    def validate(self, payload: bytes, manifest: ModelManifest) -> None: ...


class OnnxArtifactInspector:
    def validate(self, payload: bytes, manifest: ModelManifest) -> None:
        try:
            onnx: Any = import_module("onnx")
        except ModuleNotFoundError as error:
            raise ArtifactValidationError("MODEL_INSPECTOR_UNAVAILABLE") from error
        try:
            model = onnx.load_model_from_string(payload)
            onnx.checker.check_model(model)
        except Exception as error:
            raise ArtifactValidationError("INVALID_MODEL_FORMAT") from error
        dtype_names = {1: "float32", 2: "uint8", 7: "int64", 10: "float16"}

        def graph_contract(items: Any) -> dict[str, tuple[list[int | str], str | None]]:
            result: dict[str, tuple[list[int | str], str | None]] = {}
            for item in items:
                tensor_type = item.type.tensor_type
                shape: list[int | str] = []
                for dimension in tensor_type.shape.dim:
                    if dimension.HasField("dim_value"):
                        shape.append(int(dimension.dim_value))
                    elif dimension.dim_param:
                        shape.append(str(dimension.dim_param))
                    else:
                        shape.append("dynamic")
                result[item.name] = (shape, dtype_names.get(tensor_type.elem_type))
            return result

        expected_inputs = {item.name: (item.shape, item.dtype) for item in manifest.inputs}
        expected_outputs = {item.name: (item.shape, item.dtype) for item in manifest.outputs}
        if graph_contract(model.graph.input) != expected_inputs:
            raise ArtifactValidationError("INVALID_TENSOR_CONTRACT")
        if graph_contract(model.graph.output) != expected_outputs:
            raise ArtifactValidationError("INVALID_TENSOR_CONTRACT")


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    id: str
    checksum: str
    size_bytes: int
    format: str
    storage_key: str


class LocalModelArtifactStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_identity(value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9-]{1,80}", value):
            raise ArtifactValidationError("INVALID_ARTIFACT_IDENTITY")
        return value

    def store(self, definition_id: str, version_id: str, payload: bytes) -> str:
        definition = self._safe_identity(definition_id)
        version = self._safe_identity(version_id)
        destination = (self._root / definition / version / "model.onnx").resolve()
        if not destination.is_relative_to(self._root):
            raise ArtifactValidationError("INVALID_STORAGE_PATH")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError("model version artifact is immutable")
        temporary = destination.with_name(f".{uuid4()}.upload")
        try:
            temporary.write_bytes(payload)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination.as_posix()

    def read(self, storage_key: str) -> bytes:
        candidate = (self._root / storage_key).resolve()
        if not candidate.is_relative_to(self._root):
            raise ArtifactValidationError("INVALID_STORAGE_PATH")
        return candidate.read_bytes()

    def delete(self, storage_key: str) -> None:
        candidate = (self._root / storage_key).resolve()
        if not candidate.is_relative_to(self._root):
            raise ArtifactValidationError("INVALID_STORAGE_PATH")
        candidate.unlink(missing_ok=True)


class ModelArtifactIngestor:
    def __init__(
        self,
        storage: LocalModelArtifactStorage,
        inspector: ArtifactInspector,
        max_size_bytes: int,
    ) -> None:
        if max_size_bytes <= 0:
            raise ValueError("max_size_bytes must be positive")
        self._storage = storage
        self._inspector = inspector
        self._max_size_bytes = max_size_bytes

    @property
    def max_size_bytes(self) -> int:
        return self._max_size_bytes

    def ingest(
        self,
        definition_id: str,
        version_id: str,
        original_filename: str,
        payload: bytes,
        manifest: ModelManifest,
        expected_type: ModelType | None = None,
    ) -> ModelArtifact:
        if not original_filename.lower().endswith(".onnx"):
            raise ArtifactValidationError("INVALID_MODEL_FORMAT")
        if not payload:
            raise ArtifactValidationError("EMPTY_ARTIFACT")
        if len(payload) > self._max_size_bytes:
            raise ArtifactValidationError("ARTIFACT_TOO_LARGE")
        if expected_type is not None and manifest.model_type is not expected_type:
            raise ArtifactValidationError("MODEL_TYPE_MISMATCH")
        self._inspector.validate(payload, manifest)
        checksum = sha256(payload).hexdigest()
        storage_key = self._storage.store(definition_id, version_id, payload)
        return ModelArtifact(str(uuid4()), checksum, len(payload), "ONNX", storage_key)
