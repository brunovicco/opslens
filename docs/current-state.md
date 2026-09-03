# OpsLens — Current State

_Last updated: 2026-09-03_

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
Phase 6    Semantic Query Layer                               NEXT
```

Latest implementation checkpoint:

```text
commit: 81a2e78a3e8329aa811c20012bc565f35f1a87e5
PR:     #80 — feat(risk): introduce deterministic Risk Policy v1
CI:     33810836040 — SUCCESS
```

Phase 5 closeout evidence:

```text
docs/labs/phase-5-risk-prioritization-closeout.md
ADR 0019 — Deterministic Risk Policy v1
```

## Permanent semantic and security boundaries

The following boundaries remain authoritative unless changed through an explicit versioned architecture decision:

> **Agents reason. Code verifies evidence.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

Deterministic mechanisms remain authoritative for:

- package identity normalization;
- concrete version parsing;
- vulnerable-range matching;
- vulnerability applicability;
- CVE/GHSA/NVD alias reconciliation;
- KEV, EPSS, and CVSS evidence;
- canonical evidence serialization and content addressing;
- risk-policy evaluation and ranking;
- semantic-query validation and SQL compilation;
- evidence validation;
- execution, tool, and cost limits.

LLMs may later plan, route, synthesize, explain, and reason over validated evidence, but they do not replace these deterministic authorities.

## AWS foundation

Primary environment:

```text
environment:             dev
primary workload Region: us-east-1
AWS account:             487757851499
human profile:           opslens-bootstrap
IaC:                     Terraform
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Athena
```

Primary buckets:

```text
Data bucket:
opslens-dev-data-487757851499-us-east-1

Deployment artifact bucket:
opslens-dev-artifacts-487757851499-us-east-1

Terraform state bucket:
opslens-dev-tfstate-487757851499-us-east-1
```

Glue/Athena:

```text
Glue database:    opslens_dev
Athena workgroup: opslens-dev
scan cutoff:      10,485,760 bytes
```

Human administration uses IAM Identity Center temporary credentials. GitHub Actions uses OIDC. Persistent AWS access keys are not stored in GitHub.

Phase 3, Phase 4, and Phase 5 introduced no new AWS resources or IAM permissions.

## Phase 1 — FIRST EPSS — COMPLETE

Forward path:

```text
FIRST EPSS
 -> EventBridge Scheduler
 -> EPSS ingestion Lambda
 -> S3 Bronze
 -> EPSS Silver Lambda
 -> canonical S3 Silver / Parquet
 -> Glue Data Catalog
 -> Athena
```

Primary storage:

```text
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

The forward path preserves exact source evidence, deterministic Silver transformation, replay safety, bounded failure recovery, and Athena scan-cost controls.

## Phase 2 — Threat Intelligence Data Lake — COMPLETE

Phase 2 established independent source-local authority for:

```text
FIRST EPSS current snapshots
Historical FIRST EPSS
CISA KEV
NVD / CVE
GitHub Security Advisories
```

The data lake does not collapse these sources into one lossy universal record.

### Historical EPSS authority

```text
repository:                  empiricalsec/epss_scores
archive commit:              7ba701f5599057c496489ceecd701cbd43911f5c
root tree:                   2a12b2030cda9b94573bca01b67a6f0d72ab71e8
first forward snapshot date: 2026-08-14
historical interval:         2021-04-14 .. 2026-08-13
candidate snapshots:         1,939
source-absent dates:         9
plan_id:                     3b3c8c58009f46b61f6bb9e82f6b6c0bcf675e72b940326d7fcccf962d7bd4de
```

The nine source-absent dates remain explicit evidence and were never fabricated or substituted.

## Phase 3 — Vulnerability Correlation Engine — COMPLETE

Phase 3 is complete for the supported **PyPI v1** scope.

Implemented deterministic capabilities include:

- PyPI/PyPA package-name normalization;
- PEP 440 concrete-version parsing and comparison;
- canonical package URL (`purl`) construction;
- deterministic GHSA PyPI vulnerable-range evaluation;
- fixed-version evidence kept separate from applicability truth;
- exact GHSA advisory/version/vulnerability-entry provenance;
- CVE/GHSA-to-NVD alias reconciliation without merging source-local records;
- canonical JSON v1 evidence records;
- SHA-256 content addressing with `correlation:v1@sha256:...` identities.

Phase 3 closeout validation:

```text
Correlation Ruff:     PASS
Correlation Pyright:  0 errors / 0 warnings
Correlation pytest:   116 passed
```

## Phase 4 — Repository Intelligence — COMPLETE

Supported v1 repository scope:

```text
repository provider:  public GitHub
dependency evidence:  root-level uv.lock
supported ecosystem:  PyPI
version semantics:    PEP 440
vulnerability source: GHSA PyPI occurrences
enrichment:           NVD/CVSS + CISA KEV + FIRST EPSS
repository execution: never
```

Implemented chain:

```text
public GitHub repository
 -> immutable exact commit/tree snapshot
 -> bounded GET-only GitHub REST acquisition
 -> immutable inert uv.lock evidence
 -> deterministic stdlib TOML parsing
 -> Phase 3 PyPI normalization
 -> GHSA vulnerable-range applicability
 -> repository vulnerability findings
 -> exact NVD/CVSS enrichment
 -> complete CISA KEV snapshot membership
 -> explicit FIRST EPSS snapshot evidence
 -> content-addressed RepositoryAnalysisResult
```

A final Phase 4 result intentionally contains no policy score, priority, LLM-authored applicability, or runtime-exposure claim.

Phase 4 closeout validation:

```text
Repository Intelligence Ruff:     PASS
Repository Intelligence Pyright:  0 errors / 0 warnings
Repository Intelligence pytest:   174 passed
Correlation Ruff:                 PASS
Correlation Pyright:              0 errors / 0 warnings
Correlation pytest:               116 passed
```

## Phase 5 — Risk Prioritization Engine — COMPLETE

Phase 5 introduced a separate deterministic policy authority over already-proven Phase 4 findings.

Architecture:

```text
RepositoryAnalysisResult
 -> Phase 5 application bridge
 -> typed RiskFindingInput
 -> pure Risk Policy v1 evaluator
 -> factor contributions
 -> priority score / tier / completeness
 -> deterministic ranking
```

Implemented package:

```text
src/opslens/risk_policy/
```

### Risk Policy v1

Maximum priority score:

```text
100
```

Contributions:

```text
CISA KEV present                    +40
EPSS >= 0.70 / 0.30 / 0.10         +30 / +20 / +10
max supported CVSS >= 9 / 7 / 4    +20 / +10 / +5
known first patched version         +10
```

Priority tiers:

```text
P0 >= 80
P1 >= 60
P2 >= 30
P3 < 30
```

The score is explicitly an OpsLens **priority policy**, not a vulnerability probability, a CVSS replacement, or runtime-exposure evidence.

Evidence completeness remains separate from score:

```text
complete | partial
review_required: true | false
```

Missing or unsupported evidence never receives fabricated positive or negative semantics. Proven source absence remains distinct from unavailable evidence.

### Deterministic identities

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

The same evidence and same policy reproduce the same evaluation and ranking identities.

### Phase 5 validation

An initial Risk Policy CI attempt failed on mechanical Ruff findings and was corrected without changing policy semantics:

```text
run 33810786432 -> FAILURE
run 33810836040 -> SUCCESS
```

Final validation:

```text
Risk Policy Ruff:                 PASS
Risk Policy Pyright:              0 errors / 0 warnings
Risk Policy pytest:               31 passed
Repository Intelligence Ruff:     PASS
Repository Intelligence Pyright:  0 errors / 0 warnings
Repository Intelligence pytest:   174 passed
Correlation Ruff:                 PASS
Correlation Pyright:              0 errors / 0 warnings
Correlation pytest:               116 passed
```

Phase 5 introduced:

```text
new AWS resources:     0
new IAM permissions:   0
model calls:           0
incremental AWS cost:  $0
```

The v1 weights/thresholds are explicit product-policy choices. They should be evaluated against historical security cases before any future Risk Policy v2; v1 must not be silently mutated.

## Current quality boundary

Permanent scoped quality gates now exist for:

```text
src/opslens/correlation
src/opslens/repository_intelligence
src/opslens/risk_policy
```

A pre-existing repo-wide Ruff backlog outside these scoped deterministic slices remains separate technical debt and should not be mixed into Phase 6 work unless explicitly planned.

## Phase 6 — Semantic Query Layer — NEXT

Phase 6 has not started.

Target authority flow:

```text
User question
 -> Bedrock planner
 -> typed semantic query
 -> deterministic validator
 -> code-owned SQL compiler
 -> bounded read-only Athena workgroup
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

Before model integration, Phase 6 should first freeze the smallest typed semantic-query vocabulary and deterministic SQL-compiler boundary.

Expected initial decisions include:

- first supported metric(s);
- allowed dimensions;
- typed filters;
- ordering and limit semantics;
- temporal snapshot semantics;
- compiler-owned parameterization/escaping;
- Athena workgroup and scan-limit enforcement;
- unsupported-query behavior;
- planner output schema and validation boundary.

No later agentic phase should be started until the Phase 6 deterministic query contract and exit criteria are satisfied or explicitly deferred.
