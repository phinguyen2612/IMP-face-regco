from control_api.camera_connection import GStreamerCameraConnectionTester


class Backend:
    def __init__(self, result: object | None = object(), error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.closed = False
        self.received_uri: str | None = None

    def open(self, uri: str, codec: str, transport: str) -> None:
        self.received_uri = uri
        if self.error is not None:
            raise self.error

    def read(self, camera_id: str, session_id: str, sequence: int) -> object | None:
        return self.result

    def close(self) -> None:
        self.closed = True


def test_connection_probe_reads_one_frame_and_closes_without_echoing_secret() -> None:
    backend = Backend()
    result = GStreamerCameraConnectionTester(backend).test("rtsp://alice:secret@camera.local/live")
    assert result.status == "CONNECTED"
    assert result.error_category is None
    assert backend.received_uri == "rtsp://alice:secret@camera.local/live"
    assert backend.closed is True
    assert "secret" not in result.model_dump_json()


def test_connection_probe_maps_errors_to_safe_category() -> None:
    backend = Backend(error=RuntimeError("rtsp://alice:secret@camera.local/live failed"))
    result = GStreamerCameraConnectionTester(backend).test("rtsp://alice:secret@camera.local/live")
    assert result.status == "DECODE_FAILED"
    assert result.error_category == "STREAM_PROBE_FAILED"
    assert "secret" not in result.model_dump_json()
    assert backend.closed is True


def test_connection_probe_reports_timeout_when_no_frame_arrives() -> None:
    result = GStreamerCameraConnectionTester(Backend(result=None)).test("rtsp://camera.local/live")
    assert result.status == "TIMEOUT"
    assert result.error_category == "NO_FRAME"
