# ADR 0017 — Repository EPSS snapshot enrichment

- Status: Accepted
- Date: 2026-09-03
- Phase: 4 — Repository Intelligence
- Gate: 4.10

## Context

Gate 4.7 proves package applicability from immutable repository dependency evidence and exact GHSA vulnerability occurrences. Gate 4.8 attaches exact CVE/NVD/CVSS evidence without changing that applicability truth. Gate 4.9 adds CISA KEV membership from one complete immutable catalog snapshot.

EPSS is different from CVSS and KEV because its probability score is explicitly temporal. A CVE can have different EPSS scores on different dates and across model eras. OpsLens already preserves current EPSS snapshots and historical snapshots spanning legacy and modern source shapes.

Repository Intelligence therefore needs EPSS evidence without introducing hidden temporal selection, partial-source absence claims, or Phase 5 risk policy into Phase 4.

## Decision

Gate 4.10 accepts exactly one immutable EPSS source snapshot per enrichment execution. The snapshot may be either:

1. a current `EpssSnapshot`; or
2. a validated `HistoricalEpssSnapshot` for an explicit archive date.

The supplied snapshot is not trusted merely because it is a typed object. Gate 4.10 revalidates the original gzip bytes using the existing Phase 2 parser authority and then retransforms the complete source using the existing Silver transformer authority.

For current snapshots:

- `EpssSnapshotParser` reparses the exact bytes;
- the parsed snapshot must equal the supplied snapshot;
- `EpssSilverTransformer` must emit every declared row.

For historical snapshots:

- `HistoricalEpssSnapshotParser` reparses the exact bytes for the supplied archive date;
- the parsed historical snapshot must equal the supplied snapshot;
- `HistoricalEpssSilverRecordTransformer` must emit every declared row;
- EPSS v1 metadata or percentile values that were absent in the source remain absent rather than being fabricated.

The source SHA-256 is independently recomputed before any score lookup.

## Lookup identity

EPSS lookup uses the GitHub-asserted CVE already carried through the deterministic repository evidence chain.

It does not require:

- an NVD observation;
- NVD CVSS metrics;
- KEV membership.

A finding may therefore have an EPSS score even when its NVD evidence was not supplied or its CVE is absent from the selected KEV snapshot.

## States

Each affected repository finding receives exactly one EPSS state against the selected complete snapshot:

- `score_present`: the GitHub-asserted CVE occurs in the complete selected EPSS snapshot;
- `score_absent`: a GitHub-asserted CVE is proven absent after the complete selected snapshot has been validated and transformed;
- `cve_unavailable`: GHSA did not assert a CVE, so EPSS lookup cannot be performed.

`cve_unavailable` must never collapse into `score_absent`.

A detached or partial collection of `SilverEpssRecord` values is not accepted as proof of absence.

## Temporal semantics

The selected snapshot date is evidence, not policy.

Gate 4.10 does not:

- choose the latest snapshot;
- choose a snapshot nearest to repository commit time;
- combine multiple dates;
- compute EPSS trends;
- select a maximum score;
- define a high-risk threshold;
- convert EPSS into priority or remediation policy.

If a future use case requires a selection rule such as "latest available EPSS", that rule must be explicit outside this evidence domain and must provide the exact chosen snapshot to Gate 4.10.

## Evidence preservation

Positive and negative decisions preserve the selected snapshot identity, including:

- snapshot kind (`current` or `historical`);
- canonical snapshot date;
- model version when source-declared;
- score timestamp when source-declared;
- source SHA-256;
- row count;
- compressed payload size.

Historical evidence additionally preserves:

- model era;
- physical source shape;
- whether source metadata was present;
- whether percentile values were available.

For `score_present`, OpsLens preserves the complete normalized `SilverEpssRecord`, including score, nullable percentile, nullable source model metadata, source digest, and snapshot date.

The EPSS enrichment receives its own content-addressed identity while referencing the immutable Gate 4.9 KEV-enriched finding. Prior finding, NVD, and KEV identities are unchanged.

## Bounds

Gate 4.10 is bounded independently from ingestion:

- maximum EPSS rows: 1,000,000;
- maximum compressed source bytes: 64 MiB.

Exceeding either bound fails closed. The source is never truncated to satisfy a bound.

These limits are execution-safety bounds, not statements about FIRST coverage or CVE population size.

## Consequences

### Positive

- EPSS absence is evidence-backed rather than inferred from a partial lookup.
- Current and historical EPSS share one repository-enrichment contract.
- Legacy EPSS v1 remains truthful about unavailable metadata and percentile values.
- Temporal selection stays separate from evidence validation.
- Phase 4 remains deterministic and model-free.

### Trade-offs

- Complete snapshot validation costs O(n) per enrichment execution.
- The domain intentionally does not optimize by accepting detached pre-indexed rows.
- Callers that need a particular temporal policy must select an exact snapshot before invoking this gate.

## Rejected alternatives

### Accept arbitrary Silver rows

Rejected because absence from a partial list cannot prove score absence from the source snapshot.

### Automatically use the newest available EPSS date

Rejected because it hides a temporal policy decision inside the evidence layer.

### Merge current and historical records into one multi-date enrichment

Rejected because one finding would no longer have a single unambiguous score observation coordinate.

### Apply EPSS thresholds in Phase 4

Rejected because weighting and prioritization belong to Phase 5 Risk Policy v1.

## Security, cost, IAM, and infrastructure

This gate is pure deterministic application/domain logic.

- New AWS services: none.
- New IAM permissions: none.
- Incremental AWS cost: $0.
- Third-party repository code execution: none.
- LLM dependency: none.

Repository Risk remains distinct from Runtime Exposure.
