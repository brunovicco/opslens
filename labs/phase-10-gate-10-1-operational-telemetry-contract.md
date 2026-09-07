# Phase 10 — Gate 10.1: Content-Minimized Operational Telemetry Contract

_Date: 2026-09-07_

## Status

**IMPLEMENTED — exact-head CI and protected merge pending.**

Starting main:

```text
1e182e593518f657d03c8f805a15528ec64c951f
```

Tracking:

```text
issue:  #134
branch: feat/phase10-operational-telemetry-contract
```

## Goal

Freeze a provider-neutral operational telemetry contract before any new public runtime, AWS resource, IAM permission, OpenTelemetry exporter, CloudWatch dashboard/alarm, or production SLO exists.

Phase 10 starts from the Phase 9 closeout rule:

```text
application boundary validated != public runtime deployed
```

## Existing observability baseline

OpsLens already has a shared `OperationalTelemetry` protocol and AWS Lambda Powertools adapter used by existing ingestion/transformation Lambdas for:

```text
structured logs
EMF metrics
X-Ray subsegments
```

Gate 10.1 does not replace those adapters. It adds a stricter event contract for the public-analysis boundary.

## Contract

```text
operational-telemetry:v1
```

Operation:

```text
analyze_public_repository
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

Failure categories:

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

Failure categories are stage-scoped. A planner failure cannot be mislabeled as a route-authority failure, and a request-contract rejection cannot be projected as a source-resolution failure.

## Content-minimization boundary

`OperationalEvent` contains no arbitrary attributes dictionary.

The only Phase 9 identity references available are:

```text
public_request_id
source_execution_id
handoff_id
```

Each field accepts only the exact content-addressed identifier shape produced by the corresponding frozen Phase 9 contract.

The v1 event has no field for:

```text
raw repository URL
repository owner/name
dependency names or versions
uv.lock bytes
prompt text
retrieved text
model output
SQL
provider/model selection
credentials or secrets
```

Raw content cannot be smuggled through the identity fields because those fields validate contract-specific content-addressed formats.

## Provenance progression

Identity references are permitted only after the corresponding authority object can exist:

```text
request admission success
 -> public_request_id

repository evidence success
 -> public_request_id
 -> source_execution_id

semantic planning / route admission
 -> public_request_id
 -> source_execution_id

public handoff success
 -> public_request_id
 -> source_execution_id
 -> handoff_id
```

Earlier stages reject later-stage identities.

## Deterministic identity

Canonical event semantics include only:

```text
contract version
operation
stage
outcome
duration_ms
attempt_count
failure category
Phase 9 content-addressed identity references
```

The event SHA-256 and `operational-telemetry:v1@sha256:<digest>` identifier are verified on object construction. Forged identity fails closed.

## Budgets

```text
duration_ms: 0..900000
attempt_count: 1..3
```

These are telemetry contract bounds, not a claim that the eventual public runtime has a 900-second timeout or three application retries.

## Low-cardinality metric projection

Every admitted event projects exactly two provider-neutral metric points:

```text
OperationalStageCount    Count
OperationalStageLatency  Milliseconds
```

Fixed dimensions:

```text
ContractVersion
Operation
Stage
Outcome
```

Explicitly excluded from metric dimensions:

```text
public_request_id
source_execution_id
handoff_id
repository identity
provider request ID
```

This makes the cardinality boundary executable instead of relying on dashboard conventions.

## Authority boundary

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
```

Observability can explain what happened. It cannot redefine repository identity, vulnerability applicability, risk, SQL, route, evidence completeness, or execution authority.

## Regression coverage

Tests prove:

- equivalent operational semantics produce the same event identity;
- raw repository URL cannot enter `public_request_id`;
- dependency/prompt-like text cannot enter `source_execution_id`;
- post-admission stages require admitted request identity;
- successful repository evidence requires source execution identity;
- successful public handoff requires exact source/handoff identities;
- success cannot carry a failure category;
- reject/fail requires a bounded failure category;
- failure categories must match the stage;
- duration/attempt budgets fail closed;
- forged event hashes fail closed;
- metric projection uses only the four fixed low-cardinality dimensions;
- request/source/handoff IDs never become metric dimensions;
- event identity changes when operational semantics change.

## CI

Gate 10.1 introduces a dedicated workflow:

```text
.github/workflows/operational-observability-ci.yml
```

Quality gates:

```text
uv lock --check
Ruff
Pyright strict
pytest
```

Scope:

```text
src/opslens/shared/observability
tests/unit/shared/observability
```

## External call / resource budget

```text
new public HTTP runtime:        0
new AWS resources:              0
new IAM roles/policies:         0
real GitHub runtime calls:      0
Athena calls:                   0
Bedrock calls:                  0
model calls:                    0
OpenTelemetry exporter calls:   0
CloudWatch/X-Ray runtime calls: 0
```

GitHub repository operations used to develop the gate are not application/runtime telemetry calls.

## Why OpenTelemetry is not introduced yet

OpenTelemetry is a useful instrumentation/export standard, but it does not define OpsLens authority, privacy, cardinality, or failure semantics.

Gate 10.1 therefore freezes the semantics first. A later adapter may map the frozen contract to Powertools/X-Ray, OpenTelemetry, or another provider without reopening arbitrary content fields.

## AIP-C01 learning notes

```text
observability evidence != authorization evidence
logs/traces should minimize user/source/model content
high-cardinality dimensions create operational and cost risk
immutable IDs are safer correlation handles than raw source content
SLOs require deployed workload evidence
least privilege means no runtime role before concrete runtime compute exists
```

ADR: `docs/adr/0032-content-minimized-operational-telemetry-contract.md`.

## Exit checklist

```text
[x] provider-neutral telemetry event contract
[x] bounded public-analysis stage taxonomy
[x] bounded outcome/failure taxonomy
[x] content-addressed event identity
[x] provenance progression rules
[x] hard duration/attempt accounting bounds
[x] fixed low-cardinality metric projection
[x] content leakage regressions
[x] forged identity regression
[x] dedicated strict CI workflow
[x] ADR recorded
[x] lab recorded
[ ] exact-head CI green
[ ] PR reviewed / mergeable
[ ] protected squash merge
[ ] issue #134 CLOSED / COMPLETED
[ ] postmerge current-state/roadmap sync
```

## Next gate

Gate 10.2 remains blocked until Gate 10.1 merges.
