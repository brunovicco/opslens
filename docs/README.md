# OpsLens Documentation

This directory contains the public technical documentation for OpsLens.

The project has completed its deterministic foundation through **Phase 5 — Risk Prioritization Engine**. The next roadmap boundary is **Phase 6 — Semantic Query Layer**.

## Start here

- [`current-state.md`](current-state.md) — factual implementation checkpoint and current supported scope.
- [`roadmap.md`](roadmap.md) — incremental roadmap from the deterministic foundation through planned semantic/retrieval/agentic phases.
- [`architecture.md`](architecture.md) — accumulated English architecture.
- [`architecture.pt-br.md`](architecture.pt-br.md) — accumulated Portuguese architecture.
- [`adr/README.md`](adr/README.md) — architecture decision index.
- [`labs/`](labs/) — implementation, failure, workload, AWS, and closeout evidence.

## Current architecture boundary

The implemented deterministic chain is:

```text
NVD / CISA KEV / FIRST EPSS / GitHub Security Advisories
 -> source-preserving threat evidence
 -> deterministic PyPI / PEP 440 correlation
 -> immutable public GitHub snapshot
 -> bounded GET-only repository acquisition
 -> exact inert uv.lock
 -> deterministic repository findings
 -> exact NVD/CVSS + complete KEV + explicit EPSS evidence
 -> content-addressed RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> factor contributions + priority tier + completeness
 -> content-addressed RiskPrioritizationResult
```

No third-party repository code is executed.

The Phase 5 priority result remains **Repository Risk** policy evidence. It is not proof of deployed Runtime Exposure.

## Architecture Decision Records

The ADR series covers AWS foundation and authority paths, deterministic correlation, immutable repository intelligence, threat-intelligence enrichment, final repository analysis projection, and Risk Policy v1.

| ADR | Decision |
| --- | --- |
| [`0001`](adr/0001-terraform-state-strategy.md) | Terraform state strategy |
| [`0002`](adr/0002-github-actions-oidc.md) | GitHub Actions OIDC deployment identity |
| [`0003`](adr/0003-aws-region-strategy.md) | AWS regional strategy |
| [`0004`](adr/0004-nvd-ingestion-and-versioning-strategy.md) | NVD ingestion and vulnerability versioning strategy |
| [`0005`](adr/0005-ghsa-source-and-synchronization-strategy.md) | GHSA source and synchronization strategy |
| [`0006`](adr/0006-ghsa-silver-content-versioning-and-physical-shape.md) | GHSA Silver content versioning and physical shape |
| [`0007`](adr/0007-ghsa-runtime-credential-and-retry-strategy.md) | GHSA runtime credential and retry strategy |
| [`0008`](adr/0008-pypi-correlation-semantics.md) | PyPI deterministic correlation semantics |
| [`0009`](adr/0009-immutable-public-repository-snapshot.md) | Immutable public GitHub repository snapshot |
| [`0010`](adr/0010-bounded-read-only-github-rest-transport.md) | Bounded read-only GitHub REST transport |
| [`0011`](adr/0011-immutable-uv-lock-evidence.md) | Immutable `uv.lock` evidence |
| [`0012`](adr/0012-deterministic-uv-lock-parser.md) | Deterministic `uv.lock` parser |
| [`0013`](adr/0013-phase3-pypi-normalization-bridge.md) | Phase 3 PyPI normalization bridge |
| [`0014`](adr/0014-deterministic-repository-vulnerability-findings.md) | Deterministic repository vulnerability findings |
| [`0015`](adr/0015-repository-nvd-cvss-enrichment.md) | Repository NVD/CVSS enrichment |
| [`0016`](adr/0016-repository-kev-snapshot-enrichment.md) | Repository KEV snapshot enrichment |
| [`0017`](adr/0017-repository-epss-snapshot-enrichment.md) | Repository EPSS snapshot enrichment |
| [`0018`](adr/0018-repository-analysis-result-projection.md) | Final repository-analysis result projection and safe cache boundary |
| [`0019`](adr/0019-deterministic-risk-policy-v1.md) | Deterministic Risk Policy v1 |

See [`adr/README.md`](adr/README.md) for the canonical ADR index.

## Phase closeouts

### Phase 0 — AWS Foundation

Key evidence includes IAM/OIDC and CloudWatch authorization failure labs, Terraform bootstrap, remote state, least-privilege identities, observability, and cost controls.

### Phase 1 — FIRST EPSS

- [`phase-1-epss-athena-query.md`](labs/phase-1-epss-athena-query.md)

This phase established the first complete Bronze -> Silver -> Glue -> Athena path.

### Phase 2 — Threat Intelligence Data Lake

Phase 2 completed:

```text
CISA KEV
NVD / CVE
GitHub Security Advisories
FIRST EPSS current path
Historical EPSS expansion
```

Representative closeouts:

- [`phase-2-nvd-authoritative-runtime-closeout.md`](labs/phase-2-nvd-authoritative-runtime-closeout.md)
- [`phase-2-ghsa-cross-source-closeout.md`](labs/phase-2-ghsa-cross-source-closeout.md)
- [`phase-2-epss-history-c6-closeout.md`](labs/phase-2-epss-history-c6-closeout.md)

Phase 2 preserves source-local authority instead of collapsing NVD, KEV, EPSS, and GHSA into one lossy universal record.

### Phase 3 — Vulnerability Correlation Engine

- [`phase-3-correlation-engine-closeout.md`](labs/phase-3-correlation-engine-closeout.md)

Phase 3 is complete for PyPI v1. It defines canonical package/version identity, PEP 440 applicability, GHSA range semantics, fixed-version evidence, deterministic CVE/GHSA/NVD reconciliation, and content-addressed correlation records.

```text
Correlation Ruff:                 PASS
Correlation Pyright:              0 errors / 0 warnings
Correlation pytest:               116 passed
```

### Phase 4 — Repository Intelligence

- [`phase-4-repository-intelligence-closeout.md`](labs/phase-4-repository-intelligence-closeout.md)

Phase 4 completed the read-only repository path through immutable snapshot resolution, bounded GitHub acquisition, inert `uv.lock`, deterministic parsing/normalization, repository findings, NVD/CVSS, complete-snapshot KEV, explicit EPSS, and final `RepositoryAnalysisResult`.

```text
Repository Intelligence Ruff:     PASS
Repository Intelligence Pyright:  0 errors / 0 warnings
Repository Intelligence pytest:   174 passed
Correlation regression:           116 passed
```

### Phase 5 — Risk Prioritization Engine

- [`phase-5-risk-policy-closeout.md`](labs/phase-5-risk-policy-closeout.md)

Phase 5 introduces a separate deterministic policy authority without changing Phase 4 source or applicability truth.

Risk Policy v1:

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

Policy/evaluation/ranking identities are content-addressed:

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

Missing or unsupported source evidence remains explicit through `partial` / `review_required`; proven KEV/EPSS absence remains complete negative evidence.

Final validation:

```text
Risk Policy Ruff:                 PASS
Risk Policy Pyright:              0 errors / 0 warnings
Risk Policy pytest:               31 passed
Repository Intelligence pytest:   174 passed
Correlation pytest:               116 passed
```

Phase 5 added no AWS resource, IAM permission, or model call.

## Evidence and authority principles

- raw third-party evidence is preserved before interpretation;
- deterministic facts remain authoritative;
- exact versions/hashes participate in provenance;
- malformed, unsupported, or inconsistent evidence fails closed;
- package identity, version/range matching, aliases, KEV/EPSS/CVSS evidence, repository findings, and risk-policy evaluation remain deterministic;
- third-party repository code is untrusted data and is never executed;
- Repository Risk and Runtime Exposure remain separate concepts;
- missing evidence is explicit, not silently benign;
- LLMs may later plan, explain, route, and synthesize, but do not replace deterministic evidence or enforcement authorities.

## Current milestone

```text
Phase 0 — AWS Foundation:                    COMPLETE
Phase 1 — EPSS Vertical Slice:               COMPLETE
Phase 2 — Threat Intelligence Data Lake:     COMPLETE
Phase 3 — Vulnerability Correlation Engine:  COMPLETE
Phase 4 — Repository Intelligence:           COMPLETE
Phase 5 — Risk Prioritization Engine:        COMPLETE
Phase 6 — Semantic Query Layer:               NEXT
```

Phase 6 will introduce the first FM planner in the current sequence, but the planner will emit a typed semantic query rather than arbitrary SQL. Validation and SQL compilation remain deterministic.

Permanent guardrail:

> **No unrestricted text-to-SQL.**
