# OpsLens — Current State

_Last updated: 2026-09-12_

## Authoritative checkpoint

```text
latest protected repository checkpoint:
PR: #373
protected main SHA: 8700478c7fca230e5984c3ce034194ea3bd337e4
post-merge CodeQL run: 34711607099 / run #382 / success

Phase 18 — Evaluation, Cost & Portfolio Readiness
status: COMPLETE
protected closeout PR: #290
protected closeout SHA: feca774535b7d83f57c26f4e9fe7da71ce268f0f

Phase 19 — Bounded Public Runtime & Productization
status: IN PROGRESS

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

Gate 19.4 — Disabled Async Runtime Implementation            COMPLETE
protected merge PR: #351
protected merge SHA: a5067e05fda74aad4d95d7f1a875110fb676304a

Gate 19.5 — Immutable Async Deployment Artifacts             COMPLETE
protected merge PR: #353
protected merge SHA: 61749bfac7b7bc9d032567e0b1870f8c1f7dedd4
publication status: ADMITTED
S3 PutObject mutation count: 2
API VersionId: E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63
worker VersionId: sxiOdii4yFwR13t23xP5A8EU1JPV_7P1

Gate 19.6 — Exact Terraform Plan & Offline Admission         COMPLETE
protected closeout PR: #360
protected closeout SHA: c76432dfcd97110ca43d91d77084f4367b9a89fd
human plan source head: d4d852c7ebc97f6fd9ee19d868fa12bc4ab031f2
plan JSON SHA-256: eb01396b92879243fd2e16e7791957e3289b459facc9db9524a4d890574aa83f
managed plan: 21 create / 0 update / 0 delete / 0 replacement

Gate 19.7 — Controlled Disabled Runtime Materialization      COMPLETE
source issue: #361 / closed completed
protected closeout PR: #372
protected closeout SHA: 21a5930fd770eddf26a5c7425ffcaddfdfa6d357
final current-state sync PR: #373
final protected main SHA: 8700478c7fca230e5984c3ce034194ea3bd337e4
final post-merge CodeQL: 34711607099 / run #382 / success
runtime materialized: YES
runtime enabled: NO
public endpoint enabled: NO
provider-heavy public execution enabled: NO

Gate 19.8 — Request-time Threat Evidence Authority Contract  IN PROGRESS
source issue: #374
implementation PR: #375 / draft
source protected main: 8700478c7fca230e5984c3ce034194ea3bd337e4
physical access decision: DEFERRED_PENDING_BOUNDED_RUNTIME_ADAPTER_EVIDENCE
AWS/Terraform/IAM/provider mutation authority: NONE
```

Gate 19.7 is formally complete. The asynchronous runtime resources are materialized in AWS but remain intentionally disabled/non-public. Gate 19.8 is an offline-only application-authority slice and does not grant standing authority for Terraform apply/replan, runtime enablement, public endpoint enablement, worker/event-source enablement, IAM mutation, quota mutation, provider-heavy execution, or custom-domain publication.

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency.

## Retained Phase 17 security lineage

Gate 17.1 — evidence-first threat/control-gap inventory — COMPLETE.  
Gate 17.2 — CI/CD and workflow authority hardening — COMPLETE.

Both remain authoritative. Later Phase 18/19 work adds no exception to their workflow, IAM, least-privilege, telemetry, or protected-main controls.

## Retained security and authority invariants

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
materialized != enabled
AIP-C01 topic != product requirement
```

## Historical Gate 19.1 authority

Gate 19.1 remains immutable historical evidence. Its protected decision was `DEFERRED_PENDING_MEASUREMENT`, its leading hypothesis was `ASYNC_SUBMIT_STATUS_RESULT`, and its retained pre-runtime boundary was:

```text
PublicAnalysisAdmissionHandoff -> STOP
```

Later gates do not rewrite that historical state.

## Gate 19.2 retained measurement evidence

Canonical live evidence remains:

```text
artifact: labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
artifact SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
outcome: SUCCESS
end_to_end_duration_ms: 17748
serialized_result_bytes: 5285
GitHub physical HTTP requests: 4 MEASURED
Athena query count: 0 NOT_APPLICABLE
Bedrock Retrieve count: 1 MEASURED
Bedrock Retrieve client elapsed ms: 4148 MEASURED
Bedrock model call count: 1 MEASURED
Bedrock input tokens: 5936 MEASURED
Bedrock output tokens: 408 MEASURED
Bedrock model client elapsed ms: 8901 MEASURED
Bedrock provider latency ms: 7772 MEASURED
retry count: 0 MEASURED
throttle count: 0 UNMEASURED
```

The successful baseline completed below 30 seconds. Async selection was based on provider-latency coupling, retry safety, backpressure, and failure isolation; derived retry scenarios remain explicitly `DERIVED`.

## Gate 19.3–19.4 retained runtime contract

Selected topology:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
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

Gate 19.4 implemented the topology as typed/tested application code, narrow AWS adapters, separate API/worker Lambda composition, and Terraform with responsibility-separated IAM bindings. The original Gate 19.4 historical defaults remain historical evidence and are not rewritten by later materialization.

## Gate 19.5 — immutable artifact provenance

Gate 19.5 created exactly two content-addressed deployment-artifact object versions in the existing versioned deployment bucket.

```text
bucket: opslens-dev-artifacts-487757851499-us-east-1
region: us-east-1
account: 487757851499

API
  SHA-256:          99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e
  source_code_hash: mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=
  VersionId:        E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63

Worker
  SHA-256:          0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9
  source_code_hash: DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=
  VersionId:        sxiOdii4yFwR13t23xP5A8EU1JPV_7P1
```

`artifact hash != S3 VersionId` remains authoritative.

## Gate 19.6 — exact-plan admission

Canonical admitted result:

```text
artifact: labs/evidence/phase-19-gate-19-6-plan-admission-v1.json
plan_json_sha256: eb01396b92879243fd2e16e7791957e3289b459facc9db9524a4d890574aa83f
managed creates: 21
updates: 0
deletes: 0
replacements: 0
execute-api endpoint disabled: true
API submit switch: false
SQS -> worker event source mapping: false
worker reserved concurrency: 0
terraform_apply_authorized: false
```

Gate 19.6 was planning evidence only and did not itself authorize or perform mutation.

## Gate 19.7 — controlled disabled materialization

Gate 19.7 separated resource materialization from runtime enablement and exercised the human-authorization boundary end to end.

### First authorized apply attempt

The first single-use human-authorized apply partially materialized the admitted runtime and then failed on API Lambda reserved concurrency `2` because the account concurrency limit could not preserve Lambda's required unreserved minimum.

```text
failure class: LAMBDA_RESERVED_CONCURRENCY_ACCOUNT_CONSTRAINT
operation: PutFunctionConcurrency
requested API reserved concurrency: 2
retry authorized: false
```

The failed plan was quarantined and never reused. Read-only reconciliation proved exactly 16 of the admitted 21 resources were managed and exactly five remained absent.

### Controlled recovery

Recovery changed the disabled API reserved concurrency target to `0`, retained worker reserved concurrency `0`, performed one controlled Terraform `untaint` after exact remote/state reconciliation, and regenerated a fresh recovery plan.

The admitted recovery plan was:

```text
source head: d6546e9d48253694e3e276940ebd2388f301d8ad
plan binary SHA-256: 48cb15a8466cc0ce77fdbe1d827b5a0aebb88460b8e8151d8c88d3c85eb9ea55
plan JSON SHA-256: 8a1f95ab8cbcbf96c708c6ced0d0127d862391a6f8e72c250fe5e7499d2a0bf7
managed creates: 5
managed updates: 1
managed deletes: 0
managed replacements: 0
```

The single authorized recovery apply completed:

```text
5 added
1 changed
0 destroyed
Terraform lineage: 6c958ab2-4cc6-7f96-a528-89535504f65c
state serial: 116 -> 117
```

Canonical post-apply evidence:

```text
labs/evidence/phase-19-gate-19-7-post-apply-verification-v1.json
```

It proves:

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

### Post-apply convergence

A separate single-use HUMAN-only convergence-plan authorization produced:

```text
No changes. Your infrastructure matches the configuration.
managed add/change/destroy/replace: 0 / 0 / 0 / 0
Terraform detailed exit code: 0
state lineage unchanged
state serial: 117 -> 117
state mutation observed: false
```

Convergence plan identities:

```text
plan binary SHA-256: 26380a6f09fc536f7738e1b855054e8a49183a24ae2e3711f6621a2c8c338157
plan JSON SHA-256: 505151c1d56f4d92483ad602185a49a89f10f1b9f6003eef9532cefcedf12f1d
resource_drift_entry_count: 5
```

`resource_drift_entry_count=5` is preserved exactly as observed. It is not interpreted as five required infrastructure changes: the same plan produced zero managed actions and Terraform's explicit no-changes result, and the bounded evidence did not retain the individual identities/semantics of those entries.

Canonical convergence evidence:

```text
labs/evidence/phase-19-gate-19-7-post-apply-convergence-v1.json
labs/phase-19-gate-19-7-closeout.md
```

Protected closeout PR #372 merged at `21a5930fd770eddf26a5c7425ffcaddfdfa6d357`. Final current-state synchronization PR #373 merged at `8700478c7fca230e5984c3ce034194ea3bd337e4`; final post-merge CodeQL run `34711607099` (run #382) completed successfully on that exact protected `main` SHA. Issue #361 is closed as completed.

## Gate 19.8 — request-time threat evidence authority

Gate 19.8 issue #374 freezes the smallest missing authority before any provider-heavy async-worker composition can be considered.

The live repository proves that:

- `AsyncAnalysisExecutor` and deterministic worker claim/attempt/terminalization authority already exist;
- the Lambda worker intentionally rejects `OPSLENS_ASYNC_WORKER_ENABLED=true` before provider composition;
- the only complete provider-heavy path is the Gate 19.2 representative harness;
- that harness uses one frozen repository plus preloaded threat evidence and is not an arbitrary public-request executor;
- no general request-time loader currently maps an admitted arbitrary dependency inventory to exact GHSA/NVD/KEV/EPSS authority.

Gate 19.8 therefore freezes this provider-neutral application boundary:

```text
PublicRepositoryEvidenceExecution
 -> PublicThreatEvidenceScope
 -> PublicThreatEvidenceRequest
 -> PublicThreatEvidenceAuthority
 -> PublicRepositoryThreatEvidence
 -> retained deterministic Phase 3/4 correlation/enrichment
```

The exact dependency scope preserves canonical package/version/purl identities and source-record indexes while exposing deduplicated package names only as a bounded lookup projection. Incomplete Phase 3 PyPI normalization fails closed.

Returned source authority must preserve exact source-local provenance:

```text
GHSA: observed_advisory_version_id
NVD:  observed_cve_version_id
KEV:  exact snapshot_date + source SHA-256
EPSS: exact snapshot_date + source SHA-256
```

A `latest_complete` request is a deterministic selection policy only. It does not erase the exact selected coordinates returned by the authority.

The physical provider adapter remains explicitly:

```text
DEFERRED_PENDING_BOUNDED_RUNTIME_ADAPTER_EVIDENCE
```

Glue/Athena and exact S3 source objects remain candidate surfaces. The repository does not yet contain a measured arbitrary request-time structured-threat path, and the current worker IAM does not grant Athena/Glue or threat-data S3 read authority. No provider adapter is selected by preference.

Gate 19.8 authority impact remains zero for Terraform/provider operations, AWS/IAM mutation, artifact publication, runtime enablement, provider execution, third-party code execution, and PR #89 modification.

## Current standing deployment truth

```text
deployment artifact S3 PutObject mutations: 2
public async runtime resources materialized: 21 managed resources
Terraform apply invocations in Gate 19.7: 2
  - first apply: failed after partial materialization; retry forbidden
  - recovery apply: succeeded with 5 add / 1 change / 0 destroy
post-apply convergence plan: 0 add / 0 change / 0 destroy / 0 replacement
Terraform state lineage: 6c958ab2-4cc6-7f96-a528-89535504f65c
Terraform state serial: 117
public endpoints enabled: 0
submit path enabled: NO
worker enabled: NO
event-source mapping enabled: NO
custom public domain: absent
provider-heavy public executions: 0
third-party repository code executions: 0
PR #89 modifications: 0
```

The existence of API Gateway routes/integration, Lambda functions, SQS, DynamoDB, IAM roles/policies, and Lambda permission is materialization evidence only. It does not mean the public runtime is reachable or authorized to execute provider-heavy work.

## Current configured disabled controls

These are configuration, not measured utilization:

```text
API reserved concurrency          0     CONFIGURED_LIMIT
worker reserved concurrency       0     CONFIGURED_LIMIT
API Lambda timeout               15 s   CONFIGURED_LIMIT
worker Lambda timeout            60 s   CONFIGURED_LIMIT
queue visibility timeout        120 s   CONFIGURED_LIMIT
redrive receive count             4     CONFIGURED_LIMIT
worker max attempts               3     CONFIGURED_LIMIT
HTTP API burst limit             10     CONFIGURED_LIMIT
HTTP API rate limit               5     CONFIGURED_LIMIT
```

## Next authority boundary

Gate 19.8 is offline-only. Its contract does **not** authorize a physical request-time structured-threat adapter, Terraform/provider operation, AWS/IAM mutation, artifact publication, worker composition, or runtime enablement.

The next bounded decision after Gate 19.8 must compare the smallest provider-backed structured-threat alternatives and freeze exact read/query semantics, resource/IAM scope, limits, failure behavior, observability, and measurement criteria. Only after that offline contract exists can a separate HUMAN authorization be requested for any live provider read/measurement or mutation that the selected gate requires.

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

`materialized != enabled` remains the controlling Phase 19 runtime invariant.
