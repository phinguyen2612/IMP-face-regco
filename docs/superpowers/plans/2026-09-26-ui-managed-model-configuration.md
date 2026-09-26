# UI-Managed Model Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build a UI-managed, persistence-ready model registry and deployment path for the three face-recognition model roles without claiming unavailable real inference.

**Architecture:** FastAPI owns model metadata and immutable artifact ingestion; worker infrastructure owns deterministic runtime resolution and atomic prepared-runtime swap. React provides operator-safe upload, deployment, assignment, and readiness views.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, PostgreSQL/psycopg, local filesystem artifacts, React/TypeScript/Vitest.

**Spec:** docs/superpowers/specs/2026-09-26-ui-managed-model-configuration-design.md

## Global Constraints

- ONNX is the portable baseline; NVIDIA dependencies remain optional.
- No uploaded artifact path is client-controlled or returned publicly.
- Explicit accelerated backends never silently fall back.
- Invalid artifacts/versions cannot deploy or activate.
- Production activation never substitutes mock inference.
- Face-embedding compatibility changes require index rebuild state.
- Normal CI requires no camera, GPU, or production model.

## Review Focus

- Multipart upload interrupted/oversized: no partial immutable artifact remains.
- Concurrent activation attempts: exactly one active deployment per model role.
- Worker unavailable during activation: previous deployment remains active.
- Duplicate version/checksum and retry: immutable, idempotent outcome without overwrite.
- Malicious filename/manifest/path content: cannot escape artifact root or expose internal paths.

---

### Task 1: Domain and manifest contracts

**Files:** Create model domain/service modules and tests; update manifest schema and config references.

**Interfaces:** Produces ModelDefinition, ModelVersion, ModelDeployment, ModelManifest, EmbeddingCompatibility.

- [ ] Write failing validation/immutability/compatibility tests and run RED.
- [ ] Implement strict enums and contracts; run GREEN.

### Task 2: Immutable artifact storage and upload validation

**Files:** Create model artifact storage/ONNX inspector modules and security tests.

**Interfaces:** Produces ModelArtifactStorage.store(bytes, identity) and inspector.validate(bytes, manifest).

- [ ] Write failing checksum, size/type, traversal, and immutable-write tests; run RED.
- [ ] Implement generated-root local storage, SHA-256, bounded upload, injectable ONNX inspection; run GREEN.

### Task 3: Runtime resolver and atomic activation

**Files:** Create worker runtime capability/resolver/lifecycle modules and tests.

**Interfaces:** Produces InferenceRuntimeResolver.resolve(deployment, artifacts, capabilities) and AtomicModelSet.activate(prepared).

- [ ] Write failing AUTO/strict/warmup/retain-previous/cache tests; run RED.
- [ ] Implement deterministic resolution, typed failures, prepared runtime lifecycle, bounded cache; run GREEN.

### Task 4: Repository, PostgreSQL migration, and API

**Files:** Create model repository/PostgreSQL adapter, migration, FastAPI routes, API tests.

**Interfaces:** Produces public CRUD/version/upload/validate/deploy/activate/runtime plus authenticated internal deployment snapshot/result endpoints.

- [ ] Write failing API/repository/activation/deletion-protection tests; run RED.
- [ ] Implement in-memory and PostgreSQL metadata repositories and routes; run GREEN.

### Task 5: Worker delivery and production wiring

**Files:** Create deployment provider/synchronizer/adapter factory boundary; modify worker construction and tests.

**Interfaces:** Consumes active deployment snapshots; produces revision-aware prepared adapters and safe runtime status.

- [ ] Write failing hot-reload/no-production-mock/status/index-invalidation tests; run RED.
- [ ] Implement fail-closed adapter resolution and atomic swap orchestration; run GREEN.

### Task 6: React Models, assignment, and readiness

**Files:** Extend API contracts/client, add ModelsPanel tests/component, integrate App.

**Interfaces:** Consumes public model/deployment/runtime DTOs; never consumes artifact paths or raw embeddings.

- [ ] Write failing upload/deploy/assignment/readiness/error-state tests; run RED.
- [ ] Implement operator-safe model cards/forms and pipeline readiness; run GREEN.
- [ ] Run Ruff, mypy, pytest, Vitest, TypeScript build, and service smoke tests.
