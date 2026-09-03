# OpsLens Architecture

_Last updated: 2026-09-03_

This document is the accumulated architecture baseline after completion of **Phase 5 — Risk Prioritization Engine**.

The next roadmap boundary is **Phase 6 — Semantic Query Layer**.

## 1. Purpose

OpsLens is an open-source software supply chain and threat-intelligence platform on AWS.

The product goal is:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, and which findings should I prioritize?

The architecture deliberately establishes trustworthy deterministic evidence and policy enforcement before adding semantic, generative, or agentic reasoning.

Core invariant:

> **Agents reason. Code verifies evidence.**

Additional permanent boundaries:

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

## 2. Permanent architectural principles

Unless changed by an explicit ADR:

- raw third-party evidence is preserved before enrichment or interpretation;
- deterministic facts remain authoritative;
- exact source versions and content hashes participate in evidence provenance;
- package identity normalization remains deterministic;
- version parsing and vulnerable-range matching remain deterministic;
- vulnerability applicability remains deterministic;
- CVE/GHSA/NVD alias reconciliation remains deterministic;
- KEV/EPSS/CVSS evidence remains deterministic and source-preserving;
- risk-policy evaluation remains deterministic;
- semantic-query validation and SQL compilation remain deterministic;
- evidence validation remains deterministic;
- execution/tool/cost enforcement remains deterministic;
- LLMs may later classify, plan, route, synthesize, and explain over validated evidence;
- LLMs do not replace applicability, source evidence, or risk-policy enforcement;
- natural-language planning never receives unrestricted SQL authority;
- third-party repository content is untrusted data to inspect, never code to execute;
- Repository Risk is not Runtime Exposure;
- missing evidence is not silently converted into benign evidence;
- duplicate delivery is expected and replay must be safe;
- schema, provenance, authority, or exact-evidence mismatches fail closed;
- IAM uses least privilege and responsibility separation;
- AWS services are introduced only for concrete requirements;
- cost and observability are architectural requirements;
- one real `dev` environment is preferred over fictional portfolio environments.

## 3. Current system shape

The implemented system now has four deterministic layers.

```text
THREAT INTELLIGENCE DATA
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
        |
        v
DETERMINISTIC CORRELATION
PyPI identity + PEP 440 + GHSA range + CVE/NVD alias evidence
        |
        v
REPOSITORY INTELLIGENCE
immutable public GitHub snapshot + inert uv.lock + deterministic findings
        |
        v
RepositoryAnalysisResult
        |
        v
RISK PRIORITIZATION
versioned Risk Policy v1 + factor evidence + deterministic ranking
        |
        v
RiskPrioritizationResult
```

Risk Policy is a downstream policy authority. It does not become a new source of vulnerability applicability truth.

## 4. AWS foundation

```text
environment:             dev
primary workload Region: us-east-1
IaC:                     Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

Only one real environment exists: `dev`.

Human administration uses temporary IAM Identity Center credentials. GitHub Actions assumes AWS roles through OIDC; persistent AWS access keys are not stored in GitHub.

Terraform layout:

```text
infra/
  bootstrap/
  environments/
    dev/
```

Primary storage:

```text
Data:       opslens-dev-data-487757851499-us-east-1
Artifacts:  opslens-dev-artifacts-487757851499-us-east-1
TF state:   opslens-dev-tfstate-487757851499-us-east-1
```

Analytics:

```text
Glue database:    opslens_dev
Athena workgroup: opslens-dev
scan cutoff:      10,485,760 bytes
```

## 5. Threat Intelligence Data Lake — Phase 2

Phase 2 preserves source-local authority. NVD, KEV, EPSS, and GHSA are not flattened into one lossy universal source record.

### 5.1 FIRST EPSS current path

```text
FIRST EPSS
 -> EventBridge Scheduler
 -> EPSS ingestion Lambda
 -> immutable S3 Bronze
 -> deterministic Silver transformer
 -> Parquet
 -> Glue: opslens_dev.epss_scores
 -> Athena
```

Temporal selection is explicit through snapshot date.

### 5.2 Historical EPSS

Historical bulk authority is pinned to a specific archive commit and fills the canonical EPSS Silver relation before the forward-path boundary.

Frozen interval:

```text
2021-04-14 .. 2026-08-13
```

The historical path preserves exact source bytes, source hash, Git archive coordinates, S3 object versions, model-era semantics, deterministic Silver output, and completion evidence.

No missing source date is silently substituted.

### 5.3 CISA KEV

```text
CISA KEV JSON
 -> bounded ingestion
 -> immutable Bronze
 -> exact-version source verification
 -> deterministic Silver normalization
 -> Parquet
 -> Glue: opslens_dev.kev_entries
 -> Athena
```

KEV absence is meaningful only against one complete validated snapshot.

### 5.4 NVD / CVE

```text
NVD yearly feeds                  NVD CVE API 2.0
       |                                  |
       v                                  v
Bootstrap Bronze                  Incremental Bronze
       |                                  |
       +----------> versioned Silver <----+
                          |
                          v
                    Silver COMPLETE
                          |
                          v
                authoritative watermark
                          |
                          v
               permanent analytics projection
                          |
                          v
                 Glue + bounded Athena
```

Authority invariant:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

The analytics projector is downstream-only and cannot advance authoritative NVD state.

### 5.5 GitHub Security Advisories

```text
GitHub Global Security Advisories REST API
 -> reviewed-only Bronze pages + COMPLETE
 -> exact advisory content identity
 -> deterministic normalization
 -> immutable one-row Parquet per observed advisory version
 -> Silver COMPLETE
 -> Glue: opslens_dev.ghsa_advisory_versions
 -> Athena
```

Important identities remain separate:

```text
sync_id                       logical source window
attempt_id                    exact physical source observation
observed_advisory_version_id  exact advisory content identity
vulnerability_entry_id        exact advisory vulnerability occurrence
```

GHSA package/range/fix evidence remains source-local even when a CVE alias is also observed in NVD.

## 6. Vulnerability Correlation Engine — Phase 3

Phase 3 is complete for the explicitly supported **PyPI v1** scope.

### 6.1 Identity authority

```text
source ecosystem alias
 -> canonical ecosystem: pypi
package name
 -> PyPA normalization
version
 -> PEP 440 Version
package + version
 -> canonical pkg:pypi/... purl
```

Original source spelling and canonical identity are both preserved.

### 6.2 Vulnerable-range authority

Supported GHSA operators:

```text
=  <  <=  >  >=
```

Comma-separated clauses are deterministic conjunctions.

Result states:

```text
affected
not_affected
unsupported
```

Unsupported/malformed semantics never collapse to `not_affected`.

`first_patched_version` is remediation evidence only; it does not override the published vulnerable range.

### 6.3 GHSA/NVD alias boundary

GitHub's CVE assertion and NVD's exact observed CVE version remain independent source records.

Reconciliation states include:

```text
no_github_cve
github_asserted_only
nvd_observed
nvd_rejected
```

A matching NVD record creates an evidence edge; it does not replace GHSA provenance.

### 6.4 Correlation evidence identity

The final Phase 3 record uses canonical JSON and SHA-256 content addressing:

```text
correlation:v1@sha256:<digest>
```

The record contains installed identity, applicability outcome, range clauses, fix evidence, exact GHSA coordinates, and exact NVD alias coordinates when supplied.

Permanent rule:

> **No LLM decides vulnerability applicability.**

## 7. Repository Intelligence — Phase 4

Phase 4 analyzes a supported public GitHub repository without executing its code.

Current v1 scope:

```text
provider:             public GitHub repositories
repository evidence: root-level uv.lock
supported packages:  canonical PyPI source records
network operation:   bounded read-only GitHub REST
code execution:      never
```

### 7.1 Immutable repository authority

Authority combines GitHub's numeric repository ID with an exact commit SHA.

```text
owner/name/ref
 -> canonical GitHub metadata
 -> exact commit SHA
 -> exact tree SHA
 -> immutable snapshot
```

After resolution, moving refs remain provenance only.

### 7.2 Bounded GitHub transport

The acquisition boundary uses HTTPS to a fixed host, GET only, bounded timeouts and response bytes, no redirects, no automatic retry loops, and no arbitrary caller-supplied absolute URL authority.

### 7.3 Immutable `uv.lock`

Only root-level `uv.lock` is allowlisted in v1.

The file is read at `snapshot.commit_sha`, treated as inert bytes, bounded to 1 MiB, verified against the Git blob SHA-1, and independently hashed with SHA-256.

No `uv`, package manager, build, test, Dockerfile, setup hook, workflow, or repository script is executed.

### 7.4 Deterministic parsing and normalization

The parser uses stdlib `tomllib` over already verified bytes, preserves source indexes and resolution markers, caps work at 5,000 package records, and keeps unsupported source kinds explicit.

Supported PyPI records are normalized only through the Phase 3 authority.

### 7.5 Repository vulnerability findings

```text
locked dependency
 + exact GHSA occurrence
 -> canonical package join
 -> deterministic range evaluation
 -> affected | not_affected | unsupported
```

Only `affected` emits a repository finding.

```text
repository-finding:v1@sha256:<digest>
```

The finding proves repository-risk evidence at the immutable snapshot. It does not prove runtime presence or exploitability.

### 7.6 NVD/CVSS enrichment

Affected findings may receive exact NVD evidence without changing applicability truth.

Every supported CVSS observation is preserved. Phase 4 intentionally does not choose a preferred/highest/merged score.

### 7.7 CISA KEV enrichment

States:

```text
present
absent
cve_unavailable
```

`absent` is valid only after proving non-membership in a complete validated catalog snapshot.

### 7.8 FIRST EPSS enrichment

States:

```text
score_present
score_absent
cve_unavailable
```

Evidence comes from exactly one explicitly selected current or historical snapshot. There is no automatic `latest`, max-score, trend, or nearest-date selection.

### 7.9 Final projection

`RepositoryAnalysisResult` derives a consumer-facing projection from the fully validated evidence chain.

Final identities:

```text
repository-analysis-finding:v1@sha256:<digest>
repository-analysis:v1@sha256:<digest>
```

Phase 4 assigns no priority and no runtime-exposure claim.

## 8. Risk Prioritization Engine — Phase 5

Phase 5 introduces a downstream **policy authority** that remains separate from Phase 4 source facts.

### 8.1 Architectural boundary

```text
RepositoryAnalysisResult
 -> application projection
 -> RiskFindingInput
 -> pure deterministic Risk Policy v1
 -> RiskFactorContribution[]
 -> priority score + tier
 -> completeness / review_required
 -> deterministic ranking
 -> RiskPrioritizationResult
```

The `risk_policy` domain makes no network calls and has no AWS, GitHub, NVD, KEV, EPSS, or model adapter authority.

### 8.2 Risk Policy v1

Maximum score: `100`.

```text
KEV present                         +40

EPSS >= 0.70                        +30
EPSS >= 0.30 and < 0.70            +20
EPSS >= 0.10 and < 0.30            +10
EPSS < 0.10                           +0

max supported CVSS >= 9.0           +20
max supported CVSS >= 7.0           +10
max supported CVSS >= 4.0            +5
max supported CVSS < 4.0              +0

known fixed version                  +10
```

Priority tiers:

```text
P0  score >= 80
P1  score >= 60 and < 80
P2  score >= 30 and < 60
P3  score < 30
```

This value is explicitly an **OpsLens priority score**.

It is not an exploitation probability, a replacement for EPSS/CVSS/KEV, or a runtime-exposure score.

### 8.3 CVSS policy aggregation

Phase 4 preserves all supported NVD CVSS observations.

Risk Policy v1 introduces the downstream aggregation:

```text
max supported observed CVSS base score
```

The selected value exists only in policy evidence. Original source observations remain intact.

If a future unsupported CVSS family appears, v1 assigns no CVSS points and marks the evaluation `partial/review_required` instead of pretending complete support.

### 8.4 Missing evidence

```text
KEV absent in complete catalog      -> complete negative evidence
EPSS absent in complete snapshot    -> complete negative evidence
CVE unavailable                     -> partial / review_required
no supported CVSS evidence          -> partial / review_required
unsupported CVSS family             -> partial / review_required
```

Missing evidence receives no fabricated risk points, but a low score with partial evidence also cannot be represented as a complete low-risk conclusion.

### 8.5 Fixed version

A known first patched version contributes `+10` as an explicit actionability bonus.

This does not alter applicability. Absence of a known fix does not prove remediation is impossible.

### 8.6 Policy identities

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

Same evidence + same policy reproduces the same identities and priority.

### 8.7 Ranking

```text
1. priority_score descending
2. analysis_finding_id ascending
```

The tie-breaker exists only for reproducibility and carries no risk meaning.

### 8.8 Factors excluded from v1

```text
direct vs transitive
runtime deployment presence
runtime package activation
reachability
internet exposure
business criticality
asset criticality
```

A future policy version may use them only after deterministic upstream evidence contracts exist.

## 9. Evidence and cache boundary

Content-addressed identities include the selected threat-intelligence evidence.

```text
same repository commit
 + different temporal KEV/EPSS evidence
 -> potentially different RepositoryAnalysisResult
 -> potentially different RiskPrioritizationResult
```

The commit alone is not a safe cache key.

No cache backend exists because no measured workload yet justifies storage cost, invalidation, IAM, observability, failure recovery, and retention semantics.

## 10. Security boundaries

```text
Human administration
 -> AWS IAM Identity Center

GitHub Actions
 -> OIDC
 -> deployment role
 -> Terraform changes

Threat-intelligence runtimes
 -> source-specific least-privilege roles

Repository Intelligence
 -> bounded public GitHub read-only authority
 -> inert data only
 -> zero third-party code execution

Risk Policy
 -> deterministic Phase 4 evidence only
 -> no network or model authority
```

A deterministic repository priority remains a **Repository Risk** result. Runtime Exposure remains a separate future evidence domain.

## 11. Cost discipline

- no Glue crawler where explicit schemas suffice;
- no DynamoDB/cache before measured reuse;
- no Step Functions without real workflow semantics;
- no Iceberg requirement yet;
- no vector database before retrieval;
- no Bedrock call in applicability or prioritization;
- Athena dev workgroup with a 10 MiB scan cutoff.

Incremental AWS cost from Phase 5: `$0`.

## 12. Quality gates

Dedicated deterministic CI slices now cover:

```text
Correlation
Repository Intelligence
Risk Policy
```

Phase 5 closeout:

```text
Risk Policy Ruff:                 PASS
Risk Policy Pyright:              0 errors / 0 warnings
Risk Policy pytest:               31 passed
Repository Intelligence pytest:   174 passed
Correlation pytest:               116 passed
```

AWS-bearing changes additionally use Terraform fmt/validate, TFLint, Checkov, canonical plan review, deployment verification, and post-apply convergence checks.

## 13. ADRs through Phase 5

```text
0001 Terraform state strategy
0002 GitHub Actions OIDC
0003 AWS Region strategy
0004 NVD ingestion/versioning
0005 GHSA source/synchronization
0006 GHSA Silver content identity
0007 GHSA runtime credentials/retry
0008 PyPI correlation semantics
0009 immutable public repository snapshot
0010 bounded read-only GitHub REST transport
0011 immutable uv.lock evidence
0012 deterministic uv.lock parser
0013 Phase 3 PyPI normalization bridge
0014 deterministic repository vulnerability findings
0015 repository NVD/CVSS enrichment
0016 repository KEV snapshot enrichment
0017 repository EPSS snapshot enrichment
0018 repository analysis result projection
0019 deterministic Risk Policy v1
```

`docs/adr/README.md` is the canonical index.

## 14. Non-goals at the current boundary

Not yet implemented:

- private repositories;
- arbitrary manifests;
- ecosystems beyond PyPI v1;
- runtime exposure;
- reachability;
- business/asset criticality;
- unrestricted text-to-SQL;
- RAG/vector retrieval;
- autonomous remediation;
- agentic authority over deterministic evidence;
- arbitrary MCP.

## 15. Next boundary — Phase 6 Semantic Query Layer

```text
User question
 -> Amazon Bedrock planner
 -> typed SemanticQuery
 -> deterministic validator
 -> deterministic SQL compiler
 -> bounded read-only Athena workgroup
 -> structured evidence
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

The model may propose a typed semantic intent. Application code owns allowlists, validation, SQL compilation, limits, and execution authority.

Before Phase 6 implementation, current official Amazon Bedrock and Athena documentation must be checked for APIs, available models, IAM, limits, and pricing.

The first Phase 6 gate should freeze one narrow factual question, the typed query contract, and the SQL compiler boundary before API/UI/RAG/agent work.
