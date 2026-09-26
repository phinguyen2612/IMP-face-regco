from importlib import import_module
from typing import Any, Protocol, cast

from control_api.cameras import CameraRecord


class Cursor(Protocol):
    def execute(self, sql: str, params: tuple[object, ...] = ()) -> None: ...
    def fetchone(self) -> tuple[Any, ...] | None: ...
    def fetchall(self) -> list[tuple[Any, ...]]: ...
    def __enter__(self) -> "Cursor": ...
    def __exit__(self, *args: object) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> None: ...


CAMERA_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cameras (
    id text PRIMARY KEY,
    name text NOT NULL,
    protected_rtsp_url bytea NOT NULL,
    redacted_rtsp_url text NOT NULL,
    codec text NOT NULL CHECK (codec IN ('AUTO','H264','H265')),
    enabled boolean NOT NULL,
    sampling_fps double precision NOT NULL CHECK (sampling_fps > 0),
    lifecycle text NOT NULL CHECK (lifecycle IN ('DRAFT','ACTIVE')),
    revision text NOT NULL
)
"""


def initialize_camera_schema(connection: Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(CAMERA_SCHEMA_SQL)
    connection.commit()


_COLUMNS = (
    "id,name,protected_rtsp_url,redacted_rtsp_url,codec,enabled,sampling_fps,lifecycle,revision"
)


class PostgresCameraRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def put(self, record: CameraRecord) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO cameras ({_COLUMNS}) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (id) DO UPDATE SET "
                "name=EXCLUDED.name,"
                "protected_rtsp_url=EXCLUDED.protected_rtsp_url,"
                "redacted_rtsp_url=EXCLUDED.redacted_rtsp_url,"
                "codec=EXCLUDED.codec,"
                "enabled=EXCLUDED.enabled,"
                "sampling_fps=EXCLUDED.sampling_fps,"
                "lifecycle=EXCLUDED.lifecycle,"
                "revision=EXCLUDED.revision",
                self._values(record),
            )
        self._connection.commit()

    def get(self, camera_id: str) -> CameraRecord | None:
        with self._connection.cursor() as cursor:
            cursor.execute(f"SELECT {_COLUMNS} FROM cameras WHERE id=%s", (camera_id,))
            row = cursor.fetchone()
        return self._record(row) if row else None

    def list(self) -> list[CameraRecord]:
        with self._connection.cursor() as cursor:
            cursor.execute(f"SELECT {_COLUMNS} FROM cameras ORDER BY name,id")
            rows = cursor.fetchall()
        return [self._record(row) for row in rows]

    @staticmethod
    def _values(r: CameraRecord) -> tuple[object, ...]:
        return (
            r.id,
            r.name,
            r.protected_rtsp_url,
            r.redacted_rtsp_url,
            r.codec,
            r.enabled,
            r.sampling_fps,
            r.lifecycle,
            r.revision,
        )

    @staticmethod
    def _record(row: tuple[Any, ...]) -> CameraRecord:
        return CameraRecord(*row)


def connect_postgres(dsn: str) -> Connection:
    try:
        psycopg = import_module("psycopg")
    except ModuleNotFoundError as error:
        raise RuntimeError("psycopg is required for PostgreSQL camera persistence") from error
    return cast(Connection, psycopg.connect(dsn))
