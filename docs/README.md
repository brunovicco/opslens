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

Phase 19 remains downstream of the Phase 17 security controls and the Phase 18 evidence closeout. Gate 17.1 established the evidence-first threat/control-gap inventory and Gate 17.2 hardened CI/CD and workflow authority. Protected-main security invariants, full-SHA external actions, Dependency Review, CodeQL, adversarial authority regression, content-minimized Lambda telemetry, and bounded operational recovery remain part of the retained platform authority chain.

Retained evidence semantics:

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
lab measurement != production SLO
responsibility -> required action -> exact resource -> IAM statement
queue delivery != business execution authority
provider retry != business retry authority
artifact hash != S3 VersionId
publication success != deployment authorization
AIP-C01 topic != product requirement
```

## Phase 18 closeout

Phase 18 is complete. Its protected closeout was squash-merged through PR #290 at:

```text
feca774535b7d83f57c26f4e9fe7da71ce268f0f
```

Historical artifacts intentionally preserve the state that existed when they were created. Current-facing documents carry later protected-main truth without rewriting historical evidence.

## Phase 19 — Bounded Public Runtime & Productization

Current protected lineage:

```text
19.1  Public Runtime Hypothesis & Launch Contract       COMPLETE
      PR #292 / ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1
      historical decision: DEFERRED_PENDING_MEASUREMENT

19.2  Representative Workload Measurement              COMPLETE
      PR #347 / 71eda2650889d3047259d37be226862ed2a09092
      measured E2E: 17,748 ms
      selected interaction: ASYNC_SUBMIT_STATUS_RESULT

19.3  Concrete Async Topology Contract                  COMPLETE
      PR #349 / 18d31c03d27448c88a6ffcba16683f3875a5ba15
      topology: HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
      deployment authorized: NO

19.4  Disabled Async Runtime Implementation             COMPLETE
      PR #351 / a5067e05fda74aad4d95d7f1a875110fb676304a
      runtime materialized by default: false
      deployment authorized: NO

19.5  Immutable Async Deployment Artifacts              CLOSEOUT IN REVIEW
      issue #352 / PR #353
      publication source head: 94af45036ba33007f45ddb69e9e6c3fa7d31d715
      S3 PutObject mutations: 2
      terraform plan input ready: YES
      runtime deployment authorized: NO
```

### Gate 19.1 — complete — historical launch contract

Gate 19.1 froze `public-analysis-workload:v1` and refused to select runtime topology before representative evidence existed. Its historical `DEFERRED_PENDING_MEASUREMENT` decision is preserved rather than rewritten.

Retained runtime decision: DEFERRED_PENDING_MEASUREMENT.

Canonical records:

- [`../labs/phase-19-gate-19-1-public-runtime-hypothesis.md`](../labs/phase-19-gate-19-1-public-runtime-hypothesis.md)
- [`../labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`](../labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json)
- [`adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md`](adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md)

### Gate 19.2 — complete — representative measurement

Gate 19.2 completed one human-operated representative live measurement, deterministic persisted-artifact review, and the evidence-backed interaction-pattern decision.

Canonical live artifact:

```text
labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
outcome: SUCCESS
```

Measured evidence included 17,748 ms end-to-end, four GitHub physical requests, one Bedrock Retrieve at 4,148 ms client elapsed, one model call at 8,901 ms client elapsed / 7,772 ms provider latency, 5,936 input + 408 output tokens, zero measured retries, `throttle_count` still `UNMEASURED`, and Athena request-time usage `NOT_APPLICABLE` for the retained path.

Selected interaction:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

Canonical closeout records:

- [`../labs/phase-19-gate-19-2-closeout.md`](../labs/phase-19-gate-19-2-closeout.md)
- [`../labs/evidence/phase-19-gate-19-2-closeout-v1.json`](../labs/evidence/phase-19-gate-19-2-closeout-v1.json)
- [`../scripts/verify_phase19_gate19_2_closeout.py`](../scripts/verify_phase19_gate19_2_closeout.py)

### Gate 19.3 — concrete async topology

Gate 19.3 selected:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

The frozen routes are:

```text
POST /v1/analyses
GET  /v1/analyses/{job_id}
GET  /v1/analyses/{job_id}/result
```

The design makes the DynamoDB/SQS dual-write boundary explicit, requires `Idempotency-Key`, treats SQS as at-least-once transport, uses DynamoDB conditional state/attempt authority, requires bounded retry and a DLQ, and separates API-handler IAM from worker/Bedrock IAM.

Canonical records:

- [`../labs/phase-19-gate-19-3-async-topology-contract.md`](../labs/phase-19-gate-19-3-async-topology-contract.md)
- [`../labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json`](../labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json)
- [`../scripts/verify_phase19_gate19_3_async_topology_contract.py`](../scripts/verify_phase19_gate19_3_async_topology_contract.py)

Gate 19.3 authorized no deployment.

### Gate 19.4 — completed disabled runtime implementation

Gate 19.4 was protected-merged through PR #351 at `a5067e05fda74aad4d95d7f1a875110fb676304a`.

It implemented the selected topology as typed/tested domain/application code, narrow AWS adapters, separate API/worker Lambda composition, and Terraform behind fail-closed defaults:

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

Gate 19.4 closed with zero Terraform apply, zero runtime AWS/IAM mutation, zero public endpoint enablement, and zero provider-heavy public execution.

Canonical records:

- [`../labs/phase-19-gate-19-4-disabled-async-runtime.md`](../labs/phase-19-gate-19-4-disabled-async-runtime.md)
- [`../labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json`](../labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json)
- [`../scripts/verify_phase19_gate19_4_disabled_async_runtime.py`](../scripts/verify_phase19_gate19_4_disabled_async_runtime.py)

### Gate 19.5 — immutable deployment artifacts — closeout in review

Gate 19.5 completed deterministic API/worker package production and one human-only create-only publication from exact reviewed head `94af45036ba33007f45ddb69e9e6c3fa7d31d715`.

Admitted immutable coordinates:

```text
API
  SHA-256: 99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e
  source_code_hash: mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=
  VersionId: E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63
  publication_status: CREATED

Worker
  SHA-256: 0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9
  source_code_hash: DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=
  VersionId: sxiOdii4yFwR13t23xP5A8EU1JPV_7P1
  publication_status: CREATED
```

The persisted publication evidence records two S3 `PutObject` mutations, zero automatic retries, and zero runtime resource/IAM/Terraform/public-endpoint mutations. The offline verifier admits these exact coordinates and reports `terraform_plan_input_ready=true` and `terraform_apply_authorized=false`.

Canonical Gate 19.5 records:

- [`../labs/evidence/phase-19-gate-19-5-prepublication-v1.json`](../labs/evidence/phase-19-gate-19-5-prepublication-v1.json)
- [`../labs/evidence/phase-19-gate-19-5-artifact-publication-v1.json`](../labs/evidence/phase-19-gate-19-5-artifact-publication-v1.json)
- [`../labs/phase-19-gate-19-5-immutable-artifact-publication-runbook.md`](../labs/phase-19-gate-19-5-immutable-artifact-publication-runbook.md)
- [`../labs/phase-19-gate-19-5-closeout.md`](../labs/phase-19-gate-19-5-closeout.md)
- [`../scripts/build_phase19_async_lambda_artifacts.py`](../scripts/build_phase19_async_lambda_artifacts.py)
- [`../scripts/verify_phase19_gate19_5_async_artifact_build.py`](../scripts/verify_phase19_gate19_5_async_artifact_build.py)
- [`../scripts/publish_phase19_gate19_5_async_artifacts.py`](../scripts/publish_phase19_gate19_5_async_artifacts.py)
- [`../scripts/verify_phase19_gate19_5_artifact_publication.py`](../scripts/verify_phase19_gate19_5_artifact_publication.py)

Protected merge/post-merge verification of PR #353 remains the final Gate 19.5 closeout boundary. Publication success is object provenance, not runtime deployment authority.

### Next boundary — Gate 19.6 exact Terraform plan

After Gate 19.5 protected closeout, Gate 19.6 may consume the exact S3 `Key + VersionId + source_code_hash` coordinates above to generate and admit an exact Terraform plan.

```text
Gate 19.5  deterministic build + human create-only immutable artifact publication
Gate 19.6  exact Terraform plan + offline admission/review
later gate human-authorized Terraform apply / controlled enablement, if admitted
```

No current gate authorizes `terraform apply`, public endpoint enablement, runtime worker enablement, or provider-heavy public execution.

## Evidence location rule

Canonical machine-readable artifacts live under `../labs/evidence/`. Human-readable experiment and closeout records live under `../labs/`. ADRs explain why a decision was made; labs/evidence record what was measured, proven, rejected, or intentionally left `UNMEASURED`.

Historical evidence is not rewritten merely to make it look current. Current-facing documents (`current-state.md`, `roadmap.md`, this index, and active runbooks) explain later superseding context while preserving original evidence lineage.

PR #89 remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency unless explicitly re-evaluated later.
