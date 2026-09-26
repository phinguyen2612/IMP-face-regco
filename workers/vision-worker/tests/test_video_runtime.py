from io import BytesIO

from vision_worker.video.buffer import BoundedFrameBuffer
from vision_worker.video.camera import (
    CameraConnectionState,
    CameraStateMachine,
    GStreamerCameraSource,
)
from vision_worker.video.frame import VideoFrame
from vision_worker.video.gstreamer import SubprocessGStreamerBackend
from vision_worker.video.sampling import FrameSampler


def frame(sequence: int, timestamp_ms: int) -> VideoFrame:
    return VideoFrame(
        camera_id="camera-01",
        stream_session_id="session-01",
        sequence=sequence,
        timestamp_ms=timestamp_ms,
        width=1920,
        height=1080,
        pixel_format="RGB",
    )


def test_ring_buffer_keeps_newest_frames_with_bounded_capacity() -> None:
    buffer = BoundedFrameBuffer(capacity=2)

    buffer.append(frame(1, 0))
    buffer.append(frame(2, 40))
    buffer.append(frame(3, 80))

    assert [item.sequence for item in buffer.snapshot()] == [2, 3]
    assert buffer.usage.frames == 2
    assert buffer.usage.capacity == 2
    assert buffer.overwritten_frames == 1


def test_frame_sampler_limits_processing_rate_per_camera() -> None:
    sampler = FrameSampler(target_fps=5.0)

    assert sampler.should_process(frame(1, 0)) is True
    assert sampler.should_process(frame(2, 100)) is False
    assert sampler.should_process(frame(3, 199)) is False
    assert sampler.should_process(frame(4, 200)) is True


def test_camera_state_transitions_through_reconnect() -> None:
    state = CameraStateMachine(camera_id="camera-01")

    state.connecting()
    state.connected()
    state.disconnected("stream timeout")

    assert state.snapshot.state is CameraConnectionState.RECONNECTING
    assert state.snapshot.reconnect_attempts == 1
    assert state.snapshot.last_error == "stream timeout"

    state.connected()
    assert state.snapshot.state is CameraConnectionState.CONNECTED
    assert state.snapshot.reconnect_attempts == 0
    assert state.snapshot.last_error is None


class ReconnectingBackend:
    def __init__(self) -> None:
        self.open_count = 0
        self.read_count = 0

    def open(self, uri: str, codec: str, transport: str) -> None:
        self.open_count += 1

    def read(self, camera_id: str, session_id: str, sequence: int) -> VideoFrame | None:
        self.read_count += 1
        if self.read_count == 2:
            return None
        return VideoFrame(camera_id, session_id, sequence, timestamp_ms=sequence * 40)

    def close(self) -> None:
        return None


def test_gstreamer_camera_source_reconnects_after_read_failure() -> None:
    backend = ReconnectingBackend()
    source = GStreamerCameraSource(
        camera_id="camera-01",
        uri="rtsp://camera.invalid/stream",
        codec="H264",
        transport="tcp",
        backend=backend,
        max_reconnect_attempts=2,
        reconnect_delay_seconds=0,
    )

    frames = list(source.frames(limit=2))

    assert [item.sequence for item in frames] == [1, 2]
    assert frames[0].stream_session_id != frames[1].stream_session_id
    assert backend.open_count == 2
    assert source.state.snapshot.state is CameraConnectionState.STOPPED


class FakeGStreamerProcess:
    def __init__(self, payload: bytes) -> None:
        self.stdout = BytesIO(payload)
        self.returncode = None

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode or 0

    def kill(self) -> None:
        self.returncode = -1


def test_gstreamer_backend_reads_fixed_size_rgb_frame_without_shell() -> None:
    calls: list[tuple[list[str], dict]] = []

    def popen(args: list[str], **kwargs: object) -> FakeGStreamerProcess:
        calls.append((args, kwargs))
        return FakeGStreamerProcess(b"\x01\x02\x03\x04\x05\x06")

    backend = SubprocessGStreamerBackend(
        executable="gst-launch-1.0",
        width=1,
        height=2,
        decoder="decodebin",
        converter="videoconvert",
        popen_factory=popen,
    )
    backend.open("rtsp://camera.invalid/stream", "H264", "tcp")

    captured = backend.read("camera-01", "session-01", 1)

    assert captured is not None
    assert captured.width == 1
    assert captured.height == 2
    assert captured.pixel_format == "RGB"
    assert captured.payload == b"\x01\x02\x03\x04\x05\x06"
    args, kwargs = calls[0]
    assert "rtph264depay" in args
    assert "location=rtsp://camera.invalid/stream" in args
    assert kwargs["shell"] is False


class FailingOpenBackend:
    def open(self, uri: str, codec: str, transport: str) -> None:
        raise ConnectionError("offline")

    def read(self, camera_id: str, session_id: str, sequence: int) -> VideoFrame | None:
        return None

    def close(self) -> None:
        return None


def test_reconnect_uses_bounded_exponential_backoff() -> None:
    sleeps: list[float] = []
    source = GStreamerCameraSource(
        camera_id="camera-01",
        uri="rtsp://camera.invalid/stream",
        codec="AUTO",
        transport="tcp",
        backend=FailingOpenBackend(),
        max_reconnect_attempts=3,
        reconnect_delay_seconds=1.0,
        max_reconnect_delay_seconds=3.0,
        sleeper=sleeps.append,
    )

    assert list(source.frames(limit=1)) == []
    assert sleeps == [1.0, 2.0, 3.0]
    assert source.state.snapshot.total_reconnects == 4


def test_subprocess_diagnostic_refuses_credential_bearing_uri() -> None:
    calls: list[tuple[list[str], dict]] = []

    def popen(args: list[str], **kwargs: object) -> FakeGStreamerProcess:
        calls.append((args, kwargs))
        return FakeGStreamerProcess(b"")

    backend = SubprocessGStreamerBackend(
        executable="gst-launch-1.0",
        width=1,
        height=1,
        decoder="decodebin",
        converter="videoconvert",
        popen_factory=popen,
    )
    try:
        backend.open("rtsp://alice:secret@camera.invalid/stream", "AUTO", "tcp")
    except ValueError as error:
        assert str(error) == "credential-bearing RTSP requires in-process GStreamer"
    else:
        raise AssertionError("credential-bearing URI was accepted")
    assert calls == []
