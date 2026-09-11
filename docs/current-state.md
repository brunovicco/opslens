# OpsLens — Current State

_Last updated: 2026-09-11_

## Authoritative checkpoint

```text
protected main:
71eda2650889d3047259d37be226862ed2a09092

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

Gate 19.3 — Concrete Async Topology Contract                 IN PROGRESS
source issue: #348
draft PR: #349
selected design topology: HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
deployment authorized: NO
```

Phases 0–18 remain complete. Gate 19.1 is historical launch-contract authority. Gate 19.2 is now protected-merged and complete. Gate 19.3 selects the smallest concrete async topology as **design authority only**; it does not deploy or authorize a public runtime. PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency.

## Retained Phase 17 security lineage

**Gate 17.1** established the evidence-first threat/control-gap inventory. **Gate 17.2** hardened CI/CD and workflow authority and introduced the retained `Repository security invariants` protected-main context. Later Phase 17 controls remain authoritative for dependency/code scanning, adversarial regression, telemetry minimization, and bounded scheduled-ingestion recovery. Phase 19 adds no exception to those controls.

## Historical authority that must not be rewritten

Phase 18 was protected-squash-merged through PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`.

Gate 19.1 was protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1`. Its historical machine-readable decision remains:

```text
DEFERRED_PENDING_MEASUREMENT
```

with historical leading hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

Gate 19.2 later supplied the missing representative evidence and selected that interaction pattern. Historical artifacts retain the state they recorded when created; current-facing documentation advances separately.

## Retained platform architecture

OpsLens retains one AWS `dev` environment in `us-east-1`, source-preserving threat intelligence, deterministic vulnerability applicability and repository correlation, Risk Policy v1, bounded semantic planning with compiler-owned Athena SQL, Amazon Bedrock Knowledge Bases with Amazon S3 Vectors, deterministic hybrid evidence composition, bounded Bedrock synthesis, agent/capability authority contracts, offline MCP/A2A interoperability, optional-lab AgentCore evidence, bounded Inspector read contracts, content-minimized observability, Phase 17 security/recovery controls, and the Phase 18 evaluation/cost/portfolio evidence chain.

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
AIP-C01 topic != product requirement
```

## Retained public-analysis boundary

The protected-main public-analysis application path still stops before a deployed public product runtime:

```text
untrusted JSON
 -> strict request admission
 -> validated GitHub coordinates
 -> immutable repository snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic dependency normalization
 -> bounded metadata-only semantic planning
 -> deterministic Phase 8 route admission
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

`execute_instrumented_public_analysis` emits bounded operational evidence for that retained path and still returns the handoff. There is no protected public HTTP endpoint, public application compute, queue, public result store, or public runtime IAM.

## Gate 19.2 completed representative evidence

The exact nine-stage representative composition was:

```text
public_request_admission
repository_acquisition
dependency_evidence
vulnerability_correlation
risk_prioritization
structured_evidence
semantic_evidence
model_reasoning
result_admission
```

The human-operated run used source protected main `e45ba419414e6dd77ecad68f4d2312e9123c2223` and produced:

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

The selected interaction pattern is:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The successful baseline did not itself exceed 30 seconds. The decision instead follows provider-latency coupling, retry safety, backpressure, and failure isolation. The retained derived scenario remains explicitly separate from measurement:

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

Gate 19.2 was protected-merged through PR #347 at `71eda2650889d3047259d37be226862ed2a09092`. The protected merge preserved the exact canonical live artifact bytes. The exact-head PR merge and protected merge had the same Git tree, and post-merge CodeQL completed successfully.

Canonical closeout evidence:

```text
labs/phase-19-gate-19-2-closeout.md
labs/evidence/phase-19-gate-19-2-closeout-v1.json
scripts/verify_phase19_gate19_2_closeout.py
```

## Gate 19.3 design decision

Gate 19.3 asks only which concrete AWS topology best implements `ASYNC_SUBMIT_STATUS_RESULT` under the evidence already admitted.

Selected design identifier:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

Logical shape:

```text
public client
  -> Amazon API Gateway HTTP API
  -> API Lambda
       -> DynamoDB jobs/idempotency table
       -> SQS standard job queue
            -> Lambda worker
                 -> retained deterministic repository/risk authority
                 -> Bedrock Knowledge Base Retrieve
                 -> retained bounded model invocation
                 -> deterministic final result admission
                 -> DynamoDB status/result update
       -> SQS dead-letter queue

status/result reads
  -> Amazon API Gateway HTTP API
  -> API Lambda
  -> DynamoDB jobs table
```

Why this shape is selected:

- API Gateway HTTP API provides an explicit managed public transport/rate boundary without selecting REST-only capabilities that are not justified yet;
- the API Lambda keeps public request admission, idempotency, and job projection separate from provider-heavy analysis;
- SQS directly addresses the retry/backpressure/failure-isolation reasons behind Gate 19.2's async decision;
- the measured `17,748 ms` worker path does not justify Fargate or another container scheduler;
- the measured `5,285`-byte admitted result fits a small conditional state/result record, while DynamoDB provides idempotency and state-transition authority;
- Step Functions Standard and DynamoDB Streams are credible alternatives but add or couple semantics not required by the current single linear analysis job.

No numerical architecture score is manufactured.

## Gate 19.3 public interaction contract

Future routes, still **not deployed**:

```text
POST /v1/analyses
GET  /v1/analyses/{job_id}
GET  /v1/analyses/{job_id}/result
```

Job states:

```text
SUBMITTING
ACCEPTED
RUNNING
SUCCEEDED
FAILED
EXPIRED
```

DynamoDB conditional writes are the planned job-state authority. SQS delivery is at-least-once transport evidence and does not become business truth.

Idempotency requires `Idempotency-Key` plus a canonical request fingerprint:

```text
same key + same fingerprint       -> return existing job
same key + different fingerprint  -> HTTP 409
```

The `SUBMITTING` state explicitly models the DynamoDB/SQS dual-write boundary instead of pretending the two services form an atomic transaction.

## Gate 19.3 retry/backpressure authority

```text
queue semantics:       AT_LEAST_ONCE
worker batch size:     1
retry ownership:       SQS/Lambda event source + bounded worker policy
duplicate authority:   DynamoDB conditional state/attempt admission
DLQ:                   REQUIRED by design contract
unbounded retry:       FORBIDDEN
backpressure:          SQS queue depth/age + Lambda reserved concurrency
```

Future numeric queue/concurrency/retry settings remain `CONFIGURED_LIMIT` until measured.

## Gate 19.3 IAM responsibility split

Planned ingress/API role authority is limited to the selected queue and jobs table:

```text
sqs:SendMessage
dynamodb:GetItem
dynamodb:PutItem
dynamodb:UpdateItem
dynamodb:TransactWriteItems
```

It explicitly does not receive `bedrock:Retrieve`, `bedrock:InvokeModel`, or `sqs:ReceiveMessage`.

Planned worker role authority is limited to queue consumption, exact jobs-table updates, retained Knowledge Base retrieval, and retained model invocation:

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

Exact deployable ARNs belong to the implementation/Terraform gate. Gate 19.3 creates no IAM role or policy.

## Gate 19.3 observability and recovery

Required operational fields include `request_id`, `job_id`, `trace_id`, state transition, attempt number, queue age, stage duration, provider call counts, token counts when available, retries, throttles, outcome, failure category, and result bytes.

Forbidden telemetry still includes full prompts, repository source/file contents, full model responses, credentials, and raw user payloads.

Future disable/recovery must independently support:

```text
disable new submit route
preserve status/result reads during submit pause
disable queue -> worker event source
set worker reserved concurrency to zero
disable model invocation at worker authorization/runtime guard
```

No global kill switch is claimed.

## Gate 19.3 safety boundary

```text
public endpoints created:               0
new AWS resources created:              0
new IAM roles/policies created:         0
AWS/provider live executions:           0
third-party repository code executions: 0
PR #89 modifications:                   0
```

Canonical design evidence:

```text
labs/phase-19-gate-19-3-async-topology-contract.md
labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json
scripts/verify_phase19_gate19_3_async_topology_contract.py
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

After Gate 19.3 is protected-merged, the next gate may implement the selected topology in Terraform and application adapters **behind disabled/non-public defaults**.

Before any public deployment that implementation must provide:

1. exact Terraform plan and resource inventory;
2. exact least-privilege IAM policies bound to concrete ARNs;
3. deterministic lifecycle/idempotency tests;
4. duplicate-delivery, retry, backpressure, and failure-injection tests;
5. content-minimized telemetry tests;
6. explicit configured cost/concurrency ceilings distinct from measured utilization;
7. separate human authorization for any AWS apply or public enablement.

Gate 19.3 itself authorizes none of those mutations.
