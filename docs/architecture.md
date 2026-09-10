# OpsLens Architecture

_Last updated: 2026-09-10_

This document is the current accumulated architecture baseline through **Phase 19 — Bounded Public Runtime & Productization, Gate 19.1**.

Phases 0–18 are complete. Phase 19 is the current evidence-gated productization phase.

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

Phase 9 deliberately stopped at an application handoff. That boundary is still real on `main`:

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

### 9.2 Actual composition gap

The repository already contains real implementations for deterministic vulnerability/risk analysis, bounded Athena retrieval, Bedrock Knowledge Base retrieval, bounded synthesis, capability execution/result admission, and hybrid output admission.

Those components are **not** currently composed downstream of `PublicAnalysisAdmissionHandoff` into one representative public product execution.

Therefore:

```text
rich retained capabilities != executable public product workload
```

No public HTTP topology should be selected from partial-stage latency.

### 9.3 Frozen public workload

Gate 19.1 freezes:

```text
workload_id: public-analysis-workload:v1
provider: GitHub
visibility: public only
repositories/request: 1
supported dependency evidence: exact-commit inert uv.lock
max dependency records: 5,000
third-party code execution: FORBIDDEN
```

Existing evidence-backed component limits are reused. Missing whole-request measurements remain `UNMEASURED`.

Examples:

```text
request body                        CONFIGURED_LIMIT  2,048 bytes
repository URL                      CONFIGURED_LIMIT  256 chars
GitHub success-path physical calls  DERIVED           4
GitHub adapter retries              CONFIGURED_LIMIT  0
GitHub per-call timeout             CONFIGURED_LIMIT  10 seconds
Athena scan cutoff/query            CONFIGURED_LIMIT  10,485,760 bytes
Knowledge Retrieve top_k            CONFIGURED_LIMIT  <= 10
Knowledge context                   CONFIGURED_LIMIT  <= 16,384 UTF-8 bytes
knowledge/hybrid synthesis output   CONFIGURED_LIMIT  <= 2,048 tokens
public Athena query count           UNMEASURED
public Bedrock call count           UNMEASURED
public end-to-end p50/p95            UNMEASURED
public final response bytes         UNMEASURED
public request cost                 UNMEASURED
```

### 9.4 Runtime decision

Gate 19.1 records:

```text
DEFERRED_PENDING_MEASUREMENT
```

with leading hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The hypothesis is not standing architecture authority.

A synchronous path remains viable only if the complete representative workload fits comfortably within the selected ingress timeout under upper-bound/p95 testing. Async becomes justified if latency variability, backpressure, failure isolation, retry safety, or timeout evidence makes synchronous coupling unsafe.

### 9.5 Runtime candidate set

Current candidates are deliberately treated as alternatives, not preselected services:

```text
HTTP API + Lambda synchronous             MEASUREMENT_GATED
Regional REST API + Lambda synchronous    MEASUREMENT_GATED
API + submit/queue/worker/result           LEADING_HYPOTHESIS
Lambda Function URL                       NOT_FAVORED_FOR_PUBLIC_V1
ECS/Fargate/ALB                            DEFERRED_NO_CURRENT_NEED
AgentCore public runtime                   DEFERRED_NO_CURRENT_NEED
```

Current AWS documentation is evaluated in ADR 0076. Service limits are AWS facts, not OpsLens performance measurements.

### 9.6 IAM responsibility model

Gate 19.1 creates no IAM role. Future permissions are decomposed by concrete responsibility:

```text
public ingress
repository acquisition
Athena structured retrieval
Bedrock Knowledge Base retrieval
Bedrock model invocation
result persistence, only if justified
telemetry emission
async queue/job coordination, only if justified
```

The design rule is:

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

### 9.7 Threat and abuse model

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
Athena scan amplification
Bedrock token amplification
retry amplification
concurrency exhaustion
cost denial-of-wallet
result tampering
identity/replay
telemetry data leakage
```

Existing request admission, fixed GitHub host/no redirects, inert-file-only repository access, dependency/candidate limits, deterministic authority boundaries, and content-minimized telemetry already mitigate part of this surface. Public identity/rate/global quota/concurrency/aggregate model-call controls remain unresolved until the runtime topology is selected.

### 9.8 Cost and observability contract

The first real runtime experiment must measure request-level resource dimensions independently:

```text
cost/request
Bedrock input/output tokens
Athena bytes scanned
GitHub request count
runtime duration
queue operations, if applicable
storage, if applicable
retries
throttles
rejected requests
concurrency
```

Required future telemetry is content-minimized:

```text
request_id
trace_id
workload_id
repository_identity_hash
stage
duration_ms
outcome
failure_category
provider/service call count
Bedrock token counts when available
Athena bytes scanned
retry count
throttle count
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

### 9.9 Disable/recovery contract

Before public deployment, controls must be named by their actual scope:

```text
ingress disable
new-job admission disable
queue consumer pause
model invocation disable
Athena execution disable
background ingestion pause
```

The existing Phase 17 scheduler pause proves only `background ingestion pause` for the three named schedules. It must not be relabeled as a global kill switch.

### 9.10 Gate 19.2 experiment boundary

The next authorized experiment is **non-public representative workload measurement**.

It must compose or invoke the real product stages through deterministic final result admission and measure:

```text
end-to-end and per-stage duration
GitHub HTTP calls
Athena query count + bytes scanned when used
Bedrock Retrieve count + latency when used
Bedrock model calls + tokens + latency when used
retry/throttle counts
serialized result bytes
```

Only after that evidence exists may the project promote the runtime decision to `SYNC` or `ASYNC`.

If live AWS/model calls are required for Gate 19.2, execution remains a human boundary.

## 10. Gate 19.1 authority impact

```text
AWS mutations:          0
IAM mutations:          0
new AWS resources:      0
model invocations:      0
capability executions:  0
public endpoints:       0
PR #89 modifications:   0
```

Phase 19 does not add AWS services solely for product appearance or AIP-C01 breadth.

## 11. Canonical Phase 19 Gate 19.1 evidence

- `docs/adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md`
- `labs/phase-19-gate-19-1-public-runtime-hypothesis.md`
- `labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`
- `scripts/verify_phase19_gate19_1_public_runtime_contract.py`

PR #89 remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency unless explicitly re-evaluated later.
