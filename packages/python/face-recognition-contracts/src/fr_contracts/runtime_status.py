from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CameraConnectionState(StrEnum):
    DISABLED = "DISABLED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class RuntimeStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(min_length=1)
    camera_id: str = Field(min_length=1)
    camera_state: CameraConnectionState
    input_fps: float = Field(ge=0.0)
    processed_fps: float = Field(ge=0.0)
    dropped_frames: int = Field(ge=0)
    active_tracks: int = Field(ge=0)
    ring_buffer_frames: int = Field(ge=0)
    ring_buffer_capacity: int = Field(gt=0)
    worker_health: Literal["healthy", "degraded", "unhealthy"]
    active_config_revision: str | None = None
    stream_session_id: str | None = None
    reconnect_count: int = Field(default=0, ge=0)
    last_connected_at: str | None = None
    last_frame_at: str | None = None
    error_category: str | None = None
