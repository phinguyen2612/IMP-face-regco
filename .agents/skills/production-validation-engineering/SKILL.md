---
name: production-validation-engineering
description: Use when validating end-to-end production readiness, release gates, failure injection and recovery, restart safety, soak or resource-leak behavior, deployment health, performance evidence, or operational claims.
---

# Production Validation Engineering

## Core Principle

Production readiness is an evidence claim tied to an build, configuration, artifacts, environment, and executed validation. Label every claim `TESTED`, `PARTIALLY_TESTED`, `NOT TESTED`, or `NOT AVAILABLE IN CURRENT ENVIRONMENT`. A design, mock, configured dependency, or short demo is not runtime evidence.

Model-specific skills own component correctness; this skill owns system validation, recovery, resource stability, deployment evidence, and release decisions.

## Validation Workflow

1. Audit code, tests, artifacts, dependencies, and executed results. Build a feature matrix without trusting phase labels.
2. Define the release candidate fingerprint, thresholds, and which gates are mandatory, conditional, or out of scope before testing.
3. Validate the real flow from camera/input through recognition, event, evidence, persistence, API/WebSocket, and UI. Keep mocked/component tests correctly labelled.
4. Inject controlled failures at dependency boundaries. Verify failure visibility, bounded behavior, recovery, and state reconciliation.
5. Restart components independently/together; verify durable and rebuildable state.
6. Run soak profiles outside CI; measure resource, queue, drop, latency, and error trends.
7. Benchmark full-system performance and correctness on each claimed hardware profile.
8. Report reproducible passes, failures, limitations, untested areas, and blockers.

Any failed or untested mandatory gate means `NO-GO`. A waiver records owner, expiry, mitigation, and impact; it never creates a `PASS`. Missing claimed GPU hardware is `NOT TESTED` unless the environment was actually probed and shown unavailable.

## Non-negotiable Semantics

- Technical failure never becomes `UNKNOWN`, no detection, or successful evidence.
- Liveness means the process loop runs; readiness requires all mandatory components active. Health must change during injected failures and recovery.
- All queues, track/sample/verification/event state, evidence work, and client registries are bounded and observable.
- Graceful shutdown stops admission, closes input, drains or records bounded work, releases runtimes/indexes/connections, closes realtime clients, and exits by a deadline.
- PostgreSQL is authoritative; FAISS is derived and rebuildable. Replacement is validated and atomically activated.
- Evidence failure does not erase a valid committed event. WebSocket loss does not stop persistence; clients reconcile through REST.
- Validation data separates enrollment, development/calibration, and evaluation samples. Never invent accuracy or performance numbers.

## Evidence Laundering - Stop

Mocks remain component/integration evidence; design and Compose require runtime exercise; a short demo requires a declared soak; health requires injected transition tests; deadlines cannot waive gates. Renaming evidence never strengthens it.

## Review Checklist

- [ ] E2E tested
- [ ] CPU-only path tested
- [ ] Accelerated path tested when hardware available
- [ ] Failures tested
- [ ] Recovery tested
- [ ] Queues bounded
- [ ] Long-running memory checked
- [ ] Graceful shutdown tested
- [ ] Startup readiness tested
- [ ] Persistence survives restart
- [ ] FAISS rebuild tested
- [ ] Observability validated
- [ ] Performance measured
- [ ] Untested claims clearly identified
- [ ] Release criteria objective
