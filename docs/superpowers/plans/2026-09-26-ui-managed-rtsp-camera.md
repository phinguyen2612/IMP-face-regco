# UI-managed RTSP Camera Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let operators create, test, persist, activate, and monitor RTSP cameras through React without exposing credentials or using process command arguments.

**Architecture:** Add a camera application service with public/secret contracts and a PostgreSQL repository boundary. Preserve the existing `VideoFrame` and camera state abstractions; add an in-process GStreamer backend with injected bindings. Deliver active revisions through an internal worker client and expose only redacted public/runtime DTOs.

**Tech Stack:** FastAPI, Pydantic, psycopg 3, Fernet, React/TypeScript, GStreamer Python bindings.

**Spec:** User-provided `CORRECTION - RTSP IS UI-MANAGED CONFIGURATION` dated 2026-09-26.

## Global Constraints

- RTSP credentials never appear in GET/WebSocket/log/metric/exception/process arguments.
- Camera configuration follows draft -> activate -> worker-applied revision.
- PostgreSQL persists public config and protected secret separately.
- GStreamer runs in-process and outputs canonical `VideoFrame` values.
- CPU software decode is valid; NVIDIA elements are optional.
- Automated tests use injected repositories/bindings and require no real camera.

## Review Focus

- Credential replacement versus unchanged-secret edit behavior.
- Secret redaction for encoded usernames/passwords and malformed URLs.
- Active revision delivery without exposing secrets on public endpoints.
- Config replacement/reconnect creates a new stream session and clears scoped state.
- Missing GStreamer/PostgreSQL dependencies fail truthfully without breaking public API startup.

### Task 1: Camera contracts, secret boundary, and API lifecycle

**Files:** Create `apps/control-api/src/control_api/cameras.py`; modify `main.py`; test `apps/control-api/tests/test_cameras.py`.

- [ ] Write failing CRUD/redaction/edit/activation tests and run them RED.
- [ ] Implement public/request/internal DTOs, repository protocol, protected secret service, and camera service.
- [ ] Add injectable API routes and run tests GREEN.

### Task 2: PostgreSQL camera repository

**Files:** Create `apps/control-api/src/control_api/camera_postgres.py`; modify `pyproject.toml`; test `apps/control-api/tests/test_camera_postgres.py`.

- [ ] Write failing repository contract tests against an injected DB connection.
- [ ] Implement schema/upsert/read/revision persistence with lazy psycopg import.
- [ ] Verify repository tests and document required backend settings.

### Task 3: In-process GStreamer and worker delivery

**Files:** Create `workers/vision-worker/src/vision_worker/video/gstreamer_inprocess.py` and `camera_config.py`; modify worker startup; add worker tests.

- [ ] Write RED tests proving URL is set as an object property, never argv/log text.
- [ ] Implement injected in-process GStreamer appsink backend and safe error categories.
- [ ] Implement active-config fetch/apply boundary and replacement/session-reset tests.

### Task 4: React Camera page

**Files:** Create `apps/web/src/features/cameras/*`; modify API contracts/client and `App.tsx`.

- [ ] Add typed client/form behavior for list/create/edit/test/activate/runtime.
- [ ] Ensure saved credentials are never cached or redisplayed.
- [ ] Run TypeScript typecheck and production build.

### Task 5: Verification

- [ ] Run Python unit/contract suite, Ruff, mypy, frontend build.
- [ ] Run secret scans over API/WS responses and process construction.
- [ ] Report camera readiness separately from model-artifact readiness.
