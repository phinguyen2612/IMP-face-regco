from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageEnvelope(BaseModel):
    schema_version: int = 1
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    camera_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
