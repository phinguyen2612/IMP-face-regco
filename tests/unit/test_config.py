import pytest
from fr_config.models import ROI, FaceRecognitionConfig
from pydantic import ValidationError


def valid_config_payload() -> dict:
    return {
        "name": "Entrance recognition",
        "camera_id": "cam-01",
        "models": {
            "person_detector": {
                "model_definition_id": "yolo-person",
                "model_version": "1.0",
                "deployment_id": "jetson-default",
            },
            "face_detector": {
                "model_definition_id": "scrfd-face",
                "model_version": "1.0",
                "deployment_id": "jetson-default",
            },
            "face_embedder": {
                "model_definition_id": "adaface",
                "model_version": "1.0",
                "deployment_id": "jetson-default",
            },
        },
        "recognition": {"identity_collection_id": "employees"},
    }


def test_config_rejects_minimum_frames_above_maximum() -> None:
    payload = valid_config_payload()
    payload["verification"] = {"min_good_frames": 5, "max_frames": 3}

    with pytest.raises(ValidationError, match="min_good_frames"):
        FaceRecognitionConfig.model_validate(payload)


def test_config_rejects_inverted_brightness_range() -> None:
    payload = valid_config_payload()
    payload["quality"] = {"brightness_min": 220, "brightness_max": 40}

    with pytest.raises(ValidationError, match="brightness_min"):
        FaceRecognitionConfig.model_validate(payload)


def test_config_supplies_safe_track_based_defaults() -> None:
    config = FaceRecognitionConfig.model_validate(valid_config_payload())

    assert config.schema_version == 1
    assert config.verification.min_good_frames == 3
    assert config.verification.max_frames == 8
    assert config.timing.recognition_interval_ms == 500
    assert config.evidence.video_clip is False


def test_roi_rejects_coordinates_outside_normalized_range() -> None:
    with pytest.raises(ValidationError, match="between 0 and 1"):
        ROI.model_validate(
            {
                "id": "roi-01",
                "name": "Entrance",
                "polygon": [[0.1, 0.1], [1.2, 0.2], [0.8, 0.9]],
            }
        )


@pytest.mark.parametrize(
    "schedule",
    [
        {
            "timezone": "Asia/Ho_Chi_Minh",
            "weekly": {"monday": [{"start": "09:00:00+07:00", "end": "17:00:00"}]},
        },
        {"timezone": "not/a/timezone", "weekly": {}},
        {
            "timezone": "Asia/Ho_Chi_Minh",
            "weekly": {"flursday": [{"start": "09:00", "end": "17:00"}]},
        },
    ],
)
def test_config_rejects_invalid_schedule(schedule: dict) -> None:
    payload = valid_config_payload()
    payload["schedule"] = schedule

    with pytest.raises(ValidationError):
        FaceRecognitionConfig.model_validate(payload)
