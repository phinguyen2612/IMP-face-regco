from collections.abc import Sequence
from typing import Any

from vision_worker.inference.interfaces import BoundingBox, FaceDetection
from vision_worker.video.frame import VideoFrame


class StubPersonDetector:
    adapter_kind = "stub"

    def detect(self, frames: Sequence[VideoFrame]) -> list[list[BoundingBox]]:
        return [[] for _ in frames]


class MockPersonDetector:
    adapter_kind = "mock"

    def __init__(self, detections: Sequence[BoundingBox]) -> None:
        self._detections = list(detections)

    def detect(self, frames: Sequence[VideoFrame]) -> list[list[BoundingBox]]:
        return [list(self._detections) for _ in frames]


class StubFaceDetector:
    adapter_kind = "stub"

    def detect(self, person_crops: Sequence[Any]) -> list[list[FaceDetection]]:
        return [[] for _ in person_crops]


class StubFaceEmbedder:
    adapter_kind = "stub"

    def embed(self, aligned_faces: Sequence[Any]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0, 0.0] for _ in aligned_faces]
