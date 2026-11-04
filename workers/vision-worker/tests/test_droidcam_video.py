from io import BytesIO

import httpx
import pytest
from PIL import Image
from vision_worker.camera_config import ActiveCamera
from vision_worker.video.droidcam import DroidCamBackend
from vision_worker.video.sources import create_camera_source


def jpeg(color):
    data = BytesIO()
    Image.new("RGB", (32, 16), color).save(data, "JPEG")
    return data.getvalue()


class Chunks(httpx.SyncByteStream):
    def __init__(self, data):
        self.data = data

    def __iter__(self):
        for offset in range(0, len(self.data), 4096):
            yield self.data[offset:offset + 4096]


def test_mjpeg_decodes_rgb_and_keeps_latest_frame():
    # Split JPEG's start marker across the reader's 4096-byte chunk boundary.
    data = b"-" * 4095 + jpeg("red")
    data += b"\r\n--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg("blue")
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=Chunks(data)))
    ) as client:
        backend = DroidCamBackend(16, 16, client)
        backend.open("http://phone:4747/video", "AUTO", "http")
        backend._thread.join(timeout=2)
        frame = backend.read("cam", "session", 1)
        assert (frame.width, frame.height, frame.pixel_format) == (16, 8, "RGB")
        assert frame.payload[2] > 240 and frame.payload[0] < 10
        assert backend._latest.qsize() == 0
        with pytest.raises(RuntimeError, match="DROIDCAM_STREAM_ENDED"):
            backend.read("cam", "session", 2)
        backend.close()
        assert backend.read("cam", "session", 3) is None


@pytest.mark.parametrize(
    "status,category", [(401, "DROIDCAM_AUTHENTICATION_FAILED"), (404, "DROIDCAM_UNREACHABLE")]
)
def test_http_errors_are_categorical_without_credentials(status, category):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status))) as client:
        backend = DroidCamBackend(16, 16, client)
        backend.open("http://alice:secret@phone:4747/video", "AUTO", "http")
        backend._thread.join(timeout=2)
        with pytest.raises(RuntimeError, match=f"^{category}$"):
            backend.read("cam", "session", 1)
        backend.close()


def test_droidcam_source_routes_through_worker_preview_without_gstreamer():
    source = create_camera_source(
        ActiveCamera("cam", "Phone", "http://phone:4747/video", "AUTO", True, 5, "rev", "droidcam"),
        "http://127.0.0.1:8000",
        "worker",
        1280,
        720,
    )
    assert isinstance(source._backend, DroidCamBackend)
    source.close()
