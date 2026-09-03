# ADR 0018 — Repository analysis result projection and cache boundary

- Status: Accepted
- Date: 2026-09-03
- Phase: 4 — Repository Intelligence
- Gate: 4.11

## Context

Phase 4 now establishes a deterministic evidence chain for one immutable public GitHub repository snapshot:

1. exact repository and commit identity;
2. verified inert `uv.lock` bytes;
3. deterministic PyPI dependency normalization;
4. GHSA vulnerable-range applicability;
5. CVE/NVD/CVSS enrichment;
6. complete-snapshot CISA KEV membership;
7. exact-snapshot EPSS score evidence.

Each gate intentionally owns only its evidence contract. This separation protects source authority, but a consumer should not need to understand the internal nesting of every gate merely to read the repository-analysis fields promised by the Phase 4 roadmap.

Phase 4 also requires repeated analysis of immutable evidence to be reproducible and cacheable where justified. A repository commit alone is not a safe cache key because threat-intelligence observations are temporal: a later KEV catalog or EPSS snapshot can legitimately change the final analysis while the repository commit remains identical.

## Decision

Gate 4.11 introduces a final `RepositoryAnalysisResult` as a pure derived projection over the already validated `RepositoryEpssEnrichmentEvidence` chain.

The result does not establish new vulnerability truth and does not accept caller-supplied copies of dependency, vulnerability, CVSS, KEV, EPSS, or fixed-version fields. Those values are exposed by deterministic properties derived from the authoritative nested evidence.

For every affected finding, the projection exposes:

- dependency name;
- installed version;
- canonical package URL;
- GHSA identifier;
- GitHub-asserted CVE identifier when available;
- matched vulnerable range and parsed deterministic clauses;
- fixed version when known;
- all preserved NVD CVSS observations without selecting a preferred score;
- KEV state and exact positive KEV row when present;
- EPSS state and exact score observation when present;
- immutable evidence references and hashes for every gate in the chain.

The aggregate result also preserves repository and lockfile coordinates even when no affected finding exists.

## Final identity

The final result is serialized deterministically and receives a content-addressed identity:

`repository-analysis:v1@sha256:<digest>`

The digest commits to the complete selected evidence chain, including the exact repository snapshot and temporal threat-intelligence observations.

The same complete evidence chain must therefore reproduce the same result identity. Changing any authoritative evidence input that changes the projected result must change the result identity.

## Cache decision

Gate 4.11 does not introduce an AWS cache, database, or other persistence service.

Reasons:

1. all existing evidence records and the new final result are already content-addressed;
2. no production request volume or latency requirement currently demonstrates that a cache backend is necessary;
3. adding a cache would introduce cost, IAM permissions, invalidation semantics, observability, and failure modes without a measured need;
4. caching by repository commit alone would be incorrect because NVD, KEV, and EPSS evidence can change independently of repository content.

If a later workload justifies caching, the safe logical key is the complete final result/evidence coordinate, not merely owner/repository/ref or commit SHA. The storage technology must be chosen separately based on measured access patterns.

## No risk-policy semantics

The final projection does not:

- choose a preferred CVSS score;
- define an EPSS threshold;
- weight KEV membership;
- calculate a risk score;
- rank findings;
- claim runtime exposure;
- execute repository code;
- invoke an LLM.

Those policy decisions remain outside Phase 4. Risk weighting begins in Phase 5.

## Consequences

### Positive

- Phase 4 has one stable consumer-facing repository-analysis contract.
- Roadmap exit fields can be verified in one result without weakening gate authority.
- Repeated identical evidence produces a deterministic reusable identity.
- Future caching can use safe content-addressed coordinates.
- Zero-finding analyses still retain immutable repository and lockfile provenance.

### Trade-offs

- The final canonical JSON repeats selected values as a projection for consumers, while authority remains in the nested evidence chain.
- A future cache still requires an explicit architecture decision once workload and access patterns are known.

## Rejected alternatives

### Let callers assemble the final response from individual gates

Rejected because consumers could accidentally mix evidence from different repository or threat-intelligence observations.

### Store duplicated final fields as independently mutable dataclass inputs

Rejected because the projection could diverge from the authoritative nested evidence.

### Cache only by repository commit SHA

Rejected because temporal threat-intelligence evidence can change without repository changes.

### Add DynamoDB, Redis, S3 cache artifacts, or another backend now

Rejected because there is no demonstrated runtime requirement and the incremental IAM, cost, and invalidation surface is unjustified.

## Security, cost, IAM, and infrastructure

This gate is pure deterministic application/domain logic.

- New AWS services: none.
- New IAM permissions: none.
- Incremental AWS cost: $0.
- Third-party repository code execution: none.
- LLM dependency: none.

Repository Risk remains distinct from Runtime Exposure.
