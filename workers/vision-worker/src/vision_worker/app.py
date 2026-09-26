from fr_config.models import FaceRecognitionConfig
from fr_contracts.runtime_status import CameraConnectionState

from vision_worker.inference.interfaces import PersonDetector
from vision_worker.inference.stubs import StubPersonDetector
from vision_worker.runtime.pipeline import FrameProcessingResult, RuntimePipeline
from vision_worker.runtime.runner import RuntimeRunner, RuntimeRunSummary
from vision_worker.runtime.status_publisher import RuntimeStatusPublisher
from vision_worker.runtime.track_store import InMemoryTrackStore
from vision_worker.tracking.interfaces import StubTracker, Tracker
from vision_worker.video.buffer import BoundedFrameBuffer
from vision_worker.video.camera import GStreamerCameraSource
from vision_worker.video.frame import VideoFrame
from vision_worker.video.sampling import FrameSampler


class VisionWorker:
    def __init__(self, pipeline: RuntimePipeline) -> None:
        self._pipeline = pipeline

    @classmethod
    def with_stub_adapters(cls) -> "VisionWorker":
        pipeline = RuntimePipeline(
            person_detector=StubPersonDetector(),
            tracker=StubTracker(),
            track_store=InMemoryTrackStore(ttl_ms=10000),
            ring_buffer=BoundedFrameBuffer(capacity=100),
            sampler=FrameSampler(target_fps=5.0),
            worker_id="worker-local",
            active_config_revision=None,
        )
        return cls(pipeline)

    @classmethod
    def with_runtime_config(
        cls,
        config: FaceRecognitionConfig,
        worker_id: str,
        config_revision: str,
        processing_fps: float,
        ring_buffer_capacity: int,
        person_detector: PersonDetector | None = None,
        tracker: Tracker | None = None,
    ) -> "VisionWorker":
        if person_detector is None or tracker is None:
            raise RuntimeError("MODEL_ADAPTERS_NOT_RESOLVED")
        pipeline = RuntimePipeline(
            person_detector=person_detector,
            tracker=tracker,
            track_store=InMemoryTrackStore(ttl_ms=config.timing.track_cache_ttl_ms),
            ring_buffer=BoundedFrameBuffer(capacity=ring_buffer_capacity),
            sampler=FrameSampler(target_fps=processing_fps),
            worker_id=worker_id,
            active_config_revision=config_revision,
        )
        return cls(pipeline)

    def process_frame(self, frame: VideoFrame) -> FrameProcessingResult | None:
        return self._pipeline.process_frame(frame)

    def run_camera(
        self,
        source: GStreamerCameraSource,
        limit: int | None = None,
        status_publisher: RuntimeStatusPublisher | None = None,
    ) -> RuntimeRunSummary:
        return RuntimeRunner(source, self._pipeline, status_publisher).run(limit=limit)

    def run_once(self) -> dict[str, object]:
        runtime = self._pipeline.status(
            camera_state=CameraConnectionState.DISCONNECTED,
            elapsed_seconds=1.0,
        ).model_dump(mode="json")
        return {
            "status": "ready",
            "inference_mode": "stub",
            "camera_count": 0,
            **runtime,
        }
