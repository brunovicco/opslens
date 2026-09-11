# OpsLens Architecture

_Last updated: 2026-09-11_

This document is the current accumulated architecture baseline through **Phase 19 — Bounded Public Runtime & Productization, Gate 19.2**.

Phases 0–18 are complete. Phase 19 is the current evidence-gated productization phase. Gate 19.2 has selected the async submit/status/result interaction pattern from admitted representative workload evidence, while concrete public AWS topology remains intentionally unselected.

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
AIP-C01 topic != product requirement
```

## 2. Authority model

Deterministic code remains authoritative for:

- source and evidence identity;
- package normalization and version/range applicability;
- CVE/GHSA/NVD reconciliation;
- KEV, EPSS, CVSS and Risk Policy facts;
- structured-query parsing and SQL compilation;
- retrieval admission and required-evidence completeness;
- citation identity and output admission;
- capability authorization and executable input binding;
- capability result admission;
- single-agent and multi-agent handoff admission;
- MCP admission and result projection;
- A2A reference identity, resolution and admission;
- retry/fallback policy where explicitly frozen;
- runtime-evidence admission and correlation;
- bounded resource/cost limits;
- operational recovery control state expressed through Terraform.

Models and agents may classify, propose, summarize, explain, or synthesize over already-admitted evidence. A managed AWS service or a syntactically valid model output does not become business authority by itself.

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

The initial retained repository intelligence path reads data only. It does not run package managers, builds, tests, setup hooks, workflows, Dockerfiles, scripts, or repository code.

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

The model has no arbitrary SQL authority. The Athena adapter fixes the database/workgroup, accepts only compiler-owned query shapes, bounds rows/pagination, records scan/timing evidence, and uses best-effort cancellation on its own polling timeout.

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

Phase 11 retains direct Bedrock single-agent reasoning as the measured reference/default reasoning topology.

Phase 12 retains deterministic specialization/handoff but rejects the measured two-model topology as the default because it added model calls, tokens, latency, and cost without measured quality lift.

Phase 13 retains bounded offline MCP capability exposure/execution/projection. MCP does not add business authority.

Phase 14 retains Amazon Bedrock AgentCore as an optional lab target only. Experiment-specific standing IAM/runtime authority was removed after measurement.

Phase 15 retains bounded offline A2A reference interoperability and an official SDK conformance oracle in CI. No public A2A runtime is retained.

## 5. Runtime exposure boundary

Phase 16 retains a typed read-only Amazon Inspector evidence boundary.

The measured discovery returned zero current records. That means only:

```text
bounded Inspector read succeeded and returned zero records
```

It does not mean:

```text
runtime exposure = zero
```

Repository risk and runtime exposure remain separate evidence classes.

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

Standing architecture does **not** currently claim:

```text
public HTTP endpoint
public application compute
public MCP runtime
public A2A peer runtime
standing AgentCore experiment runtime
standing Inspector experiment IAM
production multi-tenant request surface
public result store
```

## 7. Security Hardening retained state

Phase 17 retains evidence-backed controls across CI/CD, dependency/code scanning, adversarial authority regression, telemetry, and recovery.

Important retained controls include:

```text
protected-main required context:     Repository security invariants
external GitHub Actions:             full 40-hex SHA pins
checkout persisted credentials:      disabled where not required
Dependency Review:                   pull request, fail on high severity
CodeQL Python:                       PR + main + weekly + manual
public/adversarial authority tests:  offline and deterministic
Lambda telemetry:                    implicit event/response/error capture suppressed
```

All 12 retained Powertools Lambda handlers use content-minimized telemetry patterns. Shared failure logging avoids implicit active-exception traceback serialization.

### 7.1 Scheduled-ingestion recovery control

The concrete recurring ingestion surface remains exactly three EventBridge Scheduler resources:

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

Terraform owns one reversible control:

```text
scheduled_ingestion_enabled=true   -> ENABLED
scheduled_ingestion_enabled=false  -> DISABLED
```

This is a **scheduled-ingestion pause**, not a global kill switch. It does not cancel in-flight Lambda invocations, accepted retries, emitted S3 events, manual invocations, model paths, or capability authorization.

## 8. Phase 18 evidence, cost, and portfolio boundary

Phase 18 is complete through protected PR #290 at:

```text
feca774535b7d83f57c26f4e9fe7da71ce268f0f
```

Its historical closeout artifact intentionally preserves the pre-merge evidence state. Current-facing documentation carries the post-merge truth.

Phase 18 preserves four evidence classifications:

```text
MEASURED
DERIVED
UNMEASURED
NOT_APPLICABLE
```

and a separate `CONFIGURED_LIMIT` interpretation for resource ceilings.

Permanent Phase 18 semantics include:

```text
configured limit != measured utilization
lab metric != production SLO
cost evidence != production TCO
portfolio claim != new evidence authority
AIP-C01 coverage != certification guarantee
```

The platform does not manufacture a production monthly run rate from bounded laboratory measurements.

## 9. Phase 19 — Bounded Public Runtime & Productization

### 9.1 Starting public-analysis boundary

Phase 9 deliberately stopped at an application handoff. That boundary is still real on protected `main`:

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

The fixed public v1 operation is:

```text
analyze_public_repository
```

and requires exactly:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

with `ALL_REQUIRED` evidence completeness.

The public semantic planner receives only bounded metadata. Raw repository text, credentials, arbitrary SQL, provider/model selection, and executable repository content do not become planner authority.

### 9.2 Representative product composition

Gate 19.2 composes the real retained capabilities into one **non-public** representative workload without making that composition a deployed public runtime:

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

The composition reuses retained deterministic authority rather than duplicating it. Repository evidence remains immutable and inert, threat evidence is admitted before request-time measurement, risk remains Risk Policy v1, Bedrock Retrieve and synthesis remain bounded, and final result admission remains deterministic.

### 9.3 Frozen representative workload

Gate 19.1 froze the workload identity:

```text
workload_id: public-analysis-workload:v1
provider: GitHub
visibility: public only
repositories/request: 1
supported dependency evidence: exact-commit inert uv.lock
max dependency records: 5,000
third-party code execution: FORBIDDEN
```

Gate 19.2 retained the current representative anchor:

```text
repository:      openedx/mockprock
repository URL:  https://github.com/openedx/mockprock
commit/ref:      18c954d8604df4740c829ba17fa2f3640b92b900
evidence file:  uv.lock
dependency:     webob==1.8.10
GHSA anchor:    GHSA-6hx8-3wjj-gr8g
CVE anchor:     CVE-2026-54770
```

The anchor establishes reproducibility only. It is not proof of runtime exposure.

### 9.4 Gate 19.2 measured evidence

The human-operated run was executed once from protected main:

```text
e45ba419414e6dd77ecad68f4d2312e9123c2223
```

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

The two Bedrock-facing stages measured:

```text
semantic_evidence = 4160 ms
model_reasoning   = 8938 ms
combined          = 13098 ms / 73.80% of end-to-end
```

The offline persisted-artifact reviewer admitted the artifact for topology evaluation. Numeric zero is never used to overwrite evidence semantics: Athena remains `NOT_APPLICABLE`, and throttling remains `UNMEASURED`.

### 9.5 Interaction-pattern decision

Gate 19.2 selects:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The measured success path completed in `17,748 ms`; it did **not** itself exceed the retained 30-second HTTP API reference envelope. Therefore the decision is not based on a claim of measured timeout.

The architectural reason is retry safety plus provider-latency coupling, backpressure, and failure isolation. Explicit derived scenarios keep `MEASURED != DERIVED` intact:

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

The derived values are not additional live measurements. They show that a successful 17.7-second request leaves insufficient safety margin for synchronous coupling when provider retry/failure behavior is considered.

### 9.6 Concrete runtime remains unselected

The interaction pattern is selected; the concrete service topology is not.

```text
ASYNC_SUBMIT_STATUS_RESULT     SELECTED_INTERACTION_PATTERN
API Gateway                    UNSELECTED
Lambda                         UNSELECTED
SQS                            UNSELECTED
DynamoDB                       UNSELECTED
Step Functions                 UNSELECTED
ECS/Fargate                    UNSELECTED
WAF                            UNSELECTED
AgentCore public runtime       UNSELECTED
```

Gate 19.2 authorizes no public endpoint, queue, worker, result store, AWS resource, or IAM role/policy.

### 9.7 IAM responsibility model

No public runtime role exists yet. The next topology gate must preserve responsibility decomposition before IAM materialization:

```text
public ingress admission
repository acquisition
job submission/coordination
worker execution
Bedrock Knowledge Base retrieval
Bedrock model invocation
result persistence/status, only if selected
telemetry emission
```

The design rule remains:

```text
concrete runtime responsibility
 -> required service action
 -> exact resource
 -> IAM statement
```

not:

```text
future feature aspiration
 -> broad runtime role
```

### 9.8 Threat, abuse, and async lifecycle requirements

The future public surface must address at minimum:

```text
oversized request
malformed JSON
repository URL abuse
SSRF-style source redirection
repository enumeration
large repository amplification
dependency explosion
GitHub API abuse
prompt injection from repository content
retrieval poisoning
model amplification
retry amplification
concurrency exhaustion
cost denial-of-wallet
result tampering
identity/replay
telemetry data leakage
```

The selected async pattern additionally requires deterministic authority for:

```text
job identity
idempotency key semantics
duplicate-delivery handling
retry ownership
visibility/lease semantics if a queue is selected
status lifecycle
result retention
result integrity
cancellation/disable boundaries
```

Existing request admission, fixed GitHub host/no redirects, inert-file-only repository access, dependency/candidate limits, deterministic authority boundaries, and content-minimized telemetry remain applicable.

### 9.9 Cost and observability contract

Gate 19.2 now provides real whole-workload measurements for the retained representative run, but it does not manufacture production SLOs or TCO.

The next topology gate must additionally define and later measure async-specific dimensions only if those components are actually selected:

```text
job submissions
queue operations
delivery attempts
worker concurrency
result-store operations
status reads
retention/storage
rejected requests
aggregate model-call budget
cost attribution per job/request
```

Required telemetry remains content-minimized:

```text
request_id
job_id
trace_id
workload_id
repository_identity_hash
stage
duration_ms
outcome
failure_category
provider/service call count
Bedrock token counts when available
retry count
throttle classification
admission rejection reason
cost attribution identifiers when available
```

Forbidden by default:

```text
full prompt
repository source code
repository file contents
full model response
sensitive tokens
credentials
raw user payload
```

Telemetry does not become business/evidence authority.

### 9.10 Disable/recovery contract

Before public deployment, controls must be named by their actual scope:

```text
ingress disable
new-job admission disable
queue consumer pause, if a queue is selected
model invocation disable
result publication disable, if persistence is selected
background ingestion pause
```

The existing Phase 17 scheduler pause proves only `background ingestion pause` for the three named schedules. It must not be relabeled as a global kill switch.

### 9.11 Next architecture boundary

After protected Gate 19.2 closeout merge, the next Phase 19 gate should freeze the smallest concrete async ingress/job/result architecture and least-privilege responsibility model **before** deployment.

It must compare only the minimum credible service combinations needed for the already-selected interaction pattern and preserve evidence-gated decisions for:

```text
ingress
job coordination
worker compute
result/status persistence
identity/rate/abuse controls
least-privilege IAM
concurrency/backpressure
observability
disable/recovery
Terraform ownership
```

No AWS service is selected merely because it is common for async systems or appears in AIP-C01.

## 10. Gate 19.2 authority impact

```text
public endpoints:                       0
new AWS resources:                      0
new IAM roles/policies:                 0
third-party repository code executions: 0
PR #89 modifications:                  0
```

The live measurement artifact records these counters as exactly zero.

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

PR #89 remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency unless explicitly re-evaluated later.
