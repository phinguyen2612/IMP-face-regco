import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from control_api.camera_connection import GStreamerCameraConnectionTester
from control_api.camera_postgres import (
    Connection,
    PostgresCameraRepository,
    connect_postgres,
    initialize_camera_schema,
)
from control_api.cameras import (
    CameraService,
    FernetCameraSecretProtector,
    InMemoryCameraRepository,
)


@dataclass(frozen=True, slots=True)
class CameraPersistence:
    service: CameraService
    mode: str


def build_camera_persistence(
    environment: Mapping[str, str] | None = None,
    connector: Callable[[str], Connection] = connect_postgres,
) -> CameraPersistence:
    env = os.environ if environment is None else environment
    dsn = env.get("FR_POSTGRES_DSN")
    key = env.get("FR_CAMERA_ENCRYPTION_KEY")
    if not dsn and not key:
        return CameraPersistence(
            CameraService(
                InMemoryCameraRepository(),
                FernetCameraSecretProtector.generate(),
                GStreamerCameraConnectionTester(),
            ),
            "in_memory",
        )
    if not dsn or not key:
        raise RuntimeError(
            "FR_POSTGRES_DSN and FR_CAMERA_ENCRYPTION_KEY must be configured together"
        )
    connection = connector(dsn)
    initialize_camera_schema(connection)
    return CameraPersistence(
        CameraService(
            PostgresCameraRepository(connection),
            FernetCameraSecretProtector(key.encode()),
            GStreamerCameraConnectionTester(),
        ),
        "postgresql",
    )
