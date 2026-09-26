import asyncio
import os

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request, WebSocket
from fastapi import status as http_status
from fastapi.exceptions import RequestValidationError
from fr_config.models import CameraConfig, FaceRecognitionConfig
from fr_contracts.messages import MessageEnvelope
from fr_contracts.runtime_status import RuntimeStatus
from pydantic import BaseModel
from starlette.responses import JSONResponse

from control_api.camera_bootstrap import build_camera_persistence
from control_api.cameras import (
    ActiveCameraConfig,
    CameraCreate,
    CameraPublic,
    CameraService,
    CameraUpdate,
)
from control_api.model_api import create_model_router
from control_api.model_bootstrap import build_model_registry
from control_api.model_registry import ModelRegistryService
from control_api.runtime_status import InMemoryRuntimeStatusStore, RuntimeStatusStore


class ValidationResponse(BaseModel):
    valid: bool
    config: FaceRecognitionConfig


class RuntimeStatusResponse(BaseModel):
    items: list[RuntimeStatus]


def create_app(
    runtime_status_store: RuntimeStatusStore | None = None,
    camera_service: CameraService | None = None,
    internal_camera_token: str | None = None,
    model_registry_service: ModelRegistryService | None = None,
) -> FastAPI:
    status_store = runtime_status_store or InMemoryRuntimeStatusStore()
    if camera_service is None:
        persistence = build_camera_persistence()
        cameras = persistence.service
        persistence_mode = persistence.mode
    else:
        cameras = camera_service
        persistence_mode = "injected"
    worker_token = internal_camera_token or os.getenv("FR_WORKER_INTERNAL_TOKEN")
    models = model_registry_service or build_model_registry()
    app = FastAPI(
        title="Face Recognition Control API",
        version="0.1.0",
        description="Configuration-first control plane; inference adapters are stubbed.",
    )
    api = APIRouter(prefix="/api/v1")

    @app.exception_handler(RequestValidationError)
    async def safe_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        del request, error
        return JSONResponse(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "request validation failed",
                "error_category": "VALIDATION_ERROR",
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "service": "face-recognition-control-api",
            "status": "ok",
            "external_dependencies": "configured"
            if persistence_mode == "postgresql"
            else "optional",
            "camera_persistence": persistence_mode,
        }

    @api.post("/face-recognition/configs/validate", response_model=ValidationResponse)
    def validate_config(config: FaceRecognitionConfig) -> ValidationResponse:
        return ValidationResponse(valid=True, config=config)

    @api.post("/cameras/validate", response_model=CameraConfig)
    def validate_camera_config(config: CameraConfig) -> CameraConfig:
        return config

    @api.post("/cameras", response_model=CameraPublic, status_code=http_status.HTTP_201_CREATED)
    def create_camera(request: CameraCreate) -> CameraPublic:
        return cameras.create(request)

    @api.get("/cameras")
    def list_cameras() -> dict[str, list[CameraPublic]]:
        return {"items": cameras.public_list()}

    @api.get("/cameras/{camera_id}", response_model=CameraPublic)
    def get_camera(camera_id: str) -> CameraPublic:
        try:
            return cameras.get_public(camera_id)
        except KeyError as error:
            raise HTTPException(404, "camera not found") from error

    @api.patch("/cameras/{camera_id}", response_model=CameraPublic)
    def update_camera(camera_id: str, request: CameraUpdate) -> CameraPublic:
        try:
            return cameras.update(camera_id, request)
        except KeyError as error:
            raise HTTPException(404, "camera not found") from error

    @api.post("/cameras/{camera_id}/test-connection")
    def test_camera(camera_id: str) -> object:
        try:
            return cameras.test_connection(camera_id)
        except KeyError as error:
            raise HTTPException(404, "camera not found") from error

    @api.post("/cameras/{camera_id}/activate", response_model=CameraPublic)
    def activate_camera(camera_id: str) -> CameraPublic:
        try:
            return cameras.activate(camera_id)
        except KeyError as error:
            raise HTTPException(404, "camera not found") from error

    @api.get("/internal/cameras/active")
    def active_cameras(
        x_worker_token: str | None = Header(default=None),
    ) -> dict[str, list[ActiveCameraConfig]]:
        if worker_token is None or x_worker_token != worker_token:
            raise HTTPException(403, "worker authorization required")
        return {"items": cameras.active_list()}

    @api.get("/cameras/{camera_id}/runtime", response_model=RuntimeStatusResponse)
    def camera_runtime(camera_id: str) -> RuntimeStatusResponse:
        try:
            cameras.require(camera_id)
        except KeyError as error:
            raise HTTPException(404, "camera not found") from error
        return RuntimeStatusResponse(
            items=[item for item in status_store.list() if item.camera_id == camera_id]
        )

    @api.get("/runtime/status", response_model=RuntimeStatusResponse)
    def runtime_status() -> RuntimeStatusResponse:
        return RuntimeStatusResponse(items=status_store.list())

    @api.put("/runtime/status", response_model=RuntimeStatus)
    def update_runtime_status(status: RuntimeStatus) -> RuntimeStatus:
        status_store.update(status)
        return status

    @api.websocket("/ws")
    async def websocket_status(websocket: WebSocket) -> None:
        await websocket.accept()
        message = MessageEnvelope(type="system.ready", payload={"mode": "scaffold"})
        await websocket.send_json(message.model_dump(mode="json"))
        sent: dict[tuple[str, str], str] = {}
        while True:
            for status in status_store.list():
                key = (status.worker_id, status.camera_id)
                serialized = status.model_dump_json()
                if sent.get(key) == serialized:
                    continue
                status_message = MessageEnvelope(
                    type="runtime.status",
                    camera_id=status.camera_id,
                    payload=status.model_dump(mode="json"),
                )
                await websocket.send_json(status_message.model_dump(mode="json"))
                sent[key] = serialized
            await asyncio.sleep(0.05)

    app.include_router(api)
    app.include_router(create_model_router(models, worker_token))
    return app


app = create_app()
