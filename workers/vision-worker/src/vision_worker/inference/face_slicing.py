"""Bounded, overlapping SCRFD views; detections remain relative to the parent ROI."""

from dataclasses import dataclass
from math import isfinite
from typing import Any

from vision_worker.face_recognition.images import PersonCrop
from vision_worker.inference.interfaces import BoundingBox, FaceDetection, FaceLandmarks


@dataclass(frozen=True, slots=True)
class FaceSlicingConfig:
    enabled: bool = False
    tile_width: int = 640
    tile_height: int = 640
    overlap_ratio: float = 0.2
    max_tiles: int = 16  # excludes the standard pass

    @classmethod
    def from_metadata(cls, value: Any) -> "FaceSlicingConfig":
        if not isinstance(value, dict) or set(value) - cls.__dataclass_fields__.keys():
            raise ValueError("INVALID_FACE_SLICING_CONFIG")
        config = cls(**value)
        if (
            not isinstance(config.enabled, bool)
            or any(
                type(size) is not int or not 32 <= size <= 16384
                for size in (config.tile_width, config.tile_height)
            )
            or type(config.max_tiles) is not int or not 1 <= config.max_tiles <= 64
            or isinstance(config.overlap_ratio, bool)
            or not isinstance(config.overlap_ratio, (int, float))
            or not isfinite(config.overlap_ratio) or not 0 <= config.overlap_ratio <= 0.5
        ):
            raise ValueError("INVALID_FACE_SLICING_CONFIG")
        return config

    def windows(self, width: int, height: int) -> list[tuple[int, int, int, int]]:
        if not self.enabled:
            return []
        tile_width, tile_height = min(width, self.tile_width), min(height, self.tile_height)
        # Coarsen instead of truncating the grid: every part of the ROI stays covered.
        while True:
            xs = self._starts(width, tile_width)
            ys = self._starts(height, tile_height)
            if len(xs) * len(ys) <= self.max_tiles:
                break
            tile_width = min(width, tile_width * 2)
            tile_height = min(height, tile_height * 2)
        if tile_width == width and tile_height == height:
            return []  # already covered by the mandatory standard pass
        return [(x, y, x + tile_width, y + tile_height) for y in ys for x in xs]

    def _starts(self, length: int, tile: int) -> list[int]:
        step = max(1, int(tile * (1 - self.overlap_ratio)))
        end = length - tile
        starts = list(range(0, end, step))
        return [*starts, end]


def slice_crop(crop: PersonCrop, window: tuple[int, int, int, int]) -> PersonCrop:
    left, top, right, bottom = window
    return PersonCrop(
        crop.pixels[top:bottom, left:right], crop.frame, crop.left + left, crop.top + top,
    )


def translate_face(face: FaceDetection, left: int, top: int) -> FaceDetection:
    box = face.box
    landmarks = face.landmarks
    return FaceDetection(
        BoundingBox(box.x1 + left, box.y1 + top, box.x2 + left, box.y2 + top, box.confidence),
        FaceLandmarks(*((x + left, y + top) for x, y in landmarks.points()))
        if landmarks is not None else None,
    )
