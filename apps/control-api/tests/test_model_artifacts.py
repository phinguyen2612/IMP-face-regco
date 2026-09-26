from pathlib import Path

import pytest
from control_api.model_artifacts import (
    ArtifactValidationError,
    LocalModelArtifactStorage,
    ModelArtifactIngestor,
    OnnxArtifactInspector,
)
from control_api.model_domain import ModelType
from test_model_domain import person_manifest


class Inspector:
    def __init__(self, valid: bool = True) -> None:
        self.valid = valid

    def validate(self, payload: bytes, manifest: object) -> None:
        if not self.valid or not payload.startswith(b"controlled-onnx"):
            raise ArtifactValidationError("INVALID_MODEL_FORMAT")


def test_upload_is_checksum_addressed_and_immutable(tmp_path: Path) -> None:
    storage = LocalModelArtifactStorage(tmp_path)
    ingestor = ModelArtifactIngestor(storage, Inspector(), max_size_bytes=1024)
    artifact = ingestor.ingest(
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
        "../renamed.onnx",
        b"controlled-onnx-v1",
        person_manifest(),
    )
    assert artifact.checksum == "2d2e33652bfc898454b8b5a63124084e0448c514bafd2bb5213e097f552edd78"
    assert artifact.size_bytes == 18
    assert artifact.storage_key.endswith("/model.onnx")
    assert ".." not in artifact.storage_key
    assert storage.read(artifact.storage_key) == b"controlled-onnx-v1"
    with pytest.raises(FileExistsError):
        storage.store(
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
            b"different",
        )


def test_invalid_content_and_oversized_upload_leave_no_artifact(tmp_path: Path) -> None:
    storage = LocalModelArtifactStorage(tmp_path)
    ingestor = ModelArtifactIngestor(storage, Inspector(), max_size_bytes=8)
    with pytest.raises(ArtifactValidationError, match="ARTIFACT_TOO_LARGE"):
        ingestor.ingest("a" * 36, "b" * 36, "model.onnx", b"123456789", person_manifest())
    with pytest.raises(ArtifactValidationError, match="INVALID_MODEL_FORMAT"):
        ModelArtifactIngestor(storage, Inspector(valid=False), 1024).ingest(
            "a" * 36, "b" * 36, "model.onnx", b"invalid", person_manifest()
        )
    assert list(tmp_path.rglob("*.onnx")) == []


def test_manifest_type_must_match_model_definition_role(tmp_path: Path) -> None:
    ingestor = ModelArtifactIngestor(LocalModelArtifactStorage(tmp_path), Inspector(), 1024)
    with pytest.raises(ArtifactValidationError, match="MODEL_TYPE_MISMATCH"):
        ingestor.ingest(
            "a" * 36,
            "b" * 36,
            "model.onnx",
            b"controlled-onnx",
            person_manifest(),
            expected_type=ModelType.FACE_DETECTOR,
        )


def test_real_onnx_inspector_validates_graph_and_tensor_names() -> None:
    from onnx import TensorProto, helper

    graph = helper.make_graph(
        [helper.make_node("Identity", ["images"], ["output0"])],
        "controlled-test-model",
        [helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])],
        [helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 3, 640, 640])],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    contract_data = person_manifest().model_dump()
    contract_data["outputs"] = [{"name": "output0", "shape": [1, 3, 640, 640], "dtype": "float32"}]
    contract = type(person_manifest()).model_validate(contract_data)
    OnnxArtifactInspector().validate(model.SerializeToString(), contract)

    invalid_data = contract.model_dump()
    invalid_data["outputs"] = [{"name": "wrong", "shape": [1], "dtype": "float32"}]
    invalid_contract = type(person_manifest()).model_validate(invalid_data)
    with pytest.raises(ArtifactValidationError, match="INVALID_TENSOR_CONTRACT"):
        OnnxArtifactInspector().validate(model.SerializeToString(), invalid_contract)
