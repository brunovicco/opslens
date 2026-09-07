# Phase 10 — Gate 10.3: CloudWatch EMF Telemetry Adapter Boundary

_Date: 2026-09-07_

## Status

**COMPLETE / MERGED.**

Starting main:

```text
88adb87d19b4c1d3cc7bb6ccfed69ea1724b353d
```

Tracking:

```text
issue:      #140 — CLOSED / COMPLETED
branch:     feat/phase10-cloudwatch-emf-adapter
PR:         #141 — MERGED
final head: 632e778d36ada833505342708379603a1080d390
merge SHA:  0c5bf6bab39a3980c063fcb44f657c412111fefa
```

## Goal

Adapt the frozen provider-neutral `operational-telemetry:v1` contract to deterministic Amazon CloudWatch Embedded Metric Format (EMF) without deploying a public runtime, adding IAM, or claiming that CloudWatch ingestion has occurred.

## Existing authority

Gate 10.3 consumes already-admitted operational evidence only:

```text
OperationalEvent
 -> project_operational_metrics(...)
 -> cloudwatch-emf:v1
```

It does not become a source of business truth or route authority.

Permanent boundary:

```text
telemetry evidence != business truth
telemetry evidence != route authority
provider serialization != execution authority
EMF document created != CloudWatch ingestion proven
```

## AWS EMF mapping

Frozen adapter contract:

```text
cloudwatch-emf:v1
namespace: OpsLens/Operational
storage resolution: 60 seconds
maximum canonical document: 16 KiB
```

One canonical JSON document contains:

```text
_aws.Timestamp
_aws.CloudWatchMetrics
```

with exactly one metric directive and the existing two operational metrics:

```text
OperationalStageCount      Count
OperationalStageLatency    Milliseconds
```

Exact metric dimension set:

```text
ContractVersion
Operation
Stage
Outcome
```

High-cardinality correlation identities remain root log metadata only:

```text
EventId
PublicRequestId
SourceExecutionId
HandoffId
```

They never become metric dimensions.

## Adapter boundary

```text
OperationalEvent
 -> existing deterministic project_operational_metrics(...)
 -> canonical EMF payload
 -> CloudWatchEmfDocument
 -> injected EmfLineWriter
 -> STOP
```

The writer receives one canonical JSON byte line. No stdout/global logger or AWS SDK client is hard-coded into the adapter.

## Clock semantics

Gate 10.2 uses an injected monotonic clock for stage duration accounting. EMF requires wall-clock epoch-millisecond timestamp semantics, so Gate 10.3 introduces a distinct injected port:

```text
EpochMillisecondsClock
```

The two clocks are intentionally not interchangeable.

Malformed epoch values and clock exceptions map to:

```text
clock_contract
```

before the writer can execute.

## Delivery semantics

Each `emit(...)` invocation attempts writer delivery at most once.

```text
adapter retry count: 0
writer invocations per emit: <= 1
```

Writer failure maps to:

```text
writer_delivery
```

and arbitrary writer/provider exception text is discarded.

## Document identity

Canonical payloads use deterministic JSON serialization and SHA-256 identity:

```text
cloudwatch-emf:v1@sha256:<digest>
```

Identity binds:

```text
admitted OperationalEvent semantics
+ projected metrics
+ exact EMF timestamp
+ frozen EMF schema/constants
```

Same event plus same timestamp is deterministic. Changing the timestamp changes document identity.

## Failure taxonomy

```text
non-OperationalEvent input       -> document_contract
invalid wall-clock value         -> clock_contract
canonical document rejection     -> document_contract
writer exception                 -> writer_delivery
```

No failure changes application, route, evidence, model, or execution authority.

## Regression coverage

Gate 10.3 adds tests for:

- exact `_aws.Timestamp` and `CloudWatchMetrics` shape;
- exact namespace, metric names, units, and 60-second storage resolution;
- exact low-cardinality dimension set;
- request/source/handoff/event IDs excluded from metric dimensions;
- deterministic stage-count and stage-latency projection reuse;
- bounded success/rejected/failed metadata;
- content-addressed document identity;
- timestamp-bound identity change;
- invalid wall-clock values;
- content-free clock failures;
- one writer attempt with no retry;
- content-free writer failures;
- exact canonical JSON line delivery;
- forged/non-event rejection before clock/writer use;
- forged and oversized direct document rejection;
- no arbitrary attribute bag for repository/dependency/prompt/SQL/credential/provider text.

## First CI attempt

Draft PR #141 initially ran:

```text
Operational Observability CI
run: 34143614259
head: 75b6f9dd1fb1da5c3bb8ac3ad9e9df8280bd99ac
```

Result:

```text
uv lock --check: PASS
Ruff:            PASS
Pyright strict:  FAIL
pytest:           SKIPPED
```

The single Pyright error was test-only typing:

```text
RecordingWriter.lines -> list[Unknown]
```

Cause: `dataclasses.field(default_factory=list)` did not provide sufficient generic information under the repository's strict Pyright configuration.

No production/adapter behavior changed. The fake writer was replaced by an explicitly typed class field:

```text
self.lines: list[bytes] = []
```

Fix commit:

```text
510110609d65d14d44c48653179531913b7efa3a
```

This failure is preserved as quality-gate evidence rather than hidden.

## Implementation hardening discovered before final validation

The first adapter draft exposed two deterministic issues during review before merge:

1. the provider-neutral metric mapping exposes dimensions as a mapping whose insertion order is not the EMF dimension-order contract, so EMF validation must compare the exact key set rather than inherit mapping iteration order;
2. a malformed clock value must be classified as `clock_contract`, not `document_contract`.

Both were corrected before final validation. The adapter reads projected dimension values by frozen key names and validates clock output before document construction.

## Final exact-head CI

Final implementation head:

```text
632e778d36ada833505342708379603a1080d390
```

Operational Observability CI:

```text
run:              34143908297 / run #9 / SUCCESS
uv lock --check:  PASS
Ruff:             PASS
Pyright strict:   0 errors / 0 warnings / 0 informations
pytest:           26 passed
```

The protected squash merge used that exact validated head and produced:

```text
0c5bf6bab39a3980c063fcb44f657c412111fefa
```

Issue #140 then closed as `COMPLETED`.

## Resource / external-call budget

```text
new public runtime:        0
new AWS resources:         0
new IAM roles/policies:    0
CloudWatch Logs calls:     0
PutMetricData calls:       0
OpenTelemetry calls:       0
real GitHub runtime calls: 0
Athena calls:              0
Bedrock/model calls:       0
```

All tests use injected clock/writer fakes.

## Cost boundary

This gate proves low-cardinality representation, not CloudWatch cost.

Request/source/handoff/event IDs are deliberately excluded from metric dimensions because high-cardinality dimensions create distinct metric time series and can materially increase CloudWatch cost.

Still not claimed:

```text
CloudWatch ingestion volume
log retention cost
metric time-series count under production load
production cost/request
production p95/p99
production error rate
alarm/SLO compliance
```

## IAM boundary

No runtime principal exists for this adapter gate. Therefore no new permissions are justified.

Specifically absent:

```text
logs:PutLogEvents
cloudwatch:PutMetricData
```

A future runtime-specific writer must receive least-privilege IAM only after its concrete compute and delivery mechanism exist.

## Architecture record

ADR:

```text
docs/adr/0034-bounded-cloudwatch-emf-telemetry-adapter.md
```

## Exit checklist

```text
[x] deterministic cloudwatch-emf:v1 document
[x] existing operational metric projection reused
[x] exact four-dimension low-cardinality set
[x] high-cardinality identities metadata-only
[x] separate injected epoch-millisecond clock
[x] injected line-writer port
[x] no adapter retry
[x] bounded content-free failure taxonomy
[x] SHA-256 content-addressed document identity
[x] 16 KiB OpsLens document limit
[x] strict regressions added
[x] ADR recorded
[x] draft PR #141 created
[x] final exact-head Operational Observability CI green
[x] PR reviewed / mergeable
[x] protected squash merge
[x] issue #140 CLOSED / COMPLETED
[x] postmerge state-sync branch created
```

## Next authorized gate

```text
Phase 10 Gate 10.4 — Phase 10 Closeout
```

Gate 10.4 must close the observability phase at the currently proven boundary. It must explicitly preserve that EMF serialization is not CloudWatch ingestion, a validated application boundary is not a deployed public runtime, and production SLO/cost/alert claims require a concrete workload. It must not introduce runtime compute or IAM merely to complete Phase 10.
