from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Literal

from fr_contracts.runtime_status import CameraConnectionState, RuntimeStatus
from fr_domain.models import TrackKey

from vision_worker.inference.interfaces import PersonDetector
from vision_worker.runtime.track_store import InMemoryTrackStore
from vision_worker.tracking.interfaces import TrackedPerson, Tracker
from vision_worker.video.buffer import BoundedFrameBuffer
from vision_worker.video.frame import VideoFrame
from vision_worker.video.sampling import FrameSampler


@dataclass(frozen=True, slots=True)
class FrameProcessingResult:
    camera_id: str
    sequence: int
    track_results: list[TrackedPerson]


class RuntimePipeline:
    def __init__(
        self,
        person_detector: PersonDetector,
        tracker: Tracker,
        track_store: InMemoryTrackStore,
        ring_buffer: BoundedFrameBuffer,
        sampler: FrameSampler,
        worker_id: str,
        active_config_revision: str | None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._person_detector = person_detector
        self._tracker = tracker
        self._track_store = track_store
        self._ring_buffer = ring_buffer
        self._sampler = sampler
        self._worker_id = worker_id
        self._active_config_revision = active_config_revision
        self._clock = clock
        self._started_at = clock()
        self._input_frames = 0
        self._processed_frames = 0
        self._dropped_frames = 0
        self._last_camera_id: str | None = None
        self._sessions: dict[str, str] = {}

    def process_frame(self, frame: VideoFrame) -> FrameProcessingResult | None:
        previous_session = self._sessions.get(frame.camera_id)
        if previous_session is not None and previous_session != frame.stream_session_id:
            self._track_store.clear_camera(frame.camera_id)
            self._tracker.reset(frame.camera_id)
        self._sessions[frame.camera_id] = frame.stream_session_id
        self._last_camera_id = frame.camera_id
        self._input_frames += 1
        self._ring_buffer.append(frame)
        self._track_store.evict_expired(now_ms=frame.timestamp_ms)
        if not self._sampler.should_process(frame):
            return None

        detections = self._person_detector.detect([frame])[0]
        tracks = self._tracker.update(frame, detections)
        for track in tracks:
            key = TrackKey(frame.camera_id, frame.stream_session_id, track.track_id)
            self._track_store.get_or_create(key, seen_at_ms=frame.timestamp_ms)
        self._processed_frames += 1
        return FrameProcessingResult(frame.camera_id, frame.sequence, list(tracks))

    def status(
        self,
        camera_state: CameraConnectionState,
        elapsed_seconds: float | None = None,
    ) -> RuntimeStatus:
        elapsed = max(
            elapsed_seconds if elapsed_seconds is not None else self._clock() - self._started_at,
            1e-9,
        )
        usage = self._ring_buffer.usage
        if camera_state is CameraConnectionState.CONNECTED:
            health: Literal["healthy", "degraded", "unhealthy"] = "healthy"
        elif camera_state in {CameraConnectionState.ERROR, CameraConnectionState.FAILED}:
            health = "unhealthy"
        else:
            health = "degraded"
        return RuntimeStatus(
            worker_id=self._worker_id,
            camera_id=self._last_camera_id or "unassigned",
            camera_state=camera_state,
            input_fps=self._input_frames / elapsed,
            processed_fps=self._processed_frames / elapsed,
            dropped_frames=self._dropped_frames,
            active_tracks=self._track_store.active_count,
            ring_buffer_frames=usage.frames,
            ring_buffer_capacity=usage.capacity,
            worker_health=health,
            active_config_revision=self._active_config_revision,
        )
