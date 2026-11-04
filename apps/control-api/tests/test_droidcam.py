import pytest
from auth_test_support import TestClient, create_app
from control_api.cameras import CameraService, FernetCameraSecretProtector, InMemoryCameraRepository


def test_droidcam_create_update_activate_and_secret_delivery():
    service = CameraService(InMemoryCameraRepository(), FernetCameraSecretProtector.generate())
    client = TestClient(create_app(camera_service=service, internal_camera_token="worker"))
    uri = "http://alice:secret@192.168.1.20:4747/video?token=private"
    created = client.post(
        "/api/v1/cameras",
        json={
            "name": "Phone",
            "source_type": "droidcam",
            "rtsp_url": uri,
        },
    )
    assert created.status_code == 201
    camera = created.json()
    assert camera["lifecycle"] == "DRAFT"
    assert camera["rtsp_url"] == "http://***:***@192.168.1.20:4747/video"
    assert b"secret" not in service.require(camera["id"]).protected_rtsp_url
    camera_id = camera["id"]
    assert client.patch(f"/api/v1/cameras/{camera_id}", json={"name": "Phone 2"}).status_code == 200
    assert client.post(f"/api/v1/cameras/{camera_id}/activate").status_code == 200
    assert client.get("/api/v1/internal/cameras/active").status_code == 403
    delivered = client.get("/api/v1/internal/cameras/active", headers={"X-Worker-Token": "worker"})
    assert delivered.json()["items"][0]["rtsp_url"] == uri
    assert delivered.json()["items"][0]["source_type"] == "droidcam"
    # Preview uses the same backend-owned revision and worker authorization.
    from io import BytesIO

    from PIL import Image

    image = BytesIO()
    Image.new("RGB", (8, 8)).save(image, "JPEG")
    revision = service.require(camera_id).revision
    preview = client.post(
        f"/api/v1/internal/cameras/{camera_id}/preview?revision={revision}",
        content=image.getvalue(),
        headers={
            "X-Worker-Token": "worker",
            "Content-Type": "image/jpeg",
            "X-Preview-Session": "session",
        },
    )
    assert preview.status_code == 204
    assert (
        client.patch(
            f"/api/v1/cameras/{camera_id}", json={"rtsp_url": "rtsp://host/live"}
        ).status_code
        == 422
    )
    changed = client.patch(f"/api/v1/cameras/{camera_id}", json={"source_type": "webcam"})
    assert changed.status_code == 200 and changed.json()["rtsp_url"] is None


@pytest.mark.parametrize(
    "uri", [None, "192.168.1.20", "file:///video", "http://host/", "rtsp://host/video"]
)
def test_droidcam_rejects_invalid_urls(uri):
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/cameras",
        json={
            "name": "Phone",
            "source_type": "droidcam",
            "rtsp_url": uri,
        },
    )
    assert response.status_code == 422
