import os
from pathlib import Path

from control_api.camera_postgres import connect_postgres
from control_api.model_artifacts import (
    LocalModelArtifactStorage,
    ModelArtifactIngestor,
    OnnxArtifactInspector,
)
from control_api.model_postgres import PostgresModelRepository, initialize_model_schema
from control_api.model_registry import (
    InMemoryModelRepository,
    ModelRegistryService,
    ModelRepository,
)


def build_model_registry() -> ModelRegistryService:
    root = Path(os.getenv("FR_MODEL_ARTIFACT_ROOT", "data/models"))
    maximum = int(os.getenv("FR_MODEL_MAX_UPLOAD_BYTES", str(512 * 1024 * 1024)))
    dsn = os.getenv("FR_POSTGRES_DSN")
    if dsn:
        connection = connect_postgres(dsn)
        initialize_model_schema(connection)
        repository: ModelRepository = PostgresModelRepository(connection)
    else:
        repository = InMemoryModelRepository()
    return ModelRegistryService(
        repository,
        ModelArtifactIngestor(
            LocalModelArtifactStorage(root),
            OnnxArtifactInspector(),
            maximum,
        ),
    )
