from typing import Protocol

from vision_worker.video.gstreamer_inprocess import GStreamerRtspBackend, load_gstreamer

from control_api.cameras import CameraConnectionResult


class ProbeBackend(Protocol):
    def open(self, uri: str, codec: str, transport: str) -> None: ...
    def read(self, camera_id: str, session_id: str, sequence: int) -> object | None: ...
    def close(self) -> None: ...


class GStreamerCameraConnectionTester:
    """Performs a one-frame probe and returns only safe error categories."""

    def __init__(self, backend: ProbeBackend | None = None) -> None:
        self._backend = backend

    def _get_backend(self) -> ProbeBackend:
        if self._backend is None:
            return GStreamerRtspBackend(load_gstreamer(), width=64, height=64)
        return self._backend

    def test(self, rtsp_url: str) -> CameraConnectionResult:
        backend: ProbeBackend | None = None
        try:
            backend = self._get_backend()
            backend.open(rtsp_url, "AUTO", "tcp")
            frame = backend.read("connection-test", "probe", 1)
            if frame is None:
                return CameraConnectionResult(status="TIMEOUT", error_category="NO_FRAME")
            return CameraConnectionResult(status="CONNECTED")
        except OSError:
            return CameraConnectionResult(status="UNREACHABLE", error_category="NETWORK_ERROR")
        except RuntimeError as error:
            category = str(error)
            if category == "GSTREAMER_BINDINGS_UNAVAILABLE":
                return CameraConnectionResult(
                    status="BACKEND_UNAVAILABLE",
                    error_category="GSTREAMER_UNAVAILABLE",
                )
            return CameraConnectionResult(
                status="DECODE_FAILED",
                error_category="STREAM_PROBE_FAILED",
            )
        finally:
            if backend is not None:
                backend.close()
