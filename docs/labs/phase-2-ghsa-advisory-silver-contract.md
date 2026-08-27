# Phase 2.4B — GHSA Advisory / Silver Contract

_Date started: 2026-08-27_

_Status: IN PROGRESS_

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
```

Phase 2.4B defines how one exact source advisory becomes versioned structured evidence.

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

The current increment composes the previously validated domain components into one logical record:

```text
GhsaSilverRecordV1
├── core
├── collections
└── vulnerabilities
```

All three components must describe the same exact `ObservedGhsaAdvisoryVersion`. Cross-advisory or cross-CVE composition fails closed.

### Dataset shape

The selected Silver v1 dataset is:

```text
dataset:           ghsa_advisory_versions
schema_version:    1
row identity:      observed_advisory_version_id
physical grain:    one row per exact advisory content version
```

One advisory version remains one physical row. One-to-many advisory facts use nested Arrow collections instead of multiplying advisory rows:

```text
identifiers            list<struct<type,value>>
references             list<string>
cwes                   list<struct<cwe_id,name>>
cvss_metrics            list<struct<family,vector_string,score>>
vulnerabilities         list<struct<...>>
```

The vulnerability struct preserves source occurrence identity, package identity, exact range expression, nullable first-patched version, vulnerable functions, and canonical source-entry evidence.

This shape keeps advisory-level identity stable while retaining package multiplicity. Future analytical SQL can explode nested evidence deliberately rather than ingesting a prematurely flattened source model.

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

The logical hash uses a domain separator:

```text
opslens-ghsa-logical-record-set-v1
```

This separates logical data identity from a particular PyArrow/Parquet encoding.

### Parquet v1 writer contract

The physical writer contract mirrors the already proven deterministic NVD settings:

```text
Parquet format version: 1.0
data page version:      1.0
compression:            snappy
row group size:         5000
compliant nested type:  enabled
INT96 timestamps:       disabled
Arrow schema metadata:  stored
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

The Phase 2.4A live workload proved that one advisory may contain many package/range entries. Flattening at Silver ingestion would duplicate advisory text, timestamps, identifiers, CWE, references, and CVSS once per package occurrence and would make advisory-version identity depend on a derived relational expansion.

Nested Arrow/Parquet instead preserves the source cardinality boundary directly:

```text
one observed advisory content version
    -> one Silver row
    -> zero or more nested vulnerability occurrences
```

A later analytics projection may create a package-oriented relation if a concrete Athena workload proves that projection worthwhile. That projection must remain derived and must not replace the authoritative Silver advisory-version dataset.

### Provenance boundary

The v1 row grain in this increment is **advisory content version**, not physical REST retrieval occurrence.

Phase 2.4A already established:

```text
sync_id != attempt_id
```

The exact Bronze manifest/object/version binding and physical observation coordinates remain Phase 2.4C/2.4D contract work. They must be added as verification/completion evidence without changing the meaning of the `observed_advisory_version_id` content key.

No claim is made here that repeated physical observations of identical content are the same source occurrence; they are only the same advisory content version.

## Explicit Phase boundary

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

## AWS / IAM / cost boundary

This increment creates no AWS resources and introduces no AWS runtime cost.

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

## Current gates

```text
GHSA_OBSERVED_ADVISORY_IDENTITY_GATE=PASS
GHSA_CORE_FIELDS_GATE=PASS
GHSA_REVIEWED_SCOPE_SILVER_GATE=PASS
GHSA_CVE_NULLABILITY_GATE=PASS
GHSA_WITHDRAWAL_CORE_GATE=PASS
GHSA_COLLECTIONS_CONTRACT_GATE=PASS
GHSA_VULNERABILITY_ENTRIES_GATE=PASS
GHSA_LOGICAL_RECORD_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_ARROW_SCHEMA_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_LOGICAL_HASH_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_PARQUET_DETERMINISM_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_BRONZE_PROVENANCE_BINDING_GATE=PENDING_FUTURE_GATE
GHSA_2_4B_GATE=IN_PROGRESS
```

## Next step

Run focused GHSA tests, Ruff, and strict Pyright against the new logical/Arrow/Parquet increment.

If green, record the evidence and decide whether Phase 2.4B can close with exact Bronze provenance explicitly deferred to Phase 2.4C, or whether an additional contract-only provenance shape is required before the Silver schema is declared frozen.

Do not introduce GHSA AWS runtime resources until that decision is explicit.

## Official references

- GitHub REST API — Global security advisories: https://docs.github.com/en/rest/security-advisories/global-advisories
- GitHub REST API breaking changes — `cvss` deprecation in favor of `cvss_severities`: https://docs.github.com/en/enterprise-cloud@latest/rest/about-the-rest-api/breaking-changes?apiVersion=2026-03-10
- ADR-0005 — GHSA source and synchronization strategy: `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
