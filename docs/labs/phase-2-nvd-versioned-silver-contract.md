# Phase 2 — NVD Versioned Silver Contract

## Purpose

Phase 2.3D freezes the deterministic NVD Silver contract before introducing
incremental AWS runtime resources.

The architectural rule remains:

```text
Agents reason.
Code verifies evidence.
```

No LLM participates in NVD normalization, version identity, provenance,
Parquet serialization, completion, or watermark promotion eligibility.

## Scope

Implemented:

```text
Observed CVE version identity
NVD core normalization
descriptions and CVE tags
CWE / weakness evidence
references
CVSS v2 / v3.0 / v3.1 / v4 evidence
CPE configuration preservation
explicit Arrow schema v1
deterministic Parquet serialization
exact Bronze evidence verification
Silver COMPLETE proof
zero-result incremental completion
watermark promotion eligibility
```

Not implemented:

```text
NVD Silver Lambda/runtime
incremental EventBridge Scheduler
Terraform runtime resources for this path
Glue registration for NVD
Athena queries for NVD
authoritative watermark write
```

## Identity model

Three identities remain separate:

```text
cve_id
    vulnerability identity

observed_cve_version_id
    exact source-content identity

observation_id
    exact Bronze occurrence identity
```

`observed_cve_version_id` is based on the SHA-256 of a canonical representation
of the complete source `cve` object. Unknown additive source fields therefore
participate in identity even before they receive dedicated normalized columns.

Historical modification, rejection, and unrejection create new observed
versions rather than overwriting prior evidence.

## Structured normalization

The contract preserves deterministic structured evidence for:

```text
core NVD fields
localized descriptions
CVE tags
weaknesses and derived canonical CWE identifiers
references
CVSS v2 / v3.0 / v3.1 / v4 observations
canonical full CVSS metric JSON
canonical full CPE configuration trees
```

OpsLens does not select one universal canonical CVSS score.

Known malformed supported CVSS structures fail closed. Unknown future
`cvssMetricV*` families remain preserved in Bronze and are represented as
deterministic Silver completion warnings.

CPE AND/OR/NEGATE trees are preserved rather than flattened into misleading
fixed-version claims.

## Exact Bronze provenance

Every Silver observation binds to exact immutable Bronze evidence:

```text
Bronze COMPLETE manifest key
Bronze manifest VersionId
Bronze manifest SHA-256
Bronze object key
Bronze object VersionId
Bronze object SHA-256
record index
source batch identity
```

An unversioned S3 key alone is not sufficient evidence.

## Parquet v1

```text
dataset:           nvd_cve_versions
schema_version:    1
format:            Parquet 1.0
data_page_version: 1.0
compression:       snappy
row_group_size:    5000
```

Input order does not change canonical output order.

The serializer rejects mixed source batches and duplicate observation
identities. `serialize([])` remains invalid because an empty iterable has no
batch identity.

A proven zero-result incremental window uses an explicit empty serializer with
the exact incremental source identity.

## Logical and physical completion proof

`logical_record_set_sha256` identifies the normalized logical record set
independently of physical Parquet encoding.

The completion contract separately binds:

```text
logical record-set SHA-256
Parquet bytes
Parquet SHA-256
Parquet size
row count
exact persisted Silver VersionId
```

The completion factory reserializes the supplied logical records and verifies
that they produce the exact supplied Parquet artifact.

## Cardinality and zero-result windows

Incremental Silver completion requires:

```text
Silver row_count == verified Bronze total_results
```

This prevents silent record loss.

A legitimate empty NVD incremental window is valid:

```text
Bronze total_results = 0
Silver row_count     = 0
=> Silver COMPLETE
```

Bootstrap empty completion remains invalid.

## Silver COMPLETE

The conceptual order is:

```text
Bronze COMPLETE
    |
    v
exact Bronze verification
    |
    v
normalized observed CVE versions
    |
    v
logical record-set proof
    |
    v
deterministic Parquet
    |
    v
exact persisted Silver VersionId
    |
    v
Silver COMPLETE manifest
```

The COMPLETE manifest is deterministic and contains no runtime-generated
timestamp that would change replay bytes.

## Watermark authority

The authority states remain intentionally distinct:

```text
bronze_complete
    |
    v
silver_complete
promotion eligible
    |
    X
authoritative watermark not yet mutated
```

Promotion eligibility verifies:

```text
gap-free current committed boundary
candidate update_id and window
candidate Bronze manifest identity
canonical persisted Silver COMPLETE bytes
exact Silver manifest VersionId
exact persisted Silver Parquet VersionId
exact persisted Silver Parquet SHA-256
row_count == total_results
Bronze page inventory count
logical record-set evidence
```

Eligibility is evidence, not state mutation.

A future authoritative watermark writer must validate continuity again before
committing the next boundary.

## IAM

Phase 2.3D adds no IAM permissions because it adds no AWS runtime.

Future runtime permissions must be limited to the concrete exact-version
Bronze reads, Silver persistence, completion evidence, and authoritative
watermark operations that are actually required.

Broad `s3:*` access is not justified.

## Cost

Phase 2.3D introduces no AWS runtime cost.

Future runtime cost drivers include Lambda duration/memory, S3 requests and
versions, Glue metadata, Athena scanned bytes, and CloudWatch telemetry.

## Observability

No new CloudWatch runtime resources exist in 2.3D.

Future runtime should expose at least:

```text
Bronze records expected
Silver rows produced
zero-result runs
unsupported CVSS warnings
transformation failures
Silver completion success/failure
promotion eligibility success/failure
watermark commit success/failure
```

## Failure semantics

```text
provenance mismatch
    -> fail closed

known malformed CVSS
    -> fail closed

unknown future CVSS family
    -> warning, preserve immutable Bronze

duplicate observation
    -> fail closed

Bronze total_results != Silver row_count
    -> fail closed

zero-result incremental window
    -> valid Silver completion

partial Silver output without COMPLETE manifest
    -> not silver_complete

promotion eligibility
    -> no watermark mutation
```

## AIP-C01 learning mapping

Phase 2.3D reinforces:

```text
Domain 1
structured data management, evidence, integrity

Domain 3
security boundaries and deterministic controls

Domain 4
columnar data format and future analytical cost reasoning

Domain 5
validation, testing, replay, troubleshooting
```

No AWS service was introduced merely for certification coverage.

## Exit criteria

Phase 2.3D is complete when:

```text
observed CVE identity is deterministic
historical modifications are preserved
rejected CVEs remain historical evidence
CVSS/CWE/reference/CPE contracts are explicit
Arrow/Parquet schema v1 is explicit
Bronze provenance is exact and versioned
logical-to-physical Parquet binding is proven
zero-result incremental windows can complete
Silver COMPLETE is deterministic
promotion eligibility is deterministic
authoritative watermark remains unmodified
full repository regression is green
```

The next NVD increment operationalizes this frozen contract.
