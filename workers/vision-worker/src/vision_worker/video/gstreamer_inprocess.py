from importlib import import_module
from time import monotonic_ns
from typing import Any

from vision_worker.video.frame import VideoFrame


class GStreamerRtspBackend:
    uses_subprocess = False

    def __init__(self, gst: Any, width: int, height: int, latency_ms: int = 200) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("GStreamer output dimensions must be positive")
        self._gst = gst
        self._width = width
        self._height = height
        self._latency_ms = latency_ms
        self._pipeline: Any = None
        self._sink: Any = None

    def open(self, uri: str, codec: str, transport: str) -> None:
        self.close()
        if codec not in {"AUTO", "H264", "H265"}:
            raise ValueError("unsupported codec")
        if transport not in {"tcp", "udp"}:
            raise ValueError("unsupported RTSP transport")
        description = (
            f"rtspsrc name=source latency={self._latency_ms} protocols={transport} "
            "! decodebin ! videoconvert ! videoscale "
            f"! video/x-raw,format=RGB,width={self._width},height={self._height} "
            "! appsink name=sink sync=false max-buffers=1 drop=true"
        )
        pipeline = self._gst.parse_launch(description)
        source = pipeline.get_by_name("source")
        sink = pipeline.get_by_name("sink")
        if source is None or sink is None:
            raise RuntimeError("GSTREAMER_PIPELINE_INVALID")
        source.set_property("location", uri)
        pipeline.set_state(self._gst.State.PLAYING)
        self._pipeline = pipeline
        self._sink = sink

    def read(self, camera_id: str, session_id: str, sequence: int) -> VideoFrame | None:
        if self._sink is None:
            raise RuntimeError("GSTREAMER_NOT_OPEN")
        sample = self._sink.emit("try-pull-sample", 1_000_000_000)
        if sample is None:
            return None
        buffer = sample.get_buffer()
        payload = bytes(buffer.extract_dup(0, buffer.get_size()))
        expected = self._width * self._height * 3
        if len(payload) != expected:
            raise RuntimeError("INVALID_FRAME_SIZE")
        return VideoFrame(
            camera_id=camera_id,
            stream_session_id=session_id,
            sequence=sequence,
            timestamp_ms=monotonic_ns() // 1_000_000,
            width=self._width,
            height=self._height,
            pixel_format="RGB",
            payload=payload,
        )

    def close(self) -> None:
        pipeline = self._pipeline
        self._pipeline = None
        self._sink = None
        if pipeline is not None:
            pipeline.set_state(self._gst.State.NULL)


def load_gstreamer() -> Any:
    try:
        gi = import_module("gi")
        gi.require_version("Gst", "1.0")
        Gst = import_module("gi.repository.Gst")
    except (ModuleNotFoundError, ValueError) as error:
        raise RuntimeError("GSTREAMER_BINDINGS_UNAVAILABLE") from error
    Gst.init(None)
    return Gst
