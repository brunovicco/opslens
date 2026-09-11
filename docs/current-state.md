# OpsLens — Current State

_Last updated: 2026-09-11_

## Authoritative checkpoint

```text
protected main:
18d31c03d27448c88a6ffcba16683f3875a5ba15

Phase 18 — Evaluation, Cost & Portfolio Readiness
status: COMPLETE
protected closeout PR: #290

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

Gate 19.3 — Concrete Async Topology Contract                  COMPLETE
protected merge PR: #349
protected merge SHA: 18d31c03d27448c88a6ffcba16683f3875a5ba15
selected design topology: HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
deployment authorized: NO

Gate 19.4 — Disabled Async Runtime Implementation             IN PROGRESS
source issue: #350
implementation PR: #351
source main: 18d31c03d27448c88a6ffcba16683f3875a5ba15
deployment authorized: NO
```

Phases 0–18 remain complete. Gate 19.1 remains historical launch-contract authority. Gate 19.2 supplied the admitted whole-workload measurement and selected `ASYNC_SUBMIT_STATUS_RESULT`. Gate 19.3 converted that interaction decision into one concrete AWS design contract. Gate 19.4 is implementing that design in code and Terraform behind disabled/non-public defaults and still creates no deployment authority.

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency.

## Retained security and authority invariants

Phase 17 security controls remain authoritative for CI/CD authority, dependency/code scanning, adversarial regression, telemetry minimization, and bounded operational recovery. Phase 19 adds no exception.

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
AIP-C01 topic != product requirement
```

## Historical Phase 19 authority

Gate 19.1 was protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1`. Its historical machine-readable decision remains:

```text
DEFERRED_PENDING_MEASUREMENT
```

with historical leading hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

Gate 19.2 later supplied the missing representative evidence. Historical artifacts retain the state they recorded when created; later gates do not rewrite them.

Gate 19.2 was protected-merged through PR #347 at `71eda2650889d3047259d37be226862ed2a09092`. The canonical human-operated representative run recorded:

```text
artifact: labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
artifact SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
outcome: SUCCESS
```

Measured whole-workload evidence:

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

Frozen future interaction contract:

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

Queue semantics are at-least-once. DynamoDB conditional state/attempt authority, not SQS delivery, owns duplicate admission and business execution truth.

Canonical Gate 19.3 evidence:

```text
labs/phase-19-gate-19-3-async-topology-contract.md
labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json
scripts/verify_phase19_gate19_3_async_topology_contract.py
```

Gate 19.3 authorized no deployment.

## Gate 19.4 — implementation checkpoint

Gate 19.4 implements the selected topology without applying it.

### Domain and application authority

The implementation now includes:

```text
deterministic job identity
hashed idempotency identity
canonical public request fingerprint
persisted exact request coordinates
exact async state machine
optimistic version/CAS authority
bounded attempt accounting
submission and worker leases
submit/status/result use cases
worker claim/completion use cases
idempotency conflict semantics
duplicate-delivery no-op/concurrent-claim semantics
expired-result semantics
queue-publication failure terminalization
```

The job record remains business authority. Queue delivery is only transport evidence.

### AWS adapter and Lambda boundaries

Implemented adapters include:

```text
DynamoDB transactional/conditional job store
SQS publisher with {"job_id": ...} only
strict API Gateway HTTP API v2 admission
strict SQS event admission + partial batch response
API Lambda control-path composition
worker Lambda fail-closed composition
```

The API Lambda performs no provider-heavy analysis. The worker refuses enablement until a provider-heavy executor is separately admitted and composed.

### Terraform fail-closed defaults

Gate 19.4 Terraform materializes nothing by default:

```text
public_async_runtime_materialized = false
```

All new Gate 19.4 resources are gated by that count. Even if a later plan intentionally materializes them, this gate retains:

```text
disable execute-api endpoint:      true
new-job submit runtime switch:      false
worker runtime switch:              false
SQS -> worker event mapping:        false
worker reserved concurrency:        0
custom public domain:               absent
provider-heavy worker executor:     not composed
```

Lambda artifacts require exact S3 key, exact object `VersionId`, and exact source-code hash before materialization.

Terraform inventory represented in PR #351:

```text
DynamoDB jobs/idempotency/result table
SQS standard job queue
SQS DLQ + redrive allow policy
API Lambda
worker Lambda
SQS event-source mapping
API Gateway HTTP API + integration + three routes + stage
Lambda invoke permission for API Gateway
CloudWatch API/worker/access log groups
separate API and worker IAM roles/policies
```

No `terraform apply` has been authorized or performed by Gate 19.4.

### Exact IAM responsibility split

API business authority is limited to the exact job queue and jobs table:

```text
sqs:SendMessage
dynamodb:GetItem
dynamodb:PutItem
dynamodb:UpdateItem
dynamodb:TransactWriteItems
```

It receives no Bedrock retrieval/invocation or SQS-consumer authority.

Worker business authority is limited to queue consumption, exact jobs-table state updates, retained Knowledge Base retrieval, and retained model invocation:

```text
sqs:ReceiveMessage
sqs:DeleteMessage
sqs:ChangeMessageVisibility
sqs:GetQueueAttributes
dynamodb:GetItem
dynamodb:UpdateItem
bedrock:Retrieve
bedrock:InvokeModel
```

It receives no queue-send, DynamoDB create/transaction/scan, or IAM-management authority. CloudWatch Logs and X-Ray writes are separate runtime-support authority.

### Configured limits

Current Gate 19.4 values are configuration only:

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

### Gate 19.4 evidence

Canonical implementation/readiness evidence in PR #351:

```text
labs/phase-19-gate-19-4-disabled-async-runtime.md
labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json
scripts/verify_phase19_gate19_4_disabled_async_runtime.py
```

The verifier is offline-only and checks design identity, zero mutation/execution authority, exact resource inventory, fail-closed defaults, IAM responsibility separation, configured-limit classification, and the uncomposed provider-heavy worker boundary.

## Retained public-analysis boundary

Protected `main` at the Gate 19.3 merge still has **no deployed public HTTP runtime**. PR #351 contains a disabled implementation only.

Therefore the standing deployment truth remains:

```text
public endpoints enabled:                0
AWS resources created/changed/deleted:   0
IAM roles/policies created/changed:      0
AWS/provider live executions:            0
third-party repository code executions:  0
PR #89 modifications:                    0
```

## Current representative anchor

The Gate 19.2 measurement anchor remains historical reproducibility evidence:

```text
repository:      openedx/mockprock
repository URL:  https://github.com/openedx/mockprock
commit/ref:      18c954d8604df4740c829ba17fa2f3640b92b900
evidence file:  uv.lock
dependency:     webob==1.8.10
GHSA anchor:    GHSA-6hx8-3wjj-gr8g
CVE anchor:     CVE-2026-54770
```

It is not runtime-exposure evidence and is not a standing requirement for every future public job.

## Next checkpoint

Gate 19.4 can close only after the exact implementation is independently green in Python/static/security/Terraform validation and protected merge/post-merge verification completes.

Gate 19.4 still does **not** authorize deployment. A later human-authorized gate must review an exact Terraform plan before any AWS mutation, including concrete artifact identities, IAM/resource bindings, enablement sequence, and rollback/disable controls.
