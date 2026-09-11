# OpsLens — Incremental Roadmap

_Last updated: 2026-09-11_

The roadmap is evidence-gated. A later phase does not invalidate earlier authority boundaries, and certification topics do not automatically become product requirements.

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

### Retained lineage

Phase 17 security controls remain authoritative. **Gate 17.1** established the evidence-first threat/control-gap inventory, and **Gate 17.2** hardened CI/CD and workflow authority. Later Phase 17 controls remain part of the protected security lineage.

Phase 18 was protected-squash-merged through PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`.

Gate 19.1 was protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1`. Its historical decision remains `DEFERRED_PENDING_MEASUREMENT` and its historical leading hypothesis remains `ASYNC_SUBMIT_STATUS_RESULT`.

Gate 19.2 was protected-merged through PR #347 at `71eda2650889d3047259d37be226862ed2a09092` after one admitted human-operated representative run and deterministic closeout verification.

Gate 19.3 was protected-merged through PR #349 at `18d31c03d27448c88a6ffcba16683f3875a5ba15`, selecting `HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB` as the concrete implementation topology while explicitly withholding deployment authority.

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work. Phase 19 does not rebase, merge, modify, or depend on it.

## Phase 19 — Bounded Public Runtime & Productization

### Goal

Move from the retained Phase 9 application boundary toward the smallest safe, measurable public product surface while preserving deterministic authority boundaries, least privilege, fail-closed defaults, and explicit human review before AWS mutation.

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
AIP-C01 topic != product requirement
```

### Gate 19.1 — Public Runtime Hypothesis & Launch Contract — COMPLETE

Gate 19.1 froze `public-analysis-workload:v1`, identified the composition/measurement gaps, and refused to select runtime topology before representative evidence existed.

Historical decision:

```text
DEFERRED_PENDING_MEASUREMENT
```

Historical leading hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

Gate 19.1 created no public endpoint, queue, result store, worker, public compute, or runtime IAM.

### Gate 19.2 — Representative Workload Measurement — COMPLETE

Representative anchor:

```text
repository:      openedx/mockprock
commit/ref:      18c954d8604df4740c829ba17fa2f3640b92b900
evidence file:  uv.lock
dependency:     webob==1.8.10
GHSA anchor:    GHSA-6hx8-3wjj-gr8g
CVE anchor:     CVE-2026-54770
```

Human live measurement:

```text
source main:     e45ba419414e6dd77ecad68f4d2312e9123c2223
artifact:        labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
artifact SHA256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id:          gate19.2-live-20260911T131121Z
outcome:         SUCCESS
```

Measured values:

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

Selected interaction pattern:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

Derived retry-safety evidence remains explicitly `DERIVED`:

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

Gate 19.2 selected the interaction pattern only and authorized no deployment.

### Gate 19.3 — Concrete Async Topology Contract — COMPLETE

Protected merge: PR #349 at `18d31c03d27448c88a6ffcba16683f3875a5ba15`.

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

Job states:

```text
SUBMITTING
ACCEPTED
RUNNING
SUCCEEDED
FAILED
EXPIRED
```

Idempotency:

```text
required: Idempotency-Key
request identity: SHA256 canonical public-analysis request v1
same key + same fingerprint       -> existing job
same key + different fingerprint  -> HTTP 409
```

`SUBMITTING` explicitly models the DynamoDB/SQS dual-write boundary rather than pretending it is atomic.

Queue/worker semantics:

```text
queue semantics:       AT_LEAST_ONCE
worker batch size:     1
duplicate authority:   DynamoDB conditional state/attempt admission
retry owner:           SQS/Lambda event source + bounded worker policy
provider retry owner:  bounded worker policy
DLQ:                   REQUIRED by design
unbounded retry:       FORBIDDEN
backpressure:          SQS queue depth/age + Lambda reserved concurrency
```

Gate 19.3 responsibility authority:

```text
api_handler_role:
  sqs:SendMessage
  dynamodb:GetItem
  dynamodb:PutItem
  dynamodb:UpdateItem
  dynamodb:TransactWriteItems
  NO bedrock:InvokeModel
  NO bedrock:Retrieve
  NO sqs:ReceiveMessage

worker_role:
  sqs:ReceiveMessage
  sqs:DeleteMessage
  sqs:ChangeMessageVisibility
  sqs:GetQueueAttributes
  dynamodb:GetItem
  dynamodb:UpdateItem
  bedrock:Retrieve
  bedrock:InvokeModel
  NO dynamodb:Scan
  NO iam:*
```

Canonical Gate 19.3 evidence:

```text
labs/phase-19-gate-19-3-async-topology-contract.md
labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json
scripts/verify_phase19_gate19_3_async_topology_contract.py
```

Gate 19.3 authorized no Terraform apply, IAM mutation, public endpoint creation, or live provider workload.

### Gate 19.4 — Disabled Async Runtime Implementation — IN PROGRESS

Issue: #350  
PR: #351  
Source main: `18d31c03d27448c88a6ffcba16683f3875a5ba15`

Purpose: implement the selected Gate 19.3 design as typed/tested code and Terraform while retaining **zero deployment authority**.

Implemented domain/application authority includes:

```text
deterministic job/idempotency identity
canonical request fingerprint and exact request coordinates
exact async state machine
optimistic version/CAS authority
bounded attempts and leases
submit/status/result
worker claim/success/failure
semantic idempotency conflict
duplicate-delivery/concurrent-claim no-op semantics
queue-publish failure terminalization
result expiry semantics
```

Implemented AWS adapter/runtime boundaries include:

```text
DynamoDB transactional/conditional job store
SQS publisher containing only deterministic job_id
strict API Gateway HTTP API v2 request admission
strict SQS event admission and partial-batch failures
thin API Lambda control-path composition
worker Lambda fail-closed composition
```

Implemented Terraform inventory includes:

```text
DynamoDB jobs/idempotency/result table
SQS job queue + DLQ + redrive policy
API Lambda
worker Lambda
SQS worker event-source mapping
API Gateway HTTP API + integration + three routes + stage
CloudWatch API/worker/access logs
separate API and worker IAM roles/policies
```

All Gate 19.4 resources are gated behind:

```text
public_async_runtime_materialized = false
```

Additional fail-closed defaults are:

```text
disable_execute_api_endpoint = true
OPSLENS_ASYNC_SUBMIT_ENABLED = false
OPSLENS_ASYNC_WORKER_ENABLED = false
SQS event-source mapping enabled = false
worker reserved concurrency = 0
custom public domain = absent
provider-heavy worker executor = not composed
```

Exact API and worker IAM policies are bound to the concrete queue/table/Knowledge Base/model resources represented by Terraform. Runtime-support logging/X-Ray actions are kept separate from functional business authority.

Current numeric values are design configuration only:

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

Canonical Gate 19.4 implementation evidence in PR #351:

```text
labs/phase-19-gate-19-4-disabled-async-runtime.md
labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json
scripts/verify_phase19_gate19_4_disabled_async_runtime.py
```

Gate 19.4 remains bounded by:

```text
public endpoints enabled:                0
AWS resources created/changed/deleted:   0
IAM roles/policies created/changed:      0
AWS/provider live executions:            0
third-party repository code executions:  0
PR #89 modifications:                    0
```

### Next Gate 19 boundary — exact plan and human deployment review

Only after Gate 19.4 passes all offline/unit/Terraform/security validation and is protected-merged may a later gate consider AWS mutation.

That later gate must begin with an **exact Terraform plan** and human review. Before any apply or public enablement it must verify:

```text
exact artifact Key + VersionId + hash
exact Terraform resource changes
exact IAM action/resource statements
disable/rollback sequence
public ingress enablement sequence
new-job admission enablement sequence
worker/event-source enablement sequence
provider-heavy worker executor composition
configured concurrency/cost ceilings
human authorization for AWS mutation
```

No `terraform apply`, IAM mutation, endpoint enablement, worker enablement, or provider-heavy public execution is authorized by Gate 19.4.
