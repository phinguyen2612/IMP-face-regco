"""Database-backed checks must leave the ASGI event loop free for frame uploads."""

import asyncio
from io import BytesIO
from threading import get_ident
from types import SimpleNamespace

import httpx
from control_api.auth_domain import Principal
from control_api.browser_stream import BrowserStreamStore
from control_api.browser_stream_api import create_browser_stream_router
from control_api.main import BrowserAuthBoundary
from fastapi import FastAPI
from PIL import Image


def test_auth_database_checks_run_outside_the_event_loop() -> None:
    async def exercise():
        loop_thread = get_ident()
        checks = []

        class Auth:
            def resolve_session(self, token):
                assert get_ident() != loop_thread
                checks.append("session")
                return Principal("admin", "admin@example.test", "ADMIN")

            def verify_csrf(self, csrf, token):
                assert get_ident() != loop_thread
                checks.append("csrf")
                return True

        app = FastAPI()
        app.add_middleware(BrowserAuthBoundary, auth=Auth())

        @app.post("/api/v1/probe")
        async def probe():
            return {"ok": True}

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver",
        ) as client:
            response = await client.post("/api/v1/probe", headers={"Origin": "http://testserver"})
            assert response.status_code == 200
        assert checks == ["session", "csrf"]

    asyncio.run(exercise())


def test_webcam_upload_database_checks_run_outside_the_event_loop() -> None:
    async def exercise():
        loop_thread = get_ident()

        def require(camera_id):
            assert get_ident() != loop_thread
            return SimpleNamespace(source_type="webcam", lifecycle="ACTIVE", enabled=True,
                                   revision="r1")

        def revision(camera_id):
            assert get_ident() != loop_thread
            return "r1"

        store = BrowserStreamStore(revision_resolver=revision)
        app = FastAPI()
        app.include_router(create_browser_stream_router(SimpleNamespace(require=require), store,
                                                        "worker"))
        output = BytesIO()
        Image.new("RGB", (64, 48), "gray").save(output, format="JPEG")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver",
        ) as client:
            session = await client.post("/api/v1/cameras/camera/webcam/session")
            assert session.status_code == 201
            response = await client.post(
                "/api/v1/cameras/camera/webcam/frames", content=output.getvalue(),
                headers={"X-Webcam-Token": session.json()["token"]},
            )
            assert response.status_code == 200
            assert response.json()["sequence"] == 1

    asyncio.run(exercise())
