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
Phase 5    Risk Prioritization Engine                         NEXT
```

Phase 4 implementation closeout checkpoint:

```text
commit: 4baa9bddd20d827aa06654fc14f52c7ec5135f2c
PR:     #78 — feat(repository): close Phase 4 with final analysis result
```

The documentation refresh that introduced this file is intentionally separate from that implementation checkpoint.

## What is implemented

OpsLens can currently build deterministic, reproducible software-supply-chain evidence from threat-intelligence sources and from an immutable public GitHub repository snapshot.

The implemented repository-analysis chain is:

```text
public GitHub repository
 -> immutable repository identity
 -> exact commit + tree SHA
 -> bounded GET-only GitHub REST acquisition
 -> exact inert uv.lock bytes
 -> deterministic TOML parsing
 -> PyPI package/version/purl normalization
 -> GHSA vulnerable-range applicability
 -> CVE/GHSA alias reconciliation
 -> exact NVD/CVSS enrichment
 -> complete-snapshot CISA KEV evidence
 -> explicit-date FIRST EPSS evidence
 -> content-addressed RepositoryAnalysisResult
```

No repository code is executed.

## Phase 2 — Threat Intelligence Data Lake

The data lake provides deterministic evidence for:

- FIRST EPSS current snapshots;
- historical EPSS from 2021-04-14 through 2026-08-13 under a pinned archive commit;
- CISA Known Exploited Vulnerabilities;
- NVD CVE observations and CVSS metrics;
- GitHub reviewed security advisories;
- GHSA package, vulnerable-range, and first-patched-version evidence;
- explicit source provenance and time coordinates.

Implemented AWS services currently include S3, Lambda, EventBridge Scheduler, Glue, Athena, CloudWatch, X-Ray, SQS failure destinations, IAM Identity Center, and GitHub Actions OIDC deployment identities where required by the implemented data paths.

The architecture deliberately does not add a service merely because it appears in a future roadmap phase.

## Phase 3 — Vulnerability Correlation Engine

Phase 3 is complete for the explicitly supported PyPI v1 scope.

Implemented deterministic semantics include:

- PyPI/PyPA package-name validation and normalization;
- PEP 440 concrete-version parsing;
- canonical PyPI package URLs;
- strict GHSA range operators `=`, `<`, `<=`, `>`, `>=`;
- comma-separated conjunction evaluation;
- `affected`, `not_affected`, and `unsupported` outcomes;
- fail-closed invalid/unsupported range behavior;
- first-patched-version evidence kept separate from applicability truth;
- exact GHSA occurrence provenance;
- deterministic GHSA CVE assertion to exact NVD observation reconciliation;
- canonical JSON correlation records with `correlation:v1@sha256:...` identity.

Permanent rule:

> **No LLM decides vulnerability applicability.**

The Phase 3 closeout is documented in [`labs/phase-3-correlation-engine-closeout.md`](labs/phase-3-correlation-engine-closeout.md).

## Phase 4 — Repository Intelligence

Phase 4 is complete for the deliberately narrow v1 scope:

```text
provider:          public GitHub
repository file:   uv.lock only
ecosystem:         canonical PyPI records
repository action: read only
code execution:    never
```

The implementation gates established:

1. immutable public repository identity and exact commit/tree evidence;
2. bounded fixed-host, GET-only GitHub REST transport;
3. exact inert `uv.lock` evidence with Git blob SHA-1 and independent SHA-256 verification;
4. bounded stdlib `tomllib` parsing;
5. normalization through the Phase 3 PyPI authority;
6. deterministic repository vulnerability findings;
7. exact NVD/CVSS enrichment;
8. complete-snapshot CISA KEV membership evidence;
9. exact current or historical EPSS score evidence;
10. a final consumer-facing, content-addressed `RepositoryAnalysisResult`.

A final finding can expose:

```text
dependency
installed version
canonical purl
GHSA id
CVE id when asserted
matched vulnerable range
clause-level deterministic match evidence
fixed version when published
all preserved NVD CVSS observations
KEV state and exact positive row when present
EPSS state and exact score observation when present
immutable repository / lockfile / threat-intelligence evidence references
```

The result does **not** contain a risk score or priority. That belongs to Phase 5.

## Evidence identity and reuse

Repository findings and enrichment stages are content-addressed. The final analysis has a stable identity:

```text
repository-analysis:v1@sha256:<digest>
```

The safe future cache coordinate is the complete selected evidence chain, not only the repository commit.

Threat intelligence is temporal. The same repository snapshot analyzed against a different EPSS or KEV snapshot can legitimately produce a different final analysis identity.

For this reason, Phase 4 deliberately did not introduce DynamoDB, ElastiCache, or another cache backend before a measured workload justifies storage, invalidation, IAM, observability, and cost.

## Quality checkpoint

The final Phase 4 PR validated:

```text
uv lock --check:                  PASS
uv sync --frozen:                 PASS
Repository Intelligence Ruff:     PASS
Repository Intelligence Pyright:  0 errors / 0 warnings
Repository Intelligence pytest:   174 passed
Correlation Ruff:                 PASS
Correlation Pyright:              0 errors / 0 warnings
Correlation pytest:               116 passed
```

Infrastructure validation remains separate through Terraform, TFLint, Checkov, canonical plans, and post-apply convergence checks for AWS-bearing changes.

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

Persistent AWS access keys are not stored in GitHub.

## Next boundary — Phase 5

Phase 5 introduces **Risk Policy v1**.

This is a deliberate authority change: Phase 0–4 establish facts and reproducible evidence; Phase 5 will assign deterministic priority to those facts.

Candidate policy factors include affected status, direct/transitive evidence when available, KEV, EPSS, CVSS, fix availability, future runtime evidence, and evidence completeness.

The Phase 5 policy must remain deterministic, versioned, explainable at factor level, and independently testable without an LLM.
