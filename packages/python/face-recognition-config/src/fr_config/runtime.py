from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, PostgresDsn, RedisDsn


class RuntimeSettings(BaseModel):
    """Backend-only settings; never serialized as FaceRecognition feature config."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(min_length=1)
    postgres_dsn: PostgresDsn
    redis_url: RedisDsn
    evidence_root: Path
    gstreamer_decoder: str = Field(min_length=1)
