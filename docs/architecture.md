# OpsLens Architecture

_Last updated: 2026-09-11_

This document is the current accumulated architecture baseline through **Phase 19 — Bounded Public Runtime & Productization, Gate 19.3**.

Phases 0–18 are complete. Phase 19 is the current evidence-gated productization phase. Gate 19.2 selected the async submit/status/result interaction pattern from admitted representative workload evidence. Gate 19.3 now selects the smallest concrete async topology as **design authority only**; no public runtime deployment is authorized.

## 1. Purpose

OpsLens is an open-source software-supply-chain and threat-intelligence platform on AWS.

Product goal:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, which findings should I prioritize, and what verified guidance can help me act on them?

Core invariant:

> **Agents reason. Code verifies evidence.**

Permanent boundaries:

> **MCP is an interoperability boundary, not new business authority.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Additional retained rules:

```text
retrieved content != instruction authority
model proposal != authorization
capability invocation != execution result
execution result != admitted evidence
tool/protocol success != business truth
historical evidence != standing authority
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
responsibility -> required action -> exact resource -> IAM statement
AIP-C01 topic != product requirement
```

## 2. Authority model

Deterministic code remains authoritative for source/evidence identity, package and version applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS/Risk Policy facts, structured-query parsing and SQL compilation, retrieval admission and completeness, citation and output admission, capability authorization/result admission, agent/MCP/A2A handoff admission, runtime-evidence correlation, bounded resource/cost limits, and Terraform-owned recovery state.

Models and agents may classify, propose, summarize, explain, or synthesize over already-admitted evidence. A managed AWS service or a syntactically valid model output does not become business authority by itself.

Gate 19.3 extends deterministic authority to future public job identity, idempotency binding, state transitions, duplicate-delivery admission, retry ceilings, and result/status admission. Queue delivery is transport evidence, not job-state truth.

## 3. Retained platform shape

### 3.1 Threat intelligence and deterministic repository risk

```text
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
 -> source-preserving raw evidence
 -> deterministic normalization and applicability
 -> immutable repository dependency evidence
 -> deterministic vulnerability correlation
 -> RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> RiskPrioritizationResult
```

Raw third-party evidence is preserved before enrichment. Exact source versions, immutable snapshots, hashes, and typed evidence identities participate in provenance.

### 3.2 Repository intelligence

```text
public GitHub repository request
 -> strict request admission
 -> source-confirmed repository metadata
 -> immutable commit snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic TOML parsing
 -> canonical PyPI dependency identity
 -> deterministic vulnerability applicability
```

The retained repository intelligence path reads data only. It does not run package managers, builds, tests, setup hooks, workflows, Dockerfiles, scripts, or repository code.

### 3.3 Structured natural-language query path

```text
natural-language factual question
 -> bounded Bedrock planner proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured evidence
```

The model has no arbitrary SQL authority. The Athena adapter fixes database/workgroup, accepts only compiler-owned query shapes, bounds rows/pagination, records scan/timing evidence, and uses best-effort cancellation on its own polling timeout.

### 3.4 Semantic remediation path

```text
explicit official source pins
 -> deterministic canonical corpus
 -> S3 publication
 -> Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> bounded Retrieve
 -> provenance/hash admission
 -> deterministic context assembly
 -> bounded Bedrock Converse synthesis
 -> deterministic citation identity
 -> groundedness/support evaluation
```

`RetrieveAndGenerate` is not the retained default because retrieval and synthesis are intentionally measured and admitted separately.

Current knowledge baseline:

```text
embedding model:       amazon.titan-embed-text-v2:0
embedding dimensions:  1024
embedding data type:   FLOAT32
vector store:          Amazon S3 Vectors
distance:              cosine
chunking:              NONE
canonical chunks:      9
synthesis profile:     us.anthropic.claude-haiku-4-5-20251001-v1:0
```

### 3.5 Hybrid evidence path

```text
EvidenceNeed[] proposal
 -> deterministic route authority
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> evidence-class acquisition and admission
 -> ALL_REQUIRED completeness
 -> HybridEvidenceEnvelope
 -> F* structured facts + S* semantic citations
 -> route-aware bounded synthesis
 -> deterministic output admission
```

Hybrid means hybrid **evidence routing and composition**, not an automatic claim of keyword-plus-vector search.

## 4. Agentic and interoperability boundaries

Phase 11 retains direct Bedrock single-agent reasoning as the measured reference/default reasoning topology. Phase 12 retains deterministic specialization/handoff but rejects the measured two-model topology as default because it added calls, tokens, latency, and cost without quality lift. Phase 13 retains bounded offline MCP. Phase 14 retains AgentCore as optional lab only. Phase 15 retains bounded offline A2A reference interoperability with no public A2A runtime.

## 5. Runtime exposure boundary

Phase 16 retains a typed read-only Amazon Inspector evidence boundary. Its measured discovery returned zero current records. That proves only that the bounded read succeeded and returned zero records; it does not prove `runtime exposure = zero`. Repository risk and runtime exposure remain separate evidence classes.

## 6. AWS foundation and standing resources

```text
environment:             dev
primary Region:          us-east-1
IaC:                     Terraform
human administration:    AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray patterns
analytics:               AWS Glue + Amazon Athena
knowledge retrieval:     Amazon Bedrock Knowledge Base + Amazon S3 Vectors
compute:                  AWS Lambda for retained ingestion/transformation paths
recurring triggers:      Amazon EventBridge Scheduler
```

Standing architecture does **not** currently claim a public HTTP endpoint, public application compute, public queue, public result store, public MCP/A2A runtime, standing AgentCore experiment runtime, standing Inspector experiment IAM, or production multi-tenant request surface.

## 7. Security Hardening retained state

Phase 17 retains protected-main security invariants, full-SHA external actions, Dependency Review, CodeQL, adversarial authority tests, content-minimized telemetry, and Terraform-owned recovery for exactly three recurring ingestion schedules.

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

`scheduled_ingestion_enabled=false` is a scheduled-ingestion pause, not a global kill switch.

## 8. Phase 18 evidence, cost, and portfolio boundary

Phase 18 is complete through protected PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`. Its historical closeout artifact intentionally preserves pre-merge evidence state.

Phase 18 preserves:

```text
MEASURED
DERIVED
UNMEASURED
NOT_APPLICABLE
CONFIGURED_LIMIT
```

and the permanent rules `configured limit != measured utilization`, `lab metric != production SLO`, `cost evidence != production TCO`, and `portfolio claim != new evidence authority`.

## 9. Phase 19 — Bounded Public Runtime & Productization

### 9.1 Starting public-analysis boundary

Phase 9 deliberately stopped at an application handoff. That boundary remains real on protected `main`:

```text
untrusted JSON
 -> <= 2,048-byte request admission
 -> validated GitHub coordinates
 -> immutable repository evidence
 -> bounded metadata-only semantic planning
 -> deterministic public-v1 route admission
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

The fixed public v1 operation is `analyze_public_repository` and requires `remediation_guidance`, `risk_priority`, and `vulnerability_facts` with `ALL_REQUIRED` evidence completeness.

### 9.2 Gate 19.1 historical launch contract

Gate 19.1 froze the representative workload identity:

```text
public-analysis-workload:v1
```

Its historical runtime decision remains explicitly preserved as:

```text
DEFERRED_PENDING_MEASUREMENT
```

with leading hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

Gate 19.1 created no public endpoint, worker, queue, result store, or runtime IAM. Later gates do not rewrite this historical decision.

### 9.3 Gate 19.2 representative composition and evidence

Gate 19.2 composed retained capabilities into one **non-public** representative workload:

```text
public_request_admission
 -> repository_acquisition
 -> dependency_evidence
 -> vulnerability_correlation
 -> risk_prioritization
 -> structured_evidence
 -> semantic_evidence
 -> model_reasoning
 -> result_admission
```

The measurement anchor was `openedx/mockprock` at exact commit `18c954d8604df4740c829ba17fa2f3640b92b900`, using inert `uv.lock`, `webob==1.8.10`, GHSA `GHSA-6hx8-3wjj-gr8g`, and CVE `CVE-2026-54770`. The anchor establishes reproducibility, not runtime exposure.

The human-operated run was executed once from protected main `e45ba419414e6dd77ecad68f4d2312e9123c2223`.

Canonical artifact:

```text
labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
outcome: SUCCESS
```

Measured request-time evidence:

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

The Bedrock-facing stages measured `13,098 ms`, or `73.80%` of end-to-end. Numeric zero never overwrites evidence semantics.

### 9.4 Gate 19.2 interaction-pattern decision — COMPLETE

Gate 19.2 selected:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The measured success path completed in `17,748 ms`; it did **not** itself exceed the retained 30-second HTTP API reference envelope. The decision is based on retry safety, provider-latency coupling, backpressure, and failure isolation.

Explicit derived scenarios preserve `MEASURED != DERIVED`:

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

Gate 19.2 was protected-merged through PR #347 at `71eda2650889d3047259d37be226862ed2a09092`. It authorized no public deployment.

### 9.5 Gate 19.3 concrete topology decision — DESIGN ONLY

Gate 19.3 selects the logical topology identifier:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

Selected shape:

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

The selection is architecture evidence only. Gate 19.3 creates none of those resources.

### 9.6 Candidate comparison

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB            SELECTED
HTTP_API_LAMBDA_DYNAMODB_STREAMS_LAMBDA        REJECTED
HTTP_API_LAMBDA_STEP_FUNCTIONS_STANDARD_LAMBDA REJECTED
FUNCTION_URL_LAMBDA_SQS_LAMBDA_DYNAMODB        REJECTED
HTTP_API_LAMBDA_SQS_FARGATE_DYNAMODB           REJECTED
```

Rationale:

- HTTP API gives an explicit managed public routing/rate boundary without selecting REST-only capabilities not yet justified;
- API Lambda keeps deterministic request/idempotency/status logic away from provider-heavy worker latency;
- SQS expresses durable at-least-once buffering, retry isolation, and backpressure directly;
- a DLQ bounds poison/repeated delivery rather than allowing unbounded redelivery;
- the measured `17,748 ms` worker workload does not justify Fargate/container scheduling;
- the measured `5,285`-byte result and conditional state/idempotency requirements justify DynamoDB rather than blob-scale result storage;
- Step Functions Standard adds orchestration semantics not required by one linear analysis operation;
- DynamoDB Streams couple dispatch to persistence-stream semantics and provide weaker queue-specific failure/backpressure controls for this boundary.

No numerical architecture score is manufactured.

### 9.7 Public interaction and job-state contract

Future routes, not deployed by Gate 19.3:

```text
POST /v1/analyses
GET  /v1/analyses/{job_id}
GET  /v1/analyses/{job_id}/result
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

DynamoDB conditional writes are the planned job-state authority. SQS is at-least-once delivery transport and cannot itself mutate business truth.

The public submit contract requires `Idempotency-Key` plus `SHA256_CANONICAL_PUBLIC_ANALYSIS_REQUEST_V1`:

```text
same key + same fingerprint       -> RETURN_EXISTING_JOB
same key + different fingerprint  -> HTTP_409
```

`SUBMITTING` explicitly models the DynamoDB/SQS dual-write boundary. The design does not pretend those services provide one atomic transaction.

### 9.8 Retry, duplicate delivery, and backpressure

```text
queue semantics:       AT_LEAST_ONCE
worker batch size:     1
duplicate authority:   DYNAMODB_CONDITIONAL_STATE_AND_ATTEMPT_ADMISSION
retry owner:           SQS/Lambda event source + worker state machine
provider retry owner:  bounded worker policy
DLQ:                   REQUIRED
unbounded retry:       FORBIDDEN
backpressure:          SQS queue depth/age + Lambda reserved concurrency
```

Future numeric retry/concurrency/retention values are `CONFIGURED_LIMIT` until measured.

### 9.9 IAM responsibility contract

Planned API-handler role authority is limited to public-control-plane state and submission:

```text
sqs:SendMessage
dynamodb:GetItem
dynamodb:PutItem
dynamodb:UpdateItem
dynamodb:TransactWriteItems
```

It explicitly excludes `bedrock:Retrieve`, `bedrock:InvokeModel`, and `sqs:ReceiveMessage`.

Planned worker role authority is limited to queue consumption, exact job-state updates, retained Knowledge Base retrieval, and retained model invocation:

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

Exact resource ARNs belong to the future Terraform implementation gate.

The design rule remains:

```text
concrete runtime responsibility
 -> required service action
 -> exact resource
 -> IAM statement
```

not `future feature aspiration -> broad runtime role`.

### 9.10 Observability, cost, and data minimization

Gate 19.3 requires future operational evidence for request/job/trace identity, state transitions, attempt number, stage duration, queue age, provider call counts, Bedrock tokens when available, retries, throttles, outcome/failure category, and result bytes.

Telemetry remains content-minimized. Full prompts, repository source, repository file contents, full model responses, credentials, sensitive tokens, and raw user payloads remain forbidden by default.

Gate 19.3 creates no production SLO or TCO claim. Async-specific queue operations, status reads, worker concurrency, storage/retention, and aggregate model-call budgets become measurement obligations only after implementation exists.

### 9.11 Disable/recovery contract

Future implementation must independently support:

```text
disable new submit route
preserve status/result reads during submit pause
disable queue -> worker event source
set worker reserved concurrency to zero
disable model invocation at worker authorization/runtime guard
```

The Phase 17 scheduler pause remains separate and is not a global kill switch.

### 9.12 Next architecture boundary

After protected Gate 19.3 merge, the next gate may implement the selected topology in Terraform and application adapters **behind disabled/non-public defaults**.

Before any AWS apply or public enablement, it must produce exact Terraform resource inventory/plan, exact least-privilege IAM bound to concrete ARNs, lifecycle/idempotency tests, duplicate-delivery/retry/backpressure/failure-injection tests, content-minimized telemetry tests, and explicit configured cost/concurrency ceilings.

No apply or public enablement is authorized by Gate 19.3.

## 10. Gate 19.3 authority impact

```text
public endpoints created:               0
new AWS resources created:              0
new IAM roles/policies created:         0
AWS/provider live executions:           0
third-party repository code executions: 0
PR #89 modifications:                   0
```

## 11. Canonical Phase 19 evidence

Gate 19.1:

- `docs/adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md`
- `labs/phase-19-gate-19-1-public-runtime-hypothesis.md`
- `labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`
- `scripts/verify_phase19_gate19_1_public_runtime_contract.py`

Gate 19.2:

- `labs/phase-19-gate-19-2-human-live-measurement-runbook.md`
- `labs/evidence/phase-19-gate-19-2-live-measurement-v1.json`
- `scripts/verify_phase19_gate19_2_live_measurement.py`
- `labs/phase-19-gate-19-2-closeout.md`
- `labs/evidence/phase-19-gate-19-2-closeout-v1.json`
- `scripts/verify_phase19_gate19_2_closeout.py`

Gate 19.3:

- `labs/phase-19-gate-19-3-async-topology-contract.md`
- `labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json`
- `scripts/verify_phase19_gate19_3_async_topology_contract.py`

PR #89 remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency unless explicitly re-evaluated later.
