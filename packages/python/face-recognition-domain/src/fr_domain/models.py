from dataclasses import dataclass
from enum import StrEnum


class ModelType(StrEnum):
    PERSON_DETECTION = "PERSON_DETECTION"
    FACE_DETECTION = "FACE_DETECTION"
    FACE_RECOGNITION = "FACE_RECOGNITION"


@dataclass(frozen=True, slots=True)
class TrackKey:
    camera_id: str
    stream_session_id: str
    track_id: int
