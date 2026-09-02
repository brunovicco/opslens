# ADR 0013 — Normalize locked PyPI records through the Phase 3 identity contract

- Status: Accepted
- Date: 2026-09-02
- Phase: 4 — Repository Intelligence

## Context

ADR 0012 produces typed package records from an integrity-verified immutable `uv.lock`. It deliberately preserves package names and versions exactly as they appear in the lockfile and does not duplicate ecosystem semantics.

Phase 3 already owns deterministic PyPI identity:

- PyPA distribution-name validation and normalization;
- PEP 440 concrete version parsing and canonicalization;
- canonical package URL construction;
- stable fail-closed reason codes such as `invalid_package_name` and `invalid_version`.

Phase 4 must reuse that authority before repository dependency evidence can ever be correlated with vulnerability ranges.

The architectural rule is:

> **One normalization authority per ecosystem.**

Repository parsing establishes what the repository says. Phase 3 establishes canonical ecosystem identity.

## Decision

Phase 4 introduces a deterministic bridge from `ParsedUvLockEvidence.pypi_packages` to the existing Phase 3 PyPI identity functions.

```text
ParsedUvLockEvidence
  -> canonical-PyPI source records only
  -> Phase 3 canonicalize_pypi_package
  -> Phase 3 canonicalize_pypi_version
  -> Phase 3 build_pypi_purl
  -> normalized repository PyPI dependency evidence
```

The bridge does not perform vulnerability lookup or range evaluation.

## Authority boundary

The bridge imports and uses the existing Phase 3 functions directly. It does not copy their regular expressions, PEP 440 logic, package-name normalization rules, purl encoding rules, or reason-code taxonomy into Phase 4.

A future change to PyPI identity semantics must therefore occur in the Phase 3 authority and flow into this bridge through tests.

## Normalized record evidence

For every successfully normalized canonical-PyPI lock record, Phase 4 preserves:

```text
snapshot_id
file_evidence_id
uv.lock record_index
source name_original
source version_original
canonical package object
canonical version object
canonical purl
registry_url
resolution_markers
```

The original lockfile record remains linked rather than replaced. Marker provenance remains uninterpreted.

No deduplication occurs. Two lock records with the same canonical name/version but different source indexes or markers remain separate evidence records.

## Record-level fail-closed behavior

A record whose source is exactly canonical PyPI can still contain a name or version that the Phase 3 authority cannot normalize. Such a record must never become correlatable dependency evidence.

Instead of aborting the entire repository inventory, the bridge emits explicit unsupported normalization evidence for that record with the exact Phase 3 `reason_code`.

This behavior is fail-closed **per record**:

```text
valid normalization -> normalized evidence eligible for later correlation
normalization error -> explicit unsupported evidence; never correlated
```

The bridge does not rewrite invalid data, guess a corrected package, or downgrade the failure to a valid dependency.

This preserves visibility into other valid packages in the same immutable lockfile while preventing one malformed record from creating false identity.

## Source-unsupported records

Records already classified by ADR 0012 as custom registry, virtual, editable, Git, path/directory, or another unsupported source kind do not enter the Phase 3 PyPI normalization bridge at all.

They remain in `ParsedUvLockEvidence.unsupported_packages` with their original source reason. The bridge result preserves the parsed lock evidence, so the complete source inventory remains auditable without falsely assigning PyPI identity.

## Completeness invariant

Every record in `ParsedUvLockEvidence.pypi_packages` must appear exactly once in one of these bridge outputs:

```text
normalized_pypi_dependencies
unsupported_pypi_normalization
```

No PyPI-source record may disappear silently, appear in both categories, or be synthesized from a source-unsupported record.

The original zero-based `uv.lock` record indexes remain the cross-stage evidence key.

## Runtime boundary

Normalization establishes canonical repository dependency identity only. It does not prove the dependency is active in a deployed workload.

Universal-lock resolution markers remain provenance and are not evaluated in this gate.

> **Repository Risk != Runtime Exposure.**

## No vulnerability authority yet

This gate does not:

- look up GHSA, NVD, KEV, EPSS, or CVSS;
- parse vulnerable ranges;
- decide `affected` / `not_affected`;
- reconcile CVE/GHSA aliases;
- rank findings;
- infer runtime exposure.

Those remain later deterministic stages.

## Security, AWS, IAM, and cost

This gate is pure in-process domain/application logic over already verified inert evidence.

It adds no network request, AWS service, IAM permission, database, queue, cache, model call, package-manager execution, or third-party repository execution.

Incremental AWS cost: **$0**.

## Alternatives considered

### Normalize inside the `uv.lock` parser

Rejected. It would combine repository-format parsing with ecosystem authority and create a second place where Phase 3 semantics could drift.

### Treat raw lockfile name/version as canonical

Rejected. PyPI names have defined normalization semantics and concrete versions require deterministic PEP 440 parsing before vulnerability matching.

### Abort the complete inventory on one invalid PyPI record

Rejected. That loses valid repository evidence unnecessarily. Record-level explicit unsupported evidence is still fail-closed for the bad identity while retaining deterministic visibility into independent records.

### Silently skip invalid records

Rejected. Silent omission destroys auditability and can make repository coverage appear stronger than it is.

## Exit criteria

This gate is complete when:

- only ADR 0012 canonical-PyPI source records enter the bridge;
- Phase 3 remains the only PyPI name/version/purl normalization authority;
- valid records emit canonical package, version, and purl evidence;
- Phase 3 normalization reason codes are preserved for unsupported records;
- every PyPI-source record is accounted for exactly once;
- source-unsupported records remain outside the bridge;
- original indexes and resolution markers are preserved;
- duplicate canonical identities are not deduplicated;
- no vulnerability lookup or range evaluation is introduced;
- Repository Intelligence and Phase 3 quality gates remain green.

## Next gate

Join normalized repository PyPI dependency evidence to deterministic GHSA advisory/package evidence and invoke the existing Phase 3 range evaluator, producing repository vulnerability findings that preserve both dependency and advisory provenance while still avoiding runtime-exposure claims.
