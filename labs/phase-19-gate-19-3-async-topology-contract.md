# Phase 19 Gate 19.3 — Concrete Async Topology Contract

Issue: #348  
Source protected main: `71eda2650889d3047259d37be226862ed2a09092`  
Source Gate 19.2 PR: #347  
Gate 19.2 decision: `ASYNC_SUBMIT_STATUS_RESULT`

## 1. Purpose

Gate 19.2 selected the async interaction pattern from admitted representative evidence. Gate 19.3 answers the next, narrower question:

> What is the smallest concrete AWS topology that can implement submit/status/result while preserving deterministic authority, bounded retries, backpressure, failure isolation, and least privilege?

This gate is **design authority only**. It creates no public endpoint, AWS resource, IAM role/policy, queue, table, function, model invocation, or third-party execution.

## 2. Evidence carried forward

Canonical live artifact:

```text
labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
```

Retained measurements:

```text
end-to-end                              17,748 ms    MEASURED
Bedrock Retrieve client elapsed          4,148 ms    MEASURED
Bedrock model client elapsed             8,901 ms    MEASURED
Bedrock provider latency                 7,772 ms    MEASURED
serialized admitted result               5,285 bytes MEASURED
GitHub physical HTTP requests                4        MEASURED
retry count                                  0        MEASURED
throttle count                               0        UNMEASURED
Athena request-time query/scan                0        NOT_APPLICABLE
```

The Gate 19.2 closeout also preserved the derived retry-safety scenario of `30,797 ms`; it remains `DERIVED`, not measured.

## 3. Decision

Gate 19.3 selects this logical topology for a later implementation gate:

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
       -> SQS dead-letter queue for poison/repeated delivery isolation

status/result reads
  -> Amazon API Gateway HTTP API
  -> API Lambda
  -> DynamoDB jobs table
```

Decision identifier:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

This is a topology selection, **not deployment authorization**.

## 4. Why this is the smallest credible shape

### API Gateway HTTP API

The product needs three bounded HTTP interactions: submit, status, and result. A managed API boundary keeps transport/routing/rate controls separate from business authority. Lambda Function URLs were rejected because they weaken that explicit public boundary. REST API was not selected because capabilities unique to REST API are not yet justified by the retained workload.

### API Lambda

The public control path is short and deterministic. It performs request admission, idempotency binding, job/status/result projection, and queue submission. It does **not** execute the measured 17.748-second analysis workload.

### SQS standard queue

Gate 19.2 selected async because provider latency must be isolated from the public request path and because retry/backpressure behavior matters. SQS provides explicit at-least-once buffering and a natural concurrency boundary for the worker.

A dead-letter queue is part of the selected queue contract so poison or repeatedly failing deliveries cannot redeliver forever. Application state still remains authoritative in DynamoDB; a DLQ record is operational evidence, not business truth by itself.

### Lambda worker

The admitted representative workload completed in 17.748 seconds. Nothing in the evidence requires container scheduling, long-running compute, GPU capacity, or a durable multi-step orchestrator. A bounded Lambda worker is therefore the smallest compute candidate supported by current evidence.

Fargate remains unselected because it adds operating surface without workload evidence. Step Functions Standard remains unselected because the current job is one linear admitted analysis operation rather than a workflow requiring durable business-step orchestration.

### DynamoDB jobs table

The admitted result is only 5,285 bytes. The product instead needs conditional state transitions, idempotency binding, small status/result reads, and expiry metadata. DynamoDB matches those requirements without introducing blob-oriented result storage.

DynamoDB Streams were not selected as the job queue. They can trigger the worker with fewer resource types, but that couples dispatch to persistence-stream semantics and provides weaker queue-specific control for retry, backpressure, and dead-letter behavior—the exact concerns that caused Gate 19.2 to select async isolation.

## 5. Public contract

### Submit

```http
POST /v1/analyses
Idempotency-Key: <opaque client token>
```

Success:

```text
202 Accepted
job_id
status_url
result_url
```

### Status

```http
GET /v1/analyses/{job_id}
```

State vocabulary:

```text
SUBMITTING
ACCEPTED
RUNNING
SUCCEEDED
FAILED
EXPIRED
```

### Result

```http
GET /v1/analyses/{job_id}/result
```

The result is available only after `SUCCEEDED`. Expired jobs return an explicit expired outcome; expiry must never be inferred from missing telemetry alone.

## 6. Idempotency and dual-write boundary

Submission cannot pretend that DynamoDB and SQS form one atomic transaction.

The handler therefore models the dual-write boundary explicitly:

```text
1. derive canonical request fingerprint
2. bind Idempotency-Key -> request fingerprint -> job_id
3. create/retain job as SUBMITTING with a bounded submission lease
4. send exactly one logical job message to SQS
5. move SUBMITTING -> ACCEPTED after successful send
```

Failure/recovery rules:

```text
same key + same fingerprint       -> return existing job
same key + different fingerprint  -> reject with HTTP 409
crash before SQS send             -> bounded SUBMITTING lease permits safe idempotent resubmission
crash after SQS send              -> worker may admit SUBMITTING -> RUNNING
SQS duplicate delivery            -> DynamoDB conditional state/attempt admission decides whether work may execute
```

The queue is transport authority for delivery, not authority for job state.

## 7. Worker retry and failure semantics

SQS is at-least-once. Duplicate delivery is expected, not exceptional.

Each delivery must acquire a deterministic attempt transition in DynamoDB before provider work. Provider retry policy remains explicitly bounded inside the worker. An application failure may either:

- persist a retryable attempt state and allow SQS redelivery; or
- persist terminal `FAILED` and acknowledge the message.

Uncaught/poison deliveries are bounded by queue redrive and isolated in the DLQ. A DLQ message does not silently rewrite job state; status remains derived from admitted DynamoDB state plus explicit expiry rules.

No automatic unbounded retry is authorized.

## 8. Backpressure and concurrency

Backpressure is owned by:

```text
SQS queue depth / age
+ Lambda event-source concurrency
+ Lambda reserved concurrency
+ worker retry ceiling
```

This prevents public request concurrency from directly becoming Bedrock concurrency.

No production concurrency value is claimed by this gate. Any future numeric setting is `CONFIGURED_LIMIT` until measured.

## 9. IAM responsibility split

### API handler role

Allowed design authority:

```text
sqs:SendMessage              selected job queue only
dynamodb:GetItem             selected jobs table only
dynamodb:PutItem             selected jobs table only
dynamodb:UpdateItem          selected jobs table only
dynamodb:TransactWriteItems  selected jobs table only
```

Explicitly not part of ingress authority:

```text
bedrock:Retrieve
bedrock:InvokeModel
sqs:ReceiveMessage
```

### Worker role

Allowed design authority:

```text
sqs:ReceiveMessage
sqs:DeleteMessage
sqs:ChangeMessageVisibility
sqs:GetQueueAttributes

dynamodb:GetItem
dynamodb:UpdateItem

bedrock:Retrieve     retained Knowledge Base BTVJ2PBR2A only
bedrock:InvokeModel  retained model/inference profile only
```

The exact deployable ARNs belong to Terraform outputs in the implementation gate. Gate 19.3 does not create or attach IAM policy.

Design rule:

```text
responsibility
 -> required action
 -> exact resource
 -> IAM statement
```

not:

```text
future feature aspiration
 -> broad runtime role
```

## 10. Observability boundary

Required operational fields include:

```text
request_id
job_id
trace_id
state_transition
attempt_number
stage
duration_ms
outcome
failure_category
provider_service_call_count
Bedrock token counts when available
retry_count
throttle_count
queue_age_ms
result_bytes
```

Forbidden telemetry remains:

```text
full prompt
repository source code
repository file contents
full model response
credentials
raw user payload
```

`UNMEASURED != zero` remains mandatory for throttling or any new metric that lacks an observation boundary.

## 11. Disable and recovery contract

The future implementation must provide independent controls for:

```text
disable new submit route
preserve status/result reads while submit is paused
disable SQS -> worker event source
set worker reserved concurrency to zero
disable model invocation at worker authorization/runtime guard
```

These controls do not constitute one global kill switch.

## 12. Candidate comparison

| Candidate | Decision | Evidence-bound reason |
|---|---|---|
| HTTP API + Lambda + SQS + Lambda + DynamoDB | **SELECTED** | Explicit queue/backpressure/retry isolation, small conditional state/result store, short worker runtime |
| HTTP API + Lambda + DynamoDB Streams + Lambda | Rejected | Fewer resource types, but dispatch is coupled to persistence-stream behavior and queue controls are weaker |
| HTTP API + Lambda + Step Functions Standard + Lambda | Rejected | Durable orchestration is credible but not justified for one linear analysis operation |
| Function URL + Lambda + SQS + Lambda + DynamoDB | Rejected | Weaker explicit public ingress/abuse-control boundary |
| HTTP API + Lambda + SQS + Fargate + DynamoDB | Rejected | Measured 17.748-second workload does not justify container orchestration |

No numerical score is manufactured. The decision follows retained requirements and measured workload characteristics.

## 13. Authority impact

Gate 19.3 remains design-only:

```text
public endpoints created:               0
new AWS resources created:              0
new IAM roles/policies created:         0
AWS/provider live executions:           0
third-party repository code executions: 0
PR #89 modifications:                   0
```

## 14. Next boundary

After protected merge of this contract, the next gate may implement the selected topology in Terraform and application adapters **behind disabled/non-public defaults**.

Before any public deployment, that implementation must produce:

- exact Terraform plan/resource inventory;
- exact least-privilege IAM policy review;
- deterministic lifecycle/idempotency tests;
- retry/backpressure/failure-injection tests;
- cost and concurrency configured limits clearly separated from measured utilization;
- explicit authorization for any human-run AWS apply or public enablement.

Gate 19.3 itself authorizes none of those mutations.
