from control_api.camera_postgres import PostgresCameraRepository, initialize_camera_schema
from control_api.cameras import CameraRecord


class Cursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []

    def execute(self, sql, params=()):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


class Connection:
    def __init__(self, rows=None):
        self.cursor_value = Cursor(rows)
        self.commits = 0

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1


def test_postgres_repository_persists_secret_separately_and_commits():
    db = Connection()
    repo = PostgresCameraRepository(db)
    record = CameraRecord(
        "cam-1",
        "Entrance",
        b"encrypted",
        "rtsp://***:***@camera/stream",
        "AUTO",
        True,
        5.0,
        "ACTIVE",
        "rev-1",
    )
    repo.put(record)
    sql, params = db.cursor_value.executed[0]
    assert "camera_secrets" not in sql
    assert b"encrypted" in params
    assert "password" not in str(params)
    assert db.commits == 1


def test_postgres_repository_reads_record():
    row = (
        "cam-1",
        "Entrance",
        b"encrypted",
        "rtsp://***:***@camera/stream",
        "AUTO",
        True,
        5.0,
        "ACTIVE",
        "rev-1",
    )
    repo = PostgresCameraRepository(Connection([row]))
    assert repo.get("cam-1") == CameraRecord(*row)


def test_schema_initializer_executes_and_commits() -> None:
    db = Connection()
    initialize_camera_schema(db)
    sql, params = db.cursor_value.executed[0]
    assert "CREATE TABLE IF NOT EXISTS cameras" in sql
    assert params == ()
    assert db.commits == 1
