# OpsLens — Current State

_Last updated: 2026-09-11_

## Authoritative checkpoint

```text
protected main:
a5067e05fda74aad4d95d7f1a875110fb676304a

Phase 18 — Evaluation, Cost & Portfolio Readiness
status: COMPLETE
protected closeout PR: #290
protected closeout SHA: feca774535b7d83f57c26f4e9fe7da71ce268f0f

Phase 19 — Bounded Public Runtime & Productization
Gate 19.1 — Public Runtime Hypothesis & Launch Contract      COMPLETE
protected merge PR: #292
historical runtime decision: DEFERRED_PENDING_MEASUREMENT
historical leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT

Gate 19.2 — Representative Workload Measurement             COMPLETE
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

Gate 19.5 — Immutable Async Deployment Artifacts             IN PROGRESS
source issue: #352
implementation PR: #353
source main: a5067e05fda74aad4d95d7f1a875110fb676304a
publication authority: HUMAN_ONLY_CREATE_ONLY
runtime deployment authorized: NO
```

Phases 0–18 remain complete. Gate 19.1 remains historical launch-contract authority. Gate 19.2 supplied the admitted whole-workload measurement and selected `ASYNC_SUBMIT_STATUS_RESULT`. Gate 19.3 converted that interaction decision into one concrete AWS design contract. Gate 19.4 implemented that design in code and Terraform behind disabled/non-public defaults. Gate 19.5 now freezes deterministic API/worker Lambda artifacts and prepares a narrowly scoped human-only immutable S3 publication boundary so Gate 19.6 can later review an exact Terraform plan using real object `VersionId` coordinates.

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

## Gate 19.5 — current immutable-artifact checkpoint

Gate 19.5 exists to bridge a deliberate provenance dependency: Terraform needs an exact S3 `VersionId`, but a `VersionId` cannot exist until the immutable deployment object has been created.

The retained sequence is therefore:

```text
Gate 19.5  deterministic artifact build + human create-only artifact publication
Gate 19.6  exact Terraform plan + offline admission/review
later gate human-authorized Terraform apply / enablement, if admitted
```

The first Gate 19.5 deterministic build/rebuild verifier is green in CI and freezes these pre-publication identities:

```text
API Lambda
  SHA-256:            99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e
  source_code_hash:   mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=
  compressed bytes:   17271715
  uncompressed bytes: 26156069
  files:              2507
  S3 key:             lambda/public-analysis/api/sha256=99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e/opslens-public-async-api.zip

Worker Lambda
  SHA-256:            0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9
  source_code_hash:   DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=
  compressed bytes:   1036437
  uncompressed bytes: 3739031
  files:              352
  S3 key:             lambda/public-analysis/worker/sha256=0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9/opslens-public-async-worker.zip
```

Canonical pre-publication authority:

```text
labs/evidence/phase-19-gate-19-5-prepublication-v1.json
scripts/build_phase19_async_lambda_artifacts.py
scripts/verify_phase19_gate19_5_async_artifact_build.py
labs/phase-19-gate-19-5-immutable-artifact-publication-runbook.md
```

Before human publication, each S3 `VersionId` remains:

```text
classification: UNMEASURED
reason: PENDING_HUMAN_PUBLICATION
value: null
```

The future publication boundary is intentionally narrow: exactly two content-addressed ZIP objects, written create-only to the existing versioned deployment-artifacts bucket. CI and ChatGPT are not publication authorities. Publication success will establish immutable object coordinates only; it will not authorize runtime materialization, IAM mutation, Terraform apply, or public enablement.

## Current standing deployment truth

Protected `main` still has **no deployed public HTTP runtime**. Gate 19.4 added a disabled repository implementation; Gate 19.5 has not changed runtime AWS state.

```text
public endpoints enabled:                0
runtime AWS resources changed:           0
IAM roles/policies changed:              0
Terraform apply executions:              0
provider-heavy public executions:        0
third-party repository code executions:  0
PR #89 modifications:                    0
```

A future human Gate 19.5 publication may create only the two frozen deployment-artifact objects. That narrowly scoped artifact write is not a runtime-resource or deployment authorization.

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

Gate 19.5 must first finish exact-head static/security/CI validation and protected review of PR #353. The human AWS publication boundary is crossed only after the reviewed artifact identities are frozen and reproduced from the protected code checkpoint. The human operator must then publish exactly the admitted API and worker content-addressed objects, with no automatic retry or IAM broadening, and run the offline post-publication verifier.

Only admitted publication evidence containing the two real S3 `VersionId` values can make Gate 19.6 Terraform-plan input ready. Gate 19.6, not Gate 19.5, owns exact Terraform plan generation. No gate currently authorizes `terraform apply` or public enablement.