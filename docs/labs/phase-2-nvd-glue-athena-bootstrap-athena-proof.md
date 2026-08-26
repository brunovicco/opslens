# Phase 2.3G.3C — Bootstrap Athena Projection Proof

## Status

IN PROGRESS — ordinary-Parquet Athena addressability and bounded scan behavior have been proven for the exact-version Bootstrap analytics projection. Exact PyArrow-to-Athena result cross-check and cleanup remain pending.

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

Local PyArrow reference prepared from the exact projected VersionId:

```text
row_count: 48293
distinct_cves: 48293
min_last_modified_at: 2026-01-03 04:15:50.813000+00:00
max_last_modified_at: 2026-08-22 06:16:17.510000+00:00
```

The Athena query result file exists locally and still requires exact result cross-check before the cardinality gate is closed.

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

The query completed below the unchanged 10 MiB workgroup cutoff. Exact returned-field comparison with the local PyArrow observation remains pending.

## Cost-boundary result so far

The physical Bootstrap Parquet is 36,240,684 bytes, larger than the 10,485,760-byte workgroup cutoff, yet both bounded columnar data queries completed successfully:

```text
cardinality query scanned: 629676 bytes
complex query scanned:     3927639 bytes
workgroup cutoff:          10485760 bytes
```

This proves that physical object size alone does not determine query rejection. Column pruning and Parquet scan behavior can keep bounded analytical queries below the workgroup guardrail without increasing the cutoff.

This proof does not claim that every Bootstrap query is safe under the cutoff.

## Current gate state

```text
NVD_2_3G_BOOTSTRAP_DIRECT_TABLE_ABSENT_GATE=PASS
NVD_2_3G_BOOTSTRAP_DIRECT_CREATE_GATE=PASS
NVD_2_3G_BOOTSTRAP_CARDINALITY_EXECUTION_GATE=PASS
NVD_2_3G_BOOTSTRAP_COMPLEX_EXECUTION_GATE=PASS
NVD_2_3G_BOOTSTRAP_SCAN_LIMIT_GATE=PASS

NVD_2_3G_BOOTSTRAP_ROW_COUNT_GATE=PENDING
NVD_2_3G_BOOTSTRAP_DISTINCT_CVE_GATE=PENDING
NVD_2_3G_BOOTSTRAP_OBSERVATION_GATE=PENDING
NVD_2_3G_BOOTSTRAP_COMPLEX_TYPE_GATE=PENDING
NVD_2_3G_BOOTSTRAP_PARQUET_CROSSCHECK_GATE=PENDING
Cleanup gates: PENDING
```

## Next proof step

Read the already-produced Athena result files, compare cardinality and deterministic nested fields against exact local PyArrow values, then record cleanup of the temporary Glue/Athena table and exact temporary Bootstrap projection VersionId.

Permanent Terraform/Lambda/Glue infrastructure remains deferred until Bootstrap validation and cleanup are complete and the permanent AWS path is designed and proven.
