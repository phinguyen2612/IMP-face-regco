import pytest
from fr_config.models import ROI, CameraConfig, FaceRecognitionConfig
from fr_config.runtime import RuntimeSettings
from pydantic import ValidationError


def complete_feature_payload() -> dict:
    return {
        "schema_version": 1,
        "feature_type": "face_recognition",
        "name": "Entrance recognition",
        "camera_id": "camera-01",
        "enabled": True,
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
        "roi": {
            "recognition_area_ids": ["entrance"],
            "track_anchor": "bottom_center",
            "face_anchor": "center",
        },
        "quality": {
            "min_face_size_px": 80,
            "min_detection_confidence": 0.8,
            "max_abs_yaw_deg": 30,
            "max_abs_pitch_deg": 25,
            "max_abs_roll_deg": 25,
            "blur_threshold": 100,
            "brightness_min": 40,
            "brightness_max": 220,
            "max_occlusion": 0.3,
            "require_landmarks": True,
        },
        "recognition": {
            "identity_collection_id": "employees",
            "top_k": 5,
            "similarity_threshold": 0.72,
        },
        "verification": {
            "strategy": "quality_weighted_vote",
            "min_good_frames": 3,
            "max_frames": 8,
            "timeout_ms": 2000,
            "similarity_threshold": 0.72,
            "identity_consistency": 0.75,
            "min_candidate_margin": 0.05,
        },
        "timing": {
            "recognition_interval_ms": 500,
            "recognition_retry_ms": 5000,
            "verified_identity_ttl_ms": 10000,
            "track_cache_ttl_ms": 10000,
            "unknown_dwell_ms": 3000,
            "event_cooldown_ms": 30000,
            "duplicate_suppression_ms": 5000,
        },
        "schedule": {
            "timezone": "Asia/Ho_Chi_Minh",
            "weekly": {"monday": [{"start": "08:00", "end": "18:00"}]},
        },
        "policies": [
            {
                "id": "unknown-person",
                "priority": 100,
                "conditions": {
                    "verification_statuses": ["UNKNOWN"],
                    "roi_ids": ["entrance"],
                    "minimum_dwell_ms": 3000,
                },
                "action": {"event_type": "UNKNOWN_PERSON", "severity": "high"},
            }
        ],
        "evidence": {
            "snapshot": True,
            "video_clip": True,
            "pre_event_seconds": 5,
            "post_event_seconds": 5,
        },
    }


def test_complete_ui_configuration_loads_all_required_sections() -> None:
    config = FaceRecognitionConfig.model_validate(complete_feature_payload())

    assert config.camera_id == "camera-01"
    assert config.models.person_detector.model_definition_id == "yolo-person"
    assert config.models.face_detector.model_definition_id == "scrfd-face"
    assert config.models.face_embedder.model_definition_id == "adaface"
    assert config.roi.recognition_area_ids == ["entrance"]
    assert config.quality.min_face_size_px == 80
    assert config.recognition.similarity_threshold == 0.72
    assert config.recognition.top_k == 5
    assert config.verification.min_good_frames == 3
    assert config.timing.recognition_interval_ms == 500
    assert config.timing.recognition_retry_ms == 5000
    assert config.timing.track_cache_ttl_ms == 10000
    assert config.schedule.timezone == "Asia/Ho_Chi_Minh"
    assert config.policies[0].action.event_type == "UNKNOWN_PERSON"
    assert config.timing.event_cooldown_ms == 30000
    assert config.evidence.video_clip is True


def test_feature_config_rejects_backend_only_runtime_fields() -> None:
    payload = complete_feature_payload()
    payload["postgres_dsn"] = "postgresql://internal"

    with pytest.raises(ValidationError, match="postgres_dsn"):
        FaceRecognitionConfig.model_validate(payload)


def test_camera_config_supports_rtsp_without_runtime_pipeline_details() -> None:
    camera = CameraConfig.model_validate(
        {
            "id": "camera-01",
            "name": "Entrance",
            "enabled": True,
            "stream": {
                "uri": "rtsp://camera.invalid/stream",
                "codec": "H264",
                "transport": "tcp",
            },
            "rois": [
                {
                    "id": "entrance",
                    "name": "Entrance recognition zone",
                    "purpose": "recognition",
                    "polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9]],
                }
            ],
        }
    )

    assert camera.stream.codec == "H264"
    assert camera.rois[0].purpose == "recognition"
    assert "gstreamer_pipeline" not in camera.model_dump()


def test_runtime_settings_are_backend_only_and_validate_service_urls() -> None:
    settings = RuntimeSettings.model_validate(
        {
            "worker_id": "worker-01",
            "postgres_dsn": "postgresql://dev:dev@127.0.0.1:55432/face_recognition_dev",
            "redis_url": "redis://127.0.0.1:56379/0",
            "evidence_root": "data/evidence",
            "gstreamer_decoder": "nvv4l2decoder",
        }
    )

    assert settings.worker_id == "worker-01"
    assert str(settings.postgres_dsn).startswith("postgresql://")
    assert str(settings.redis_url).startswith("redis://")


def test_roi_requires_normalized_non_degenerate_polygon() -> None:
    with pytest.raises(ValidationError):
        ROI.model_validate(
            {
                "id": "line",
                "name": "Invalid line",
                "polygon": [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]],
            }
        )
