# OpsLens Architecture

_Last updated: 2026-09-12_

This document is the current accumulated architecture baseline through **Phase 19 Gate 19.8**, with Gate 19.9 freezing the demonstration-focused V1 closeout boundary.

Phases 0–18 are complete. The retained historical phase selected after Phase 18 remains **Phase 19 — Bounded Public Runtime & Productization**; Gate 19.9 narrows V1 completion scope without rewriting that decision.

Retained Gate 19.1 launch-contract markers:

```text
public-analysis-workload:v1
DEFERRED_PENDING_MEASUREMENT
```

Those markers are historical evidence only; Gate 19.2 later supplied the representative measurement that selected `ASYNC_SUBMIT_STATUS_RESULT`.

OpsLens V1 is a demonstration and architecture lab, not a production SaaS.

## 1. Purpose

OpsLens is an open-source software-supply-chain and GenAI architecture project on AWS.

Product question:

> Given the software actually used by a repository, which vulnerabilities affect it, what exact evidence proves that, which findings should be prioritized, and what verified guidance can help act on them?

Core invariant:

> **Agents reason. Code verifies evidence.**

Permanent boundaries:

```text
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
missing evidence != benign evidence
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
artifact hash != S3 VersionId
publication success != deployment authorization
plan != apply
materialized != enabled
demonstration readiness != production readiness
AIP-C01 topic != product requirement
```

## 2. V1 architecture objective

The V1 demonstration must make the following authority chain understandable and reproducible:

```text
public repository evidence
 -> inert dependency evidence
 -> structured threat evidence
 -> deterministic applicability/correlation
 -> deterministic risk prioritization
 -> bounded retrieval/reasoning where appropriate
 -> evidence-backed result
```

Canonical reviewer target:

```text
clone
 -> setup
 -> one deterministic offline demo command
 -> evidence-backed result
```

No Internet-facing production runtime is required for V1 completion.

## 3. Authority model

### 3.1 Deterministic authority

Deterministic code owns:

- repository/source identity admission;
- immutable repository snapshot identity;
- dependency/package normalization;
- package/version applicability;
- GHSA/NVD reconciliation;
- KEV/EPSS/CVSS evidence lookup;
- risk policy evaluation;
- semantic-query admission;
- SQL compilation;
- retrieval evidence admission;
- citation/result admission;
- capability/tool authorization;
- bounded execution/cost/resource limits;
- async job identity/state/idempotency/retry authority;
- deployment artifact identity;
- Terraform plan/apply evidence boundaries.

### 3.2 Model/agent authority

Models and agents may:

- classify;
- plan;
- route;
- summarize;
- explain;
- synthesize over admitted evidence.

They may not invent or override package identity, vulnerability applicability, source provenance, risk truth, arbitrary SQL, tool authorization, or missing-evidence semantics.

## 4. Retained platform architecture

### 4.1 Threat intelligence

```text
NVD
GitHub Security Advisories
CISA KEV
FIRST EPSS
        |
        v
source-preserving raw evidence
        |
        v
deterministic normalization/versioning
        |
        v
exact source coordinates + hashes/snapshots
```

The project preserves source-local provenance before enrichment.

### 4.2 Repository intelligence

```text
public GitHub coordinates
 -> strict request admission
 -> source-confirmed repository metadata
 -> immutable commit snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic TOML parsing
 -> canonical PyPI identity
```

Repository code is never executed.

### 4.3 Vulnerability correlation and risk

```text
canonical dependency identity
 + GHSA/NVD applicability evidence
 + KEV snapshot
 + EPSS snapshot
 + CVSS evidence
        |
        v
RepositoryAnalysisResult
        |
        v
deterministic Risk Policy
```

Risk remains deterministic. A model may explain the admitted result but cannot change it.

### 4.4 Structured natural-language fact path

```text
natural-language factual question
 -> bounded Bedrock proposal
 -> deterministic parser/admission
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured result
```

No unrestricted text-to-SQL authority is granted.

### 4.5 Knowledge/remediation path

```text
official knowledge corpus
 -> canonical documents/chunks
 -> Bedrock Knowledge Base
 -> S3 Vectors
 -> bounded Retrieve
 -> deterministic evidence admission
 -> bounded synthesis
 -> answer + citations
```

Structured vulnerability truth remains outside the RAG authority boundary.

### 4.6 Hybrid retrieval

```text
question
 -> deterministic routing/scope
 -> structured evidence and/or semantic evidence
 -> authority-preserving evidence envelope
 -> bounded synthesis
```

Semantic evidence does not replace structured facts.

### 4.7 Agentic reasoning

```text
admitted evidence
 -> deterministic capability scope
 -> bounded model reasoning/proposal
 -> deterministic capability authorization
 -> typed execution
 -> result admission
```

The simpler single-agent baseline remains the reference reasoning architecture. Multi-agent specialization/handoff is retained where useful, but measured additional model topology is not retained by default without quality lift.

### 4.8 MCP and A2A

MCP and A2A are bounded interoperability layers, not new business authority.

```text
protocol request
 -> strict identity/schema admission
 -> existing typed capability boundary
 -> admitted result projection
```

Public production MCP/A2A runtimes are not V1 requirements.

### 4.9 AgentCore

Amazon Bedrock AgentCore is retained as an optional lab target after capability-fit experiments. It is not the default production runtime and carries no standing experiment IAM merely because it exists in the project history.

### 4.10 Runtime exposure evidence

Amazon Inspector is treated as an independent read-only runtime-evidence authority.

```text
Inspector read evidence != repository risk truth
zero Inspector records != zero runtime exposure
```

## 5. Observability, security, and cost

### 5.1 Observability

Operational telemetry is content-minimized and does not become business authority.

The project retains CloudWatch/EMF-oriented operational evidence, traces/metrics where relevant, explicit retry/latency counters, and persisted experiment artifacts.

### 5.2 Security

Retained hardening includes:

- full-SHA GitHub Actions pinning;
- Dependency Review;
- CodeQL;
- adversarial authority regression;
- least-privilege IAM;
- content-minimized Lambda telemetry;
- bounded scheduled-ingestion pause/recovery;
- protected-main review boundaries;
- fail-closed request/evidence/result admission.

### 5.3 Cost semantics

OpsLens distinguishes:

```text
MEASURED
DERIVED
CONFIGURED_LIMIT
UNMEASURED
NOT_APPLICABLE
```

Bounded experiment cost evidence is never promoted to a production TCO claim.

## 6. Phase 19 async runtime architecture

Gate 19.2 selected `ASYNC_SUBMIT_STATUS_RESULT` from representative measurement evidence.

Gate 19.3 selected:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

Retained shape:

```text
POST /v1/analyses
 -> API Gateway HTTP API
 -> API Lambda
 -> DynamoDB job/idempotency authority
 -> SQS standard queue
 -> Lambda worker
 -> retained analysis authorities
 -> DynamoDB status/result
 -> SQS DLQ

GET /v1/analyses/{job_id}
GET /v1/analyses/{job_id}/result
```

Queue delivery is transport evidence, not execution truth. DynamoDB conditional state/attempt authority owns business execution state.

## 7. Phase 19 deployment evidence

### 7.1 Immutable artifacts

Gate 19.5 produced separate deterministic API/worker deployment ZIPs and preserved both content hash and exact S3 object VersionId.

```text
artifact hash != S3 VersionId
publication success != deployment authorization
```

### 7.2 Exact Terraform planning

Gate 19.6 admitted an exact plan before any apply:

```text
21 create
0 update
0 delete
0 replacement
```

### 7.3 Controlled disabled materialization

Gate 19.7 materialized the runtime through bounded HUMAN-authorized Terraform operations, recovered from one account-level Lambda reserved-concurrency constraint, and proved final convergence:

```text
0 add
0 change
0 destroy
0 replacement
```

Current retained runtime truth:

```text
public async runtime resources materialized: 21
public endpoint enabled: NO
submit enabled: NO
worker enabled: NO
event-source mapping enabled: NO
custom public domain: absent
provider-heavy public executions: 0
```

```text
materialized != enabled
```

## 8. Gate 19.8 request-time threat evidence authority

Gate 19.8 protected-merged through PR #375 at:

```text
e538fa3e96c29cf76dd3aa83a9967e090587b6fb
```

Post-merge CodeQL:

```text
34713360403 / run #393 / success
```

The provider-neutral authority chain is:

```text
PublicRepositoryEvidenceExecution
 -> PublicThreatEvidenceScope
 -> PublicThreatEvidenceRequest
 -> PublicThreatEvidenceAuthority
 -> PublicRepositoryThreatEvidence
 -> retained deterministic correlation/enrichment
```

Semantics:

```text
scope derives only from admitted repository evidence
incomplete PyPI normalization -> fail closed
out-of-scope GHSA evidence -> reject
unrelated NVD evidence -> reject
latest_complete = selection policy, not provenance
selected KEV/EPSS evidence carries exact snapshot date + SHA-256
model authority for source truth/applicability = none
```

The physical provider adapter remains deliberately deferred. Because V1 is offline-first, that adapter is now a Post-V1 experiment instead of a V1 blocker.

## 9. Gate 19.9 V1 demonstration boundary

Gate 19.9 freezes the first-release product boundary:

```text
V1 mode: DEMONSTRATION_ARCHITECTURE_LAB
production SaaS claim: NO
Internet-facing runtime required: NO
AWS credentials required for canonical demo: NO
third-party repository code execution: NO
```

Remaining completion slices:

```text
19.9   V1 demonstration contract + current-state synchronization
19.10  deterministic end-to-end demo runner
19.11  curated scenarios + deterministic evaluation
19.12  minimal local visual demo
19.13  portfolio/readme/architecture polish
19.14  V1 closeout + release readiness
```

## 10. Canonical V1 demo architecture

The canonical V1 demo path will be local and offline-first:

```text
curated inert scenario fixture
 -> existing repository/dependency evidence contracts
 -> existing threat evidence contracts
 -> deterministic correlation/enrichment
 -> deterministic risk policy
 -> stable machine-readable result
 -> human-readable projection
 -> optional bounded explanation over admitted evidence
```

The demo must reuse retained OpsLens application/domain authorities rather than create a second implementation of business truth.

Required scenario classes:

```text
material vulnerability
controlled benign
fail-closed incomplete/ambiguous evidence
```

## 11. V1 non-goals

The first release does not require:

```text
Internet-facing production runtime
authentication / OIDC / Cognito
multi-tenancy
commercial billing/quotas
custom public domain
WAF / production abuse controls
24x7 operations
production SLO/SLA
HA/DR program
production TCO claim
public worker/event-source enablement
provider-backed arbitrary request-time threat adapter
```

These are tracked in [`post-v1-backlog.md`](post-v1-backlog.md).

## 12. Current authority boundary

Gate 19.9 is repository-only and offline-only.

```text
Terraform/provider operations: NOT AUTHORIZED
AWS mutation:                 NOT AUTHORIZED
IAM mutation:                 NOT AUTHORIZED
artifact publication:         NOT AUTHORIZED
runtime enablement:           NOT AUTHORIZED
provider-heavy live execution:NOT AUTHORIZED
protected merge:              HUMAN REVIEW REQUIRED
```

## 13. Key documents

- [`current-state.md`](current-state.md)
- [`roadmap.md`](roadmap.md)
- [`v1-demonstration-scope.md`](v1-demonstration-scope.md)
- [`v1-completion-checklist.md`](v1-completion-checklist.md)
- [`demo/README.md`](demo/README.md)
- [`post-v1-backlog.md`](post-v1-backlog.md)
- [`adr/0077-phase19-v1-demonstration-boundary.md`](adr/0077-phase19-v1-demonstration-boundary.md)
- [`../labs/phase-19-gate-19-9-v1-demonstration-contract.md`](../labs/phase-19-gate-19-9-v1-demonstration-contract.md)

Historical labs and machine-readable evidence remain immutable records of the state that existed when each experiment was executed.
