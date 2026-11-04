import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from importlib import import_module
from threading import RLock
from typing import Any, Protocol, cast

from control_api.cameras import CameraRecord, CameraRevisionConflict


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
);
CREATE TABLE IF NOT EXISTS camera_source_settings (
    camera_id text PRIMARY KEY REFERENCES cameras(id) ON DELETE CASCADE,
    source_type text NOT NULL CHECK (source_type IN ('rtsp','webcam'))
);
CREATE TABLE IF NOT EXISTS camera_source_configs (
    camera_id text PRIMARY KEY REFERENCES cameras(id) ON DELETE CASCADE,
    source_type text NOT NULL CHECK (source_type IN ('rtsp','local_webcam','webcam')),
    device_index integer CHECK (device_index BETWEEN 0 AND 63),
    CHECK ((source_type='local_webcam' AND device_index IS NOT NULL)
        OR (source_type<>'local_webcam' AND device_index IS NULL))
);
CREATE TABLE IF NOT EXISTS camera_monitoring_settings (
    camera_id text PRIMARY KEY REFERENCES cameras(id) ON DELETE CASCADE,
    display_fps double precision NOT NULL DEFAULT 15 CHECK(display_fps > 0 AND display_fps <= 30),
    roi_polygon jsonb NOT NULL DEFAULT '[]'::jsonb,
    attendance_enabled boolean NOT NULL DEFAULT true,
    evidence_retention_days integer NOT NULL DEFAULT 30
      CHECK(evidence_retention_days BETWEEN 1 AND 3650)
);
ALTER TABLE camera_source_configs DROP CONSTRAINT IF EXISTS camera_source_configs_source_type_check;
ALTER TABLE camera_source_configs ADD CONSTRAINT camera_source_configs_source_type_check
 CHECK (source_type IN ('rtsp','local_webcam','webcam','droidcam'));
ALTER TABLE camera_monitoring_settings ADD COLUMN IF NOT EXISTS unknown_alert_frames
 integer NOT NULL DEFAULT 5 CHECK(unknown_alert_frames BETWEEN 2 AND 60);
INSERT INTO camera_source_configs (camera_id,source_type)
 SELECT camera_id,source_type FROM camera_source_settings ON CONFLICT DO NOTHING;
"""


def initialize_camera_schema(connection: Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(CAMERA_SCHEMA_SQL)
    connection.commit()


_COLUMNS = (
    "id,name,protected_rtsp_url,redacted_rtsp_url,codec,enabled,sampling_fps,lifecycle,revision"
)
_PUBLIC_COLUMNS = ",".join(f"c.{column}" for column in _COLUMNS.split(","))
_READ_SOURCE = (
    f"SELECT {_PUBLIC_COLUMNS},coalesce(s.source_type,'rtsp'),s.device_index,"
    "coalesce(m.display_fps,15),coalesce(m.roi_polygon,'[]'::jsonb),"
    "coalesce(m.attendance_enabled,true),coalesce(m.evidence_retention_days,30),"
    "coalesce(m.unknown_alert_frames,5) "
    "FROM cameras c LEFT JOIN camera_source_configs s ON s.camera_id=c.id "
    "LEFT JOIN camera_monitoring_settings m ON m.camera_id=c.id "
)


class PostgresCameraRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection
        self._lock = RLock()

    @contextmanager
    def _transaction(self) -> Iterator[Cursor]:
        with self._lock:
            try:
                with self._connection.cursor() as cursor:
                    yield cursor
                self._connection.commit()
            except Exception:
                rollback = getattr(self._connection, "rollback", None)
                if callable(rollback):
                    rollback()
                raise

    def put(self, record: CameraRecord, expected_revision: str | None = None) -> None:
        with self._transaction() as cursor:
            if expected_revision is not None:
                cursor.execute("SELECT revision FROM cameras WHERE id=%s FOR UPDATE", (record.id,))
                row = cursor.fetchone()
                if row is None or row[0] != expected_revision:
                    raise CameraRevisionConflict("CAMERA_REVISION_CONFLICT")
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
            cursor.execute(
                "INSERT INTO camera_source_configs (camera_id,source_type,device_index) "
                "VALUES (%s,%s,%s) ON CONFLICT(camera_id) DO UPDATE SET "
                "source_type=EXCLUDED.source_type,device_index=EXCLUDED.device_index",
                (record.id, record.source_type, record.device_index),
            )
            cursor.execute(
                "INSERT INTO camera_monitoring_settings "
                "(camera_id,display_fps,roi_polygon,attendance_enabled,"
                "evidence_retention_days,unknown_alert_frames) "
                "VALUES(%s,%s,%s::jsonb,%s,%s,%s) ON CONFLICT(camera_id) DO UPDATE SET "
                "display_fps=EXCLUDED.display_fps,roi_polygon=EXCLUDED.roi_polygon,"
                "attendance_enabled=EXCLUDED.attendance_enabled,evidence_retention_days=EXCLUDED.evidence_retention_days,"
                "unknown_alert_frames=EXCLUDED.unknown_alert_frames",
                (
                    record.id,
                    record.display_fps,
                    json.dumps(record.roi_polygon),
                    record.attendance_enabled,
                    record.evidence_retention_days,
                    record.unknown_alert_frames,
                ),
            )

    def get(self, camera_id: str) -> CameraRecord | None:
        with self._transaction() as cursor:
            cursor.execute(_READ_SOURCE + "WHERE c.id=%s", (camera_id,))
            row = cursor.fetchone()
        return self._record(row) if row else None

    def delete(self, camera_id: str, expected_revision: str) -> None:
        try:
            with self._transaction() as cursor:
                cursor.execute("SELECT revision FROM cameras WHERE id=%s FOR UPDATE", (camera_id,))
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(camera_id)
                if row[0] != expected_revision:
                    raise CameraRevisionConflict("CAMERA_REVISION_CONFLICT")
                cursor.execute("DELETE FROM cameras WHERE id=%s", (camera_id,))
        except Exception as error:
            if getattr(error, "sqlstate", None) == "23503":
                raise ValueError("CAMERA_IN_USE_BY_CLASS_SESSION") from error
            raise

    def list(self) -> list[CameraRecord]:
        with self._transaction() as cursor:
            cursor.execute(_READ_SOURCE + "ORDER BY c.name,c.id")
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


class PersistentPostgresConnection:
    """Replace a lost connection at the next operation, never replay a transaction."""

    def __init__(self, connector: Callable[[], Any]) -> None:
        self._connector = connector
        self._connection = connector()
        self._lock = RLock()
        self._closed = False
        self._transaction_depth = 0

    def _ready(self) -> Any:
        with self._lock:
            if self._closed:
                raise RuntimeError("POSTGRES_CONNECTION_CLOSED")
            if self._connection.closed and not self._transaction_depth:
                self._connection = self._connector()
            return self._connection

    def cursor(self) -> Any:
        return self._ready().cursor()

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        with self._lock:
            connection = self._ready()
            self._transaction_depth += 1
            try:
                with connection.transaction() as transaction:
                    yield transaction
            finally:
                self._transaction_depth -= 1

    def commit(self) -> None:
        # A lost commit has an unknown outcome. Reconnecting here would falsely
        # report success for a different, empty transaction.
        self._connection.commit()

    def rollback(self) -> None:
        if not self._connection.closed:
            self._connection.rollback()

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._connection.close()


def connect_persistent_postgres(dsn: str) -> Connection:
    return PersistentPostgresConnection(lambda: connect_postgres(dsn))
