from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelType(StrEnum):
    PERSON_DETECTOR = "PERSON_DETECTOR"
    FACE_DETECTOR = "FACE_DETECTOR"
    FACE_EMBEDDER = "FACE_EMBEDDER"


class ArtifactFormat(StrEnum):
    ONNX = "ONNX"
    TENSORRT_ENGINE = "TENSORRT_ENGINE"


class ValidationStatus(StrEnum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    VALID = "VALID"
    INVALID = "INVALID"


class DeploymentBackend(StrEnum):
    AUTO = "AUTO"
    ONNX_CPU = "ONNX_CPU"
    ONNX_CUDA = "ONNX_CUDA"
    TENSORRT = "TENSORRT"


class DeploymentStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVATION_PENDING = "ACTIVATION_PENDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"


class ModelRuntimeState(StrEnum):
    NOT_LOADED = "NOT_LOADED"
    LOADING = "LOADING"
    WARMING_UP = "WARMING_UP"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
    RELOADING = "RELOADING"


class TensorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(min_length=1)
    shape: list[int | str] = Field(min_length=1)
    dtype: Literal["float32", "float16", "uint8", "int64"]


class PreprocessingContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    layout: Literal["NCHW", "NHWC"]
    color_order: Literal["RGB", "BGR"]
    normalization: str = Field(min_length=1)
    resize_mode: Literal["letterbox", "stretch", "aligned"]


class ModelManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    model_type: ModelType
    inputs: list[TensorSpec] = Field(min_length=1)
    outputs: list[TensorSpec] = Field(min_length=1)
    preprocessing: PreprocessingContract
    metadata: dict[str, Any]
    runtime_compatibility: list[DeploymentBackend] = Field(
        default_factory=lambda: [DeploymentBackend.ONNX_CPU]
    )

    @model_validator(mode="after")
    def validate_role_contract(self) -> "ModelManifest":
        required: dict[ModelType, set[str]] = {
            ModelType.PERSON_DETECTOR: {
                "architecture",
                "output_semantics",
                "person_class_id",
            },
            ModelType.FACE_DETECTOR: {
                "architecture",
                "output_semantics",
                "landmark_points",
            },
            ModelType.FACE_EMBEDDER: {
                "architecture",
                "embedding_dimension",
                "l2_normalized",
                "distance_metric",
                "alignment_profile",
            },
        }
        missing = required[self.model_type] - self.metadata.keys()
        if missing:
            raise ValueError(f"missing model metadata: {', '.join(sorted(missing))}")
        if self.model_type is ModelType.FACE_DETECTOR and self.metadata["landmark_points"] != 5:
            raise ValueError("FACE_DETECTOR requires a 5-point landmark contract")
        if self.model_type is ModelType.FACE_EMBEDDER:
            dimension = self.metadata["embedding_dimension"]
            if not isinstance(dimension, int) or dimension <= 0:
                raise ValueError("embedding_dimension must be a positive integer")
            if self.metadata["distance_metric"] not in {"cosine", "inner_product"}:
                raise ValueError("unsupported embedding distance_metric")
        return self


@dataclass(frozen=True, slots=True)
class ModelDefinition:
    id: str
    name: str
    model_type: ModelType
    framework: str
    description: str
    created_at: str
    updated_at: str

    @classmethod
    def create(
        cls,
        name: str,
        model_type: ModelType,
        framework: str,
        description: str = "",
    ) -> "ModelDefinition":
        now = datetime.now(UTC).isoformat()
        return cls(str(uuid4()), name, model_type, framework, description, now, now)


@dataclass(frozen=True, slots=True)
class ModelVersion:
    id: str
    model_definition_id: str
    version: str
    artifact_id: str
    format: ArtifactFormat
    checksum: str
    size_bytes: int
    manifest: ModelManifest
    validation_status: ValidationStatus
    validation_error: str | None
    created_at: str

    @classmethod
    def create(
        cls,
        definition_id: str,
        version: str,
        artifact_id: str,
        artifact_format: ArtifactFormat,
        checksum: str,
        size_bytes: int,
        manifest: ModelManifest,
        validation_status: ValidationStatus = ValidationStatus.UPLOADED,
        validation_error: str | None = None,
    ) -> "ModelVersion":
        return cls(
            str(uuid4()),
            definition_id,
            version,
            artifact_id,
            artifact_format,
            checksum,
            size_bytes,
            manifest,
            validation_status,
            validation_error,
            datetime.now(UTC).isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ModelDeployment:
    id: str
    model_version_id: str
    backend: DeploymentBackend
    precision: str
    status: DeploymentStatus
    revision: str
    resolved_backend: DeploymentBackend | None
    error_category: str | None
    created_at: str
    updated_at: str

    @classmethod
    def create(
        cls,
        model_version_id: str,
        backend: DeploymentBackend,
        precision: str = "FP32",
    ) -> "ModelDeployment":
        now = datetime.now(UTC).isoformat()
        return cls(
            str(uuid4()),
            model_version_id,
            backend,
            precision,
            DeploymentStatus.DRAFT,
            str(uuid4()),
            None,
            None,
            now,
            now,
        )


@dataclass(frozen=True, slots=True)
class EmbeddingCompatibility:
    model_definition_id: str
    model_version_id: str
    artifact_checksum: str
    dimension: int
    preprocessing_profile: str
    alignment_profile: str
    normalization_profile: str
    normalized: bool
    metric: str

    @classmethod
    def from_manifest(
        cls,
        definition_id: str,
        version_id: str,
        checksum: str,
        manifest: ModelManifest,
    ) -> "EmbeddingCompatibility":
        if manifest.model_type is not ModelType.FACE_EMBEDDER:
            raise ValueError("embedding compatibility requires FACE_EMBEDDER manifest")
        return cls(
            definition_id,
            version_id,
            checksum,
            int(manifest.metadata["embedding_dimension"]),
            manifest.preprocessing.normalization,
            str(manifest.metadata["alignment_profile"]),
            manifest.preprocessing.normalization,
            bool(manifest.metadata["l2_normalized"]),
            str(manifest.metadata["distance_metric"]),
        )
