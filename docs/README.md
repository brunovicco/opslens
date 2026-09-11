# OpsLens Documentation

_Last updated: 2026-09-11_

This directory contains the retained architecture, operational state, decisions, learning maps, and runbooks for OpsLens.

## Start here

- [`current-state.md`](current-state.md) — authoritative current project state and next decision boundary.
- [`roadmap.md`](roadmap.md) — evidence-gated phase/gate progression.
- [`architecture.md`](architecture.md) — retained architecture and authority boundaries.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture view.
- [`portfolio-evidence.md`](portfolio-evidence.md) — recruiter/architect-facing evidence projection.
- [`aip-c01-learning-map.md`](aip-c01-learning-map.md) — current AIP-C01 task-to-evidence learning map.
- [`adr/README.md`](adr/README.md) — Architecture Decision Record index.
- [`runbooks/`](runbooks/) — bounded operational procedures.

## Retained security lineage

Phase 19 remains downstream of the Phase 17 security controls and the Phase 18 evidence closeout. **Gate 17.1** established the evidence-first threat/control-gap inventory, and **Gate 17.2** hardened CI/CD and workflow authority. The `Repository security invariants` protected-main context, full-SHA external actions, Dependency Review, CodeQL, adversarial authority regression, content-minimized Lambda telemetry, and the narrowly scoped scheduled-ingestion pause remain part of the retained platform authority chain.

## Phase 18 closeout

Phase 18 is complete. Its protected closeout was squash-merged through PR #290 at:

```text
feca774535b7d83f57c26f4e9fe7da71ce268f0f
```

Historical Phase 18 artifacts intentionally preserve the state that existed when they were created. Current-facing documents carry later protected-main truth without rewriting historical evidence.

Retained evidence semantics:

```text
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
lab measurement != production SLO
cost evidence != production TCO
portfolio claim != new evidence authority
AIP-C01 topic != product requirement
AIP-C01 coverage != certification guarantee
historical experiment != standing authority
```

## Phase 19 — Bounded Public Runtime & Productization

### Gate 19.1 — complete

Gate 19.1 was protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1`.

Historical retained launch contract:

```text
public-analysis-workload:v1
runtime decision: DEFERRED_PENDING_MEASUREMENT
leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT
AWS mutations: 0
IAM mutations: 0
new AWS resources: 0
public endpoints: 0
model/capability executions: 0
```

Key records:

- [`../labs/phase-19-gate-19-1-public-runtime-hypothesis.md`](../labs/phase-19-gate-19-1-public-runtime-hypothesis.md)
- [`../labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`](../labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json)
- [`adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md`](adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md)

### Gate 19.2 — complete

Gate 19.2 completed one human-operated representative live measurement, deterministic persisted-artifact review, and the evidence-backed interaction-pattern decision.

Protected closeout merge:

```text
PR #347
71eda2650889d3047259d37be226862ed2a09092
```

Canonical live artifact:

- [`../labs/evidence/phase-19-gate-19-2-live-measurement-v1.json`](../labs/evidence/phase-19-gate-19-2-live-measurement-v1.json)
- SHA-256 `04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114`
- run id `gate19.2-live-20260911T131121Z`
- outcome `SUCCESS`

Measured evidence:

```text
end-to-end duration                    17,748 ms
GitHub physical requests                     4  MEASURED
Bedrock Retrieve client elapsed         4,148 ms  MEASURED
Bedrock model client elapsed            8,901 ms  MEASURED
Bedrock provider model latency          7,772 ms  MEASURED
Bedrock input/output tokens        5,936 / 408  MEASURED
retry count                                  0  MEASURED
throttle count                               0  UNMEASURED
Athena query count / bytes                    0  NOT_APPLICABLE
serialized admitted result              5,285 bytes
```

Selected interaction pattern:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

Gate 19.2 did not claim a measured timeout. The measured baseline completed below 30 seconds; the async decision follows provider-latency coupling, retry safety, backpressure, and failure isolation. Derived retry-safety scenarios remain explicitly `DERIVED`.

Canonical closeout records:

- [`../labs/phase-19-gate-19-2-closeout.md`](../labs/phase-19-gate-19-2-closeout.md)
- [`../labs/evidence/phase-19-gate-19-2-closeout-v1.json`](../labs/evidence/phase-19-gate-19-2-closeout-v1.json)
- [`../scripts/verify_phase19_gate19_2_closeout.py`](../scripts/verify_phase19_gate19_2_closeout.py)

### Gate 19.3 — complete

Gate 19.3 was protected-merged through PR #349 at:

```text
18d31c03d27448c88a6ffcba16683f3875a5ba15
```

It selected the smallest concrete topology for the already-selected async interaction pattern while preserving zero deployment authority.

Selected design identifier:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

Logical shape:

```text
Amazon API Gateway HTTP API
 -> API Lambda
    -> DynamoDB jobs/idempotency
    -> SQS standard queue
       -> Lambda worker
          -> retained OpsLens analysis authorities
          -> DynamoDB status/result
    -> SQS DLQ
```

Frozen routes:

```text
POST /v1/analyses
GET  /v1/analyses/{job_id}
GET  /v1/analyses/{job_id}/result
```

The contract makes the DynamoDB/SQS dual-write boundary explicit, requires `Idempotency-Key`, treats SQS as at-least-once transport, uses DynamoDB conditional state/attempt admission for duplicate authority, requires bounded retry and a DLQ, and separates API-handler IAM from worker/Bedrock IAM.

Canonical Gate 19.3 records:

- [`../labs/phase-19-gate-19-3-async-topology-contract.md`](../labs/phase-19-gate-19-3-async-topology-contract.md)
- [`../labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json`](../labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json)
- [`../scripts/verify_phase19_gate19_3_async_topology_contract.py`](../scripts/verify_phase19_gate19_3_async_topology_contract.py)

Gate 19.3 authorized no deployment.

### Gate 19.4 — in progress

Issue: #350  
PR: #351  
Source protected main: `18d31c03d27448c88a6ffcba16683f3875a5ba15`

Gate 19.4 implements the selected Gate 19.3 design as typed/tested application code, narrow AWS adapters, Lambda composition boundaries, and Terraform **behind disabled/non-public defaults**.

Current implementation authority includes:

```text
deterministic job + hashed idempotency identity
canonical request fingerprint and exact request coordinates
SUBMITTING | ACCEPTED | RUNNING | SUCCEEDED | FAILED | EXPIRED
optimistic version/CAS authority
submission and worker leases
bounded attempts
submit/status/result use cases
worker claim/success/failure use cases
semantic idempotency conflicts
duplicate-delivery/concurrent-claim no-op semantics
DynamoDB transactional/conditional store
SQS content-minimized job publication
strict HTTP API v2 and SQS event admission
thin API/worker Lambda composition
```

Terraform now represents the selected resources but creates none by default:

```text
public_async_runtime_materialized = false
disable_execute_api_endpoint = true
OPSLENS_ASYNC_SUBMIT_ENABLED = false
OPSLENS_ASYNC_WORKER_ENABLED = false
SQS -> worker event-source mapping enabled = false
worker reserved concurrency = 0
custom public domain = absent
```

The worker additionally refuses provider-heavy execution enablement until a provider executor is separately admitted and composed.

Functional IAM is split by responsibility and exact Terraform resource binding. API business authority is limited to queue send plus jobs-table item/transaction operations. Worker business authority is limited to queue consumption, jobs-table state updates, retained Knowledge Base retrieval, and retained model invocation. Logging/X-Ray writes are tracked separately as runtime-support authority.

Current numeric runtime values are `CONFIGURED_LIMIT`, never measured utilization:

```text
API reserved concurrency          2
worker reserved concurrency       0
API timeout                      15 s
worker timeout                   60 s
queue visibility                120 s
redrive receive count             4
worker max attempts               3
HTTP API burst/rate            10 / 5
```

Canonical Gate 19.4 records in PR #351:

- [`../labs/phase-19-gate-19-4-disabled-async-runtime.md`](../labs/phase-19-gate-19-4-disabled-async-runtime.md)
- [`../labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json`](../labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json)
- [`../scripts/verify_phase19_gate19_4_disabled_async_runtime.py`](../scripts/verify_phase19_gate19_4_disabled_async_runtime.py)

Gate 19.4 retains this safety boundary:

```text
public endpoints enabled:                0
AWS resources created/changed/deleted:   0
IAM roles/policies created/changed:      0
AWS/provider live executions:            0
third-party repository code executions:  0
PR #89 modifications:                    0
```

No `terraform apply` or public enablement is authorized. A later human-authorized gate must review an exact Terraform plan, artifact identities, IAM/resource bindings, enablement sequence, and rollback/disable path before any AWS mutation.

## Evidence location rule

Canonical machine-readable artifacts live under `../labs/evidence/`. Human-readable experiment and closeout records live under `../labs/`. ADRs explain why a decision was made; labs/evidence record what was measured, proven, rejected, or intentionally left `UNMEASURED`.

Historical evidence is not rewritten merely to make it look current. Current-facing documents (`current-state.md`, `roadmap.md`, this index, and active runbooks) explain later superseding context while preserving original evidence lineage.

PR #89 remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency unless explicitly re-evaluated later.
