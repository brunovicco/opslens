# OpsLens Architecture

_Last updated: 2026-09-03_

This document is the accumulated architecture baseline after completion of **Phase 4 — Repository Intelligence**.

The next authority boundary is **Phase 5 — Risk Prioritization Engine**.

## 1. Purpose

OpsLens is an open-source software supply chain and threat-intelligence platform on AWS.

The product goal is:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, and how should those findings eventually be prioritized?

The architecture deliberately establishes trustworthy deterministic evidence before adding semantic or agentic reasoning.

Core invariant:

> **Agents reason. Code verifies evidence.**

## 2. Permanent architectural principles

Unless changed by an explicit ADR:

- raw third-party evidence is preserved before enrichment or interpretation;
- deterministic facts remain authoritative;
- exact source versions and content hashes participate in evidence provenance;
- package identity normalization remains deterministic;
- version parsing and version-range matching remain deterministic;
- vulnerability applicability remains deterministic;
- CVE/GHSA/NVD alias reconciliation remains deterministic;
- KEV/EPSS/CVSS evidence lookup remains deterministic;
- risk policy evaluation will remain deterministic;
- semantic-query validation and SQL compilation remain deterministic;
- evidence validation remains deterministic;
- execution/tool/cost enforcement remains deterministic;
- LLMs may later classify, plan, route, synthesize, and explain over validated evidence;
- natural-language planning never receives unrestricted SQL authority;
- third-party repository code is untrusted data to inspect, never code to execute;
- Repository Risk is not Runtime Exposure;
- duplicate delivery is expected and replay must be safe;
- schema, provenance, authority, or exact-evidence mismatches fail closed;
- IAM uses least privilege and responsibility separation;
- AWS services are introduced only for concrete requirements;
- cost and observability are architectural requirements;
- one real `dev` environment is preferred over fictional portfolio environments.

## 3. Current system shape

The implemented system has three deterministic layers.

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
```

Phase 5 will add a fourth layer:

```text
RepositoryAnalysisResult
        |
        v
Risk Policy v1
        |
        v
versioned deterministic priority decision
```

Risk Policy does not become a new source of applicability truth.

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
provider:             GitHub public repositories
repository evidence:  uv.lock
supported packages:   canonical PyPI source records
network operation:    bounded read-only GitHub REST
code execution:       never
```

### 7.1 Immutable repository identity

Repository identity uses GitHub's numeric repository ID plus source coordinates. A requested ref is resolved to an exact commit and tree SHA.

```text
repository owner/name/ref
 -> GitHub metadata
 -> exact commit SHA
 -> exact tree SHA
 -> immutable snapshot_id
```

Example shape:

```text
github:<repository_id>@<40-char-commit-sha>
```

Moving branch names never become evidence authority after resolution.

### 7.2 Bounded GitHub transport

The repository transport is intentionally narrow:

- fixed GitHub API host;
- GET only;
- bounded timeouts;
- bounded response bytes;
- no redirect authority expansion;
- no automatic unbounded retries;
- explicit rate-limit failures;
- no generic remote URL execution path.

### 7.3 Immutable `uv.lock` evidence

Only the allowlisted `uv.lock` path is accepted in v1.

Acquisition always uses the exact immutable commit, never the moving requested ref.

The evidence verifies:

```text
GitHub path/type/name/encoding/size
Base64 payload
Git blob SHA-1 = sha1("blob <len>\0" + bytes)
independent OpsLens SHA-256
1 MiB content bound
```

The bytes remain inert data.

### 7.4 Deterministic lock parsing

The parser uses Python stdlib `tomllib` over already verified bytes.

It preserves:

- lock schema/revision evidence;
- `requires-python`;
- global/package resolution markers;
- zero-based source record indexes;
- duplicate marker-fork records;
- explicit unsupported source kinds.

It does not execute `uv`, install dependencies, or infer deployment truth from resolution markers.

### 7.5 Phase 3 normalization bridge

Supported canonical-PyPI lock records are normalized only through the existing Phase 3 package/version/purl authority.

Every PyPI-source record is accounted for exactly once as:

```text
normalized
or
unsupported with explicit reason
```

### 7.6 Repository vulnerability findings

Normalized repository dependencies are joined to exact GHSA PyPI vulnerability occurrences by canonical package identity before applicability evaluation.

```text
locked dependency
 + exact GHSA occurrence
 -> canonical package join
 -> Phase 3 range evaluator
 -> assessment
 -> affected repository finding when applicable
```

Unsupported evidence remains explicit and never becomes a false negative.

A positive finding proves repository-risk evidence for the immutable lock snapshot; it does not prove runtime presence or exploitability.

Base findings use content-addressed canonical evidence:

```text
repository-finding:v1@sha256:<digest>
```

### 7.7 NVD/CVSS enrichment

An already affected finding may be enriched with exact NVD evidence without changing applicability truth.

Properties:

- the exact GHSA occurrence is rebound before alias reconciliation;
- zero or one exact NVD observed version is supplied per CVE;
- duplicate NVD candidates fail closed instead of choosing `latest`;
- CVSS metrics are re-derived from the exact NVD canonical source content;
- every supported CVSS observation is preserved;
- no preferred/highest/merged score is selected;
- NVD rejected state remains distinct.

### 7.8 CISA KEV enrichment

KEV enrichment consumes one complete immutable catalog snapshot, re-verifies its source hash, and reruns the existing deterministic Silver transformer over the full catalog.

States are exactly:

```text
present
absent
cve_unavailable
```

`absent` requires a GitHub-asserted CVE plus validated complete-snapshot non-membership.

### 7.9 FIRST EPSS enrichment

EPSS enrichment consumes exactly one explicitly selected current or historical EPSS snapshot.

States are exactly:

```text
score_present
score_absent
cve_unavailable
```

There is no automatic `latest`, nearest-date, max-score, trend, or multi-date selection inside the evidence domain.

Historical EPSS v1 preserves unavailable model metadata/percentile fields rather than fabricating modern values.

### 7.10 Final analysis projection

`RepositoryAnalysisResult` accepts only the already validated final EPSS enrichment chain and derives a consumer-facing projection.

It can expose:

```text
dependency
installed version
purl
GHSA/CVE identifiers
matched range and clauses
fixed version
all CVSS observations
KEV evidence
EPSS evidence
exact evidence-chain references
```

It does not expose a risk score, priority, or runtime-exposure assertion.

Final identities:

```text
repository-analysis-finding:v1@sha256:<digest>
repository-analysis:v1@sha256:<digest>
```

## 8. Evidence chain and cache boundary

The final analysis identity changes when any authoritative selected evidence changes.

This is intentional:

```text
same repository commit
 + different EPSS snapshot
 -> different analysis_id
```

Therefore a repository commit alone is not a safe cache key.

Future reuse should key storage by the complete content-addressed evidence identity. Phase 4 deliberately deferred DynamoDB/ElastiCache/other cache infrastructure until a measured workload justifies:

- storage cost;
- invalidation semantics;
- IAM surface;
- observability;
- failure recovery;
- retention policy.

## 9. Security boundaries

```text
Human administration
 -> AWS IAM Identity Center

GitHub Actions
 -> OIDC
 -> deployment role
 -> Terraform-managed AWS changes

Threat-intelligence runtimes
 -> source-specific least-privilege roles

Repository Intelligence
 -> public GitHub read-only network authority
 -> inert repository evidence only
 -> no third-party code execution
```

A deterministic finding remains a repository observation. Runtime exposure is a later independent evidence domain.

## 10. Cost discipline

Current examples:

- no Glue crawler where explicit schemas suffice;
- no DynamoDB repository cache before measured reuse;
- no Step Functions unless workflow semantics justify it;
- no Iceberg requirement yet;
- no vector database before retrieval work begins;
- no Bedrock call for deterministic applicability/findings;
- Athena dev workgroup enforces a 10 MiB scan cutoff.

## 11. Quality gates

Code-bearing deterministic changes are validated with scoped CI so newly introduced code cannot hide behind historical repository findings.

Current correlation/repository gates:

```text
uv lock --check
uv sync --frozen
Ruff
strict Pyright
Pytest
```

Phase 4 closeout:

```text
Repository Intelligence pytest: 174 passed
Correlation pytest:             116 passed
Pyright:                         0 errors / 0 warnings
Ruff:                            PASS
```

AWS-bearing changes additionally use Terraform fmt/validate, TFLint, Checkov, canonical plan review, deployment verification, and post-apply convergence checks.

## 12. Phase 5 boundary

Phase 5 introduces **Risk Policy v1** over the final Phase 4 evidence.

Candidate factors include:

```text
affected status
KEV
EPSS
CVSS
fix availability
direct/transitive evidence when available
future runtime evidence
evidence completeness
```

Required invariants:

- same evidence + same policy version => same priority;
- factor-level explanation is reconstructable;
- policy version is recorded;
- missing/unsupported evidence has explicit semantics;
- LLM is not required for ranking;
- risk policy cannot rewrite applicability or source evidence;
- Repository Risk remains distinct from Runtime Exposure.

This boundary intentionally starts only after the Phase 4 evidence system is complete.
