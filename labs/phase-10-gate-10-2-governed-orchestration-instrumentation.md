# Phase 10 — Gate 10.2: Governed Public-Analysis Orchestration Instrumentation

_Date: 2026-09-07_

## Status

**IMPLEMENTED — final exact-head CI and protected merge pending.**

Starting main:

```text
0a141db2cc0a1cb28ebac2c53d58758025d164f9
```

Tracking:

```text
issue:  #137
branch: feat/phase10-governed-orchestration-instrumentation
PR:     #138 (draft)
```

## Goal

Wire the frozen `operational-telemetry:v1` contract into the existing Phase 9 public-analysis application path without deploying a public runtime and without moving any deterministic authority into telemetry.

## Governed path

```text
untrusted public request bytes
 -> Gate 9.1 request admission
 -> Gate 9.2 immutable repository evidence
 -> Gate 9.3 metadata-only semantic planning proposal
 -> Phase 8 deterministic hybrid route admission
 -> Phase 9 deterministic public handoff binding
```

Gate 10.2 adds operational evidence around those authorities; it does not replace them.

## Instrumented stages

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

Successful execution must emit exactly five `succeeded` events in that order.

A rejected/failed stage is terminal and emits no later-stage business work or later-stage event.

## Semantic-planning refactor

The pre-existing `plan_public_analysis_handoff()` behavior remains available. Internally, the deterministic admission path is now separately callable as:

```text
route_public_semantic_plan(...)
build_public_analysis_admission_handoff(...)
```

This exposes route admission and final handoff binding for measurement while preserving:

```text
planner proposal != route authority
route decision != handoff identity
```

## Operational ports

```text
MonotonicClock
OperationalEventSink
```

Both are injected. There is no global clock or sink state.

The clock controls duration accounting only. Clock exceptions, malformed readings, regression, or out-of-contract durations fail instrumentation closed.

The sink receives only an already-admitted immutable `OperationalEvent`.

## Sink policy

```text
mandatory in-process event construction
best-effort external sink delivery
```

A sink exception does not convert business success into rejection/failure, cannot change route authority, and cannot authorize later work. Only undelivered event IDs that reference already-admitted events may be retained in bounded execution/failure evidence.

Delivery-accounting integrity is validated for:

```text
PublicAnalysisInstrumentationError
PublicAnalysisOperationalFailure
PublicAnalysisOperationalExecution
```

Forged IDs, duplicate undelivered IDs, non-string IDs, or non-`OperationalEvent` evidence fail closed. This prevents sink-delivery accounting from becoming an unverified side channel.

## Failure mapping

```text
request contract rejection        -> PUBLIC_REQUEST_ADMISSION / rejected / request_contract
source transport failure          -> REPOSITORY_EVIDENCE / failed / source_resolution
repository evidence rejection     -> REPOSITORY_EVIDENCE / rejected / evidence_contract
planner invocation failure        -> SEMANTIC_PLANNING / failed / planner_invocation
planner output rejection          -> SEMANTIC_PLANNING / rejected / planner_output_contract
route/policy rejection            -> HYBRID_ROUTE_ADMISSION / rejected / route_authority
handoff binding rejection         -> PUBLIC_HANDOFF / rejected / handoff_contract
unexpected stage failure          -> current stage / failed / unexpected_internal
```

Provider/exception messages are not copied into events.

## Regression coverage

Gate 10.2 adds tests for:

- exact five-stage success ordering and provenance progression;
- request rejection before any source/planner work;
- source transport failure vs repository evidence rejection;
- planner invocation failure vs malformed output rejection;
- under-scoped plan rejection at deterministic route admission;
- final handoff-binding rejection after a successful route;
- best-effort sink failure with unchanged application authority;
- forged and duplicate undelivered-event accounting rejection;
- clock regression failure before downstream work;
- out-of-budget event duration failure before downstream work;
- absence of raw repository URL, dependency/version, prompt, SQL, credential, provider, and sink-error text from event JSON;
- preservation of all existing Phase 9 semantic-planning regressions.

## CI evidence

Implementation head `bcc3bb277078d623d350b136e54dd263d173b36d` passed Python CI run `34139712501` across all seven repository jobs. Public Analysis reported:

```text
Ruff:            PASS
Pyright strict:  PASS — 0 errors, 0 warnings, 0 informations
pytest:          PASS — 68 passed
```

After that green run, delivery-accounting integrity was hardened and explicit regressions were added. Those changes intentionally invalidate the earlier head as the final merge checkpoint. A new exact-head Python CI is required before PR #138 can leave draft state.

## Resource / external-call budget

```text
new public runtime:        0
new AWS resources:         0
new IAM roles/policies:    0
real GitHub runtime calls: 0
Athena calls:              0
Bedrock/model calls:       0
CloudWatch/OTel calls:     0
```

All Gate 10.2 tests use injected fake source/planner/clock/sink ports.

## Architecture boundary

```text
application boundary validated != public runtime deployed
telemetry evidence != business truth
telemetry evidence != route authority
telemetry delivery accounting != permission to invent evidence identities
```

Operational instrumentation explains the path. It does not grant authority to execute it differently.

ADR: `docs/adr/0033-governed-operational-orchestration-instrumentation.md`.

## Exit checklist

```text
[x] five bounded operational stages
[x] mandatory in-process OperationalEvent construction
[x] injected monotonic clock
[x] injected best-effort sink
[x] deterministic failure taxonomy
[x] route vs handoff stage separation
[x] content-minimization regressions
[x] delivery-accounting integrity regressions
[x] no real provider/runtime calls in tests
[x] ADR recorded
[x] lab recorded
[x] draft PR #138 created
[ ] final exact-head Python CI green
[ ] PR reviewed / mergeable
[ ] protected squash merge
[ ] issue #137 CLOSED / COMPLETED
[ ] postmerge current-state/roadmap sync
```

Gate 10.3 remains blocked until Gate 10.2 is merged and postmerge state is synchronized.
