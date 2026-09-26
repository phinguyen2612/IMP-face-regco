# Phase 10 - Production Hardening and End-to-End Validation

**Status:** Proposed design only
**Scope:** Face Recognition only
**Gate:** No product implementation before `APPROVE PHASE 10 DESIGN`.

## Decision and evidence policy

Phase 10 is an evidence program, not a feature phase. The recommended approach is a layered validation harness around production-equivalent components: deterministic fixtures for correctness, controlled dependency proxies/fakes for failure injection, process-level restart tests, a separate soak runner, and a versioned release report. Tests must retain their real level (`UNIT`, `CONTRACT`, `INTEGRATION`, `E2E`, `HARDWARE`, `SOAK`, or `BENCHMARK`).

Alternatives considered:

1. **Layered evidence harness - selected.** It isolates failures while retaining a real process-level E2E lane and produces reproducible release evidence.
2. **One giant Docker E2E suite.** Useful as one lane, but insufficient alone: failures are hard to localize and GPU/camera dependencies make it brittle.
3. **Manual checklist/demo.** Rejected as the primary mechanism because it is not repeatable and cannot detect regressions or resource growth.

Coverage and outcome are separate. Coverage is `TESTED`, `PARTIALLY TESTED`, `NOT TESTED`, or `NOT AVAILABLE IN CURRENT ENVIRONMENT`. Outcome is `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN`. Any failed or untested mandatory gate is `NO-GO`; a documented waiver never changes it to `PASS`.

## 1. System audit

The repository does not match the premise “functionally complete through Phase 9.” The checked-in worker executes GStreamer input, sampling, a mock person detector, a mock tracker, and in-memory track state. Face detection, alignment, embedding, FAISS, policy, events, persistence, runtime resolution, and evidence orchestration are absent or stubs. The API stores runtime status only in memory; PostgreSQL and Redis are declared in Compose/configuration but are not used by application code. The React app is a status/configuration shell.

Audit verification executed on 2026-09-26:

- `python -m pytest`: **PASS**, 52 tests.
- `python -m ruff check .`: **PASS**.
- `.venv/Scripts/python.exe -m mypy ...`: **PASS**, 38 source files.
- local Node `npm run build`: **PASS**, Vite production build.

These results validate the current scaffold/component surface only. They are not Face Recognition E2E, hardware, soak, or deployment evidence.

## 2. Feature validation matrix

`Tested` means an automated test exists and the current suite passed. `E2E Tested` requires a production-equivalent cross-component flow; no such test currently exists. `Hardware Tested` requires an executed physical-runtime test, not a mocked backend.

| Component | Implemented | Tested | E2E Tested | Hardware Tested | Notes |
|---|---|---|---|---|---|
| Camera ingestion | YES | YES | NO | NO | Source/reconnect with fake backend |
| GStreamer/video source | PARTIAL | YES | NO | NO | Command/read behavior mocked; no real stream result |
| YOLO | NO | PARTIAL | NO | NO | Interface/mock only |
| BoT-SORT | NO | PARTIAL | NO | NO | `MockTracker`, not BoT-SORT |
| ROI | PARTIAL | YES | NO | NOT APPLICABLE | Config validation only; no runtime gate |
| SCRFD | NO | PARTIAL | NO | NO | Interface/stub only |
| Quality gate | PARTIAL | YES | NO | NOT APPLICABLE | Config fields only |
| Alignment | NO | NO | NO | NOT APPLICABLE | Design document only |
| AdaFace | NO | PARTIAL | NO | NO | Stub embedder only |
| FAISS | NO | PARTIAL | NO | NO | `VectorStore`/stub only |
| Verification | PARTIAL | YES | NO | NOT APPLICABLE | Bounded verifier unit-tested, not live pipeline |
| Policy | PARTIAL | YES | NO | NOT APPLICABLE | Config models only |
| Events | NO | NO | NO | NOT APPLICABLE | README/design only |
| Evidence | PARTIAL | YES | NO | NO | Local blob round-trip only |
| PostgreSQL | NO | PARTIAL | NO | NO | Compose/DSN validation; no repository |
| Redis | NOT APPLICABLE | PARTIAL | NO | NO | Configured but unused by current runtime |
| REST | PARTIAL | YES | NO | NOT APPLICABLE | Validation/status scaffold only |
| WebSocket | PARTIAL | YES | NO | NOT APPLICABLE | Status push; no reconnect/reconcile |
| React UI | PARTIAL | YES | NO | NOT APPLICABLE | Build passes; monitoring shell only |
| ONNX CPU | NO | NO | NO | NO | No dependency/adapters/artifacts |
| ONNX CUDA | NO | NO | NO | NO | Design only |
| TensorRT | NO | NO | NO | NO | Design only |

## 3. Current test coverage

Existing tests cover strict configuration and ROI validation, enrollment entities, verifier basics, scheduler intervals/cache, track-store expiry, ring-buffer bounds, sampling, camera state/reconnect with fakes, shell-free GStreamer argument/read behavior, mock detection-to-tracking, HTTP runtime-status publication, local blob containment/CRUD, API contracts, and basic WebSocket status delivery.

No checked-in test exercises real video decoding, real model artifacts, real vector search, event/evidence lifecycle, PostgreSQL/Redis, multi-process recovery, UI browser behavior, hardware providers, or long-running resources.

## 4. Missing coverage and issue severity

**BLOCKER**

- Full CPU Face Recognition pipeline and approved artifacts do not exist.
- YOLO, BoT-SORT, SCRFD, AdaFace, FAISS, event persistence, and Phase 9 runtime resolver are not implemented.
- No production-equivalent E2E path can currently be run.

**CRITICAL**

- API `/health` reports `ok` without required recognition dependencies; worker `run_once` reports `ready` while using stubs.
- PostgreSQL is not authoritative because application persistence is absent; FAISS cannot be rebuilt.
- Technical inference/index failures have no live-path proof that they cannot become no-detection or `UNKNOWN`.

**MAJOR**

- No WebSocket reconnect/REST reconciliation, graceful shutdown protocol, bounded inference/evidence queues, restart suite, real camera recovery, or resource/soak evidence.
- Evidence storage lacks atomic-write, failure, retention, and metadata consistency semantics.

**MINOR**

- UI wording still describes a scaffold/Jetson-ready control plane and may mislead operators once real readiness states are introduced.

Fix priority is correctness, data/privacy integrity, recovery, leaks, portability, backpressure, observability, then UX.

## 5. E2E scenarios

Build a deterministic process-level harness using an approved local video fixture, real CPU model adapters/artifacts, temporary PostgreSQL, local storage, and the built web/API/worker. IDs are asserted across frame, camera, stream session, track, observation, identity decision, event, evidence, persistence, WebSocket, REST, and UI.

Mandatory cases:

1. **Known:** consistent candidates across multiple frames produce `VERIFIED`, the enabled known policy, one persisted event, evidence outcome, realtime message, and queryable UI state.
2. **Unknown:** sufficient valid, successful no-match searches produce `UNKNOWN`; dwell then policy may emit `UNKNOWN_PERSON`.
3. **Uncertain:** conflicting/margin-ambiguous valid observations produce `UNCERTAIN` and never an unknown-person event.
4. **Poor face:** structured quality rejection prevents embedding/search/event and increments a bounded reason metric.
5. **Outside ROI:** prevents expensive face processing while tracking continues.

The harness records fixture/artifact/config/index/build fingerprints and rejects mocks in the production-equivalent lane.

## 6. Failure scenarios

Inject faults through explicit test boundaries, disposable proxies, temporary directories, invalid fixture variants, and adapter test doubles outside production configuration. Cover camera loss, corrupt/short frames, model initialization and inference errors, unavailable CUDA/TensorRT, missing/corrupt/incompatible FAISS, PostgreSQL loss, evidence storage error/full condition, WebSocket loss, and queue saturation.

Every assertion includes domain non-conversion: model/index failures do not add verification observations and never create `UNKNOWN`; evidence failure leaves the committed event valid with evidence `FAILED`; database failure creates neither a falsely committed event nor evidence.

## 7. Recovery scenarios

For recoverable dependencies assert `healthy/ready -> degraded or unready -> bounded retry/backoff -> recovered -> ready`. Camera recovery creates a new `stream_session_id` and cannot reuse prior track/verification state. Database recovery preserves ordering/idempotency rules. Storage recovery retries only within declared bounds. WebSocket reconnect performs a REST snapshot reconciliation and deduplicates versioned messages. Runtime-provider failure follows Phase 9 strict/`auto` policy rather than ad hoc switching.

## 8. Restart scenarios

Restart worker, API, web, PostgreSQL, Redis only if actually required, and the complete stack. Verify configuration, people, enrollments, events, evidence metadata, and active revision metadata survive. FAISS is reloaded or rebuilt from one authoritative PostgreSQL snapshot, validated, warmed, and atomically activated before readiness. In-memory tracks/verification windows are intentionally discarded; recognition resumes with new session-scoped state. Assert no undocumented event duplication or loss.

## 9. Resource leak strategy

Take timestamped samples of RSS/private bytes, CPU, GPU memory when available, thread count, file/handle count where portable, DB pool usage, WebSocket clients, queue depths, frame-buffer bytes, active tracks, retained face samples/observations, evidence jobs, and encoder/model resources. Use warmup exclusion and trend analysis rather than one before/after number. Flag sustained positive slopes after workload reaches steady state and correlate with object/state counters.

Explicit cleanup assertions cover track expiry, reconnect/session replacement, index/model reload, evidence completion/failure, WebSocket disconnect, and shutdown. Raw frames, crops, NumPy/ORT buffers, FAISS query arrays, and GPU bindings must become unreachable at their ownership boundary.

## 10. Soak strategy

Create separate `15m`, `1h`, and `8h` profiles; reserve `24h` for release candidates/target deployments. Normal CI runs no long soak. Each profile declares input rate, resolution, identities/unknown mix, event/evidence rate, reconnect/fault schedule, queue capacities, resource ceilings, and permitted drop/latency behavior before execution.

Emit periodic schema-versioned JSON samples plus a final trend summary. A short soak is mandatory for Phase 10 completion. Eight-hour/24-hour claims remain `NOT RUN` until executed. Monotonic resource growth, unbounded state, hanging shutdown, or repeated recovery failure is a release blocker according to its impact.

## 11. CPU validation

CPU-only is the mandatory release lane: clean environment without NVIDIA packages, real ORT CPU models, real FAISS, file/camera input, all five E2E outcomes, events/evidence/persistence/realtime/UI, overload bounds, restart, failure semantics, short soak, and release-check. Performance may be lower, but recognition semantics remain unchanged. This lane is presently `NOT TESTED` because real adapters/artifacts and downstream runtime are absent.

## 12. NVIDIA validation

On each claimed NVIDIA class, probe actual providers, activate explicit ORT CUDA, compare domain outputs to CPU tolerances, run E2E/failure/restart/short-soak/benchmark profiles, and record driver/runtime/artifact metadata. `auto` selection and fallback are asserted separately. No suitable current hardware means `NOT TESTED` or, after a real probe, `NOT AVAILABLE IN CURRENT ENVIRONMENT`; it never means pass.

## 13. TensorRT validation

Only validate provisioned engines whose source checksum, TensorRT/CUDA/platform, compute capability, precision, profiles, and plugins match. Test explicit failure, `auto` fallback, correctness against CPU, repeated lifecycle cleanup, full E2E, and sustained resource behavior. Desktop results do not validate Jetson. Current repository status is `NOT TESTED` and `NOT IMPLEMENTED`, not “optional support.”

## 14. Performance validation

Reuse Phase 9 model benchmarks, then measure the whole flow: input/processed FPS, YOLO/SCRFD/AdaFace/FAISS/verification latency, time-to-decision, event commit, WebSocket publication, evidence completion, end-to-end p50/p95/p99, queue depth, drops, memory, and optional GPU utilization/thermal state. Results bind to hardware, configuration, artifacts, dataset, duration, and build. Hardware-specific budgets are declared before the run; no universal laptop limit is invented.

## 15. Recognition evaluation

When a documented dataset exists, evaluate disjoint enrollment, development/calibration, known-validation, and unknown-validation partitions. Report sample/identity counts, known acceptance, unknown rejection, false accept/reject counts and rates, uncertain rate, observations and time to decision, with confidence limitations. Until representative data exists, accuracy remains `NOT TESTED`; smoke fixtures cannot support accuracy claims.

## 16. Threshold evaluation

Provide an offline evaluator that sweeps similarity threshold, candidate margin, minimum good frames, consistency, and timeout against frozen embeddings/search results or a versioned evaluation corpus. Output curves/tables for human review. It never writes production configuration, declares an optimum, or changes runtime recognition logic. Calibration and evaluation partitions remain separate and every result records compatibility/calibration revision.

## 17. Health and readiness

Standardize lifecycle as `STARTING`, `HEALTHY`, `DEGRADED`, `UNHEALTHY`, `STOPPING`. Liveness answers whether the process/control loop responds. Readiness requires valid configuration, required dependencies, resolved/active/warmed models, compatible active index, camera policy satisfaction, and operational persistence/evidence boundaries according to declared requirements.

Component health includes reason codes and timestamps. Tests inject each failure and observe API, WebSocket, metrics, and UI transition plus recovery. `/health: ok` cannot imply recognition readiness; provide distinct liveness/readiness endpoints or an explicitly structured response.

## 18. Logging and privacy audit

Logs use structured bounded fields: correlation/event ID, camera ID, stream session, scoped track ID, component, model/runtime revision, backend, stable error category, and retry attempt where relevant. Redact RTSP/DB credentials and never log embeddings, image bytes, passwords, authorization data, or full local paths. Avoid per-frame INFO logs and person IDs in metrics. Tests capture representative failure logs and assert required context/redaction.

## 19. Deployment validation

Add schema-valid secret-free examples for CPU laptop and NVIDIA `auto` following existing JSON configuration conventions, with backend-only runtime values separate from UI config. Validate fresh install, migrations, dependency health, startup order/readiness, graceful stop, data/evidence volumes, and backup/restore of authoritative state. Prefer existing Compose plus documented commands over a monolithic script. One-command development startup may orchestrate infrastructure/API/worker/web but must surface individual failures and remain optional.

## 20. Release-check design

Provide one repository-native command that records versions and runs formatting/lint, mypy, Python unit/contract/integration tests, frontend typecheck/build, manifest/config validation, migration checks, CPU runtime smoke, and the short deterministic E2E lane. It excludes long soak, optional GPU/hardware, destructive failure tests, and full benchmarks. Missing mandatory prerequisites fails; it is never converted to skip. Output is human-readable plus schema-versioned JSON/JUnit references.

## 21. Release criteria

Mandatory gates are: clean CPU install; real CPU full pipeline; five E2E scenarios; correct failure non-conversion; camera reconnect; persistence and FAISS rebuild/restart; evidence failure semantics; WebSocket recovery/reconciliation; bounded queues/state; graceful shutdown; executed short soak without critical growth; release-check pass; truthful health/status/logging; and documentation matching the tested build.

NVIDIA/TensorRT gates are conditional only when the release claims those targets. Any BLOCKER/CRITICAL open issue, failed mandatory gate, or untested mandatory gate yields `NO-GO`. Waivers require owner, scope, impact, mitigation, expiry, and approval, and remain visible as risk rather than pass.

## 22. Known limitations

- The current codebase is a scaffold despite Phase 4–9 design documents.
- There are no approved executable models, validation dataset, real FAISS index, persistence repositories, event engine, or evidence workflow.
- GStreamer has no executed physical-camera evidence in this audit.
- Redis is not currently needed by code; do not manufacture a Redis dependency for validation.
- GPU and Jetson availability/performance are untested.
- Authentication/RBAC remains outside Face Recognition MVP core, but deployment/security review must prevent unintended exposure.
- Hardware budgets, numerical tolerances, retention, backup/restore objectives, and soak growth thresholds require project decisions before execution.

## 23. Expected files

```text
.agents/skills/production-validation-engineering/SKILL.md
docs/superpowers/specs/2026-09-26-phase-10-production-hardening-validation-design.md
tests/e2e/{fixtures,harness,scenarios}/
tests/integration/{postgres,faiss,evidence,realtime,runtime}/
tests/failure/{camera,models,index,database,storage,websocket}/
tests/restart/
tests/hardware/{cuda,tensorrt,jetson}/
tests/soak/{runner,profiles,schemas}/
tests/performance/full_pipeline/
tools/{release_check,recognition_evaluate,threshold_evaluate}/
configuration/examples/{cpu,nvidia-auto}.json
docs/operations/{health,shutdown,recovery,deployment}.md
docs/validation/phase-10-release-readiness-report.md
```

Exact placement follows repository packaging conventions during planning. Production prerequisites from earlier phases receive their own test-first tasks rather than being disguised as Phase 10 test utilities.

## 24. Implementation task breakdown

1. Freeze audit vocabulary, release-result schema, build/artifact fingerprinting, and severity rules.
2. Close prerequisite BLOCKERs in dependency order: real CPU model pipeline, FAISS/index lifecycle, policy/event/evidence persistence, runtime resolution, and UI reconciliation.
3. Correct liveness/readiness/status semantics with injected transition tests.
4. Build deterministic fixture/catalog discipline and five real CPU E2E scenarios.
5. Add controlled failure injection and non-conversion assertions.
6. Add PostgreSQL persistence, FAISS rebuild/atomic replacement, and process restart suites.
7. Add evidence failure/atomicity and WebSocket reconnect/REST reconciliation suites.
8. Implement graceful shutdown and bounded-state/resource instrumentation tests.
9. Add soak runner/profiles and execute the mandatory short profile.
10. Add full-pipeline benchmark and recognition/threshold evaluation tools.
11. Add CPU/NVIDIA example deployment validation and optional hardware lanes.
12. Implement release-check, execute all available gates, and produce the 17-section Phase 10 Release Readiness Report.

Each implementation task follows TDD. Work stops on newly discovered correctness/privacy blockers before performance or UX polish.

## Self-review

- The audit is based on actual source/tests and executed current checks, not phase completion messages.
- Mock tests are not called E2E or hardware tests.
- Failures cannot become identity outcomes.
- Recovery, restart, bounded state, shutdown, and observability are independently testable.
- CPU is mandatory; accelerated claims are conditional on executed hardware evidence.
- Long soak is separated from CI; acceptance thresholds precede measurement.
- No accuracy, latency, GPU, or Jetson result is invented.
- No unrelated IOC feature or distributed/cloud scope is introduced.
- This phase cannot declare production readiness until missing prerequisite implementations and mandatory evidence exist.

---

**STOP:** Await exactly `APPROVE PHASE 10 DESIGN` before product implementation or an implementation plan.
