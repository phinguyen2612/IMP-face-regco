from dataclasses import dataclass
from typing import Any, Protocol

import httpx


@dataclass(frozen=True, slots=True)
class ActiveCamera:
    id: str
    name: str
    rtsp_url: str
    codec: str
    enabled: bool
    sampling_fps: float
    revision: str


class ActiveCameraProvider(Protocol):
    def fetch(self) -> list[ActiveCamera]: ...


class HttpActiveCameraProvider:
    def __init__(
        self,
        control_api_url: str,
        worker_token: str,
        timeout_seconds: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._endpoint = f"{control_api_url.rstrip('/')}/api/v1/internal/cameras/active"
        self._worker_token = worker_token
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def fetch(self) -> list[ActiveCamera]:
        response = self._client.get(
            self._endpoint,
            headers={"X-Worker-Token": self._worker_token},
        )
        response.raise_for_status()
        payload: Any = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise RuntimeError("INVALID_CAMERA_CONFIGURATION_RESPONSE")
        return [ActiveCamera(**item) for item in payload["items"]]


class ManagedSource(Protocol):
    def close(self) -> None: ...


class TrackStateCleaner(Protocol):
    def clear_camera(self, camera_id: str) -> None: ...


class SourceFactory(Protocol):
    def __call__(self, config: ActiveCamera) -> ManagedSource: ...


class CameraRuntimeManager:
    def __init__(self, factory: SourceFactory, track_store: TrackStateCleaner) -> None:
        self._factory = factory
        self._track_store = track_store
        self._active: dict[str, tuple[str, ManagedSource]] = {}

    def apply(self, configs: list[ActiveCamera]) -> list[str]:
        desired = {c.id: c for c in configs if c.enabled}
        changed = []
        for camera_id in set(self._active) - set(desired):
            self._stop(camera_id)
            changed.append(camera_id)
        for camera_id, config in desired.items():
            current = self._active.get(camera_id)
            if current is not None and current[0] == config.revision:
                continue
            if current is not None:
                self._stop(camera_id)
            self._active[camera_id] = (config.revision, self._factory(config))
            changed.append(camera_id)
        return changed

    def close_all(self) -> None:
        for camera_id in list(self._active):
            self._stop(camera_id)

    def _stop(self, camera_id: str) -> None:
        _, source = self._active.pop(camera_id)
        source.close()
        self._track_store.clear_camera(camera_id)


class CameraConfigSynchronizer:
    def __init__(
        self,
        provider: ActiveCameraProvider,
        manager: CameraRuntimeManager,
    ) -> None:
        self._provider = provider
        self._manager = manager

    def sync_once(self) -> list[str]:
        return self._manager.apply(self._provider.fetch())
