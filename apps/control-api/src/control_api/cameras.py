from dataclasses import dataclass, replace
from typing import Literal, Protocol
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

Codec = Literal["AUTO", "H264", "H265"]
Lifecycle = Literal["DRAFT", "ACTIVE"]


class CameraCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    rtsp_url: SecretStr
    codec: Codec = "AUTO"
    enabled: bool = True
    sampling_fps: float = Field(default=5.0, gt=0, le=60)

    @model_validator(mode="after")
    def valid_url(self) -> "CameraCreate":
        validate_rtsp_url(self.rtsp_url.get_secret_value())
        return self


class CameraUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1)
    rtsp_url: SecretStr | None = None
    codec: Codec | None = None
    enabled: bool | None = None
    sampling_fps: float | None = Field(default=None, gt=0, le=60)

    @model_validator(mode="after")
    def valid_url(self) -> "CameraUpdate":
        if self.rtsp_url is not None:
            validate_rtsp_url(self.rtsp_url.get_secret_value())
        return self


class CameraPublic(BaseModel):
    id: str
    name: str
    source_type: Literal["rtsp"] = "rtsp"
    rtsp_url: str
    codec: Codec
    enabled: bool
    sampling_fps: float
    lifecycle: Lifecycle
    revision: str


class ActiveCameraConfig(BaseModel):
    id: str
    name: str
    rtsp_url: str
    codec: Codec
    enabled: bool
    sampling_fps: float
    revision: str


class CameraConnectionResult(BaseModel):
    status: Literal[
        "CONNECTED",
        "AUTHENTICATION_FAILED",
        "UNREACHABLE",
        "TIMEOUT",
        "UNSUPPORTED_STREAM",
        "DECODE_FAILED",
        "BACKEND_UNAVAILABLE",
    ]
    error_category: str | None = None


class CameraConnectionTester(Protocol):
    def test(self, rtsp_url: str) -> CameraConnectionResult: ...


class UnavailableCameraConnectionTester:
    def test(self, rtsp_url: str) -> CameraConnectionResult:
        return CameraConnectionResult(
            status="BACKEND_UNAVAILABLE", error_category="GSTREAMER_UNAVAILABLE"
        )


class CameraSecretProtector(Protocol):
    def protect(self, value: str) -> bytes: ...
    def reveal(self, value: bytes) -> str: ...


class FernetCameraSecretProtector:
    @classmethod
    def generate(cls) -> "FernetCameraSecretProtector":
        return cls(Fernet.generate_key())

    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    def protect(self, value: str) -> bytes:
        return self._fernet.encrypt(value.encode())

    def reveal(self, value: bytes) -> str:
        return self._fernet.decrypt(value).decode()


@dataclass(frozen=True, slots=True)
class CameraRecord:
    id: str
    name: str
    protected_rtsp_url: bytes
    redacted_rtsp_url: str
    codec: Codec
    enabled: bool
    sampling_fps: float
    lifecycle: Lifecycle
    revision: str


class CameraRepository(Protocol):
    def put(self, record: CameraRecord) -> None: ...
    def get(self, camera_id: str) -> CameraRecord | None: ...
    def list(self) -> list[CameraRecord]: ...


class InMemoryCameraRepository:
    def __init__(self) -> None:
        self._records: dict[str, CameraRecord] = {}

    def put(self, record: CameraRecord) -> None:
        self._records[record.id] = record

    def get(self, camera_id: str) -> CameraRecord | None:
        return self._records.get(camera_id)

    def list(self) -> list[CameraRecord]:
        return list(self._records.values())


class CameraService:
    def __init__(
        self,
        repository: CameraRepository,
        protector: CameraSecretProtector,
        connection_tester: CameraConnectionTester | None = None,
    ) -> None:
        self.repo = repository
        self.protector = protector
        self.tester = connection_tester or UnavailableCameraConnectionTester()

    def create(self, req: CameraCreate) -> CameraPublic:
        uri = req.rtsp_url.get_secret_value()
        rec = CameraRecord(
            str(uuid4()),
            req.name,
            self.protector.protect(uri),
            redact_rtsp_url(uri),
            req.codec,
            req.enabled,
            req.sampling_fps,
            "DRAFT",
            str(uuid4()),
        )
        self.repo.put(rec)
        return self.public(rec)

    def require(self, camera_id: str) -> CameraRecord:
        rec = self.repo.get(camera_id)
        if rec is None:
            raise KeyError(camera_id)
        return rec

    def update(self, camera_id: str, req: CameraUpdate) -> CameraPublic:
        current = self.require(camera_id)
        protected_url = current.protected_rtsp_url
        redacted_url = current.redacted_rtsp_url
        if req.rtsp_url is not None:
            uri = req.rtsp_url.get_secret_value()
            protected_url = self.protector.protect(uri)
            redacted_url = redact_rtsp_url(uri)
        updated = CameraRecord(
            id=current.id,
            name=req.name if req.name is not None else current.name,
            protected_rtsp_url=protected_url,
            redacted_rtsp_url=redacted_url,
            codec=req.codec if req.codec is not None else current.codec,
            enabled=req.enabled if req.enabled is not None else current.enabled,
            sampling_fps=(
                req.sampling_fps if req.sampling_fps is not None else current.sampling_fps
            ),
            lifecycle="DRAFT",
            revision=str(uuid4()),
        )
        self.repo.put(updated)
        return self.public(updated)

    def activate(self, camera_id: str) -> CameraPublic:
        rec = replace(self.require(camera_id), lifecycle="ACTIVE", revision=str(uuid4()))
        self.repo.put(rec)
        return self.public(rec)

    def test_connection(self, camera_id: str) -> CameraConnectionResult:
        rec = self.require(camera_id)
        return self.tester.test(self.protector.reveal(rec.protected_rtsp_url))

    def get_public(self, camera_id: str) -> CameraPublic:
        return self.public(self.require(camera_id))

    def public_list(self) -> list[CameraPublic]:
        return [self.public(r) for r in self.repo.list()]

    def active_list(self) -> list[ActiveCameraConfig]:
        return [
            ActiveCameraConfig(
                id=r.id,
                name=r.name,
                rtsp_url=self.protector.reveal(r.protected_rtsp_url),
                codec=r.codec,
                enabled=r.enabled,
                sampling_fps=r.sampling_fps,
                revision=r.revision,
            )
            for r in self.repo.list()
            if r.lifecycle == "ACTIVE" and r.enabled
        ]

    @staticmethod
    def public(r: CameraRecord) -> CameraPublic:
        return CameraPublic(
            id=r.id,
            name=r.name,
            rtsp_url=r.redacted_rtsp_url,
            codec=r.codec,
            enabled=r.enabled,
            sampling_fps=r.sampling_fps,
            lifecycle=r.lifecycle,
            revision=r.revision,
        )


def validate_rtsp_url(value: str) -> None:
    p = urlsplit(value)
    if p.scheme not in {"rtsp", "rtsps"} or not p.hostname:
        raise ValueError("camera URL must be an absolute rtsp or rtsps URL")


def redact_rtsp_url(value: str) -> str:
    p = urlsplit(value)
    validate_rtsp_url(value)
    host = p.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    if p.port is not None:
        host = f"{host}:{p.port}"
    netloc = f"***:***@{host}" if p.username is not None else host
    return urlunsplit((p.scheme, netloc, p.path, "", ""))
