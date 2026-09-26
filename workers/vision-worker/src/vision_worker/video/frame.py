from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class VideoFrame:
    camera_id: str
    stream_session_id: str
    sequence: int
    timestamp_ms: int = 0
    width: int = 0
    height: int = 0
    pixel_format: str = "UNKNOWN"
    payload: Any = field(default=None, compare=False, repr=False)
