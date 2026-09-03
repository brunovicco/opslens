# OpsLens Documentation

This directory contains the public technical documentation for OpsLens.

The project has completed the deterministic foundation through **Phase 4 — Repository Intelligence**. The next roadmap boundary is **Phase 5 — Risk Prioritization Engine**.

## Start here

- [`current-state.md`](current-state.md) — factual implementation checkpoint and current supported scope.
- [`roadmap.md`](roadmap.md) — incremental roadmap from completed foundation through the planned agentic phases.
- [`architecture.md`](architecture.md) — current accumulated English architecture.
- [`architecture.pt-br.md`](architecture.pt-br.md) — current accumulated Portuguese architecture.
- [`adr/README.md`](adr/README.md) — architecture decision index.
- [`labs/`](labs/) — implementation, failure, workload, AWS, and closeout evidence.

## Current architecture boundary

The implemented deterministic repository-analysis chain is:

```text
public GitHub repository
 -> immutable repository snapshot
 -> bounded GET-only GitHub REST acquisition
 -> exact inert uv.lock evidence
 -> deterministic lock parsing
 -> PyPI / PEP 440 / purl normalization
 -> GHSA vulnerable-range applicability
 -> CVE/GHSA/NVD alias reconciliation
 -> NVD/CVSS enrichment
 -> complete CISA KEV snapshot evidence
 -> explicit FIRST EPSS snapshot evidence
 -> content-addressed RepositoryAnalysisResult
```

No third-party repository code is executed.

The final result remains repository-risk evidence. It is not proof of deployed runtime exposure and does not yet contain a risk score or priority.

## Architecture Decision Records

The current ADR series covers the AWS foundation, NVD/GHSA source and authority paths, deterministic correlation semantics, immutable repository intelligence, threat-intelligence enrichment, and the final Phase 4 analysis projection.

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

See [`adr/README.md`](adr/README.md) for the canonical ADR index.

## Phase closeouts

### Phase 0 — AWS Foundation

Key evidence includes IAM/OIDC and CloudWatch authorization failure labs, Terraform bootstrap, remote state, least-privilege identities, observability, and budget/cost controls.

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

The detailed NVD, GHSA, and historical EPSS design/runtime/closeout records remain in [`labs/`](labs/).

Representative closeouts:

- [`phase-2-nvd-authoritative-runtime-closeout.md`](labs/phase-2-nvd-authoritative-runtime-closeout.md)
- [`phase-2-ghsa-cross-source-closeout.md`](labs/phase-2-ghsa-cross-source-closeout.md)
- [`phase-2-epss-history-c6-closeout.md`](labs/phase-2-epss-history-c6-closeout.md)

Phase 2 preserves source-local authority instead of collapsing NVD, KEV, EPSS, and GHSA into one lossy universal record.

### Phase 3 — Vulnerability Correlation Engine

- [`phase-3-correlation-engine-closeout.md`](labs/phase-3-correlation-engine-closeout.md)

Phase 3 is complete for the supported PyPI v1 scope. It defines canonical package/version identity, PEP 440 applicability, GHSA range semantics, fixed-version evidence, deterministic CVE/GHSA/NVD reconciliation, and content-addressed correlation records.

Final Phase 3 validation:

```text
Correlation Ruff:                 PASS
Correlation Pyright:              0 errors / 0 warnings
Correlation pytest:               116 passed
```

### Phase 4 — Repository Intelligence

Phase 4 completed the read-only repository path through PRs #68–#78.

Implemented gates:

```text
4.1 immutable repository snapshot
4.2 repository/ref -> exact commit resolution
4.3 bounded read-only GitHub transport
4.4 immutable uv.lock evidence
4.5 deterministic uv.lock parser
4.6 Phase 3 PyPI normalization bridge
4.7 deterministic vulnerability findings
4.8 exact NVD/CVSS enrichment
4.9 complete-snapshot CISA KEV enrichment
4.10 exact FIRST EPSS snapshot enrichment
4.11 final RepositoryAnalysisResult projection
```

Final Phase 4 validation:

```text
Repository Intelligence Ruff:     PASS
Repository Intelligence Pyright:  0 errors / 0 warnings
Repository Intelligence pytest:   174 passed
Correlation regression:           116 passed
```

The final `RepositoryAnalysisResult` is content-addressed and contains only evidence-derived fields. Risk ranking remains outside Phase 4.

## Evidence and authority principles

The documentation should be read with these permanent constraints in mind:

- raw third-party evidence is preserved before interpretation;
- deterministic facts remain authoritative;
- exact versions/hashes participate in provenance;
- duplicate delivery is expected and replay must be safe;
- malformed, unsupported, or inconsistent evidence fails closed;
- package identity, version parsing, range matching, aliases, KEV/EPSS/CVSS lookup, and final repository findings remain deterministic;
- third-party repository code is untrusted data and is never executed;
- Repository Risk and Runtime Exposure are separate concepts;
- LLMs may later plan, explain, route, and synthesize, but do not replace deterministic evidence authorities.

## Current milestone

```text
Phase 0 — AWS Foundation:                    COMPLETE
Phase 1 — EPSS Vertical Slice:               COMPLETE
Phase 2 — Threat Intelligence Data Lake:     COMPLETE
Phase 3 — Vulnerability Correlation Engine:  COMPLETE
Phase 4 — Repository Intelligence:           COMPLETE
Phase 5 — Risk Prioritization Engine:        NEXT
```

Phase 5 will introduce a versioned deterministic **Risk Policy v1** over the evidence already established by Phase 4. It must not retroactively change package applicability, source provenance, or runtime-exposure semantics.
