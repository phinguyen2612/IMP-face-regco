from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from vision_worker.video.frame import VideoFrame


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


@dataclass(frozen=True, slots=True)
class FaceDetection:
    box: BoundingBox
    landmarks: tuple[tuple[float, float], ...] = ()


class PersonDetector(Protocol):
    adapter_kind: str

    def detect(self, frames: Sequence[VideoFrame]) -> list[list[BoundingBox]]: ...


class FaceDetector(Protocol):
    adapter_kind: str

    def detect(self, person_crops: Sequence[Any]) -> list[list[FaceDetection]]: ...


class FaceEmbedder(Protocol):
    adapter_kind: str

    def embed(self, aligned_faces: Sequence[Any]) -> list[list[float]]: ...
