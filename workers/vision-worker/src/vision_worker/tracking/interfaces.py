from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from vision_worker.inference.interfaces import BoundingBox
from vision_worker.video.frame import VideoFrame


@dataclass(frozen=True, slots=True)
class TrackedPerson:
    track_id: int
    box: BoundingBox
    confidence: float


class Tracker(Protocol):
    adapter_kind: str

    def update(
        self, frame: VideoFrame, detections: Sequence[BoundingBox]
    ) -> list[TrackedPerson]: ...

    def reset(self, camera_id: str) -> None: ...


class StubTracker:
    adapter_kind = "stub"

    def reset(self, camera_id: str) -> None:
        return None

    def update(self, frame: VideoFrame, detections: Sequence[BoundingBox]) -> list[TrackedPerson]:
        return []


class MockTracker:
    """Deterministic tracker for exercising track-based runtime flow without BoT-SORT."""

    adapter_kind = "mock"

    def reset(self, camera_id: str) -> None:
        return None

    def update(self, frame: VideoFrame, detections: Sequence[BoundingBox]) -> list[TrackedPerson]:
        return [
            TrackedPerson(track_id=index + 1, box=box, confidence=box.confidence)
            for index, box in enumerate(detections)
        ]
