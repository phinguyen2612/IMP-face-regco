from datetime import time
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, model_validator

NormalizedCoordinate = Annotated[float, Field(ge=0.0, le=1.0)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ROI(StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    purpose: Literal["observation", "processing", "recognition"] = "recognition"
    polygon: list[tuple[float, float]] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_normalized_polygon(self) -> "ROI":
        if any(not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) for x, y in self.polygon):
            raise ValueError("ROI coordinates must be between 0 and 1")
        doubled_area = sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(
                self.polygon,
                self.polygon[1:] + self.polygon[:1],
                strict=True,
            )
        )
        if abs(doubled_area) < 1e-9:
            raise ValueError("ROI polygon must have a non-zero area")
        return self


class RTSPStreamConfig(StrictModel):
    uri: AnyUrl
    codec: Literal["H264", "H265"] = "H264"
    transport: Literal["tcp", "udp"] = "tcp"

    @model_validator(mode="after")
    def validate_rtsp_scheme(self) -> "RTSPStreamConfig":
        if self.uri.scheme not in {"rtsp", "rtsps"}:
            raise ValueError("camera stream URI must use rtsp or rtsps")
        return self


class CameraConfig(StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    enabled: bool = True
    stream: RTSPStreamConfig
    rois: list[ROI] = Field(default_factory=list)


class ModelReference(StrictModel):
    model_definition_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    deployment_id: str = Field(min_length=1)


class ModelSelection(StrictModel):
    person_detector: ModelReference
    face_detector: ModelReference
    face_embedder: ModelReference


class ROISelection(StrictModel):
    recognition_area_ids: list[str] = Field(default_factory=list)
    track_anchor: Literal["center", "bottom_center"] = "bottom_center"
    face_anchor: Literal["center"] = "center"


class FaceQualityConfig(StrictModel):
    min_face_size_px: int = Field(default=80, ge=1)
    min_detection_confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    max_abs_yaw_deg: float = Field(default=30.0, ge=0.0, le=90.0)
    max_abs_pitch_deg: float = Field(default=25.0, ge=0.0, le=90.0)
    max_abs_roll_deg: float = Field(default=25.0, ge=0.0, le=180.0)
    blur_threshold: float = Field(default=100.0, ge=0.0)
    brightness_min: float = Field(default=40.0, ge=0.0, le=255.0)
    brightness_max: float = Field(default=220.0, ge=0.0, le=255.0)
    max_occlusion: float = Field(default=0.3, ge=0.0, le=1.0)
    require_landmarks: bool = True

    @model_validator(mode="after")
    def validate_brightness_range(self) -> "FaceQualityConfig":
        if self.brightness_min >= self.brightness_max:
            raise ValueError("brightness_min must be lower than brightness_max")
        return self


class RecognitionConfig(StrictModel):
    identity_collection_id: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)
    similarity_threshold: float = Field(default=0.72, ge=0.0, le=1.0)


class VerificationConfig(StrictModel):
    strategy: Literal["quality_weighted_vote"] = "quality_weighted_vote"
    min_good_frames: int = Field(default=3, ge=2)
    max_frames: int = Field(default=8, ge=2)
    timeout_ms: int = Field(default=2000, gt=0)
    similarity_threshold: float = Field(default=0.72, ge=0.0, le=1.0)
    identity_consistency: float = Field(default=0.75, ge=0.0, le=1.0)
    min_candidate_margin: float = Field(default=0.05, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_frame_bounds(self) -> "VerificationConfig":
        if self.min_good_frames > self.max_frames:
            raise ValueError("min_good_frames must not exceed max_frames")
        return self


class TimingConfig(StrictModel):
    recognition_interval_ms: int = Field(default=500, ge=0)
    recognition_retry_ms: int = Field(default=5000, ge=0)
    verified_identity_ttl_ms: int = Field(default=10000, gt=0)
    track_cache_ttl_ms: int = Field(default=10000, gt=0)
    unknown_dwell_ms: int = Field(default=3000, ge=0)
    event_cooldown_ms: int = Field(default=30000, ge=0)
    duplicate_suppression_ms: int = Field(default=5000, ge=0)

    @model_validator(mode="after")
    def validate_cache_lifetime(self) -> "TimingConfig":
        if self.track_cache_ttl_ms <= self.recognition_interval_ms:
            raise ValueError("track_cache_ttl_ms must exceed recognition_interval_ms")
        return self


class TimeRange(StrictModel):
    start: time
    end: time

    @model_validator(mode="after")
    def validate_order(self) -> "TimeRange":
        if self.start.utcoffset() is not None or self.end.utcoffset() is not None:
            raise ValueError("schedule times must be local wall-clock times without UTC offsets")
        if self.start >= self.end:
            raise ValueError("schedule start must be before end")
        return self


class ScheduleConfig(StrictModel):
    timezone: str = "Asia/Ho_Chi_Minh"
    weekly: dict[str, list[TimeRange]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timezone_and_weekdays(self) -> "ScheduleConfig":
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA timezone") from error

        allowed_weekdays = {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }
        unknown_weekdays = set(self.weekly) - allowed_weekdays
        if unknown_weekdays:
            raise ValueError(f"unknown weekdays: {', '.join(sorted(unknown_weekdays))}")
        return self


class PolicyCondition(StrictModel):
    verification_statuses: list[Literal["PENDING", "VERIFIED", "UNCERTAIN", "UNKNOWN"]]
    roi_ids: list[str] = Field(default_factory=list)
    identity_group_ids: list[str] = Field(default_factory=list)
    minimum_dwell_ms: int = Field(default=0, ge=0)


class PolicyAction(StrictModel):
    emit_event: bool = True
    event_type: Literal["KNOWN_PERSON", "UNKNOWN_PERSON", "WATCHLIST_PERSON"]
    severity: Literal["info", "low", "medium", "high", "critical"] = "info"


class RecognitionPolicy(StrictModel):
    id: str = Field(min_length=1)
    priority: int = 0
    enabled: bool = True
    conditions: PolicyCondition
    action: PolicyAction


class EvidenceOverlayConfig(StrictModel):
    person_bbox: bool = True
    face_bbox: bool = True
    roi: bool = True
    identity: bool = True
    similarity: bool = False


class EvidenceConfig(StrictModel):
    snapshot: bool = True
    video_clip: bool = False
    pre_event_seconds: int = Field(default=5, ge=0, le=60)
    post_event_seconds: int = Field(default=5, ge=0, le=60)
    overlays: EvidenceOverlayConfig = Field(default_factory=EvidenceOverlayConfig)


class FaceRecognitionConfig(StrictModel):
    schema_version: Literal[1] = 1
    feature_type: Literal["face_recognition"] = "face_recognition"
    name: str = Field(min_length=1)
    camera_id: str = Field(min_length=1)
    enabled: bool = True
    models: ModelSelection
    roi: ROISelection = Field(default_factory=ROISelection)
    quality: FaceQualityConfig = Field(default_factory=FaceQualityConfig)
    recognition: RecognitionConfig
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    policies: list[RecognitionPolicy] = Field(default_factory=list)
    evidence: EvidenceConfig = Field(default_factory=EvidenceConfig)
