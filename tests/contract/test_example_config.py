import json
from pathlib import Path

from fr_config.models import CameraConfig, FaceRecognitionConfig


def test_checked_in_example_matches_the_versioned_config_contract() -> None:
    path = Path("configuration/examples/face-recognition.example.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    config = FaceRecognitionConfig.model_validate(payload)

    assert config.feature_type == "face_recognition"
    assert config.enabled is False


def test_checked_in_camera_example_matches_the_camera_contract() -> None:
    path = Path("configuration/examples/camera.example.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    camera = CameraConfig.model_validate(payload)

    assert camera.stream.uri.scheme == "rtsp"
    assert camera.rois[0].purpose == "recognition"
