# Phase 19 Gate 19.2 — Threat Evidence Admission Boundary

_Status: IN PROGRESS_

## Purpose

Gate 19.2 requires one non-public representative workload measurement before selecting a public runtime. The live path needs typed repository threat evidence, but the retained `CrossSourceCveEvidenceV1` analytical proof is intentionally not equivalent to complete source authority.

The admission boundary added in issue #298 therefore validates the analytical bundle against already-materialized typed source evidence instead of synthesizing authoritative domain objects from partial rows.

## Retained principle

```text
analytical projection != complete source authority
absence row != empty source snapshot
retrieved content != instruction authority
model proposal != authorization
```

`CrossSourceCveEvidenceV1` may prove source-local analytical facts such as one GHSA package occurrence, one selected NVD observation, KEV membership/absence at a selected snapshot coordinate, and one EPSS score. It does not contain the complete immutable source bytes needed to create complete KEV/EPSS snapshots or the canonical NVD source content required by `ObservedCveVersion`.

## Adapter contract

The pure application adapter accepts:

```text
CrossSourceCveEvidenceV1 mapping
+
RepresentativeThreatEvidenceAuthority
  - tuple[GhsaPyPIVulnerabilityEvidence, ...]
  - tuple[NvdCveCoreRecord, ...]
  - KevCatalogSnapshot
  - EpssSnapshot | HistoricalEpssSnapshot
```

and returns:

```text
RepresentativeRepositoryThreatEvidence
```

only when the analytical projection and exact typed source authority agree.

## Deterministic admission checks

The adapter requires:

- `schema_version == 1`;
- `bundle_type == CrossSourceCveEvidenceV1`;
- `read_only == true`;
- one exact CVE identity across admitted sources;
- PyPI (`pip`) GHSA package evidence for the current representative repository bridge;
- exact GHSA advisory content identity, package occurrence identity, vulnerable range, and first patched version;
- `range_evaluation_performed == false` so installed-version applicability remains owned by the retained correlation layer;
- exact NVD observed-version identity and core timestamps/status against already-typed `NvdCveCoreRecord` values;
- KEV membership or absence revalidated against one complete immutable `KevCatalogSnapshot`;
- EPSS score/presence revalidated against one complete immutable current or historical EPSS snapshot.

Missing, contradictory, duplicate, or unsupported evidence fails closed.

## Representative evidence discovered during human pre-live preparation

The previous frozen Requests anchor was not materialized in the current analytical GHSA state. Read-only discovery selected a reproducible PyPI candidate instead:

```text
CVE:        CVE-2026-54770
GHSA:       GHSA-6hx8-3wjj-gr8g
ecosystem:  pip
package:    webob
range:      < 1.8.11
patched:    1.8.11
NVD:        present
KEV:        absent in selected 2026-09-10 snapshot
EPSS:       present
```

A public immutable repository target was also identified with `webob==1.8.10` in an inert root `uv.lock`:

```text
repository: openedx/mockprock
commit:     18c954d8604df4740c829ba17fa2f3640b92b900
file:       uv.lock
```

These coordinates are pre-live evidence, not proof of repository runtime exposure.

## Explicit non-goals

This increment does not:

- load source snapshots from AWS;
- create a public endpoint;
- create or alter AWS resources;
- create or alter IAM authority;
- execute third-party repository code;
- invoke Bedrock;
- select `SYNC` or `ASYNC` runtime topology;
- modify PR #89.

## Next boundary

After exact-head CI passes, the remaining human execution step is to materialize the complete typed GHSA/NVD/KEV/EPSS source objects through retained read-only source/transform contracts, admit them against the cross-source bundle, and then execute exactly one bounded non-public representative GitHub + Bedrock measurement.
