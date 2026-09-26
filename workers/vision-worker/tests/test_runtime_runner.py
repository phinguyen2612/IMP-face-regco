import httpx
from fr_contracts.runtime_status import CameraConnectionState, RuntimeStatus
from vision_worker.inference.interfaces import BoundingBox
from vision_worker.inference.stubs import MockPersonDetector
from vision_worker.runtime.pipeline import RuntimePipeline
from vision_worker.runtime.runner import RuntimeRunner
from vision_worker.runtime.status_publisher import HttpRuntimeStatusPublisher
from vision_worker.runtime.track_store import InMemoryTrackStore
from vision_worker.tracking.interfaces import MockTracker
from vision_worker.video.buffer import BoundedFrameBuffer
from vision_worker.video.camera import GStreamerCameraSource
from vision_worker.video.frame import VideoFrame
from vision_worker.video.sampling import FrameSampler


class TwoFrameBackend:
    def open(self, uri: str, codec: str, transport: str) -> None:
        return None

    def read(self, camera_id: str, session_id: str, sequence: int) -> VideoFrame | None:
        return VideoFrame(camera_id, session_id, sequence, timestamp_ms=sequence * 100)

    def close(self) -> None:
        return None


class CapturingPublisher:
    def __init__(self) -> None:
        self.statuses: list[RuntimeStatus] = []

    def publish(self, status: RuntimeStatus) -> None:
        self.statuses.append(status)


def test_camera_ingestion_flows_through_sampling_detection_tracking_and_state() -> None:
    source = GStreamerCameraSource(
        camera_id="camera-01",
        uri="rtsp://camera.invalid/stream",
        codec="H264",
        transport="tcp",
        backend=TwoFrameBackend(),
    )
    pipeline = RuntimePipeline(
        person_detector=MockPersonDetector(
            detections=[BoundingBox(0.1, 0.1, 0.5, 0.9, confidence=0.95)]
        ),
        tracker=MockTracker(),
        track_store=InMemoryTrackStore(ttl_ms=1000),
        ring_buffer=BoundedFrameBuffer(capacity=4),
        sampler=FrameSampler(target_fps=10.0),
        worker_id="worker-01",
        active_config_revision="revision-7",
    )

    publisher = CapturingPublisher()
    summary = RuntimeRunner(source, pipeline, status_publisher=publisher).run(limit=2)

    assert summary.frames_received == 2
    assert summary.frames_processed == 2
    assert summary.last_result is not None
    assert summary.last_result.track_results[0].track_id == 1
    assert summary.camera_state is CameraConnectionState.STOPPED
    assert all(status.stream_session_id for status in publisher.statuses)
    assert all(status.reconnect_count == 0 for status in publisher.statuses)
    assert [status.camera_state for status in publisher.statuses] == [
        CameraConnectionState.CONNECTED,
        CameraConnectionState.CONNECTED,
        CameraConnectionState.STOPPED,
    ]


def test_http_status_publisher_puts_runtime_contract() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={})

    status = RuntimeStatus(
        worker_id="worker-01",
        camera_id="camera-01",
        camera_state=CameraConnectionState.CONNECTED,
        input_fps=25,
        processed_fps=5,
        dropped_frames=0,
        active_tracks=1,
        ring_buffer_frames=2,
        ring_buffer_capacity=4,
        worker_health="healthy",
        active_config_revision="revision-7",
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    HttpRuntimeStatusPublisher("http://control-api/api/v1/runtime/status", client=client).publish(
        status
    )

    assert captured[0].method == "PUT"
    assert captured[0].url.path == "/api/v1/runtime/status"
    assert b'"active_tracks":1' in captured[0].content
