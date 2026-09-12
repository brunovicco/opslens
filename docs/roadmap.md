# OpsLens — Incremental Roadmap

_Last updated: 2026-09-11_

The roadmap is evidence-gated. A later phase does not invalidate earlier authority boundaries, and certification topics do not automatically become product requirements.

## Phase status

```text
Phase 0   AWS Foundation                                      COMPLETE
Phase 1   EPSS Vertical Slice                                 COMPLETE
Phase 2   Threat Intelligence Data Lake                       COMPLETE
Phase 3   Vulnerability Correlation Engine                    COMPLETE
Phase 4   Repository Intelligence                             COMPLETE
Phase 5   Risk Prioritization Engine                          COMPLETE
Phase 6   Semantic Query Layer                                COMPLETE
Phase 7   Knowledge Retrieval with Bedrock                    COMPLETE
Phase 8   Hybrid Retrieval                                    COMPLETE
Phase 9   Public Analyze Your Repository application boundary COMPLETE
Phase 10  Observability & Operational Excellence              COMPLETE
Phase 11  Single-Agent Baseline                               COMPLETE
Phase 12  Multi-Agent Architecture                            COMPLETE
Phase 13  MCP                                                 COMPLETE
Phase 14  Amazon Bedrock AgentCore                            COMPLETE
Phase 15  A2A                                                 COMPLETE
Phase 16  Runtime Exposure with Amazon Inspector              COMPLETE
Phase 17  Security Hardening                                  COMPLETE
Phase 18  Evaluation, Cost & Portfolio Readiness              COMPLETE
Phase 19  Bounded Public Runtime & Productization             IN PROGRESS
```

## Retained lineage

Phase 17 security controls remain authoritative. Gate 17.1 established the evidence-first threat/control-gap inventory and Gate 17.2 hardened CI/CD and workflow authority. Later phases add no exception.

Phase 18 was protected-squash-merged through PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`.

Phase 19 protected lineage now includes:

```text
Gate 19.1  PR #292  ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1
Gate 19.2  PR #347  71eda2650889d3047259d37be226862ed2a09092
Gate 19.3  PR #349  18d31c03d27448c88a6ffcba16683f3875a5ba15
Gate 19.4  PR #351  a5067e05fda74aad4d95d7f1a875110fb676304a
Gate 19.5  PR #353  61749bfac7b7bc9d032567e0b1870f8c1f7dedd4
```

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work. Phase 19 does not rebase, merge, modify, or depend on it.

## Phase 19 — Bounded Public Runtime & Productization

### Goal

Move from the retained Phase 9 application boundary toward the smallest safe, measurable public product surface while preserving deterministic authority boundaries, least privilege, fail-closed defaults, and explicit human review before AWS mutation.

Phase 19 preserves:

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
retrieved content != instruction authority
model proposal != authorization
tool/protocol success != business truth
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
responsibility -> required action -> exact resource -> IAM statement
queue delivery != business execution authority
provider retry != business retry authority
artifact hash != S3 VersionId
publication success != deployment authorization
plan != apply
AIP-C01 topic != product requirement
```

### Gate 19.1 — Public Runtime Hypothesis & Launch Contract — COMPLETE

Gate 19.1 froze `public-analysis-workload:v1`, identified the composition/measurement gaps, and refused to select runtime topology before representative evidence existed.

```text
historical decision:          DEFERRED_PENDING_MEASUREMENT
historical leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT
AWS mutations:                 0
IAM mutations:                 0
public endpoints:              0
```

Historical Gate 19.1 evidence remains unchanged.

### Gate 19.2 — Representative Workload Measurement — COMPLETE

Protected merge: PR #347 at `71eda2650889d3047259d37be226862ed2a09092`.

Canonical human-operated evidence:

```text
repository:      openedx/mockprock
commit/ref:      18c954d8604df4740c829ba17fa2f3640b92b900
evidence file:  uv.lock
dependency:     webob==1.8.10
GHSA anchor:    GHSA-6hx8-3wjj-gr8g
CVE anchor:     CVE-2026-54770

artifact:        labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
artifact SHA256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id:          gate19.2-live-20260911T131121Z
outcome:         SUCCESS
```

Measured values:

```text
end_to_end_duration_ms                  17748
serialized_result_bytes                 5285
GitHub physical HTTP requests              4     MEASURED
Athena query count                         0     NOT_APPLICABLE
Athena bytes scanned                       0     NOT_APPLICABLE
Bedrock Retrieve count                     1     MEASURED
Bedrock Retrieve client elapsed ms      4148     MEASURED
Bedrock model call count                   1     MEASURED
Bedrock input tokens                    5936     MEASURED
Bedrock output tokens                    408     MEASURED
Bedrock model client elapsed ms         8901     MEASURED
Bedrock provider latency ms             7772     MEASURED
retry count                                0     MEASURED
throttle count                             0     UNMEASURED
```

Selected interaction pattern:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The successful baseline completed below 30 seconds. The async selection follows provider-latency coupling, retry safety, backpressure, and failure isolation. Derived retry scenarios remain explicitly `DERIVED`. Gate 19.2 authorized no deployment.

### Gate 19.3 — Concrete Async Topology Contract — COMPLETE

Protected merge: PR #349 at `18d31c03d27448c88a6ffcba16683f3875a5ba15`.

Selected design identifier:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

Frozen logical shape:

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

Frozen job states:

```text
SUBMITTING | ACCEPTED | RUNNING | SUCCEEDED | FAILED | EXPIRED
```

The contract makes the DynamoDB/SQS dual-write boundary explicit, requires `Idempotency-Key`, treats SQS as at-least-once transport, uses DynamoDB conditional state/attempt admission for duplicate authority, requires bounded retry and a DLQ, and separates API-handler IAM from worker/Bedrock IAM. Gate 19.3 authorized no deployment.

### Gate 19.4 — Disabled Async Runtime Implementation — COMPLETE

Protected merge: PR #351 at `a5067e05fda74aad4d95d7f1a875110fb676304a`.

Gate 19.4 implemented the selected Gate 19.3 design as typed/tested application code, narrow AWS adapters, Lambda composition boundaries, and Terraform behind disabled/non-public defaults.

Implemented authority includes:

```text
deterministic job + hashed idempotency identity
canonical request fingerprint and exact request coordinates
exact async state machine
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
separate API and worker Lambda composition
exact responsibility-separated IAM bindings in Terraform
```

Fail-closed defaults remain:

```text
public_async_runtime_materialized = false
disable_execute_api_endpoint = true
OPSLENS_ASYNC_SUBMIT_ENABLED = false
OPSLENS_ASYNC_WORKER_ENABLED = false
SQS -> worker event-source mapping enabled = false
worker reserved concurrency = 0
custom public domain = absent
provider-heavy worker executor = not composed
```

Current numeric values remain `CONFIGURED_LIMIT`, never measured utilization:

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

Gate 19.4 closed with zero Terraform apply, zero runtime AWS mutation, zero public enablement, and zero provider-heavy public execution.

### Gate 19.5 — Immutable Async Deployment Artifacts — COMPLETE

Issue: #352  
Protected merge: PR #353 at `61749bfac7b7bc9d032567e0b1870f8c1f7dedd4`  
Source protected main before Gate 19.5: `a5067e05fda74aad4d95d7f1a875110fb676304a`  
Reviewed publication source head: `94af45036ba33007f45ddb69e9e6c3fa7d31d715`  
Post-merge CodeQL: `completed / success`

Gate 19.5 completed deterministic artifact production, one human-only create-only publication of exactly two content-addressed objects, offline publication admission, protected merge, and post-merge verification.

Admitted immutable coordinates:

```text
API Lambda
  SHA-256:            99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e
  source_code_hash:   mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=
  compressed bytes:   17271715
  VersionId:          E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63
  publication status: CREATED

Worker Lambda
  SHA-256:            0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9
  source_code_hash:   DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=
  compressed bytes:   1036437
  VersionId:          sxiOdii4yFwR13t23xP5A8EU1JPV_7P1
  publication status: CREATED
```

Canonical publication evidence:

```text
labs/evidence/phase-19-gate-19-5-artifact-publication-v1.json
s3_put_object_mutation_count: 2
automatic_retry_count: 0
runtime_resource_mutation_count: 0
iam_mutation_count: 0
terraform_apply_count: 0
public_endpoint_enablement_count: 0
terraform_plan_input_ready: true
terraform_apply_authorized: false
```

The exact-head CI verifier replays this admission offline; CI and ChatGPT do not make AWS calls. Gate 19.5 changed deployment-artifact provenance only, not runtime deployment authority.

### Gate 19.6 — Exact Terraform Plan & Offline Admission — NEXT

Gate 19.6 may consume the exact immutable S3 `Key + VersionId + source_code_hash` coordinates above.

Gate 19.6 owns:

```text
exact artifact Key + VersionId + source_code_hash inputs
exact Terraform plan with public_async_runtime_materialized=true
offline plan parsing/admission
exact resource-change inventory
exact IAM action/resource review
disable/rollback sequence review
configured concurrency/cost ceiling review
explicit proof that plan != apply
```

The preferred plan must preserve separation between resource materialization and enablement: execute-api remains disabled, new-job submission remains disabled, worker execution remains disabled, SQS event-source mapping remains disabled, worker reserved concurrency remains zero, no custom public domain is admitted, and provider-heavy execution remains uncomposed unless a later gate explicitly changes those boundaries.

Gate 19.6 does not itself imply public enablement or Terraform apply. Any apply/enablement requires a later explicit human-authorized gate.

### Retained deployment sequence

```text
Gate 19.5  deterministic build + human create-only immutable artifact publication      COMPLETE
Gate 19.6  exact Terraform plan + offline admission/review                              NEXT
later gate human-authorized Terraform apply / controlled enablement, if admitted       NOT AUTHORIZED
```

Current standing truth distinguishes artifact publication, planning, and runtime mutation:

```text
deployment artifact S3 PutObject mutations: 2
public endpoints enabled:                    0
runtime AWS resources changed:               0
IAM roles/policies changed:                  0
Terraform apply executions:                  0
provider-heavy public executions:            0
third-party repository code executions:      0
PR #89 modifications:                        0
```
