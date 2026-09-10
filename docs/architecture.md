# OpsLens Architecture

_Last updated: 2026-09-10_

This document is the accumulated architecture baseline through **Phase 18 — Evaluation, Cost & Portfolio Readiness: COMPLETE pending the Gate 18.5 protected closeout merge**.

The next implementation phase is intentionally **not authorized** by Phase 18. It must be selected from observed product/evidence gaps after closeout.

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
- retry/fallback policy;
- runtime-evidence admission and correlation;
- operational recovery control state expressed through Terraform.

Models and agents may classify, propose, summarize, explain, or synthesize over already-admitted evidence. They do not become authority merely because output is syntactically valid, plausible, or produced by a managed AWS service.

```text
proposal != authorization
retrieval result != sufficient evidence
citation id != semantic support
capability invocation != execution result
execution result != admitted evidence
repository finding != runtime exposure
AWS authentication != business authorization
scheduler state != business/evidence authority
```

## 3. Current system shape

### 3.1 Threat-intelligence and deterministic risk path

```text
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
 -> source-preserving raw evidence
 -> deterministic normalization and applicability
 -> repository dependency evidence
 -> vulnerability correlation
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
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic TOML parsing
 -> canonical dependency identity
 -> deterministic vulnerability applicability
```

Third-party repository code is never executed as part of analysis.

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

The planner has no arbitrary SQL authority.

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

`RetrieveAndGenerate` is not the retained default because retrieval and synthesis are intentionally measured and admitted as separate stages.

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

### 3.6 Public analysis boundary

The public-analysis contract remains an application boundary. No public HTTP compute or public endpoint is retained.

```text
untrusted JSON
 -> <=2048-byte request admission
 -> validated GitHub coordinates
 -> immutable repository evidence
 -> bounded metadata-only semantic planning
 -> deterministic public-v1 scope admission
 -> Phase 8 hybrid authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

The fixed public v1 operation is `analyze_public_repository` and requires exactly:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

No raw repository text, credentials, arbitrary SQL, provider/model selection, or executable repository content becomes planner authority.

## 4. AWS foundation and retained standing services

```text
environment:             dev
primary Region:          us-east-1
IaC:                     Terraform
human administration:    AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
knowledge retrieval:     Amazon Bedrock Knowledge Base + Amazon S3 Vectors
compute:                  AWS Lambda for retained ingestion/transformation paths
recurring triggers:      Amazon EventBridge Scheduler
```

Primary retained storage includes the data bucket, deployment-artifact bucket, Terraform state bucket, and the S3 Vectors knowledge vector bucket.

Standing architecture does **not** claim:

```text
public HTTP endpoint
public application compute
public MCP runtime
public A2A peer runtime
standing AgentCore experiment runtime
standing Inspector experiment IAM
production multi-tenant request surface
```

## 5. Knowledge retrieval baseline

The retained controlled knowledge-retrieval path uses:

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

Permanent interpretation boundaries:

```text
non-empty retrieval != sufficient evidence != authority to answer
retrieval success != citation attribution success != semantic groundedness
```

## 6. Reasoning and agentic architecture

Phase 11 retained the measured direct Bedrock single-agent reference as the default reasoning baseline.

Phase 12 retained deterministic specialization and handoff, but the measured two-model topology was rejected as the default because it added model calls, tokens, latency, and cost without measured quality lift.

Phase 13 retained bounded offline MCP capability exposure/execution/projection contracts. MCP does not add business authority.

Phase 14 retained Amazon Bedrock AgentCore as an optional lab target only. Standing experiment IAM and managed runtime resources were removed after the experiment, and the historical mutating workflow is retired/fail-closed.

Phase 15 retained bounded offline A2A reference interoperability and an exact-source official SDK conformance oracle in CI. No public/network A2A runtime is retained.

## 7. Runtime exposure boundary

Phase 16 introduced a typed read-only Amazon Inspector evidence boundary.

Measured discovery proved `ListCoverage` and `ListFindings` authorization with zero current records. The temporary dedicated Inspector role was removed afterward and independently verified absent.

Therefore:

```text
Inspector API success != runtime evidence presence
Inspector finding != repository finding
runtime evidence correlation != capability authorization
```

Repository risk and runtime exposure remain separate evidence classes.

## 8. Security Hardening — Phase 17 retained state

### 8.1 Gate 17.1 — threat/control-gap inventory

Gate 17.1 established an evidence-first threat inventory and prioritized only observed gaps.

### 8.2 Gate 17.2 — CI/CD and workflow authority

Retained repository controls include:

```text
protected-main required context:     Repository security invariants
external GitHub Actions:             full 40-hex SHA pins
checkout persisted credentials:      disabled where not required
pull_request_target/workflow_run:     rejected by default
EPSS planning identity:              read-only evidence role
EPSS execution identity:             coordinator role
long STS session:                    full-backfill execute path only
historical AgentCore mutation path:  retired / fail-closed
```

A direct write attempt to protected `main` was independently rejected, proving that required CI is merge enforcement rather than documentation-only intent.

### 8.3 Gate 17.3 — dependency and code scanning

Retained security signals:

```text
Dependency Review:  pull_request / fail-on-severity=high / contents:read
CodeQL Python:      PR + main + weekly + manual / contents:read + security-events:write
AWS/OIDC authority: none for both scanner workflows
```

Scanner output remains an engineering signal, not vulnerability-applicability or runtime-exploitability authority.

### 8.4 Gate 17.4 — adversarial authority regression

The retained offline suite contains eight deterministic cases across seven threat classes covering public-input abuse, direct/indirect prompt injection, capability widening, forged result evidence, MCP abuse, A2A reference smuggling, and bounded amplification attempts.

```text
adversarial test success != proof of universal safety
```

The suite has no AWS/OIDC authority and performs no real model or capability execution.

### 8.5 Gate 17.5 — telemetry-content hardening

All 12 retained Powertools Lambda handlers explicitly suppress automatic event, response, and error capture at the decorator boundary. Shared failure logging avoids implicit active-exception traceback serialization and retains bounded operational fields.

```text
log event suppression != trace response/error suppression
exception text != safe telemetry by default
trace metadata != business/evidence truth
```

Repository verification continuously checks the retained telemetry-safety contract.

### 8.6 Gate 17.6 — operational recovery and abuse-cost boundary

The concrete recurring automated ingestion surface is exactly three EventBridge Scheduler resources:

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

Scheduler delivery amplification remains bounded by:

```text
maximum_event_age_in_seconds = 3600
maximum_retry_attempts       = 2
```

The measured post-merge live proof succeeded through:

```text
default convergence
 -> exact 0/3/0 pause plan
 -> exact pause apply
 -> independent 3/3 DISABLED reads
 -> paused convergence
 -> exact 0/3/0 resume plan
 -> exact resume apply
 -> independent 3/3 ENABLED reads
 -> final default convergence
```

No resource was created or destroyed and no new IAM principal, permission, service, public runtime, model invocation, or capability execution was introduced by the experiment.

This is deliberately a **scheduled-ingestion pause**, not a global kill switch.

```text
scheduler pause != global workload termination
pause request != applied AWS state
Terraform apply success != independent AWS state verification
bounded retry != guaranteed delivery
failure destination != successful recovery
model token budget != tenant quota
```

Disabling the schedules does not claim to cancel in-flight Lambda invocations, already accepted retries, already emitted S3 events, manual invocations, separate model paths, or capability authorization.

### 8.7 Gate 17.7 — architecture synchronization

Gate 17.7 closed `SEC17-DOC-001` by synchronizing the accumulated EN/PT-BR architecture with the retained platform.

```text
PR:                       #276
exact head:               ea0460e549dd1b904d139632bfc2988671e23880
protected merge:          3938c6469a979f5b574755ce9fd56a56523626dc
Security Hardening CI:    34474712369 / #34 / SUCCESS
Dependency Review:        34474712371 / #19 / SUCCESS
CodeQL / Python:          34474712380 / #27 / SUCCESS
```

Documentation synchronization changes no runtime or business authority.

### 8.8 Phase 17 closeout

Phase 17 closes at the smallest evidence-backed boundary. No later evidence in the phase justified another security/runtime control.

Retained:

```text
protected-main security enforcement
Dependency Review + CodeQL
adversarial authority regression
content-minimized Lambda telemetry
telemetry-safety verification
bounded scheduled-ingestion pause
operational recovery runbook
synchronized EN/PT-BR architecture
```

Explicitly deferred or not created:

```text
Dependabot version updates
additional continuous pip-audit
broad dependency upgrades
mandatory independent review until governance requires it
public WAF/rate/tenant quotas without a public runtime
public HTTP runtime
global platform kill switch
broad S3/Lambda emergency stop controls
automatic alarm remediation
standing Inspector experiment IAM
public MCP/A2A runtimes
AgentCore as default runtime
```

## 9. IAM and trust principles

- humans use temporary IAM Identity Center credentials;
- GitHub Actions uses OIDC rather than persistent AWS access keys;
- OIDC trust is scoped by audience and repository/ref conditions;
- IAM is introduced for concrete runtime responsibility rather than speculative future surfaces;
- plan/evidence authority is separated from mutation authority where the workload requires it;
- temporary experiment authority is removed after the evidence-generating experiment when it is not part of the retained runtime.

```text
AWS authentication != authorization to perform unrelated work
OIDC authentication != authorization to reuse a shared deployment role
no concrete principal -> no speculative runtime role
```

## 10. Observability and privacy boundary

Operational observability prefers bounded categories, counters, latency, hashes, and correlation identifiers over raw source/model/user content.

Content-minimized telemetry is useful for diagnosis, but it does not become business truth or execution authority.

OpsLens still does not claim production public-request volume, public-user p95/p99 latency, production multi-tenant quotas, or public-edge SLO compliance because no public runtime is retained.

## 11. Cost and amplification boundary

Cost drivers stay separate:

```text
Athena bytes scanned
embedding/query work
S3 Vectors operations
model input/output tokens
Lambda/runtime execution
Scheduler retries
future public transport/runtime cost if ever deployed
```

Call-level token limits, Athena scan limits, Scheduler retry limits, and trigger disable controls solve different problems. None should be relabeled as a generic universal quota or kill switch.

## 12. Failure and recovery semantics

The architecture fails closed on schema, provenance, identity, scope, completeness, request/source binding, evidence-binding, capability-binding, and content-addressed identity mismatches.

A failed stage does not authorize a later stage merely because partial output exists.

Operational recovery similarly distinguishes desired state, applied provider state, independently observed provider state, and already-admitted work.

## 13. Standing versus historical surfaces

Retained historical evidence does not imply standing authority.

```text
historical workflow != inert workflow
historical experiment != standing runtime
historical IAM proof != current IAM principal
retained adapter != deployed network service
retained protocol contract != public peer endpoint
```

AgentCore and Inspector experiments are preserved as evidence while their experiment-specific standing authority remains removed. MCP and A2A are retained as bounded interoperability/reference contracts without public network runtimes.

## 14. Phase 18 — evaluation, cost, and portfolio closeout

Phase 18 is complete through Gates 18.1–18.4 and is being closed by Gate 18.5.

The retained evidence chain is:

```text
18.1 cross-phase evidence inventory + comparability
 -> 18.2 independent evaluation/reliability projection
 -> 18.3 cost/resource accounting + configured limits
 -> 18.4 evidence-bound portfolio + AIP-C01 map
 -> 18.5 closeout without new runtime or benchmark authority
```

Phase 18 preserves four evidence classifications (`MEASURED`, `DERIVED`, `UNMEASURED`, `NOT_APPLICABLE`) and explicit comparability rules. It does not collapse independent metrics into a synthetic readiness score.

Gate 18.2 preserves four negative/rejected-default decision signals. Gate 18.3 separates observed/derived cost evidence from configured limits and forbids unsupported production TCO aggregation. Gate 18.4 exposes portfolio claims only when mechanically bound to admitted source evidence and maps all 20 AIP-C01 task IDs without turning certification breadth into product requirements.

Permanent Phase 18 boundaries include:

```text
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
portfolio claim != new evidence authority
AIP-C01 topic != product requirement
AIP-C01 coverage != certification guarantee
lab metric != production SLO
cost evidence != production TCO
```

Gate 18.5 introduces no AWS/IAM/model/capability mutation, no benchmark replay, and no pricing refresh. Phase 18 therefore changes evidence interpretation and presentation surfaces around the retained architecture rather than standing runtime authority.

The next implementation phase is intentionally **not authorized**. It must be selected from observed product/evidence gaps after the Phase 18 closeout protected merge.

Deferred Governed LLM Gateway integration remains outside this authority chain unless separately re-evaluated and explicitly resumed.

## 15. Key architecture records

Important retained ADRs include:

```text
0020 no unrestricted text-to-SQL
0021 bounded Bedrock Semantic Query planner
0022 customer-managed Bedrock Knowledge Base with S3 Vectors
0023 bounded Bedrock knowledge synthesis
0025 deterministic hybrid routing authority
0026 deterministic hybrid evidence envelope
0027 frozen hybrid evaluation contract
0028 bounded route-aware hybrid synthesis
0029 public repository request admission
0030 public semantic planning proposal authority
0031 Phase 9 public analysis closeout boundary
0059 Phase 15 A2A closeout
0063 Phase 16 runtime-exposure closeout
0064 evidence-first security-hardening priorities
0065 CI/CD and workflow authority hardening
0066 bounded dependency and code-scanning signals
0067 bounded adversarial authority regression suite
0068 content-minimized Lambda telemetry
0069 bounded scheduled-ingestion pause
0070 Phase 17 security-hardening closeout
0071 cross-phase evidence classification and comparability
0072 consolidated evaluation and reliability view
0073 cost accounting and budget envelopes
0074 portfolio evidence and AIP-C01 mapping
0075 Phase 18 evaluation/cost/portfolio closeout
```

Exact historical measurements, experiments, rejected hypotheses, teardown proof, and CI run identities remain in `labs/`, `labs/evidence/`, ADRs, protected PRs, and Git history rather than being reinterpreted as new architecture authority here.
