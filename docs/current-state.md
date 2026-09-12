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
source issue: #352
protected merge PR: #353
protected merge SHA: 61749bfac7b7bc9d032567e0b1870f8c1f7dedd4
reviewed publication source head: 94af45036ba33007f45ddb69e9e6c3fa7d31d715
publication authority: HUMAN_ONLY_CREATE_ONLY
publication status: ADMITTED
S3 PutObject mutation count: 2
API VersionId: E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63
worker VersionId: sxiOdii4yFwR13t23xP5A8EU1JPV_7P1
terraform plan input ready: YES
terraform apply authorized: NO
post-merge CodeQL: completed / success
runtime deployment authorized: NO

Gate 19.6 — Exact Terraform Plan & Offline Admission         NEXT
terraform apply authorized: NO
```

Phases 0–18 remain complete. Gate 19.1 remains historical launch-contract authority. Gate 19.2 supplied the admitted whole-workload measurement and selected `ASYNC_SUBMIT_STATUS_RESULT`. Gate 19.3 converted that interaction decision into one concrete AWS design contract. Gate 19.4 implemented that design in code and Terraform behind disabled/non-public defaults. Gate 19.5 admitted exactly two human-published, create-only, content-addressed Lambda artifact versions, protected-merged them through PR #353, and passed post-merge CodeQL on the exact protected-main SHA. Gate 19.6 is now the next gate and may use those immutable coordinates only for exact Terraform planning and offline admission; no apply is authorized.

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency.

## Retained security and authority invariants

Phase 17 security controls remain authoritative for CI/CD authority, dependency/code scanning, adversarial regression, telemetry minimization, and bounded operational recovery. **Gate 17.1** retains the evidence-first security threat/control-gap inventory; **Gate 17.2** retains CI/CD and workflow-authority hardening. Phase 19 adds no exception.

Permanent boundaries remain:

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

Gate 19.1 retained the pre-runtime `PublicAnalysisAdmissionHandoff -> STOP` boundary: request admission and handoff could be reasoned about, but provider-heavy public execution remained unauthorized until later gates supplied evidence and explicit authority.

Gate 19.2 later supplied the missing representative evidence. Historical artifacts retain the state they recorded when created; later gates do not rewrite them.

Gate 19.2 was protected-merged through PR #347 at `71eda2650889d3047259d37be226862ed2a09092`. The canonical human-operated representative run recorded:

```text
artifact: labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
artifact SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
outcome: SUCCESS

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

The successful baseline did not itself exceed 30 seconds. The async decision followed provider-latency coupling, retry safety, backpressure, and failure isolation. The retained retry-safety scenario remains explicitly derived:

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

## Gate 19.3 — completed topology authority

Gate 19.3 was protected-merged through PR #349 at `18d31c03d27448c88a6ffcba16683f3875a5ba15`.

Selected design identifier:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

Selected logical shape:

```text
public client
  -> Amazon API Gateway HTTP API
  -> API Lambda
       -> DynamoDB jobs/idempotency table
       -> SQS standard job queue
            -> Lambda worker
                 -> retained OpsLens deterministic authorities
                 -> bounded Bedrock Retrieve + model path
                 -> deterministic final result admission
                 -> DynamoDB status/result update
       -> SQS dead-letter queue

status/result reads
  -> Amazon API Gateway HTTP API
  -> API Lambda
  -> DynamoDB jobs table
```

Frozen routes:

```text
POST /v1/analyses
GET  /v1/analyses/{job_id}
GET  /v1/analyses/{job_id}/result
```

Frozen lifecycle:

```text
SUBMITTING
ACCEPTED
RUNNING
SUCCEEDED
FAILED
EXPIRED
```

Queue semantics are at-least-once. DynamoDB conditional state/attempt authority, not SQS delivery, owns duplicate admission and business execution truth. Gate 19.3 authorized no deployment.

## Gate 19.4 — completed disabled implementation

Gate 19.4 was protected-merged through PR #351 at `a5067e05fda74aad4d95d7f1a875110fb676304a`.

It implemented the selected topology without applying it. The protected implementation contains deterministic job/idempotency authority, the exact async state machine, optimistic version/CAS authority, bounded attempts and leases, submit/status/result and worker claim/completion use cases, DynamoDB/SQS adapters, strict HTTP/SQS admission, separate API/worker Lambda composition, and Terraform with exact responsibility-separated IAM bindings.

Terraform remains fail-closed by default:

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

Lambda resources require exact S3 key, exact object `VersionId`, and exact Lambda `source_code_hash` before materialization. Gate 19.4 performed no `terraform apply` and authorized no deployment.

Canonical Gate 19.4 evidence remains historical and unchanged:

```text
labs/phase-19-gate-19-4-disabled-async-runtime.md
labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json
scripts/verify_phase19_gate19_4_disabled_async_runtime.py
```

## Gate 19.5 — immutable-artifact publication complete

Gate 19.5 bridged the deliberate provenance dependency between deterministic Lambda packages and exact Terraform planning. The publication occurred only after exact-head CI/security validation and a local byte-for-byte rebuild against the canonical pre-publication manifest.

Frozen identities and immutable publication coordinates are:

```text
API Lambda
  SHA-256:            99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e
  source_code_hash:   mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=
  compressed bytes:   17271715
  VersionId:          E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63
  publication:        CREATED

Worker Lambda
  SHA-256:            0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9
  source_code_hash:   DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=
  compressed bytes:   1036437
  VersionId:          sxiOdii4yFwR13t23xP5A8EU1JPV_7P1
  publication:        CREATED
```

Canonical Gate 19.5 evidence:

```text
labs/evidence/phase-19-gate-19-5-prepublication-v1.json
labs/evidence/phase-19-gate-19-5-artifact-publication-v1.json
labs/phase-19-gate-19-5-immutable-artifact-publication-runbook.md
labs/phase-19-gate-19-5-closeout.md
scripts/build_phase19_async_lambda_artifacts.py
scripts/verify_phase19_gate19_5_async_artifact_build.py
scripts/publish_phase19_gate19_5_async_artifacts.py
scripts/verify_phase19_gate19_5_artifact_publication.py
```

The human publication evidence records exactly two S3 `PutObject` mutations and zero automatic retries. Offline admission proved `terraform_plan_input_ready=true` while retaining `terraform_apply_authorized=false`. PR #353 protected-merged this evidence and implementation to `61749bfac7b7bc9d032567e0b1870f8c1f7dedd4`; post-merge CodeQL for that exact SHA completed successfully.

## Current standing deployment truth

Protected `main` still has **no deployed public HTTP runtime**. Gate 19.5 changed only deployment-artifact object provenance; it did not materialize runtime resources.

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

Current Gate 19.4 values remain configuration only:

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

They are not measured utilization.

## Next checkpoint

Gate 19.6 — Exact Terraform Plan & Offline Admission is next. It may generate an exact Terraform plan with `public_async_runtime_materialized=true` using the admitted Gate 19.5 `Key + VersionId + source_code_hash` coordinates, then parse and admit that plan offline against the frozen topology, IAM, disablement, concurrency, cost, and rollback policy.

Gate 19.6 is planning evidence only. `terraform plan != terraform apply`; plan success is not deployment authorization. No current gate authorizes `terraform apply`, runtime/public enablement, or provider-heavy public execution.
