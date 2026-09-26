from dataclasses import FrozenInstanceError

import pytest
from control_api.model_domain import (
    ArtifactFormat,
    DeploymentBackend,
    EmbeddingCompatibility,
    ModelDefinition,
    ModelDeployment,
    ModelManifest,
    ModelType,
    ModelVersion,
    TensorSpec,
    ValidationStatus,
)
from pydantic import ValidationError


def person_manifest() -> ModelManifest:
    return ModelManifest(
        model_type=ModelType.PERSON_DETECTOR,
        inputs=[TensorSpec(name="images", shape=[1, 3, 640, 640], dtype="float32")],
        outputs=[TensorSpec(name="output0", shape=[1, 84, "detections"], dtype="float32")],
        preprocessing={
            "layout": "NCHW",
            "color_order": "RGB",
            "normalization": "zero_to_one",
            "resize_mode": "letterbox",
        },
        metadata={
            "architecture": "YOLO",
            "output_semantics": "yolo_detection",
            "person_class_id": 0,
        },
    )


def test_definition_version_and_deployment_are_distinct_immutable_concepts() -> None:
    definition = ModelDefinition.create("YOLO Person", ModelType.PERSON_DETECTOR, "ONNX")
    version = ModelVersion.create(
        definition.id,
        "v1",
        "artifact-1",
        ArtifactFormat.ONNX,
        "a" * 64,
        123,
        person_manifest(),
        ValidationStatus.VALID,
    )
    deployment = ModelDeployment.create(version.id, DeploymentBackend.AUTO, "FP32")

    assert definition.id != version.id != deployment.id
    with pytest.raises(FrozenInstanceError):
        version.checksum = "b" * 64  # type: ignore[misc]


def test_role_specific_manifest_rejects_missing_yolo_contract() -> None:
    manifest = person_manifest().model_dump()
    manifest["metadata"].pop("person_class_id")
    with pytest.raises(ValidationError, match="person_class_id"):
        ModelManifest.model_validate(manifest)


def test_embedder_manifest_exposes_complete_compatibility_key() -> None:
    manifest = ModelManifest(
        model_type=ModelType.FACE_EMBEDDER,
        inputs=[TensorSpec(name="input", shape=[1, 3, 112, 112], dtype="float32")],
        outputs=[TensorSpec(name="embedding", shape=[1, 512], dtype="float32")],
        preprocessing={
            "layout": "NCHW",
            "color_order": "RGB",
            "normalization": "adaface_v1",
            "resize_mode": "aligned",
        },
        metadata={
            "architecture": "AdaFace",
            "embedding_dimension": 512,
            "l2_normalized": True,
            "distance_metric": "cosine",
            "alignment_profile": "arcface_5point_112",
        },
    )
    compatibility = EmbeddingCompatibility.from_manifest(
        "definition-1", "version-1", "c" * 64, manifest
    )
    assert compatibility.dimension == 512
    assert compatibility.model_version_id == "version-1"
    assert compatibility.normalization_profile == "adaface_v1"
    assert compatibility.alignment_profile == "arcface_5point_112"
    assert compatibility.metric == "cosine"
