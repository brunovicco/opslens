# ADR 0032 — Operational Telemetry Is Content-Minimized Evidence, Not Execution Authority

- Status: Accepted
- Date: 2026-09-07
- Phase: 10 — Observability & Operational Excellence
- Gate: 10.1 — Content-Minimized Operational Telemetry Contract

## Context

OpsLens already emits structured logs, EMF metrics, and X-Ray subsegments from existing ingestion/transformation Lambdas through the shared `OperationalTelemetry` port and AWS Lambda Powertools adapter.

Phase 9 added a different application boundary:

```text
untrusted public JSON
 -> strict request admission
 -> immutable repository evidence
 -> bounded semantic-plan proposal
 -> deterministic public-v1 scope admission
 -> deterministic Phase 8 hybrid route authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

Phase 9 deliberately did not deploy a public HTTP runtime. Therefore Phase 10 must not fabricate production telemetry, SLOs, or runtime IAM merely because observability is the phase goal.

The first Phase 10 problem is architectural: define what operational evidence is safe and stable enough to emit when a concrete runtime exists.

Telemetry creates two risks if left unbounded:

1. **authority laundering** — logs or traces accidentally become treated as business truth or authorization evidence;
2. **data/cardinality leakage** — raw repository URLs, dependency names, prompts, model output, SQL, or request/source IDs become high-cardinality metric dimensions or unnecessarily logged content.

## Decision

Gate 10.1 freezes:

```text
operational-telemetry:v1
```

Operational telemetry is provider-neutral diagnostic evidence. It is not repository, vulnerability, risk, route, SQL, evidence-completeness, or execution authority.

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
```

### Bounded stages

The v1 stage taxonomy is limited to the application boundary that actually exists after Phase 9:

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

No downstream vulnerability/risk/retrieval/synthesis runtime stage is invented by this contract.

### Bounded outcomes

```text
succeeded
rejected
failed
```

`rejected` means deterministic contract/authority admission refused progress. `failed` means execution of the stage failed. The distinction is operational; it does not alter application authority.

### Bounded failure categories

Failure categories are stage-scoped and content-free:

```text
request_contract
source_resolution
evidence_contract
planner_invocation
planner_output_contract
route_authority
handoff_contract
unexpected_internal
```

A failure category that is not authorized for the selected stage is rejected.

### Content minimization

The v1 event has no arbitrary attributes/map field. It may reference only known content-addressed identities when they exist:

```text
public_request_id
source_execution_id
handoff_id
```

Their formats are validated against the already-frozen Phase 9 contract identifiers. Raw repository URLs, owner/name values, dependency names/versions, `uv.lock` bytes, prompts, retrieved/model text, SQL, provider/model selection, credentials, and secrets have no field in `operational-telemetry:v1`.

This is enforced by executable schema/validation, not by logging guidance alone.

### Provenance progression

Operational identity references may appear only after the corresponding authority object exists.

Examples:

```text
request admission success -> public_request_id required
repository evidence success -> public_request_id + source_execution_id required
semantic planning -> public_request_id + source_execution_id required
route admission -> public_request_id + source_execution_id required
public handoff success -> public_request_id + source_execution_id + handoff_id required
```

Earlier stages cannot reference later identities.

### Content-addressed event identity

Canonical JSON includes only the frozen operational semantics:

```text
contract version
operation
stage
outcome
duration_ms
attempt_count
bounded failure category
content-addressed Phase 9 identity references
```

The SHA-256 and versioned event ID are recomputed on construction. Forged event identities fail closed.

### Hard budgets

```text
duration_ms: 0..900000
attempt_count: 1..3
```

These are telemetry-contract limits, not runtime timeout/retry policy. A future runtime may choose stricter execution limits.

### Metric projection

The deterministic v1 metric projection emits only:

```text
OperationalStageCount      Count
OperationalStageLatency    Milliseconds
```

Dimensions are fixed:

```text
ContractVersion
Operation
Stage
Outcome
```

Request, repository, source-execution, handoff, provider-request, or other high-cardinality identities are explicitly excluded from metric dimensions.

Those identities may remain in content-minimized structured operational events/traces where needed for diagnosis.

## Existing AWS Lambda Powertools boundary

Gate 10.1 does not replace or widen the existing `OperationalTelemetry` / `PowertoolsTelemetry` adapter.

Existing Lambda workloads may continue to use:

```text
structured logs
EMF metrics
X-Ray subsegments
```

A later gate may add an adapter that projects admitted `OperationalEvent` objects into those providers or into OpenTelemetry. Such an adapter must preserve this ADR rather than reopening arbitrary fields/cardinality.

## Why not deploy OpenTelemetry now

OpenTelemetry is a transport/instrumentation ecosystem, not an authority model. Deploying an SDK, Collector, or exporter before freezing the event/cardinality/privacy contract would reverse the dependency direction.

Gate 10.1 therefore freezes semantics first and performs zero provider/AWS calls.

A future OpenTelemetry adapter remains allowed if a concrete runtime and exporter target justify it.

## Failure semantics

A telemetry backend failure must never authorize continuation that the application contract would otherwise reject.

Conversely, Gate 10.1 does not declare telemetry delivery itself to be a business-transaction commit requirement. Delivery guarantees, buffering, retry, sampling, and outage behavior require a concrete runtime/backend decision in a later gate.

## Consequences

### Positive

- operational evidence has a stable provider-neutral schema;
- raw public/repository/model content cannot enter the v1 event through an arbitrary attribute map;
- provenance IDs appear only after their authority objects exist;
- metric cardinality is bounded by construction;
- event identity is deterministic and tamper-evident at the application contract level;
- existing Powertools/X-Ray investment remains reusable;
- no speculative runtime or IAM is introduced.

### Trade-offs

- the v1 event is intentionally less flexible than generic logging/OpenTelemetry attributes;
- new stages or diagnostic fields require explicit contract evolution;
- not every existing ingestion/transformation log event is automatically converted to this contract in Gate 10.1.

Those constraints are intentional for a public GenAI boundary.

## Alternatives rejected

### Arbitrary `dict[str, object]` telemetry attributes

Rejected because the contract could not prevent content leakage or uncontrolled metric cardinality.

### Request/repository IDs as CloudWatch metric dimensions

Rejected because per-request/source identities are high-cardinality and increase operational cost/noise without improving aggregate service health metrics.

### Make observability backend success an authorization gate

Rejected for Gate 10.1 because diagnostic delivery is not repository/risk/route authority and no concrete backend delivery contract exists yet.

### Deploy OpenTelemetry Collector before the schema

Rejected because transport choice should implement the telemetry contract, not define it.

## Security properties

```text
no arbitrary telemetry attribute bag
no raw repository/model/SQL content fields
no request/source IDs in metric dimensions
stage-scoped failure categories
content-addressed provenance progression
forged identity -> reject
telemetry never grants execution authority
```

## AIP-C01 learning notes

This decision demonstrates production GenAI operational patterns relevant to AIP-C01:

- separate observability evidence from authorization/business truth;
- minimize logged model/user/source data by design;
- control metric dimensions to avoid high-cardinality cost explosions;
- correlate operations through immutable IDs rather than raw content;
- define telemetry semantics before choosing an exporter/backend;
- do not claim production SLOs without deployed workload evidence;
- preserve least privilege by deferring runtime IAM until concrete compute exists.
