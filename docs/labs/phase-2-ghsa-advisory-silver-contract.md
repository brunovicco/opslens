# Phase 2.4B — GHSA Advisory / Silver Contract

_Date started: 2026-08-27_

_Date completed: 2026-08-27_

_Status: COMPLETE_

## Purpose

Freeze the deterministic GitHub Security Advisory normalization contract before GHSA Bronze/runtime AWS resources are introduced.

Phase 2.4A already accepted the source and synchronization boundary:

```text
runtime source: GitHub Global Security Advisories REST API
API version:    2026-03-10
scope:          reviewed only
identity:       GHSA-first
pagination:     exact Link continuation
bootstrap:      bounded published-time windows
incremental:    bounded modified-time windows
sync_id:        logical synchronization identity
attempt_id:     exact physical source-observation identity
```

Phase 2.4B freezes how one exact source advisory content version becomes deterministic structured Silver evidence.

The invariant remains:

> **Agents reason. Code verifies evidence.**

No LLM participates in advisory identity, CVE alias validation, package/range normalization, patched-version evidence, CVSS/CWE normalization, logical hashing, Parquet serialization, or completion decisions.

## Increment 1 — observed advisory identity and core fields

The source advisory identity and observed content-version identity remain separate:

```text
ghsa_id
    logical GitHub advisory identity

source_advisory_sha256
    exact canonical source-content identity

observed_advisory_version_id
    GHSA ID + source content SHA-256
```

`updated_at` remains source metadata and is not trusted as the sole content identity. Unknown additive fields participate in canonical source identity even before they receive dedicated normalized Silver columns.

The normalized core preserves the reviewed-only scalar source contract, optional CVE alias, explicit UTC timestamps, and nullable withdrawal state.

Local evidence for this increment:

```text
19 passed
Ruff: all checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

## Increment 2 — collections and package/range/fix evidence

The second increment preserves source-ordered one-to-many evidence:

```text
identifiers[]
references[]
cwes[]
cvss_severities
vulnerabilities[]
```

Identifiers preserve source order. GHSA and CVE values are consistency-checked against the scalar advisory fields, while additive future identifier types remain source evidence rather than being prematurely enum-bounded.

References remain ordered strings and are never dereferenced during normalization. CWE observations preserve canonical `CWE-n` identifiers and source names.

Known `cvss_severities.cvss_v3` and `cvss_severities.cvss_v4` structures become typed metric evidence while the complete `cvss_severities` object is also preserved as Canonical JSON v1. The deprecated top-level `cvss` field is not promoted to a second Silver authority.

GitHub-provided EPSS remains part of the complete source advisory identity when present, but OpsLens does not create a competing authoritative EPSS dataset because FIRST EPSS already owns that evidence path.

Each source `vulnerabilities[]` occurrence preserves:

```text
source_index
ecosystem
package name
vulnerable_version_range
first_patched_version          nullable
vulnerable_functions[]
canonical source-entry JSON
source-entry SHA-256
```

The exact occurrence identity is:

```text
<observed_advisory_version_id>/vulnerability:<source_index>@sha256:<source_entry_sha256>
```

Identical duplicate source entries therefore remain distinct occurrences when they occupy different source indexes.

Local evidence after strict-typing fixes:

```text
39 passed
Ruff: all checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

## Increment 3 — logical Silver record and physical schema v1

The final increment composes the validated domain components into one logical record:

```text
GhsaSilverRecordV1
├── core
├── collections
└── vulnerabilities
```

All three components must describe the same exact `ObservedGhsaAdvisoryVersion`. Cross-advisory or cross-CVE composition fails closed.

### Dataset shape

The frozen Silver v1 dataset is:

```text
dataset:           ghsa_advisory_versions
schema_version:    1
row identity:      observed_advisory_version_id
physical grain:    one row per exact advisory content version
```

One advisory version remains one physical row. One-to-many facts use nested Arrow collections instead of multiplying advisory rows:

```text
identifiers            list<struct<type,value>>
references             list<string>
cwes                   list<struct<cwe_id,name>>
cvss_metrics            list<struct<family,vector_string,score>>
vulnerabilities         list<struct<...>>
```

The vulnerability struct preserves source occurrence identity, package identity, exact range expression, nullable first-patched version, vulnerable functions, and canonical source-entry evidence.

Future analytical SQL may explode nested evidence deliberately. A package-oriented relation may be introduced later as a derived projection, but it must not replace the authoritative advisory-version dataset.

### Logical record-set identity

`GhsaLogicalRecordSetHasherV1` hashes canonical logical rows independently of Parquet bytes.

The rules are:

```text
caller input order does not change the digest
rows sort by ghsa_id + observed_advisory_version_id
source-internal array order remains evidence and is not resorted
duplicate observed_advisory_version_id values fail closed
nested package/range/fix changes alter the logical digest
```

The logical hash uses the domain separator:

```text
opslens-ghsa-logical-record-set-v1
```

This separates logical data identity from a particular PyArrow/Parquet encoding.

### Parquet v1 writer contract

The physical writer contract is frozen as:

```text
Parquet format version: 1.0
data page version:      1.0
compression:            snappy
row group size:         5000
compliant nested type:  enabled
INT96 timestamps:       disabled
Arrow schema metadata:  stored
timestamps:             UTC / microseconds
```

Rows are canonically sorted before table construction. Duplicate exact advisory content versions fail before serialization.

The artifact model binds:

```text
Parquet bytes
Parquet SHA-256
size bytes
row count
schema version
```

Input record order must not change Parquet bytes within the frozen writer/runtime contract.

### Why nested instead of package-row flattening

The Phase 2.4A live workload proved that one advisory may contain many package/range entries. Flattening at Silver ingestion would duplicate advisory text, timestamps, identifiers, CWE, references, and CVSS once per package occurrence and make advisory-version identity depend on a derived relational expansion.

Nested Arrow/Parquet preserves the source cardinality boundary directly:

```text
one observed advisory content version
    -> one Silver row
    -> zero or more nested vulnerability occurrences
```

## Phase 2.4D runtime refinement — unavailable CVSS placeholders

Real reviewed-advisory evidence in Phase 2.4D showed that GitHub may include a known `cvss_v3` or `cvss_v4` object whose vector is unavailable as an empty or nullable placeholder. This refines normalization without changing Silver schema v1 or content identity.

```text
usable known vector + numeric score
    -> typed cvss_metrics observation

known family present but vector unavailable
    -> preserve exact cvss_severities source JSON
    -> do not fabricate a typed metric

malformed non-null vector or incompatible score
    -> fail closed
```

The real 10-advisory Bronze attempt contained seven unavailable CVSS v4 placeholders. All seven were preserved in canonical source JSON while emitting no invented typed CVSS v4 metric.

## Explicit Phase 3 boundary

Phase 2.4 may preserve:

```text
package ecosystem
package name
vulnerable version range expression
first patched version when present
```

It must not decide:

```text
installed_version ∈ vulnerable_version_range
```

That decision remains deterministic Phase 3 — Vulnerability Correlation Engine work.

## Provenance and completion boundary

Phase 2.4A established:

```text
sync_id != attempt_id
```

Phase 2.4B now explicitly freezes:

```text
observed_advisory_version_id != sync_id != attempt_id
```

The v1 Silver row represents exact advisory **content version**, not one physical REST retrieval occurrence.

The same advisory content can legitimately be observed in multiple synchronization attempts. Re-observing identical content must not create another advisory content version merely because the request, page, retry, S3 object, or S3 VersionId differs.

Later GHSA Bronze/runtime work must preserve exact physical occurrence provenance and bind every accepted physical occurrence back to its `observed_advisory_version_id`. That binding must not mutate or redefine the content-version identifier.

The exact Bronze manifest/object/version fields and exact physical representation of occurrence-to-content provenance are deliberately deferred to Phase 2.4C/2.4D, where the real Bronze object and completion contracts exist.

End-to-end Bronze-to-Silver completion is also a runtime concern because it requires evidence not present in a contract-only Silver gate:

```text
exact synchronization window
exact attempt
ordered pages
Bronze object versions and hashes
accepted source occurrence count
Silver artifact identity
successful persistence
authority/watermark mutation rules
```

This deferral is an explicit architectural boundary, not an incomplete 2.4B contract. ADR-0006 records the decision.

## Final local validation

After Increment 3, the focused checkpoint was reported green:

```text
uv run pytest tests/unit/transformation/ghsa
uv run ruff check src/opslens/transformation/ghsa tests/unit/transformation/ghsa
uv run pyright
```

Result:

```text
PASS
```

## AWS / IAM / cost boundary

Phase 2.4B creates no AWS resources and introduces no AWS runtime cost.

Not implemented here:

```text
GHSA Bronze S3 objects
Lambda
Terraform
EventBridge Scheduler
IAM
secret storage
Silver persistence
Glue
Athena
watermark / authority mutation
```

Credential design remains deferred to the GHSA runtime/security gate accepted by ADR-0005.

## Final gates

```text
GHSA_OBSERVED_ADVISORY_IDENTITY_GATE=PASS
GHSA_CORE_FIELDS_GATE=PASS
GHSA_REVIEWED_SCOPE_SILVER_GATE=PASS
GHSA_CVE_NULLABILITY_GATE=PASS
GHSA_WITHDRAWAL_CORE_GATE=PASS
GHSA_COLLECTIONS_CONTRACT_GATE=PASS
GHSA_VULNERABILITY_ENTRIES_GATE=PASS
GHSA_LOGICAL_RECORD_GATE=PASS
GHSA_ARROW_SCHEMA_GATE=PASS
GHSA_LOGICAL_HASH_GATE=PASS
GHSA_PARQUET_DETERMINISM_GATE=PASS
GHSA_BRONZE_PROVENANCE_BINDING_GATE=DEFERRED_TO_2_4C_2_4D_BY_DESIGN
GHSA_END_TO_END_COMPLETION_GATE=DEFERRED_TO_2_4C_2_4D_BY_DESIGN
GHSA_2_4B_GATE=PASS
```

## Exit decision

Phase 2.4B is frozen and complete.

The next milestone is **Phase 2.4C — GHSA Bronze**.

The first 2.4C step must define the deterministic Bronze request/page/manifest/object contract, physical observation identity, bounded failure behavior, and credential/runtime security boundary before any AWS resource is created.

## Official references

- GitHub REST API — Global security advisories: https://docs.github.com/en/rest/security-advisories/global-advisories
- GitHub REST API breaking changes — `cvss` deprecation in favor of `cvss_severities`: https://docs.github.com/en/enterprise-cloud@latest/rest/about-the-rest-api/breaking-changes?apiVersion=2026-03-10
- ADR-0005 — `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
- ADR-0006 — `docs/adr/0006-ghsa-silver-content-versioning-and-physical-shape.md`
