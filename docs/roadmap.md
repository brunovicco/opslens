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

Phase 17 security controls remain authoritative. Phase 18 was protected-squash-merged through PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`.

Gate 19.1 was protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1`. Its historical decision remains `DEFERRED_PENDING_MEASUREMENT` and its historical leading hypothesis remains `ASYNC_SUBMIT_STATUS_RESULT`.

Gate 19.2 was protected-merged through PR #347 at `71eda2650889d3047259d37be226862ed2a09092` after one admitted human-operated representative run and deterministic closeout verification.

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work. Phase 19 does not rebase, merge, modify, or depend on it.

## Phase 19 — Bounded Public Runtime & Productization

### Goal

Move from the retained Phase 9 application boundary toward the smallest safe, measurable public product surface without selecting or deploying infrastructure before evidence justifies it.

Retained starting point:

```text
untrusted request
 -> governed repository admission/evidence
 -> bounded semantic planning
 -> deterministic hybrid route admission
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

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

Purpose: close the whole-workload `UNMEASURED` gaps and select exactly one interaction pattern without deploying a public runtime.

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

The measured run did not itself time out. The decision follows provider-latency coupling, retry safety, backpressure, and failure isolation. Derived retry-safety evidence remains explicitly `DERIVED`:

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

Gate 19.2 closeout was protected-merged through PR #347 at `71eda2650889d3047259d37be226862ed2a09092`. It selected the interaction pattern only and authorized no deployment.

Canonical Gate 19.2 evidence:

```text
labs/phase-19-gate-19-2-closeout.md
labs/evidence/phase-19-gate-19-2-closeout-v1.json
labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
scripts/verify_phase19_gate19_2_closeout.py
```

### Gate 19.3 — Concrete Async Topology Contract — IN PROGRESS

Issue: #348  
Draft PR: #349

Purpose: freeze the smallest concrete AWS topology that can implement `ASYNC_SUBMIT_STATUS_RESULT` while preserving deterministic job authority, idempotency, retry isolation, backpressure, failure isolation, content-minimized observability, and least privilege — still with **zero deployment authority**.

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

#### Why this topology

- `17,748 ms` measured E2E does not justify Fargate/container scheduling;
- provider-heavy latency is removed from the public submit request path;
- SQS directly expresses the retry/backpressure/failure-isolation concerns that drove the Gate 19.2 async decision;
- DynamoDB provides conditional job state, idempotency binding, and small result persistence for the measured `5,285`-byte result;
- API Gateway HTTP API provides an explicit managed public transport/rate boundary without selecting REST-only capabilities not yet justified;
- Step Functions Standard is credible but not required for one linear analysis operation;
- DynamoDB Streams reduce resource types but weaken the explicit queue-specific dispatch/backpressure/dead-letter boundary.

No numerical architecture score is manufactured.

#### Async lifecycle contract

Future public routes, not deployed by this gate:

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

Future numeric values for concurrency, retries, queue depth, retention, or timeouts are `CONFIGURED_LIMIT`, not measured utilization.

#### Least-privilege responsibility contract

API handler design authority:

```text
sqs:SendMessage
dynamodb:GetItem
dynamodb:PutItem
dynamodb:UpdateItem
dynamodb:TransactWriteItems
```

The API handler does not receive Bedrock invocation/retrieval or SQS receive authority.

Worker design authority:

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

Exact ARNs belong to the future implementation/Terraform gate.

#### Candidate matrix

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB           SELECTED
HTTP_API_LAMBDA_DYNAMODB_STREAMS_LAMBDA       REJECTED
HTTP_API_LAMBDA_STEP_FUNCTIONS_STANDARD_LAMBDA REJECTED
FUNCTION_URL_LAMBDA_SQS_LAMBDA_DYNAMODB       REJECTED
HTTP_API_LAMBDA_SQS_FARGATE_DYNAMODB          REJECTED
```

Canonical Gate 19.3 evidence:

```text
labs/phase-19-gate-19-3-async-topology-contract.md
labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json
scripts/verify_phase19_gate19_3_async_topology_contract.py
```

Gate 19.3 safety boundary:

```text
public endpoints created:               0
new AWS resources created:              0
new IAM roles/policies created:         0
AWS/provider live executions:           0
third-party repository code executions: 0
PR #89 modifications:                   0
```

### Next Gate 19 boundary — implementation behind disabled defaults

Only after Gate 19.3 is protected-merged should a later gate materialize the selected design in code/Terraform.

That implementation gate must begin with disabled/non-public defaults and require, before any apply or public enablement:

```text
exact Terraform resource inventory and plan
exact least-privilege IAM policies bound to concrete ARNs
deterministic submit/status/result lifecycle tests
idempotency and duplicate-delivery tests
retry/backpressure/failure-injection tests
content-minimized observability tests
configured concurrency/cost ceilings separated from measured utilization
human authorization for any AWS apply or public enablement
```

No public deployment is authorized by Gate 19.3.
