# ADR 0034 — Adapt Operational Evidence to CloudWatch EMF Without Deploying Runtime Authority

- Status: Accepted
- Date: 2026-09-07
- Phase: 10 — Observability & Operational Excellence
- Gate: 10.3 — CloudWatch EMF Telemetry Adapter Boundary

## Context

Gate 10.1 froze `operational-telemetry:v1` as provider-neutral, content-minimized operational evidence. Gate 10.2 then instrumented the governed Phase 9 public-analysis path with exactly five ordered operational stages while preserving deterministic application and route authority.

The next observability step is to prove that those admitted events can be mapped to Amazon CloudWatch Embedded Metric Format (EMF) without deploying a public runtime and without letting a provider-specific representation become business truth or execution authority.

CloudWatch EMF expects one valid JSON log event containing `_aws.Timestamp` and `CloudWatchMetrics`. Metric directives define a namespace, one or more dimension sets, and metric definitions. Dimension targets are root string members. AWS permits much larger dimension and event budgets than OpsLens needs, so this gate intentionally freezes a narrower contract.

## Decision

Introduce a deterministic provider-specific adapter over the existing provider-neutral telemetry contract:

```text
OperationalEvent
 -> project_operational_metrics(...)
 -> cloudwatch-emf:v1 document
 -> injected EpochMillisecondsClock
 -> injected EmfLineWriter
 -> STOP
```

The adapter does not call CloudWatch, CloudWatch Logs, or any AWS API. It serializes one already-admitted event into one canonical UTF-8 JSON record and delegates byte delivery to an injected writer port.

### Frozen EMF contract

```text
contract:            cloudwatch-emf:v1
namespace:           OpsLens/Operational
storage resolution:  60 seconds
maximum document:    16 KiB
```

Metric names remain the Gate 10.1 projections:

```text
OperationalStageCount
OperationalStageLatency
```

The exact CloudWatch dimension set is:

```text
ContractVersion
Operation
Stage
Outcome
```

No request, source, handoff, or event identity becomes a metric dimension.

### High-cardinality metadata

Already-admitted content-addressed identities may be present only as bounded log metadata:

```text
EventId
PublicRequestId
SourceExecutionId
HandoffId
```

They do not participate in the EMF dimension set and therefore do not create request-level metric cardinality.

### Reuse existing metric authority

The adapter must call `project_operational_metrics(...)`. It must not independently reconstruct stage count, latency, units, or metric dimensions.

This preserves:

```text
OperationalEvent -> deterministic metric projection -> provider representation
```

rather than:

```text
provider representation -> new telemetry truth
```

### Timestamp boundary

EMF requires wall-clock epoch-millisecond semantics, which are different from the monotonic duration clock used by Gate 10.2.

Therefore Gate 10.3 injects a separate:

```text
EpochMillisecondsClock
```

A clock exception or malformed epoch value maps to the bounded `clock_contract` adapter failure. Clock/provider exception text is never copied into admitted telemetry or the adapter error.

### Delivery boundary

The adapter injects:

```text
EmfLineWriter
```

Each `emit(...)` invocation attempts writer delivery at most once. There is no application retry in this adapter.

Writer failure maps to:

```text
writer_delivery
```

and exposes no arbitrary writer/provider exception text.

The writer is intentionally not a CloudWatch client. A future deployed runtime may bind it to stdout, a structured logger, or another delivery path through a separately justified runtime decision.

### Document identity

The canonical EMF payload is serialized with deterministic JSON settings and content-addressed with SHA-256:

```text
cloudwatch-emf:v1@sha256:<digest>
```

The digest binds the exact admitted event projection plus the EMF wall-clock timestamp. Same event + same timestamp yields the same document identity; a timestamp change yields a different identity.

### Failure taxonomy

```text
invalid/forged OperationalEvent -> document_contract
invalid wall-clock value         -> clock_contract
EMF document admission failure   -> document_contract
writer delivery failure          -> writer_delivery
```

All adapter failures are operational evidence about adaptation/delivery only. They do not authorize business execution, route changes, retries, or fallback.

## Authority boundary

```text
telemetry evidence != business truth
telemetry evidence != route authority
provider serialization != execution authority
EMF document created != CloudWatch ingestion proven
```

`cloudwatch-emf:v1` is a representation contract, not a new business contract.

## Security / privacy consequences

- no arbitrary EMF attribute bag exists;
- provider/writer exception messages are not serialized;
- high-cardinality identities remain out of metric dimensions;
- repository URLs, dependency/version text, prompts, SQL, credentials, and provider details have no adapter input field;
- the writer receives only one already-admitted canonical byte line;
- no adapter retry exists.

## Cost consequences

The four-dimension set is deliberately low cardinality. Request/source/handoff/event IDs are excluded from dimensions because dimensions create distinct CloudWatch metric time series and can become a material cost/cardinality driver.

Gate 10.3 does not claim CloudWatch metric/log cost because no CloudWatch ingestion occurs in this gate. Production cost requires a real runtime, request volume, event volume, retention, and ingestion evidence.

## IAM / runtime consequences

Gate 10.3 introduces:

```text
new AWS resources:      0
new IAM permissions:    0
CloudWatch API calls:   0
public runtime:         0
```

No `logs:PutLogEvents`, `cloudwatch:PutMetricData`, Lambda, API Gateway, ECS, dashboard, alarm, or SLO is created.

## Alternatives considered

### Call `PutMetricData` directly

Rejected for this gate because it would bypass the already-frozen event-to-metric representation path and would require a concrete AWS runtime identity/IAM decision before that runtime exists.

### Put high-cardinality request IDs in dimensions

Rejected because request/source/handoff identities are evidence correlation keys, not aggregation dimensions. Promoting them to dimensions would increase metric cardinality and cost without changing business authority.

### Use a global logger/stdout directly in the adapter

Rejected because it would hide the delivery boundary and make deterministic failure/no-retry testing harder. Delivery remains an injected port.

### Reuse the Gate 10.2 monotonic clock

Rejected because monotonic duration accounting and wall-clock EMF timestamps have different semantics and should not be conflated.

## Consequences

### Positive

- proves deterministic mapping from provider-neutral operational evidence to an AWS-native metric/log representation;
- preserves low-cardinality metric dimensions;
- keeps AWS/provider delivery outside deterministic application authority;
- makes clock and writer failures independently testable;
- creates a stable boundary for a future runtime-specific writer.

### Constraints

- serialized EMF remains offline evidence until a real runtime delivers it;
- no production telemetry delivery, latency distribution, alarm, or SLO can be claimed;
- the 16 KiB OpsLens document cap is intentionally narrower than the service maximum;
- standard 60-second resolution remains frozen until measured workload evidence justifies high-resolution metrics.

## Non-goals

Gate 10.3 does not deploy public HTTP compute, Lambda, API Gateway, ECS, CloudWatch Logs delivery, `PutMetricData`, OpenTelemetry exporters, dashboards, alarms, SLOs, agents, MCP, AgentCore, A2A, runtime exposure, or Governed LLM Gateway integration.

## AIP-C01 learning note

A useful GenAI operational architecture separates business/evidence authority from provider-specific observability delivery. EMF is an AWS-native representation mechanism, but the representation should consume an already-governed telemetry contract rather than redefine what the system considers true, authorized, or complete.
