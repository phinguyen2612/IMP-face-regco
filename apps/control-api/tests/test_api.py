from control_api.main import create_app
from control_api.runtime_status import InMemoryRuntimeStatusStore
from fastapi.testclient import TestClient
from fr_contracts.runtime_status import CameraConnectionState, RuntimeStatus


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


def test_health_does_not_require_external_services() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "face-recognition-control-api",
        "status": "ok",
        "external_dependencies": "optional",
        "camera_persistence": "in_memory",
    }


def test_model_catalog_starts_empty_instead_of_advertising_fake_models() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/models")

    assert response.status_code == 200
    assert response.json() == {"items": []}
    readiness = client.get("/api/v1/recognition/readiness").json()
    assert readiness["status"] == "NOT_READY"
    assert "PERSON_DETECTOR_NOT_ASSIGNED" in readiness["reasons"]


def test_validate_config_returns_effective_defaults() -> None:
    client = TestClient(create_app())

    response = client.post("/api/v1/face-recognition/configs/validate", json=valid_config_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["config"]["verification"]["min_good_frames"] == 3


def test_websocket_sends_versioned_ready_status() -> None:
    client = TestClient(create_app())

    with client.websocket_connect("/api/v1/ws") as websocket:
        message = websocket.receive_json()

    assert message["schema_version"] == 1
    assert message["type"] == "system.ready"


def test_validate_config_returns_422_for_mixed_timezone_schedule() -> None:
    client = TestClient(create_app())
    payload = valid_config_payload()
    payload["schedule"] = {
        "timezone": "Asia/Ho_Chi_Minh",
        "weekly": {"monday": [{"start": "09:00:00+07:00", "end": "17:00:00"}]},
    }

    response = client.post("/api/v1/face-recognition/configs/validate", json=payload)

    assert response.status_code == 422


def test_validate_camera_config_with_normalized_roi() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/cameras/validate",
        json={
            "id": "camera-01",
            "name": "Entrance",
            "stream": {"uri": "rtsp://camera.invalid/stream"},
            "rois": [
                {
                    "id": "entrance",
                    "name": "Entrance",
                    "purpose": "recognition",
                    "polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9]],
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["rois"][0]["purpose"] == "recognition"


def test_runtime_status_api_and_websocket_expose_worker_observability() -> None:
    client = TestClient(create_app(runtime_status_store=InMemoryRuntimeStatusStore()))
    status = RuntimeStatus(
        worker_id="worker-01",
        camera_id="camera-01",
        camera_state=CameraConnectionState.CONNECTED,
        input_fps=25.0,
        processed_fps=10.0,
        dropped_frames=15,
        active_tracks=2,
        ring_buffer_frames=50,
        ring_buffer_capacity=100,
        worker_health="healthy",
        active_config_revision="revision-7",
    )

    update_response = client.put(
        "/api/v1/runtime/status",
        json=status.model_dump(mode="json"),
    )

    response = client.get("/api/v1/runtime/status")

    assert update_response.status_code == 200
    assert update_response.json()["worker_id"] == "worker-01"
    assert response.status_code == 200
    assert response.json()["items"][0]["active_tracks"] == 2
    assert response.json()["items"][0]["active_config_revision"] == "revision-7"

    with client.websocket_connect("/api/v1/ws") as websocket:
        websocket.receive_json()
        status_message = websocket.receive_json()

        updated = status.model_copy(update={"active_tracks": 3})
        client.put("/api/v1/runtime/status", json=updated.model_dump(mode="json"))
        updated_message = websocket.receive_json()

    assert status_message["type"] == "runtime.status"
    assert status_message["payload"]["worker_id"] == "worker-01"
    assert updated_message["payload"]["active_tracks"] == 3
