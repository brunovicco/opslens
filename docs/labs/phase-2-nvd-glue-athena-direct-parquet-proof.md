# Phase 2.3G.3B — Direct Athena Parquet Projection Proof

## Status

COMPLETE — the exact-version projected incremental Parquet is directly queryable by Amazon Athena through a normal Parquet external table, without `SymlinkTextInputFormat`.

## Purpose

Prove that the exact-version analytics projection created in Phase 2.3G.3A provides both authority-preserving materialization and clean Athena addressability.

The analytical boundary remains:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

`analytics_projected` is downstream materialization only. It does not authorize or advance the NVD watermark.

## Exact projected source

Projected object:

```text
s3://opslens-dev-data-487757851499-us-east-1/analytics-spike/nvd/cve/exact-projection/schema_version=1/source_kind=incremental/update_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e/part-00000.parquet
```

Destination VersionId:

```text
A29.Nmc0IQUFAmxsNLAk9hLiG7ETLY42
```

Destination SHA-256:

```text
d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8
```

Rows:

```text
6749
```

The projection was previously proven to originate from exact Silver VersionId:

```text
f.L5xLSzp1eabl4R9VA8ebt6ReWEp9cm
```

with matching `CopySourceVersionId`, destination SHA-256, Parquet magic, lineage metadata, and fail-closed replay behavior.

## Temporary Athena table

Temporary table:

```text
opslens_dev.nvd_cve_versions_projection_spike_65e286bd
```

The table used the explicit NVD Silver v1 schema with ordinary:

```text
STORED AS PARQUET
```

and the clean exact-projection prefix as `LOCATION`.

No `SymlinkTextInputFormat` was used.

Before creation, Glue returned `EntityNotFound`, proving the temporary table name was unused:

```text
NVD_2_3G_DIRECT_TABLE_ABSENT_GATE=PASS
```

## CREATE TABLE evidence

QueryExecutionId:

```text
4f3f599a-e9da-4457-8159-91f1a993f9f2
```

Execution:

```text
State: SUCCEEDED
DataScannedInBytes: 0
EngineExecutionTimeInMillis: 2497
TotalExecutionTimeInMillis: 3193
QueryQueueTimeInMillis: 505
```

This proves the clean projected prefix is addressable by an ordinary Athena Parquet table.

## Cardinality query

QueryExecutionId:

```text
382b0d5b-e905-418c-a04f-195694293d84
```

Execution:

```text
State: SUCCEEDED
DataScannedInBytes: 94751
EngineExecutionTimeInMillis: 711
TotalExecutionTimeInMillis: 903
QueryQueueTimeInMillis: 99
```

Local PyArrow reference:

```text
row_count: 6749
distinct_cves: 6749
min_last_modified_at: 2026-08-18 09:16:47.450000+00:00
max_last_modified_at: 2026-08-25 23:17:59.860000+00:00
```

Athena result:

```text
row_count: 6749
distinct_cves: 6749
min_last_modified_at: 2026-08-18 09:16:47.450
max_last_modified_at: 2026-08-25 23:17:59.860
```

Formal gates:

```text
NVD_2_3G_DIRECT_LOCAL_ROW_COUNT_GATE=PASS
NVD_2_3G_DIRECT_ROW_COUNT_GATE=PASS
NVD_2_3G_DIRECT_DISTINCT_CVE_GATE=PASS
```

## Deterministic complex-type query

The test selected one deterministic `observation_id` from the exact projected Parquet rather than relying only on `cve_id`:

```text
observation_id:
6c693fdf8d0646949d93eedc6cd1528a3ec6ee5e84382db3aff9438d2f8f635e

cve_id:
CVE-2013-4730

vuln_status:
Modified

cwe_ids:
[CWE-119]

cvss_family:
V2

cvss_version:
2.0

cvss_base_score:
10.0
```

Athena query execution:

```text
QueryExecutionId:
13d6dbc1-1e6c-4afd-b936-76d8b8d24383

State:
SUCCEEDED

DataScannedInBytes:
1137510

EngineExecutionTimeInMillis:
567

TotalExecutionTimeInMillis:
689

QueryQueueTimeInMillis:
52
```

Athena returned the exact same observation identity and nested values.

Formal gates:

```text
NVD_2_3G_DIRECT_OBSERVATION_GATE=PASS
NVD_2_3G_DIRECT_CVE_GATE=PASS
NVD_2_3G_DIRECT_STATUS_GATE=PASS
NVD_2_3G_DIRECT_CWE_GATE=PASS
NVD_2_3G_DIRECT_CVSS_FAMILY_GATE=PASS
NVD_2_3G_DIRECT_CVSS_VERSION_GATE=PASS
NVD_2_3G_DIRECT_CVSS_SCORE_GATE=PASS
```

## Direct Parquet proof result

Final gates:

```text
NVD_2_3G_DIRECT_PARQUET_READ_GATE=PASS
NVD_2_3G_DIRECT_PARQUET_CROSSCHECK_GATE=PASS
NVD_2_3G_PROJECTION_SCAN_LIMIT_GATE=PASS
```

The count query scanned 94,751 bytes and the deterministic complex query scanned 1,137,510 bytes. Both remained below the existing 10 MiB Athena workgroup cutoff.

The complex query scan cannot be compared directly with the earlier symlink proof because the query shape changed: this proof includes and filters by `observation_id` to make the cross-check deterministic.

## Architectural result

Phase 2.3G.3B demonstrates the intended combination:

```text
exact-version authority
    +
immutable analytics projection
    +
clean Parquet-only namespace
    +
ordinary Athena Parquet table
    +
no symlink indirection
```

This is stronger than the symlink compatibility path because exact source authority is converted into a new immutable analytics object whose clean prefix is directly addressable by Athena.

## Next boundary

The temporary table and projected object remain present only until cleanup evidence is recorded.

Next sequence:

```text
record exact cleanup
    -> drop temporary Athena table
    -> verify Glue EntityNotFound
    -> delete exact temporary projection VersionId
    -> verify no current projection object remains
    -> repeat exact-version projection pattern for the verified Bootstrap seed
```

Permanent Terraform, Lambda runtime, and Glue resources remain deferred until the Bootstrap projection and permanent-path design are proven.
