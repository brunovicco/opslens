# ADR-0006: GHSA Silver Content Versioning and Physical Shape

- Status: Accepted
- Date: 2026-08-27

## Context

Phase 2.4B must freeze a deterministic Silver contract for GitHub-reviewed security advisories before GHSA Bronze or Silver AWS runtimes are introduced.

Phase 2.4A already established the source/synchronization boundary:

```text
runtime source: GitHub Global Security Advisories REST API
API version:    2026-03-10
scope:          reviewed only
identity:       GHSA-first
bootstrap:      bounded published-time windows
incremental:    bounded modified-time windows
sync_id:        logical synchronization identity
attempt_id:     exact physical source-observation identity
```

The remaining architectural questions are:

- what constitutes one logical GHSA Silver row;
- how advisory-level facts and one-to-many package/range/fix evidence are represented;
- how exact source-content identity differs from physical REST observation identity;
- how deterministic logical identity differs from Parquet byte identity;
- which provenance and completion concerns belong to later Bronze/runtime gates.

The project invariant remains:

> **Agents reason. Code verifies evidence.**

No model may decide advisory identity, CVE alias consistency, package applicability, version-range membership, patched-version evidence, serialization identity, or synchronization completion.

## Decision

### Logical dataset

Freeze the authoritative Phase 2.4B Silver dataset as:

```text
dataset:        ghsa_advisory_versions
schema_version: 1
grain:          one row per observed_advisory_version_id
```

`ghsa_id` is the logical GitHub advisory identity.

The exact observed content version is:

```text
source_advisory_sha256 = SHA256(Canonical JSON v1 of the complete source advisory object)

observed_advisory_version_id =
    <ghsa_id>@sha256:<source_advisory_sha256>
```

`updated_at` is source metadata and must not be used as the sole content-version identity.

Unknown additive source fields participate in the complete source-content hash even before they gain dedicated normalized columns.

### One-to-many advisory evidence

Keep advisory-level facts and the source-ordered `vulnerabilities[]` collection in one versioned advisory row using Arrow/Parquet nested structures.

The row preserves nested collections for:

```text
identifiers
references
CWEs
known CVSS metrics
vulnerability/package/range/fix entries
```

Each vulnerability entry keeps its source index and canonical entry SHA-256 so duplicate source-array occurrences remain distinct evidence.

Do not flatten one advisory into one physical Silver row per package/range occurrence in the authoritative dataset. That would duplicate advisory-level facts and make content-version identity depend on a query-oriented denormalization.

Package-oriented Athena projections may be introduced later as derived analytics representations without changing the authoritative Silver grain.

### Range and fix boundary

Preserve:

```text
package ecosystem
package name
vulnerable_version_range     exact source expression
first_patched_version        nullable structured source evidence
vulnerable_functions         source ordered
```

Do not evaluate whether an installed version satisfies a vulnerable range during Phase 2.4.

That remains deterministic Phase 3 — Vulnerability Correlation Engine work with ecosystem-specific version semantics.

### Deterministic physical serialization

Freeze the initial writer contract as:

```text
Parquet format version: 1.0
data page version:      1.0
compression:            snappy
row group size:         5000
nested encoding:        compliant
timestamps:             UTC / microseconds
INT96 timestamps:       disabled
canonical row ordering: observed_advisory_version_id ascending
```

The serializer returns and validates the physical Parquet SHA-256.

### Logical identity is not physical byte identity

Maintain a second deterministic identity over canonical logical rows:

```text
logical_record_set_sha256
    !=
parquet_sha256
```

The logical hash is computed from canonicalized mapped Silver rows after deterministic sorting.

This prevents an implementation-only Parquet writer change from silently redefining logical data identity.

### Content version is not physical source observation

The authoritative Silver row represents exact advisory **content**, not one specific API request occurrence.

Therefore:

```text
observed_advisory_version_id
    !=
sync_id
    !=
attempt_id
```

The same advisory content can legitimately be observed in more than one synchronization attempt. Re-observing identical content must not create a different advisory content version merely because it came from another request, page, S3 object version, or retry.

Later GHSA Bronze/runtime work must preserve exact physical occurrence provenance and bind every accepted occurrence back to its `observed_advisory_version_id`. That binding must not mutate or redefine the content-version identifier.

The exact Bronze manifest/object/version fields and the exact physical representation of occurrence-to-content provenance are intentionally deferred to Phase 2.4C/2.4D, where the real Bronze object and completion contracts exist.

### Completion proof boundary

Phase 2.4B freezes deterministic transformation and serialization semantics only.

It does **not** claim end-to-end Bronze-to-Silver completeness because completion requires runtime evidence that does not yet exist:

```text
exact sync window
exact attempt
ordered pages
Bronze object versions/hashes
accepted source occurrence count
Silver artifact identity
successful persistence
watermark/authority mutation rules
```

Those completion mechanics belong to Phase 2.4C/2.4D and must be proven against the actual Bronze/runtime contract.

Deferring those fields is therefore an explicit architectural boundary, not an incomplete Phase 2.4B decision.

## Alternatives considered

### One Silver row per vulnerability/package entry

Rejected for the authoritative content-version dataset. It duplicates advisory-level facts, couples content identity to flattening, and makes source-array cardinality a physical advisory-row multiplier.

A package-oriented derived analytics projection remains possible later.

### Include physical Bronze provenance in `observed_advisory_version_id`

Rejected. One exact advisory content version may be observed repeatedly. Physical observation coordinates belong to provenance, not source-content identity.

### Use `updated_at` as advisory version identity

Rejected. Source timestamps are metadata and do not prove exact content equality.

### Use only Parquet SHA-256 as dataset identity

Rejected. Physical serialization settings and library implementations can change while the logical records remain equivalent.

### Parse vulnerable-version expressions during Silver normalization

Rejected. Phase 2 preserves source evidence. Deterministic ecosystem-specific applicability belongs to Phase 3.

## Consequences

### Positive

- stable GHSA-first content-version identity;
- exact source-content changes are detected even for additive fields;
- repeated physical observations of identical content deduplicate naturally at the content-version layer;
- one-to-many package evidence remains faithful without duplicating advisory rows;
- Athena can later derive package-oriented projections independently;
- logical identity is insulated from Parquet implementation details;
- provenance responsibilities remain explicit rather than being guessed before Bronze exists;
- Phase 3 applicability logic remains cleanly separated from Phase 2 evidence normalization.

### Trade-offs

- nested arrays require deliberate Athena projection design later;
- physical observation provenance requires an additional binding contract in Phase 2.4C/2.4D;
- complete Bronze-to-Silver authority cannot be proven in Phase 2.4B alone;
- future physical writer changes require explicit writer-contract versioning even if logical rows are unchanged.

## Validation evidence

The Phase 2.4B focused checkpoint was run locally after the final logical-record, Arrow-schema, logical-hash, and Parquet increment:

```text
uv run pytest tests/unit/transformation/ghsa
uv run ruff check src/opslens/transformation/ghsa tests/unit/transformation/ghsa
uv run pyright
```

Result reported for all three checks:

```text
PASS
```

Earlier focused increments had already recorded green unit, Ruff, and strict Pyright evidence for core and collection/package normalization.

## Operational rule

Until superseded by another ADR:

```text
Silver dataset:
ghsa_advisory_versions

row grain:
one exact observed advisory content version

content identity:
GHSA ID + Canonical JSON v1 SHA-256

one-to-many evidence:
nested source-ordered collections

range semantics:
preserve, do not evaluate

logical identity:
canonical logical record-set SHA-256

physical identity:
Parquet SHA-256

physical observation provenance:
separate from content identity; bind in Phase 2.4C/2.4D

end-to-end completion proof:
Phase 2.4C/2.4D runtime responsibility
```

## References

- `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
- `docs/labs/phase-2-ghsa-advisory-silver-contract.md`
- `src/opslens/transformation/ghsa/serialization/schema.py`
- `src/opslens/transformation/ghsa/serialization/parquet.py`
- `src/opslens/transformation/ghsa/serialization/logical_hash.py`
