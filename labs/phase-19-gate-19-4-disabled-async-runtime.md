# Phase 19 — Gate 19.4 Disabled Async Runtime Implementation

Status: implementation checkpoint for PR #351  
Issue: #350  
Source protected main: `18d31c03d27448c88a6ffcba16683f3875a5ba15`  
Selected Gate 19.3 design: `HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB`

## Purpose

Gate 19.4 materializes the Gate 19.3 topology as strictly typed application/domain code, narrow AWS adapters, and Terraform **behind disabled/non-public defaults**. It does not authorize deployment, AWS mutation, IAM creation, public endpoint enablement, or provider-heavy live execution.

The retained interaction contract is:

```text
POST /v1/analyses
GET  /v1/analyses/{job_id}
GET  /v1/analyses/{job_id}/result
```

and the retained lifecycle is:

```text
SUBMITTING -> ACCEPTED -> RUNNING -> SUCCEEDED
     |            |          |
     +----------> FAILED <----+
                              |
SUCCEEDED/FAILED ----------> EXPIRED
```

The exact transition authority is code-owned; the diagram is explanatory only.

## Implemented authority layers

### Domain and application

The async job domain now owns:

- deterministic job identity;
- hashed idempotency identity;
- canonical public-analysis request fingerprint;
- exact request coordinates required to reconstruct work without trusting queue payloads;
- exact state machine `SUBMITTING | ACCEPTED | RUNNING | SUCCEEDED | FAILED | EXPIRED`;
- optimistic version authority;
- bounded attempt accounting;
- submission and worker lease authority;
- admitted result bytes/hash metadata;
- terminal replay and expiry semantics.

Application services implement:

- submit;
- status;
- result;
- worker claim;
- success/failure completion;
- semantic idempotency conflict;
- duplicate-delivery no-op/concurrent-claim handling;
- recovery of an expired `SUBMITTING` lease without treating SQS publication as atomic with DynamoDB persistence.

The retained rule is:

```text
queue delivery != business execution authority
```

### AWS adapters

`DynamoDbAsyncJobStore` uses:

- one immutable idempotency alias record;
- one authoritative mutable job record;
- transactional initial binding;
- consistent reads;
- conditional optimistic updates.

`SqsAsyncJobPublisher` publishes only:

```json
{"job_id":"..."}
```

Repository coordinates, raw request payloads, source contents, prompts, and result contents are not copied into the queue message.

The HTTP API adapter admits only API Gateway HTTP API v2 events matching the three frozen routes. The SQS adapter admits only bounded records from the configured queue ARN/region and projects Lambda partial-batch failures deterministically.

### Lambda composition

The API Lambda composes only the control path. Provider-heavy repository/Bedrock execution does not run in submit/status/result handling.

The worker has a second fail-closed boundary:

```text
OPSLENS_ASYNC_WORKER_ENABLED=false   by default
provider executor composition         not admitted by Gate 19.4
```

If worker execution is enabled before that executor is explicitly composed, the Lambda wrapper rejects the configuration rather than silently constructing provider authority.

## Terraform materialization contract

All new Gate 19.4 resources are guarded by:

```hcl
public_async_runtime_materialized = false
```

The selected inventory is explicit:

```text
DynamoDB jobs/idempotency/result table
SQS standard job queue
SQS dead-letter queue
API Lambda
worker Lambda
SQS -> worker event-source mapping
API Gateway HTTP API
three frozen routes
CloudWatch API/worker/access log groups
API role/policy
worker role/policy
```

Even if a later human-authorized plan intentionally sets `public_async_runtime_materialized=true`, Gate 19.4 still retains:

```text
disable_execute_api_endpoint = true
OPSLENS_ASYNC_SUBMIT_ENABLED = false
OPSLENS_ASYNC_WORKER_ENABLED = false
SQS event source mapping enabled = false
worker reserved concurrency = 0
custom public domain = absent
```

Lambda artifacts additionally require an exact S3 key, exact `VersionId`, and source-code hash before Terraform may materialize them.

## IAM responsibility binding

API functional authority:

```text
sqs:SendMessage                         exact job queue
dynamodb:GetItem                       exact jobs table
dynamodb:PutItem                       exact jobs table
dynamodb:UpdateItem                    exact jobs table
dynamodb:TransactWriteItems            exact jobs table
```

It receives no Bedrock retrieval/invocation or SQS-consumer authority.

Worker functional authority:

```text
sqs:ReceiveMessage                     exact job queue
sqs:DeleteMessage                      exact job queue
sqs:ChangeMessageVisibility            exact job queue
sqs:GetQueueAttributes                 exact job queue
dynamodb:GetItem                       exact jobs table
dynamodb:UpdateItem                    exact jobs table
bedrock:Retrieve                       retained Knowledge Base
bedrock:InvokeModel                    retained inference profile/foundation models
```

It receives no queue-send, DynamoDB create/transaction/scan, or IAM-management authority.

CloudWatch Logs and X-Ray write permissions are separately treated as runtime-support authority rather than application/business authority.

## Configured limits

The following are design configuration, not utilization evidence:

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

None is relabeled `MEASURED`.

## Offline verification

Canonical machine-readable evidence:

```text
labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json
```

Verifier:

```text
scripts/verify_phase19_gate19_4_disabled_async_runtime.py
```

The verifier checks, without AWS credentials:

- Gate 19.3 design identity is unchanged;
- deployment authorization remains false;
- all mutation/execution counters remain zero;
- resource inventory is exact;
- every new resource is gated by the disabled materialization count;
- public execute-api remains disabled and no custom domain exists;
- API/worker IAM responsibility separation is preserved;
- configured limits remain `CONFIGURED_LIMIT`;
- runtime switches are fail-closed;
- provider-heavy worker composition remains unadmitted.

CI is limited to static/unit/Terraform validation/security checks and this offline evidence review. It assumes no AWS credentials and performs no provider live execution.

## Gate 19.4 safety boundary

```text
public endpoints enabled:                0
AWS resources created/changed/deleted:   0
IAM roles/policies created/changed:      0
AWS/provider live executions:            0
third-party repository code executions:  0
PR #89 modifications:                    0
```

## Next boundary

Gate 19.4 implementation is not deployment authority.

Before any AWS mutation, a later human-authorized gate must review an **exact Terraform plan**, artifact identities, concrete IAM/resource bindings, runtime enablement sequence, and rollback/disable path. Public ingress, new-job submission, queue consumption, and provider-heavy execution remain independently disabled until explicitly reviewed.
