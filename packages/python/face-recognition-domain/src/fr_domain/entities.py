from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FaceEnrollment:
    id: str
    embedding: tuple[float, ...]
    embedding_model_id: str
    embedding_model_version: str
    quality_metadata: dict[str, float] = field(default_factory=dict)
    enrollment_evidence_ref: str | None = None
    created_at: datetime | None = None
    active: bool = True


@dataclass(slots=True)
class Person:
    id: str
    display_name: str
    enrollments: list[FaceEnrollment] = field(default_factory=list)
    identity_group_ids: list[str] = field(default_factory=list)
    active: bool = True
