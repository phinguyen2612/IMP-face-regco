import json
from typing import Any

from control_api.model_postgres import PostgresModelRepository, initialize_model_schema
from fr_domain.model_management import ArtifactFormat, ModelType, ModelVersion
from test_model_domain import person_manifest


class Cursor:
    def __init__(self, connection: "Connection") -> None:
        self.connection = connection

    def __enter__(self) -> "Cursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.connection.executed.append((query, params))

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self.connection.rows)

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.connection.rows[0] if self.connection.rows else None


class Connection:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.rows: list[tuple[Any, ...]] = []
        self.commits = 0

    def cursor(self) -> Cursor:
        return Cursor(self)

    def commit(self) -> None:
        self.commits += 1


def test_model_schema_contains_separate_metadata_and_assignment_tables() -> None:
    connection = Connection()
    initialize_model_schema(connection)  # type: ignore[arg-type]
    sql = connection.executed[0][0]
    assert "model_definitions" in sql
    assert "model_versions" in sql
    assert "model_artifacts" in sql
    assert "model_deployments" in sql
    assert "model_assignments" in sql
    assert connection.commits == 1


def test_model_assignment_round_trips_through_repository_boundary() -> None:
    connection = Connection()
    repository = PostgresModelRepository(connection)  # type: ignore[arg-type]
    repository.put_assignment(ModelType.PERSON_DETECTOR, "deployment-1")
    assert connection.executed[-1][1] == ("PERSON_DETECTOR", "deployment-1")
    connection.rows = [("PERSON_DETECTOR", "deployment-1")]
    assert repository.list_assignments() == {ModelType.PERSON_DETECTOR: "deployment-1"}


def test_put_version_serializes_pydantic_manifest_without_cycle() -> None:
    connection = Connection()
    repository = PostgresModelRepository(connection)  # type: ignore[arg-type]
    version = ModelVersion.create(
        "definition-1",
        "v1",
        "artifact-1",
        ArtifactFormat.ONNX,
        "a" * 64,
        123,
        person_manifest(),
    )

    repository.put_version(version)

    params = connection.executed[-1][1]
    assert params is not None
    payload = json.loads(str(params[-1]))
    assert payload["manifest"]["model_type"] == "PERSON_DETECTOR"
    assert payload["manifest"]["inputs"][0]["name"] == "images"
