# OpsLens — Current State

_Last updated: 2026-09-10_

## Authoritative checkpoint

```text
protected main:
feca774535b7d83f57c26f4e9fe7da71ce268f0f

Phase 18 — Evaluation, Cost & Portfolio Readiness
status: COMPLETE
protected closeout PR: #290
closeout issue: #289 CLOSED / COMPLETED

Phase 19 — Bounded Public Runtime & Productization
Gate 19.1 — Public Runtime Hypothesis & Launch Contract
status: IN PROGRESS
issue: #291
branch: docs/phase19-gate19-1-public-runtime-contract
runtime decision: DEFERRED_PENDING_MEASUREMENT
leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT
```

Phases 0–18 are complete. PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency.

## Phase 18 closeout synchronization

PR #290 was protected-squash-merged to `main` at:

```text
feca774535b7d83f57c26f4e9fe7da71ce268f0f
```

The historical closeout records under `labs/phase-18-closeout.md`, `labs/evidence/phase-18-closeout-v1.json`, and ADR 0075 intentionally preserve their pre-merge state. They are historical evidence and are not rewritten by Phase 19.

Current-facing documentation is synchronized separately so it no longer treats Gate 18.5 as pending.

## Retained Phase 17 security lineage

**Gate 17.1** established the evidence-first threat/control-gap inventory. **Gate 17.2** hardened CI/CD and workflow authority and introduced the retained `Repository security invariants` protected-main context. Later Phase 17 controls remain authoritative for dependency/code scanning, adversarial regression, telemetry minimization, and bounded scheduled-ingestion recovery. Phase 19 adds no exception to those controls.

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
AIP-C01 topic != product requirement
```

## Retained public-analysis boundary

The current public-analysis application path is real but deliberately stops before a public product runtime:

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

`execute_instrumented_public_analysis` emits bounded operational evidence for the same path and still returns the handoff. There is no retained public HTTP endpoint, public application compute, final public product result, or public result store.

Important adjacent capabilities already exist but are not yet composed downstream of that handoff into one public workload:

```text
deterministic vulnerability correlation
NVD/CVSS + KEV + EPSS enrichment
Risk Policy v1
bounded Athena structured retrieval
Bedrock Knowledge Base Retrieve
bounded grounded/hybrid synthesis
capability execution/result admission
```

Therefore:

```text
rich retained capabilities != executable public product workload
```

## Gate 19.1 frozen workload

The machine-readable authority is:

`labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`

with workload identity:

```text
public-analysis-workload:v1
```

The workload preserves the existing public request contract and current repository-evidence scope:

```text
provider:                 GitHub
visibility:               public only
repositories/request:     1
request body:             <= 2,048 bytes
repository URL:           <= 256 chars
requested_ref:            optional
immutable downstream ref: resolved commit SHA
repository files read:    exactly the supported inert uv.lock path
max dependency records:   5,000
third-party code execute: FORBIDDEN
operation:                analyze_public_repository
evidence completeness:    ALL_REQUIRED
```

Required evidence needs remain exactly:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

Existing component limits are preserved as `CONFIGURED_LIMIT`; missing whole-request measurements remain `UNMEASURED`.

## Gate 19.1 runtime decision

Current decision:

```text
DEFERRED_PENDING_MEASUREMENT
```

Leading design hypothesis:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

The hypothesis is not a selected runtime. The repository does not yet contain one representative execution that composes repository acquisition, deterministic finding/risk production, structured/semantic evidence, bounded synthesis, and admitted final result while measuring end-to-end latency, provider calls, retries, throttles, token use, Athena scan bytes, and serialized result size.

A synchronous topology remains viable only if the complete workload is measured to fit safely inside the selected ingress timeout with adequate margin. Async becomes justified if latency variability, backpressure, failure isolation, or timeout evidence makes synchronous coupling unsafe.

## Gate 19.1 authority boundary

```text
AWS mutations:          0
IAM mutations:          0
new AWS resources:      0
model invocations:      0
capability executions:  0
public endpoints:       0
PR #89 modifications:   0
```

No API Gateway, Function URL, Lambda public runtime, SQS queue, result store, WAF, ECS/Fargate, AgentCore runtime, or broad runtime role is authorized by Gate 19.1.

IAM is represented only as a responsibility-to-permission matrix. Public ingress, repository acquisition, Athena retrieval, Bedrock retrieval, Bedrock model invocation, result persistence, telemetry, and async coordination remain distinct responsibilities.

## Security, cost, and observability launch contracts

The frozen threat/abuse model covers malformed/oversized requests, repository/SSRF abuse, enumeration and amplification, GitHub abuse, indirect prompt injection, retrieval poisoning, model/Athena/token/retry amplification, concurrency exhaustion, denial-of-wallet, result/replay tampering, and telemetry leakage.

The future runtime must measure request-level cost/resource dimensions instead of extrapolating unrelated labs. Required telemetry is content-minimized and includes identities/hashes, stage durations and outcomes, provider-call counts, token counts when available, Athena bytes, retries, throttles, rejection reasons, and cost-attribution identifiers where available. Raw payloads, source code, full prompts/responses, credentials, and sensitive tokens remain forbidden by default.

## Disable/recovery semantics

The future public runtime must prove the exact scope of applicable controls rather than inventing one generic kill switch:

```text
ingress disable
new-job admission disable
queue consumer pause
model invocation disable
Athena execution disable
background ingestion pause
```

Phase 17 currently proves only the last item for exactly three recurring EventBridge Scheduler resources through `scheduled_ingestion_enabled=false`. That remains a scheduled-ingestion pause, not a global platform stop.

## Next checkpoint

Gate 19.1 still requires its deterministic verifier, read-only CI, documentation synchronization, and exact-head validation before it can be declared complete.

The smallest authorized Gate 19.2 experiment is then a **non-public representative workload measurement**. It must compose or invoke the full public-analysis product stages and measure end-to-end/stage latency, provider calls, Bedrock tokens, Athena scans where applicable, retries/throttles, and serialized result bytes before the project selects `SYNC` or `ASYNC`.

If Gate 19.2 requires live AWS or model execution, execution remains a human boundary. No AWS mutation is authorized as part of Gate 19.1.
