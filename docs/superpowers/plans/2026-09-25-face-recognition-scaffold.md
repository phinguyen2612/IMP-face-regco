# Face Recognition Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a runnable Face Recognition-only monorepo scaffold with shared contracts, validated configuration, a FastAPI API, a stub vision worker, and a React shell.

**Architecture:** Keep video and track-local state in one vision-worker process while the FastAPI control plane owns configuration and business APIs. External systems and real inference are represented by narrow interfaces with deterministic local stubs.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, React, TypeScript, Vite.

**Spec:** `docs/superpowers/specs/2026-09-25-face-recognition-design.md`

## Global Constraints

- Face Recognition only.
- No model downloads, production credentials, or invented RTSP URLs.
- Track identity uses `(camera_id, stream_session_id, track_id)`.
- Multi-frame verification is mandatory.
- MVP track state remains in process.

## Review Focus

- Invalid verification frame bounds must be rejected.
- Invalid brightness bounds must be rejected.
- A single observation must never verify an identity.
- Stub adapters must be deterministic and must not access hardware or the network.
- API startup must not require PostgreSQL, Redis, RTSP, or model artifacts.

---

### Task 1: Domain, configuration, and message contracts

**Files:** shared package modules and `tests/unit/test_config.py`, `tests/unit/test_verification.py`.

**Interfaces:** Produces `FaceRecognitionConfig`, `TrackKey`, recognition states,
candidate observations, and `QualityWeightedVerifier` for the worker and API.

- [ ] Write configuration and verification behavior tests.
- [ ] Run the tests and confirm imports/behavior fail before implementation.
- [ ] Implement minimal Pydantic models and verifier.
- [ ] Run tests and confirm they pass.

### Task 2: Worker interfaces and deterministic stubs

**Files:** `workers/vision-worker/src/vision_worker/**` and worker tests.

**Interfaces:** Consumes shared domain/config contracts. Produces detector, tracker,
embedder, vector-store, and blob-storage protocols plus stub implementations.

- [ ] Write stub pipeline behavior tests.
- [ ] Confirm the tests fail because worker modules do not exist.
- [ ] Implement the protocols, stubs, worker app, and one-cycle CLI.
- [ ] Run worker tests and the CLI smoke command.

### Task 3: FastAPI control-plane skeleton

**Files:** `apps/control-api/src/control_api/**` and API tests.

**Interfaces:** Consumes `FaceRecognitionConfig`; produces health, model catalog,
configuration validation, and WebSocket status contracts.

- [ ] Write endpoint behavior tests.
- [ ] Confirm imports/routes fail before implementation.
- [ ] Implement the application factory and routes without external startup dependencies.
- [ ] Run API tests and import/startup smoke checks.

### Task 4: React shell and repository infrastructure

**Files:** `apps/web/**`, `packages/contracts/**`, configuration examples,
infrastructure documentation, and cross-package smoke tests.

**Interfaces:** Consumes the REST/WebSocket envelope shapes and documents external
adapter boundaries without implementing production infrastructure.

- [ ] Add the Vite/React TypeScript shell and contract types.
- [ ] Add example configuration and infrastructure boundary documentation.
- [ ] Run frontend typecheck/build when Node.js is available.
- [ ] Run the complete Python test and lint suites.
