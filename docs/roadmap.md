# OpsLens — Incremental Roadmap

_Last updated: 2026-09-12_

The roadmap is evidence-gated. Later work does not rewrite earlier evidence or inherit standing mutation authority. Certification topics do not automatically become product requirements.

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

Gate 17.1 — evidence-first threat/control-gap inventory — COMPLETE.  
Gate 17.2 — CI/CD and workflow authority hardening — COMPLETE.

Phase 17 security controls remain authoritative. Phase 18 was protected-squash-merged through PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`.

Phase 19 protected lineage now includes:

```text
Gate 19.1  PR #292  ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1
Gate 19.2  PR #347  71eda2650889d3047259d37be226862ed2a09092
Gate 19.3  PR #349  18d31c03d27448c88a6ffcba16683f3875a5ba15
Gate 19.4  PR #351  a5067e05fda74aad4d95d7f1a875110fb676304a
Gate 19.5  PR #353  61749bfac7b7bc9d032567e0b1870f8c1f7dedd4
Gate 19.6  PR #360  c76432dfcd97110ca43d91d77084f4367b9a89fd
Gate 19.7  PR #372  21a5930fd770eddf26a5c7425ffcaddfdfa6d357
```

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work. Phase 19 does not rebase, merge, modify, or depend on it.

## Phase 19 — Bounded Public Runtime & Productization

### Goal

Move from the retained Phase 9 application boundary toward the smallest safe, measurable public product surface while preserving deterministic authority boundaries, least privilege, fail-closed defaults, exact evidence provenance, and explicit human review before any AWS mutation or runtime enablement.

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
materialized != enabled
AIP-C01 topic != product requirement
```

### Gate 19.1 — Public Runtime Hypothesis & Launch Contract — COMPLETE

Gate 19.1 froze `public-analysis-workload:v1`, identified composition/measurement gaps, and refused to select runtime topology before representative evidence existed.

```text
historical decision:           DEFERRED_PENDING_MEASUREMENT
historical leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT
AWS mutations:                 0
IAM mutations:                 0
public endpoints:              0
```

Historical Gate 19.1 evidence remains unchanged.

### Gate 19.2 — Representative Workload Measurement — COMPLETE

Protected merge: PR #347 at `71eda2650889d3047259d37be226862ed2a09092`.

Canonical evidence:

```text
artifact:        labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
artifact SHA256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id:          gate19.2-live-20260911T131121Z
outcome:         SUCCESS
```

Measured baseline:

```text
end_to_end_duration_ms              17748
serialized_result_bytes              5285
GitHub physical HTTP requests           4     MEASURED
Athena query count                      0     NOT_APPLICABLE
Bedrock Retrieve count                  1     MEASURED
Bedrock Retrieve client elapsed ms   4148     MEASURED
Bedrock model call count                1     MEASURED
Bedrock input tokens                 5936     MEASURED
Bedrock output tokens                 408     MEASURED
Bedrock model client elapsed ms      8901     MEASURED
Bedrock provider latency ms          7772     MEASURED
retry count                             0     MEASURED
throttle count                          0     UNMEASURED
```

Selected interaction pattern:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The async choice is based on provider-latency coupling, retry safety, backpressure, and failure isolation, not on a claim that the successful baseline timed out.

### Gate 19.3 — Concrete Async Topology Contract — COMPLETE

Protected merge: PR #349 at `18d31c03d27448c88a6ffcba16683f3875a5ba15`.

Selected topology:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

Frozen shape:

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

The job record owns business execution truth. SQS is at-least-once transport, not execution authority.

### Gate 19.4 — Disabled Async Runtime Implementation — COMPLETE

Protected merge: PR #351 at `a5067e05fda74aad4d95d7f1a875110fb676304a`.

Gate 19.4 implemented the selected design as typed/tested application code, narrow AWS adapters, separate API/worker Lambda composition, and Terraform with exact responsibility-separated IAM.

Historical fail-closed defaults included:

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

Gate 19.4 historical implementation evidence is not rewritten by later materialization.

### Gate 19.5 — Immutable Async Deployment Artifacts — COMPLETE

Protected merge: PR #353 at `61749bfac7b7bc9d032567e0b1870f8c1f7dedd4`.

Exactly two content-addressed deployment artifacts were human-published create-only and admitted offline.

```text
API Lambda
  SHA-256:          99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e
  source_code_hash: mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=
  VersionId:        E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63

Worker Lambda
  SHA-256:          0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9
  source_code_hash: DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=
  VersionId:        sxiOdii4yFwR13t23xP5A8EU1JPV_7P1
```

Canonical publication evidence records exactly two S3 PutObject mutations, zero automatic retries, zero runtime/IAM/public mutations, and no Terraform apply.

### Gate 19.6 — Exact Terraform Plan & Offline Admission — COMPLETE

Protected closeout: PR #360 at `c76432dfcd97110ca43d91d77084f4367b9a89fd`.

The human-operated exact plan from source `d4d852c7ebc97f6fd9ee19d868fa12bc4ab031f2` admitted:

```text
21 create
0 update
0 delete
0 replacement
```

Canonical plan evidence:

```text
plan JSON SHA-256: eb01396b92879243fd2e16e7791957e3289b459facc9db9524a4d890574aa83f
execute-api endpoint disabled: true
submit switch: false
event-source mapping enabled: false
worker reserved concurrency: 0
terraform_apply_authorized: false
```

Gate 19.6 proved `plan != apply` and authorized no mutation.

### Gate 19.7 — Controlled Disabled Runtime Materialization — COMPLETE

Source issue: #361.  
Protected closeout: PR #372 at `21a5930fd770eddf26a5c7425ffcaddfdfa6d357`.  
Post-merge CodeQL: run `34710882689` / `success`.

Gate 19.7 exercised the human mutation boundary while preserving `materialized != enabled`.

#### Initial materialization attempt

The first single-use authorized apply partially created the admitted resource set and failed on API Lambda reserved concurrency `2`:

```text
failure class: LAMBDA_RESERVED_CONCURRENCY_ACCOUNT_CONSTRAINT
operation: PutFunctionConcurrency
requested API reserved concurrency: 2
retry authorized: false
```

Read-only reconciliation proved exactly 16 expected resources were managed and exactly five were still missing. The failed plan was quarantined and never reused.

#### Recovery-forward contract

The recovery changed the disabled API concurrency target to `0`, kept worker concurrency at `0`, used one separately authorized Terraform `untaint` after exact state/AWS reconciliation, and generated a fresh bounded recovery plan.

Admitted recovery plan:

```text
source head: d6546e9d48253694e3e276940ebd2388f301d8ad
plan binary SHA-256: 48cb15a8466cc0ce77fdbe1d827b5a0aebb88460b8e8151d8c88d3c85eb9ea55
plan JSON SHA-256: 8a1f95ab8cbcbf96c708c6ced0d0127d862391a6f8e72c250fe5e7499d2a0bf7
5 create
1 update
0 delete
0 replacement
```

The single authorized recovery apply completed:

```text
5 added
1 changed
0 destroyed
Terraform lineage unchanged
state serial: 116 -> 117
```

Post-apply controls were verified read-only:

```text
runtime materialized: true
execute-api endpoint disabled: true
OPSLENS_ASYNC_SUBMIT_ENABLED: false
API reserved concurrency: 0
OPSLENS_ASYNC_WORKER_ENABLED: false
worker reserved concurrency: 0
SQS -> worker event-source mapping: Disabled
custom public domain mapping: absent
provider-heavy public execution path: disabled
```

Canonical post-apply evidence:

```text
labs/evidence/phase-19-gate-19-7-post-apply-verification-v1.json
```

#### Convergence closeout

A separate single-use HUMAN-only convergence plan returned:

```text
No changes. Your infrastructure matches the configuration.
0 add
0 change
0 destroy
0 replacement
Terraform detailed exit code: 0
state lineage unchanged
state serial: 117 -> 117
state mutation observed: false
```

Convergence plan identities:

```text
binary SHA-256: 26380a6f09fc536f7738e1b855054e8a49183a24ae2e3711f6621a2c8c338157
JSON SHA-256:   505151c1d56f4d92483ad602185a49a89f10f1b9f6003eef9532cefcedf12f1d
resource_drift_entry_count: 5
```

The drift-entry count is retained as observed but is not interpreted as five actionable changes. The same plan contained zero managed actions and Terraform explicitly reported no changes.

Canonical closeout evidence:

```text
labs/evidence/phase-19-gate-19-7-post-apply-convergence-v1.json
labs/phase-19-gate-19-7-closeout.md
```

### Retained deployment sequence

```text
Gate 19.5  deterministic build + immutable publication               COMPLETE
Gate 19.6  exact Terraform plan + offline admission                  COMPLETE
Gate 19.7  human-authorized disabled materialization + convergence   COMPLETE
next gate  NOT YET FROZEN                                            NO AUTHORITY
```

Current standing truth:

```text
deployment artifact S3 PutObject mutations: 2
public async runtime resources materialized: 21 managed resources
Terraform apply invocations in Gate 19.7: 2
post-apply convergence: 0 add / 0 change / 0 destroy / 0 replacement
Terraform lineage: 6c958ab2-4cc6-7f96-a528-89535504f65c
Terraform serial: 117
public endpoints enabled: 0
submit path enabled: NO
worker enabled: NO
event-source mapping enabled: NO
custom public domain: absent
provider-heavy public executions: 0
third-party repository code executions: 0
PR #89 modifications: 0
```

## Next Phase 19 boundary — NOT YET FROZEN

Gate 19.7 completion does not imply standing authority for the next operation. No Gate 19.8 contract is currently defined here.

Any future runtime composition or controlled enablement work must begin with a separate reviewed issue/gate/contract that explicitly defines the intended change, evidence, rollback path, IAM/resource scope, limits, observability, and human authority boundary.

Until then:

```text
terraform plan/replan:                NOT AUTHORIZED
terraform apply:                       NOT AUTHORIZED
terraform destroy/replacement:         NOT AUTHORIZED
terraform import/state rm/untaint:     NOT AUTHORIZED
AWS mutation:                          NOT AUTHORIZED
IAM mutation:                          NOT AUTHORIZED
public endpoint enablement:            NOT AUTHORIZED
submit enablement:                     NOT AUTHORIZED
worker enablement:                     NOT AUTHORIZED
event-source enablement:               NOT AUTHORIZED
provider-heavy execution:              NOT AUTHORIZED
custom public domain publication:      NOT AUTHORIZED
```

The next gate must preserve the Phase 19 controlling principle unless a separately reviewed decision explicitly changes it:

```text
materialized != enabled
```
