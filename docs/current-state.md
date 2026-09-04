# OpsLens — Current State

_Last updated: 2026-09-04_

This document is the public implementation checkpoint for the OpsLens repository.

## Status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2.1  CISA KEV Bronze ingestion                          COMPLETE
Phase 2.2  CISA KEV Silver + Glue + Athena                    COMPLETE
Phase 2.3  NVD / CVE Bronze + Silver + Watermark + Analytics  COMPLETE
Phase 2.4  GitHub Security Advisories                         COMPLETE
Phase 2.5  Historical EPSS expansion                          COMPLETE
Phase 2    Threat Intelligence Data Lake                      COMPLETE
Phase 3    Vulnerability Correlation Engine                   COMPLETE
Phase 4    Repository Intelligence                            COMPLETE
Phase 5    Risk Prioritization Engine                         COMPLETE
Phase 6    Semantic Query Layer                               IN PROGRESS
  Gate 6.1 Typed contract + deterministic SQL compiler        COMPLETE
  Gate 6.2 Bounded read-only Athena execution                 COMPLETE
  Gate 6.3 Bounded planner contract + offline evaluation      COMPLETE
  Gate 6.4 Real Bedrock planner invocation                    NEXT
```

Latest merged implementation checkpoint before the Gate 6.3 branch:

```text
commit: b7a05bc56269f10f841af86027260085219a7143
PR:     #87 — fix(semantic-query): close Gate 6.2 with hardened Athena boundary
status: merged
```

Gate 6.3 is implemented in PR #88 and is ready for merge after its final documentation-only CI validation. It adds no real model invocation or AWS authority.

## What is implemented

OpsLens now has five deterministic layers or authorities plus an offline bounded planner contract available to later model-driven orchestration:

```text
1. Threat Intelligence Data Lake
   NVD / CISA KEV / FIRST EPSS / GitHub Security Advisories

2. Vulnerability Correlation Engine
   PyPI identity / PEP 440 applicability / GHSA / CVE-NVD evidence

3. Repository Intelligence
   immutable public GitHub snapshot / inert uv.lock / repository findings

4. Risk Prioritization Engine
   versioned deterministic Risk Policy v1 / factor explanations / ranking

5. Semantic Query deterministic foundation
   typed query contract / allowlists / deterministic SQL / bounded Athena execution

6. Offline bounded planner contract
   bounded natural-language request / structured-output schema /
   deterministic model-output parser / golden evaluation dataset
```

End-to-end repository analysis path:

```text
public GitHub repository
 -> immutable repository identity
 -> exact commit + tree SHA
 -> bounded GET-only GitHub REST acquisition
 -> exact inert uv.lock bytes
 -> deterministic TOML parsing
 -> PyPI package/version/purl normalization
 -> GHSA vulnerable-range applicability
 -> CVE/GHSA/NVD evidence reconciliation
 -> exact NVD/CVSS enrichment
 -> complete-snapshot CISA KEV evidence
 -> explicit-date FIRST EPSS evidence
 -> content-addressed RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> factor contributions
 -> priority score + tier + evidence completeness
 -> content-addressed RiskPrioritizationResult
```

Current Phase 6 structured-query path:

```text
bounded natural-language question
 -> frozen planner request/schema contract (offline in Gate 6.3)
 -> deterministic planner-output parser
 -> typed SemanticQuery
 -> deterministic validation
 -> deterministic SQL compiler
 -> exact compiler-shape admission
 -> opslens-dev Athena workgroup
 -> explicit EPSS snapshot partition
 -> bounded structured result evidence
```

No third-party repository code is executed.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

The following remain deterministic authorities:

- package identity normalization;
- version parsing and vulnerable-range matching;
- vulnerability applicability;
- CVE/GHSA/NVD alias reconciliation;
- KEV, EPSS, and CVSS evidence;
- risk policy evaluation;
- canonical evidence serialization and content addressing;
- planner-output validation into the typed semantic contract;
- semantic-query validation and SQL compilation;
- Athena query execution bounds and result validation;
- evidence validation;
- execution/tool/cost enforcement.

LLMs may later plan, route, synthesize, and explain over validated evidence. They do not replace deterministic truth or receive arbitrary SQL authority.

## Phase 2 — Threat Intelligence Data Lake

Phase 2 is complete and provides source-local deterministic evidence for:

- FIRST EPSS current snapshots;
- historical EPSS from `2021-04-14` through `2026-08-13` under a pinned archive commit;
- CISA Known Exploited Vulnerabilities;
- NVD CVE observations and CVSS metrics;
- GitHub reviewed security advisories;
- GHSA package, vulnerable-range, and first-patched-version evidence;
- explicit source provenance and time coordinates.

Implemented AWS services include S3, Lambda, EventBridge Scheduler, Glue, Athena, CloudWatch, X-Ray, SQS failure destinations, IAM Identity Center, and GitHub Actions OIDC identities where required by the deployed data paths.

## Phase 3 — Vulnerability Correlation Engine

Phase 3 is complete for the supported **PyPI v1** scope.

Implemented deterministic semantics include:

```text
PyPI/PyPA package normalization
PEP 440 concrete versions
canonical PyPI purl
strict GHSA vulnerable-range evaluation
affected | not_affected | unsupported
first-patched-version evidence separated from applicability
exact GHSA source occurrence provenance
CVE/GHSA/NVD reconciliation
correlation:v1@sha256:<digest>
```

Final validation:

```text
Correlation Ruff:     PASS
Correlation Pyright:  0 errors / 0 warnings
Correlation pytest:   116 passed
```

Closeout: [`labs/phase-3-correlation-engine-closeout.md`](labs/phase-3-correlation-engine-closeout.md).

## Phase 4 — Repository Intelligence

Phase 4 is complete for the deliberately narrow v1 scope:

```text
provider:          public GitHub
repository file:   root-level uv.lock
ecosystem:         canonical PyPI records
version semantics: PEP 440
repository action: read only
code execution:    never
```

The implementation established:

1. immutable public repository identity and exact commit/tree evidence;
2. bounded fixed-host GET-only GitHub REST transport;
3. exact inert `uv.lock` evidence with Git blob SHA-1 and independent SHA-256 verification;
4. bounded stdlib `tomllib` parsing;
5. normalization through the Phase 3 PyPI authority;
6. deterministic repository vulnerability findings;
7. exact NVD/CVSS enrichment;
8. complete-snapshot CISA KEV membership evidence;
9. exact current or historical EPSS evidence;
10. content-addressed final `RepositoryAnalysisResult`.

Final identities include:

```text
repository-finding:v1@sha256:<digest>
repository-analysis-finding:v1@sha256:<digest>
repository-analysis:v1@sha256:<digest>
```

Final validation:

```text
Repository Intelligence Ruff:     PASS
Repository Intelligence Pyright:  0 errors / 0 warnings
Repository Intelligence pytest:   174 passed
```

Closeout: [`labs/phase-4-repository-intelligence-closeout.md`](labs/phase-4-repository-intelligence-closeout.md).

## Phase 5 — Risk Prioritization Engine

Phase 5 is complete with **Risk Policy v1**.

Risk Policy v1 consumes only evidence Phase 4 can already prove:

```text
CISA KEV membership
FIRST EPSS score at the selected snapshot
supported NVD CVSS base-score observations
known first-patched-version availability
```

It deliberately excludes direct/transitive status, runtime presence, reachability, internet exposure, business criticality, and asset criticality because those evidence contracts do not exist yet.

### Risk Policy v1

```text
KEV present                         +40
EPSS >= 0.70 / 0.30 / 0.10          +30 / +20 / +10
max supported CVSS >= 9 / 7 / 4     +20 / +10 / +5
known fixed version                 +10
maximum                              100
```

Priority tiers:

```text
P0 >= 80
P1 >= 60
P2 >= 30
P3 < 30
```

This is an OpsLens **priority score**, not exploit probability, source severity, or runtime exposure.

The CVSS maximum is an explicit downstream policy aggregation. Phase 4 still preserves all original supported CVSS observations.

### Missing evidence

Risk Policy v1 distinguishes proven negative evidence from missing/unsupported evidence.

```text
KEV absent in complete catalog     -> complete negative evidence
EPSS absent in complete snapshot   -> complete negative evidence
CVE unavailable                    -> partial / review_required
unsupported future CVSS family     -> partial / review_required
no supported CVSS evidence         -> partial / review_required
```

Missing evidence adds no fabricated points, but it also cannot masquerade as a confident low-risk result.

### Deterministic identities

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

Equal-score ranking uses `analysis_finding_id` ascending only as a reproducible tie breaker, with no risk semantics.

Final validation:

```text
Risk Policy Ruff:                 PASS
Risk Policy Pyright:              0 errors / 0 warnings
Risk Policy pytest:               31 passed
Repository Intelligence pytest:   174 passed
Correlation pytest:               116 passed
```

Phase 5 introduced:

```text
new AWS resources:     0
new IAM permissions:   0
model calls:           0
incremental AWS cost:  $0
```

Closeout: [`labs/phase-5-risk-policy-closeout.md`](labs/phase-5-risk-policy-closeout.md).

## Phase 6 — Semantic Query Layer

Phase 6 is **in progress**. The deterministic query boundary and offline planner contract are established before any real Bedrock invocation is allowed to participate.

### Gate 6.1 — typed semantic query + SQL compiler — COMPLETE

The first supported factual slice is intentionally narrow:

> Which CVEs have EPSS of at least 0.7 on an explicit snapshot date?

Implemented deterministic contract:

```text
metric:       epss_score
dimension:    cve
filters:      explicit snapshot_date, optional minimum_score
order:        epss_score ASC|DESC, deterministic cve ASC tie break
limit:        1..100, default 20
```

The compiler owns database/table/columns/predicates/order/limit. Filter values become validated positional Athena execution parameters. ADR 0020 permanently rejects unrestricted text-to-SQL.

### Gate 6.2 — bounded read-only Athena execution — COMPLETE

The application executes only compiler-owned EPSS queries through the fixed dev boundary:

```text
database:    opslens_dev
workgroup:   opslens-dev
relation:    "opslens_dev"."epss_scores"
scan cutoff: 10 MiB via enforced workgroup configuration
```

The executor bounds polling, result rows, pagination traversal, metadata consistency, and query/result limit alignment. Defense in depth admits only the exact Gate 6.1 SQL grammar and validated literal parameter shapes even if the adapter is called directly.

Successful real `dev` evidence on 2026-09-04:

```text
query_execution_id:         958fb573-1a69-4ce6-8a36-d9be45e71c79
row_count:                  20
data_scanned_bytes:         3,785,003 (~3.61 MiB)
engine_execution_time_ms:   973
total_execution_time_ms:    1,128
```

Intentional fail-closed evidence:

```text
requested limit: 101
result: SemanticQueryValidationError before compilation/Athena
reason: Semantic query limit must be an integer from 1 to 100.
```

Gate 6.2 introduced no new AWS resources and no model calls. The local IAM Identity Center profile used for smoke validation is not the final runtime least-privilege role.

Closeout: [`../labs/phase-6-gate-6-2-athena-readonly-execution.md`](../labs/phase-6-gate-6-2-athena-readonly-execution.md).

### Gate 6.3 — bounded planner contract + offline evaluation — COMPLETE

Gate 6.3 freezes the model-facing contract without making a Bedrock call:

```text
question length: <= 1,000 chars
planner decisions: semantic_query | unsupported
supported metric: epss_score
supported dimension: exactly [cve]
required time: explicit YYYY-MM-DD
threshold semantics: inclusive >= only
order: epss_score asc|desc
limit: 1..100
output: Bedrock structured-output JSON Schema
SQL authority: none
```

Model output is never trusted as a query directly. The deterministic parser rejects extra/missing fields, relative or invalid dates, unsupported values, invalid score/limit values, and injected SQL, then reconstructs the existing `SemanticQuery` type before compilation is possible.

The frozen offline evaluation fixture contains:

```text
18 total cases
  8 supported semantic-query cases
 10 fail-closed unsupported cases
```

Field-level metrics independently measure decision, metric, dimensions, date, threshold, ordering, limit, exact query, and unsupported-reason accuracy.

Final Gate 6.3 CI evidence:

```text
GitHub Actions run:        33881700812
Semantic Query Ruff:       PASS
Semantic Query Pyright:    0 errors / 0 warnings
Semantic Query pytest:     70 passed in 0.16s
Correlation regression:    PASS
Repository Intel regression: PASS
Risk Policy regression:    PASS
```

Gate 6.3 introduced:

```text
new AWS resources:   0
new IAM permissions: 0
Bedrock calls:       0
Athena calls:        0
incremental AWS cost: $0
```

ADR: [`adr/0021-bounded-bedrock-semantic-query-planner.md`](adr/0021-bounded-bedrock-semantic-query-planner.md).

Closeout: [`../labs/phase-6-gate-6-3-planner-contract-evaluation.md`](../labs/phase-6-gate-6-3-planner-contract-evaluation.md).

Phase 6 is **not complete**. Remaining phase exit criteria include a real bounded Bedrock invocation, real planner accuracy evidence, model/token/latency/cost evidence, diagnosable planner failure behavior, at least one natural-language question through the deterministic execution path, and final runtime IAM boundary when a deployed runtime exists.

## AWS foundation

```text
environment:             dev
primary workload Region: us-east-1
IaC:                     Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

Primary resources:

```text
Data bucket:      opslens-dev-data-487757851499-us-east-1
Artifacts bucket: opslens-dev-artifacts-487757851499-us-east-1
Terraform state:  opslens-dev-tfstate-487757851499-us-east-1
Glue database:    opslens_dev
Athena workgroup: opslens-dev
scan cutoff:      10,485,760 bytes
```

Persistent AWS access keys are not stored in GitHub.

## Current quality boundary

Dedicated Python CI slices now exist for:

```text
src/opslens/correlation
src/opslens/repository_intelligence
src/opslens/risk_policy
src/opslens/semantic_query
```

A pre-existing repo-wide Ruff backlog outside these scoped deterministic slices remains separate technical debt and should not be mixed into Phase 6 without an explicit cleanup decision.

## Next boundary — Gate 6.4: real Bedrock planner invocation

Target architecture remains:

```text
User question
 -> bounded Bedrock planner
 -> structured planner output
 -> deterministic planner-output parser
 -> typed SemanticQuery
 -> deterministic validation
 -> deterministic SQL compiler
 -> exact compiler-shape admission
 -> bounded read-only Athena execution
 -> structured evidence
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

Before Gate 6.4 implementation, revalidate current official AWS documentation for the selected model's lifecycle/availability, direct-vs-cross-Region inference mode, structured-output support, Converse request/response fields, IAM, quotas/throttling behavior, and pricing.

Gate 6.4 is the first gate authorized to make a real Bedrock model call. It must capture model ID, Region/inference mode, input/output/total tokens, planner latency, estimated model cost, one diagnosable planner failure, and at least one supported natural-language factual question through the already-proven deterministic query/Athena path. Do not add RAG, Knowledge Bases, agents, MCP, or AgentCore to this phase.
