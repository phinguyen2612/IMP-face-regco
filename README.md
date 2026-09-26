# Face Recognition Platform

Greenfield scaffold for a configurable, track-based, real-time face recognition system.
The repository is intentionally limited to Face Recognition.

## Applications

- `apps/control-api`: FastAPI control plane and public contracts.
- `workers/vision-worker`: portable runtime, deployment resolver, and explicit test-only stubs.
- `apps/web`: React/Vite configuration and status shell.
- `packages/python`: domain, configuration, and messaging contracts.

## Quick start

Create a Python virtual environment and install the workspace:

```bash
python -m venv .venv
.venv/Scripts/activate
python -m pip install -e ".[dev,cpu]"
```

Start local PostgreSQL and Redis (optional for the current dependency-free runtime):

```bash
docker compose --env-file infrastructure/local/.env.example \
  -f infrastructure/local/compose.yaml up -d --wait
```

Run the API:

```bash
python -m uvicorn control_api.main:app --reload
```

Run the worker smoke cycle:

```bash
python -m vision_worker.main --once
```

Run the camera pipeline after supplying enabled camera and feature JSON files with a
real RTSP URL. Configured camera execution fails clearly until real detector and BoT-SORT adapters are installed; it never silently uses mocks:

```bash
python -m vision_worker.main \
  --camera-config path/to/camera.json \
  --feature-config path/to/face-recognition.json \
  --status-url http://127.0.0.1:8000/api/v1/runtime/status
```

Run tests:

```bash
python -m pytest
python -m ruff check .
python -m mypy apps/control-api/src workers/vision-worker/src packages/python
```

The frontend requires Node.js and npm:

```bash
cd apps/web
npm ci
npm run typecheck
npm run build
npm run dev
```

Runtime status is read from `GET /api/v1/runtime/status`, submitted by a worker to
`PUT /api/v1/runtime/status`, and included as `runtime.status` messages on
`/api/v1/ws`.

UI-owned camera/ROI and face-recognition behavior live in the versioned models under
`fr_config.models`. Service URLs, evidence paths, worker identity, and low-level
GStreamer decoder selection live separately in `fr_config.runtime.RuntimeSettings`.

No model artifact, production RTSP URL, or production credential is included.

## UI-managed models

Normal model changes use the browser and Control API rather than source files or model-path
environment variables:

1. Open **Models** and create the YOLO, SCRFD, or AdaFace logical model.
2. Upload an immutable `.onnx` version. The API parses the ONNX graph, validates the
   manifest tensor names, computes SHA-256, and stores the artifact outside PostgreSQL.
3. Create and activate a deployment using `AUTO`, `ONNX_CPU`, `ONNX_CUDA`, or `TENSORRT`.
   Explicit accelerated backends fail when unavailable; only `AUTO` can fall back.
4. After the worker reports a loaded, warmed, healthy deployment, assign it to the matching
   recognition role. Readiness remains `NOT_READY` while a role or vector index is missing.

Model artifacts default to `data/models`; set backend-only `FR_MODEL_ARTIFACT_ROOT` to
change the controlled storage root. Set `FR_MODEL_MAX_UPLOAD_BYTES` to cap uploads.
`FR_POSTGRES_DSN` enables PostgreSQL metadata/assignment persistence. The internal worker
model-delivery endpoint requires `FR_WORKER_INTERNAL_TOKEN`.

The CPU profile installs ONNX Runtime CPU. CUDA and TensorRT remain optional boundaries;
they are never imported or required for CPU startup. This repository does not ship or
download production YOLO, SCRFD, or AdaFace artifacts.
