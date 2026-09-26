from dataclasses import dataclass
from datetime import UTC, datetime

from fr_contracts.runtime_status import CameraConnectionState

from vision_worker.runtime.pipeline import FrameProcessingResult, RuntimePipeline
from vision_worker.runtime.status_publisher import RuntimeStatusPublisher
from vision_worker.video.camera import GStreamerCameraSource


@dataclass(frozen=True, slots=True)
class RuntimeRunSummary:
    frames_received: int
    frames_processed: int
    camera_state: CameraConnectionState
    last_result: FrameProcessingResult | None


class RuntimeRunner:
    """Connects a camera source to the synchronous per-camera runtime pipeline."""

    def __init__(
        self,
        source: GStreamerCameraSource,
        pipeline: RuntimePipeline,
        status_publisher: RuntimeStatusPublisher | None = None,
    ) -> None:
        self._source = source
        self._pipeline = pipeline
        self._status_publisher = status_publisher
        self._last_frame_at: str | None = None

    def run(self, limit: int | None = None) -> RuntimeRunSummary:
        received = 0
        processed = 0
        last_result: FrameProcessingResult | None = None
        for frame in self._source.frames(limit=limit):
            received += 1
            self._last_frame_at = datetime.now(UTC).isoformat()
            result = self._pipeline.process_frame(frame)
            if result is not None:
                processed += 1
                last_result = result
            self._publish_status()
        self._publish_status()
        return RuntimeRunSummary(
            frames_received=received,
            frames_processed=processed,
            camera_state=self._source.state.snapshot.state,
            last_result=last_result,
        )

    def _publish_status(self) -> None:
        if self._status_publisher is None:
            return
        snapshot = self._source.state.snapshot
        status = self._pipeline.status(camera_state=snapshot.state).model_copy(
            update={
                "stream_session_id": self._source.stream_session_id,
                "reconnect_count": snapshot.total_reconnects,
                "last_connected_at": snapshot.last_connected_at,
                "last_frame_at": self._last_frame_at,
                "error_category": ("CAMERA_CONNECTION_FAILED" if snapshot.last_error else None),
            }
        )
        self._status_publisher.publish(status)
