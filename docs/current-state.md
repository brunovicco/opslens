# OpsLens — Current State

_Last updated: 2026-09-11_

## Authoritative checkpoint

```text
protected main:
61749bfac7b7bc9d032567e0b1870f8c1f7dedd4

Phase 18 — Evaluation, Cost & Portfolio Readiness
status: COMPLETE
protected closeout PR: #290
protected closeout SHA: feca774535b7d83f57c26f4e9fe7da71ce268f0f

Phase 19 — Bounded Public Runtime & Productization

Gate 19.1 — Public Runtime Hypothesis & Launch Contract      COMPLETE
protected merge PR: #292
historical runtime decision: DEFERRED_PENDING_MEASUREMENT
historical leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT
retained historical boundary: PublicAnalysisAdmissionHandoff -> STOP

Gate 19.2 — Representative Workload Measurement              COMPLETE
protected merge PR: #347
protected merge SHA: 71eda2650889d3047259d37be226862ed2a09092
selected interaction pattern: ASYNC_SUBMIT_STATUS_RESULT
canonical live artifact SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114

Gate 19.3 — Concrete Async Topology Contract                 COMPLETE
protected merge PR: #349
protected merge SHA: 18d31c03d27448c88a6ffcba16683f3875a5ba15
selected design topology: HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
deployment authorized: NO

Gate 19.4 — Disabled Async Runtime Implementation            COMPLETE
protected merge PR: #351
protected merge SHA: a5067e05fda74aad4d95d7f1a875110fb676304a
deployment authorized: NO

Gate 19.5 — Immutable Async Deployment Artifacts             COMPLETE
source issue: #352 (closed completed)
protected merge PR: #353
protected merge SHA: 61749bfac7b7bc9d032567e0b1870f8c1f7dedd4
reviewed publication source head: 94af45036ba33007f45ddb69e9e6c3fa7d31d715
publication authority: HUMAN_ONLY_CREATE_ONLY
publication status: ADMITTED
S3 PutObject mutation count: 2
automatic retry count: 0
API VersionId: E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63
worker VersionId: sxiOdii4yFwR13t23xP5A8EU1JPV_7P1
terraform plan input ready: YES
terraform apply authorized: NO
post-merge CodeQL: completed / success
runtime deployment authorized: NO

Gate 19.6 — Exact Terraform Plan & Offline Admission         IN PROGRESS
source issue: #354
implementation PR: #356
source main: 61749bfac7b7bc9d032567e0b1870f8c1f7dedd4
plan boundary: HUMAN_ONLY_READS_WITH_LOCK_FALSE
terraform apply authorized: NO
```

Phases 0–18 remain complete. Gate 19.5 is formally complete after protected merge and post-merge CodeQL success on `61749bfac7b7bc9d032567e0b1870f8c1f7dedd4`. Gate 19.6 now owns the first exact Terraform plan and offline admission using the immutable Gate 19.5 artifact coordinates. No current gate authorizes `terraform apply`, public runtime enablement, or provider-heavy public execution.

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency.

## Retained security and authority invariants

Phase 17 security controls remain authoritative. **Gate 17.1** retains the evidence-first security threat/control-gap inventory; **Gate 17.2** retains CI/CD and workflow-authority hardening.

```text
Agents reason. Code verifies evidence.
Not every question is a RAG problem.
Structured facts use structured retrieval.
No unrestricted text-to-SQL.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
Intent classification != execution authority.
retrieved content != instruction authority
model proposal != authorization
tool/protocol success != business truth
historical evidence != standing authority
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

## Historical Phase 19 authority

Gate 19.1 was protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1`. Its historical machine-readable decision remains `DEFERRED_PENDING_MEASUREMENT`, with historical leading hypothesis `ASYNC_SUBMIT_STATUS_RESULT`.

The retained pre-runtime boundary remains explicitly documented as:

```text
PublicAnalysisAdmissionHandoff -> STOP
```

Gate 19.2 later supplied the representative evidence and selected `ASYNC_SUBMIT_STATUS_RESULT`. Historical artifacts retain the state they recorded when created; later gates do not rewrite them.

Canonical Gate 19.2 live evidence remains:

```text
artifact: labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
artifact SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
outcome: SUCCESS
end_to_end_duration_ms: 17748
serialized_result_bytes: 5285
retry count: 0 MEASURED
throttle count: 0 UNMEASURED
```

The successful baseline did not itself exceed 30 seconds. Async selection was based on provider-latency coupling, retry safety, backpressure, and failure isolation; derived retry scenarios remain explicitly `DERIVED`.

## Gate 19.3 — completed topology authority

Selected design:

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

Frozen lifecycle:

```text
SUBMITTING | ACCEPTED | RUNNING | SUCCEEDED | FAILED | EXPIRED
```

SQS remains at-least-once transport. DynamoDB conditional state/attempt authority owns duplicate admission and business execution truth.

## Gate 19.4 — completed disabled implementation

Gate 19.4 implemented the selected topology as typed/tested application code, narrow AWS adapters, separate API/worker Lambda composition, and Terraform with responsibility-separated IAM bindings.

Fail-closed defaults remain:

```text
public_async_runtime_materialized = false
disable execute-api endpoint:      true
new-job submit runtime switch:      false
worker runtime switch:              false
SQS -> worker event mapping:        false
worker reserved concurrency:        0
custom public domain:               absent
provider-heavy worker executor:     not composed
```

Canonical evidence remains:

```text
labs/phase-19-gate-19-4-disabled-async-runtime.md
labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json
scripts/verify_phase19_gate19_4_disabled_async_runtime.py
```

## Gate 19.5 — completed immutable artifact provenance

Gate 19.5 created exactly two content-addressed deployment-artifact object versions in the existing versioned deployment bucket after deterministic local rebuild and exact-head review.

```text
bucket: opslens-dev-artifacts-487757851499-us-east-1
region: us-east-1
account: 487757851499

API
  SHA-256:          99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e
  source_code_hash: mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=
  VersionId:        E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63
  publication:      CREATED

Worker
  SHA-256:          0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9
  source_code_hash: DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=
  VersionId:        sxiOdii4yFwR13t23xP5A8EU1JPV_7P1
  publication:      CREATED
```

Gate 19.5 evidence records `s3_put_object_mutation_count=2`, `automatic_retry_count=0`, zero runtime/IAM mutations, zero Terraform apply, and zero public endpoint enablement. The offline verifier proved:

```text
terraform_plan_input_ready=true
terraform_apply_authorized=false
```

Canonical evidence:

```text
labs/evidence/phase-19-gate-19-5-prepublication-v1.json
labs/evidence/phase-19-gate-19-5-artifact-publication-v1.json
labs/phase-19-gate-19-5-closeout.md
scripts/verify_phase19_gate19_5_artifact_publication.py
```

## Gate 19.6 — current exact-plan boundary

Gate 19.6 freezes the exact artifact coordinates into:

```text
labs/evidence/phase-19-gate-19-6-plan-input-v1.tfvars.json
```

The exact-plan verifier must admit only a Terraform plan whose managed non-no-op changes are exactly the 21 resources frozen by Gate 19.4, each with action `create`, with no update/delete/replace or unrelated managed drift.

The verifier additionally requires:

```text
API key + VersionId + source_code_hash: exact Gate 19.5 values
worker key + VersionId + source_code_hash: exact Gate 19.5 values
execute-api endpoint disabled: true
API submit switch: false
worker switch: false
SQS -> worker event source mapping: false
worker reserved concurrency: 0
custom public domain: absent
terraform_apply_authorized: false
```

The future human plan boundary may perform backend/provider reads only. The plan command must use `-lock=false` so the S3 backend lock object is not created/deleted by this gate. The binary plan and rendered JSON remain local under `/tmp`; only a bounded admitted summary may later be persisted.

## Current standing deployment truth

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

## Configured limits

These remain configuration, not measured utilization:

```text
API reserved concurrency          2     CONFIGURED_LIMIT
worker reserved concurrency       0     CONFIGURED_LIMIT
API Lambda timeout               15 s   CONFIGURED_LIMIT
worker Lambda timeout            60 s   CONFIGURED_LIMIT
queue visibility timeout        120 s   CONFIGURED_LIMIT
redrive receive count             4     CONFIGURED_LIMIT
worker max attempts               3     CONFIGURED_LIMIT
HTTP API burst limit             10     CONFIGURED_LIMIT
HTTP API rate limit               5     CONFIGURED_LIMIT
```

## Next checkpoint

Gate 19.6 must first finish exact-head offline/static/security validation on PR #356. Only after that reviewed head is frozen may the human operator generate the exact Terraform plan with backend/provider reads and `-lock=false`, render plan JSON locally, and run the offline verifier.

No gate currently authorizes `terraform apply`, runtime/public enablement, IAM mutation, or provider-heavy public execution.
