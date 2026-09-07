# ADR 0035 — Close Phase 10 at the Proven Observability Boundary

- Status: Accepted
- Date: 2026-09-07
- Phase: 10 — Observability & Operational Excellence
- Gate: 10.4 — Phase 10 Closeout

## Context

Phase 10 started after Phase 9 deliberately closed at a governed public-analysis **application boundary**, not at a fictional public runtime. The observability phase therefore had to improve diagnosability without creating telemetry-derived business authority or claiming production evidence that did not exist.

The completed Phase 10 gates are:

```text
Gate 10.1 — operational-telemetry:v1 contract                 COMPLETE / MERGED
Gate 10.2 — governed five-stage orchestration instrumentation  COMPLETE / MERGED
Gate 10.3 — cloudwatch-emf:v1 adapter boundary                 COMPLETE / MERGED
```

Gate 10.1 froze provider-neutral, content-minimized operational evidence. Gate 10.2 instrumented the existing governed application path. Gate 10.3 demonstrated deterministic serialization into an AWS-native CloudWatch Embedded Metric Format representation through injected boundaries.

No public runtime was deployed during those gates and no CloudWatch ingestion was executed. The closeout must therefore distinguish what is architecturally proven from what remains future runtime work.

## Decision

Close Phase 10 as **COMPLETE** at the current validated observability boundary.

The phase proves:

```text
provider-neutral operational event contract
bounded deterministic stage instrumentation
content-minimized provenance/correlation identities
fixed low-cardinality metric projection
best-effort external sink semantics after mandatory in-process evidence
bounded content-free failure taxonomy
cloudwatch-emf:v1 deterministic serialization
separate monotonic-duration and epoch-millisecond clock semantics
zero adapter retries
content-addressed OperationalEvent and CloudWatchEmfDocument evidence
```

The phase does **not** prove:

```text
public HTTP runtime
CloudWatch ingestion
runtime principal / runtime IAM
public request volume
production distributed traces
production p95/p99
production error/throttle rates
production cost/request
production dashboards/alarms
production SLO compliance
```

Those claims require a separately deployed workload and direct runtime evidence.

## Frozen Phase 10 contracts

### Provider-neutral operational evidence

```text
operational-telemetry:v1
operation: analyze_public_repository
```

Stages:

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

Outcomes:

```text
succeeded
rejected
failed
```

Metrics:

```text
OperationalStageCount      Count
OperationalStageLatency    Milliseconds
```

Metric dimensions:

```text
ContractVersion
Operation
Stage
Outcome
```

### AWS-native representation

```text
cloudwatch-emf:v1
namespace: OpsLens/Operational
storage resolution: 60 seconds
maximum canonical document: 16 KiB
```

The EMF representation reuses `project_operational_metrics(...)`; it does not define new metric truth.

High-cardinality correlation identities remain log metadata only:

```text
EventId
PublicRequestId
SourceExecutionId
HandoffId
```

They never become metric dimensions.

## Authority boundary

Phase 10 permanently freezes:

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
telemetry delivery accounting != permission to invent evidence identities
provider serialization != execution authority
EMF document created != CloudWatch ingestion proven
```

These rules extend, rather than replace, the existing project boundaries:

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
Intent classification != execution authority.
No unrestricted text-to-SQL.
```

## Delivery and failure semantics

Gate 10.2 freezes mandatory in-process event construction with best-effort external delivery:

```text
invalid OperationalEvent construction -> fail closed
external sink failure                 -> no business/route authority change
```

Undelivered-event accounting may reference only already-admitted event identities.

Gate 10.3 freezes provider-adapter failure categories:

```text
clock_contract
document_contract
writer_delivery
```

The adapter performs zero retries and attempts writer delivery at most once per `emit(...)` call. Provider/writer exception messages do not enter admitted telemetry.

## Clock semantics

Two clocks intentionally exist because they measure different things:

```text
MonotonicClock          -> stage duration accounting
EpochMillisecondsClock -> EMF wall-clock timestamp
```

They must not be conflated merely because both produce time-related values.

## Privacy and cardinality boundary

Operational events contain no arbitrary attribute bag for raw repository URLs/content, dependency/version details, lockfile bytes, prompts/retrieved/model text, SQL, credentials, secrets, or provider messages.

Request/source/handoff/event IDs are correlation evidence, not CloudWatch metric dimensions. This prevents request-level identities from exploding metric cardinality and cost.

## IAM boundary

Phase 10 introduced no runtime principal. Therefore the closeout creates no runtime IAM policy.

Specifically, Phase 10 does not grant:

```text
logs:PutLogEvents
cloudwatch:PutMetricData
```

A future runtime-specific delivery adapter may receive least-privilege permissions only after a concrete compute boundary and delivery mechanism exist.

## Cost boundary

The phase proves cardinality discipline but does not claim production CloudWatch cost.

CloudWatch ingestion volume, log retention, metric time-series count under real load, retry behavior, and public request volume are all absent. Production cost/request therefore remains unmeasured.

This follows the existing OpsLens rule:

```text
unmeasured cost != zero cost
```

## Validation evidence

### Gate 10.1

```text
PR #135 final head:           7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
Operational Observability CI: 34135197989 / PASS
pytest:                       14 passed
merge SHA:                    665b86f6e527a0096d7c3db522f4bd2c95b177aa
issue #134:                   CLOSED / COMPLETED
```

### Gate 10.2

```text
PR #138 final head:           24b2affdf464e2548d94273e41007bb3256b561e
Python CI:                    34141496326 / PASS
Public Analysis pytest:       70 passed
merge SHA:                    346b223d9566a5d04d84e279f30793ad52a35b67
issue #137:                   CLOSED / COMPLETED
```

### Gate 10.3

```text
PR #141 final head:           632e778d36ada833505342708379603a1080d390
Operational Observability CI: 34143908297 / run #9 / PASS
Ruff:                         PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
pytest:                       26 passed
merge SHA:                    0c5bf6bab39a3980c063fcb44f657c412111fefa
issue #140:                   CLOSED / COMPLETED
```

The Gate 10.3 lab also preserves its initial strict-Pyright failure before the final exact-head green validation.

## Consequences

### Positive

- Phase 10 has an explicit, provider-neutral operational evidence model;
- the existing governed path is diagnosable by deterministic stage/outcome/failure semantics;
- metric cardinality is bounded before any production backend exists;
- an AWS-native EMF representation is ready for a future runtime-specific delivery decision;
- telemetry can evolve without acquiring business or route authority;
- future runtime/IAM/SLO work must provide new evidence instead of inheriting fictional production claims.

### Constraints

- no public request telemetry exists yet because no public runtime exists;
- EMF serialization alone cannot prove CloudWatch delivery;
- production latency/error/cost/SLO decisions remain deferred;
- any later telemetry backend or runtime contract that changes these semantics requires a new versioned architecture decision.

## Phase 11 entry decision

After this closeout merges and repository state is synchronized, the next authorized project phase is:

```text
Phase 11 — Single-Agent Baseline
```

Phase 11 must build one bounded agent over already-governed capabilities before introducing multi-agent complexity.

The entry boundary is:

```text
agent reasoning may select/use already-authorized capabilities
agent reasoning does not acquire deterministic truth or execution authority
```

Before any agent runtime is introduced, Phase 11 must define the exact tool surface, authorization boundary, execution limits, failure semantics, evaluation baseline, and observability mapping.

## Deferred cross-project integration

OpsLens PR #89 remains deferred consumer-side work for **Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project**. It is not OpsLens Phase 14 and is not made mergeable by Phase 10 closeout.

## Non-goals

This closeout does not deploy Lambda, API Gateway, ECS, public endpoints, runtime IAM, CloudWatch delivery, OpenTelemetry exporters, dashboards, alarms, SLOs, agents, MCP, AgentCore, A2A, runtime exposure, or Governed LLM Gateway integration.

## AIP-C01 learning note

Operational excellence for GenAI systems is not equivalent to adding a telemetry backend. A robust architecture first freezes what may be observed, how evidence is correlated, which dimensions are safe, how provider delivery can fail, and what telemetry is forbidden from authorizing. Only then should a concrete runtime receive least-privilege delivery permissions and workload-derived SLOs.
