# Phase 2.3G.3C — Bootstrap Athena Projection Proof

## Status

COMPLETE — ordinary-Parquet Athena addressability, bounded scan behavior, and exact PyArrow-to-Athena result equivalence have been proven for the exact-version Bootstrap analytics projection under the unchanged 10 MiB workgroup cutoff.

Cleanup remains pending.

## Purpose

Validate that the already-proven exact-version Bootstrap analytics projection is directly queryable through an ordinary Athena Parquet external table while preserving the existing 10 MiB workgroup cutoff.

No `SymlinkTextInputFormat` is used in this proof.

## Exact projected object under test

```text
source_kind:
bootstrap

feed_year:
2026

feed_revision:
20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68

projected VersionId:
3MQ4Yx_EfGR01vYOt1dxoQtAn746VID5

SHA-256:
4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541

physical bytes:
36240684

rows:
48293
```

The projection was already proven to originate from exact Bootstrap Silver VersionId:

```text
ucv9W1GLmaYj00PdvYp3CSBC_fPoETP_
```

with exact `CopySourceVersionId`, matching destination SHA-256, lineage metadata, conditional replay rejection, and stable destination VersionId.

## Temporary Athena table

```text
opslens_dev.nvd_cve_versions_bootstrap_projection_spike_2026
```

Before creation, Glue returned `EntityNotFound`, proving the temporary table name was unused:

```text
NVD_2_3G_BOOTSTRAP_DIRECT_TABLE_ABSENT_GATE=PASS
```

The table uses the explicit NVD Silver v1 schema with ordinary:

```text
STORED AS PARQUET
```

and the clean exact-projection prefix as `LOCATION`.

## CREATE TABLE evidence

QueryExecutionId:

```text
a5475607-9910-48db-a135-287ece00d821
```

Execution:

```text
State: SUCCEEDED
DataScannedInBytes: 0
EngineExecutionTimeInMillis: 1598
TotalExecutionTimeInMillis: 2171
QueryQueueTimeInMillis: 506
```

This proves ordinary-Parquet addressability for the Bootstrap projection.

## Cardinality query

QueryExecutionId:

```text
adb6d9f4-7c28-4689-8ed3-e2e634c277d2
```

Execution:

```text
State: SUCCEEDED
DataScannedInBytes: 629676
EngineExecutionTimeInMillis: 1200
TotalExecutionTimeInMillis: 1418
QueryQueueTimeInMillis: 105
```

Exact local PyArrow reference:

```text
row_count: 48293
distinct_cves: 48293
min_last_modified_at: 2026-01-03 04:15:50.813000+00:00
max_last_modified_at: 2026-08-22 06:16:17.510000+00:00
```

The Athena result matched the local PyArrow reference after UTC timestamp normalization.

Formal cardinality gates:

```text
NVD_2_3G_BOOTSTRAP_ROW_COUNT_GATE=PASS
NVD_2_3G_BOOTSTRAP_DISTINCT_CVE_GATE=PASS
NVD_2_3G_BOOTSTRAP_MIN_TIMESTAMP_GATE=PASS
NVD_2_3G_BOOTSTRAP_MAX_TIMESTAMP_GATE=PASS
```

## Deterministic nested-field query

Local PyArrow selected this deterministic observation:

```text
observation_id:
b7bfa3f25e6cf5cce896e797804c39880ed6e2b72036468214b562eb19af454d

cve_id:
CVE-2026-0005

vuln_status:
Modified

cwe_ids:
[CWE-200]

cvss_family:
V31

cvss_version:
3.1

cvss_base_score:
6.2
```

Athena QueryExecutionId:

```text
e8f9778f-6521-45c8-991b-8f13df27b254
```

Execution:

```text
State: SUCCEEDED
DataScannedInBytes: 3927639
EngineExecutionTimeInMillis: 901
TotalExecutionTimeInMillis: 1088
QueryQueueTimeInMillis: 65
```

The returned observation identity and nested `cwe_ids` / `cvss_metrics` values matched the exact local PyArrow observation.

Formal nested-field gates:

```text
NVD_2_3G_BOOTSTRAP_OBSERVATION_GATE=PASS
NVD_2_3G_BOOTSTRAP_CVE_GATE=PASS
NVD_2_3G_BOOTSTRAP_STATUS_GATE=PASS
NVD_2_3G_BOOTSTRAP_CWE_GATE=PASS
NVD_2_3G_BOOTSTRAP_CVSS_FAMILY_GATE=PASS
NVD_2_3G_BOOTSTRAP_CVSS_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_CVSS_SCORE_GATE=PASS
```

## Cost-boundary result

The physical Bootstrap Parquet is 36,240,684 bytes, larger than the 10,485,760-byte workgroup cutoff, yet both bounded columnar data queries completed successfully:

```text
cardinality query scanned: 629676 bytes
complex query scanned:     3927639 bytes
workgroup cutoff:          10485760 bytes
```

This proves that physical object size alone does not determine query rejection. Column pruning and Parquet scan behavior can keep bounded analytical queries below the workgroup guardrail without increasing the cutoff.

This proof does not claim that every Bootstrap query is safe under the cutoff.

## Final proof gates

```text
NVD_2_3G_BOOTSTRAP_DIRECT_TABLE_ABSENT_GATE=PASS
NVD_2_3G_BOOTSTRAP_DIRECT_CREATE_GATE=PASS
NVD_2_3G_BOOTSTRAP_CARDINALITY_EXECUTION_GATE=PASS
NVD_2_3G_BOOTSTRAP_COMPLEX_EXECUTION_GATE=PASS
NVD_2_3G_BOOTSTRAP_ROW_COUNT_GATE=PASS
NVD_2_3G_BOOTSTRAP_DISTINCT_CVE_GATE=PASS
NVD_2_3G_BOOTSTRAP_MIN_TIMESTAMP_GATE=PASS
NVD_2_3G_BOOTSTRAP_MAX_TIMESTAMP_GATE=PASS
NVD_2_3G_BOOTSTRAP_OBSERVATION_GATE=PASS
NVD_2_3G_BOOTSTRAP_CVE_GATE=PASS
NVD_2_3G_BOOTSTRAP_STATUS_GATE=PASS
NVD_2_3G_BOOTSTRAP_CWE_GATE=PASS
NVD_2_3G_BOOTSTRAP_CVSS_FAMILY_GATE=PASS
NVD_2_3G_BOOTSTRAP_CVSS_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_CVSS_SCORE_GATE=PASS
NVD_2_3G_BOOTSTRAP_COMPLEX_TYPE_GATE=PASS
NVD_2_3G_BOOTSTRAP_PARQUET_CROSSCHECK_GATE=PASS
NVD_2_3G_BOOTSTRAP_SCAN_LIMIT_GATE=PASS
NVD_2_3G_BOOTSTRAP_ATHENA_PROOF_GATE=PASS
```

## Architectural result

The Bootstrap proof now demonstrates:

```text
exact verified Bootstrap Silver COMPLETE + Parquet
    -> exact-version analytics projection
    -> immutable projected VersionId
    -> identical SHA-256 and lineage metadata
    -> ordinary Athena Parquet table
    -> 48,293-row exact PyArrow/Athena equivalence
    -> nested-type exact equivalence
    -> bounded scans below unchanged 10 MiB cutoff
```

This validates the same permanent projection model for both incremental authority and the one-time Bootstrap seed path.

## Next proof step

Record exact cleanup of the temporary Bootstrap Athena table and exact temporary projected VersionId:

```text
DROP temporary table
    -> verify Glue EntityNotFound
    -> re-read exact projected VersionId before deletion
    -> delete exact projected VersionId
    -> verify exact-version HeadObject returns 404
    -> verify current-key HeadObject returns 404
```

After cleanup, the next phase is the permanent analytics path design and implementation. Permanent Terraform/Lambda/Glue infrastructure remains deferred until that path is reviewed and proven.
