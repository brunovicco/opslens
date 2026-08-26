# Phase 2.3G.2 — NVD Athena Symlink Compatibility Proof

## Status

COMPLETE — `SymlinkTextInputFormat` is proven compatible with the NVD Silver v1 Parquet schema and bounded Athena queries, but it is not selected as the permanent authority-preserving addressability layer.

## Purpose

Prove whether Amazon Athena can safely read one already-authorized NVD Silver Parquet object without exposing the co-located Silver COMPLETE JSON manifest.

The proof keeps analytics downstream of authority:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
```

The temporary proof does not mutate Silver data or the authoritative watermark.

## Exact source used

The compatibility source was the exact incremental Silver Parquet already named by the authoritative watermark:

```text
update_id:
65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e

key:
silver/nvd/cve/schema_version=1/source_kind=incremental/update_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e/part-00000.parquet

VersionId:
f.L5xLSzp1eabl4R9VA8ebt6ReWEp9cm

SHA-256:
d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8

size_bytes:
4724916

row_count:
6749
```

Immediately before the Athena proof, the current S3 key still resolved to the authoritative VersionId and exact hash:

```text
NVD_2_3G_SYMLINK_CURRENT_VERSION=PASS
NVD_2_3G_SYMLINK_CURRENT_SHA256=PASS
NVD_2_3G_SYMLINK_CURRENT_PARQUET=PASS
```

## Temporary symlink

A single temporary symlink entry was created:

```text
s3://opslens-dev-data-487757851499-us-east-1/silver/nvd/cve/schema_version=1/source_kind=incremental/update_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e/part-00000.parquet
```

Symlink object:

```text
key:
analytics-spike/nvd/cve/symlink/update_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e/symlink.txt

VersionId:
CZvedJeGDyVFT3nvIA2uMsj3wSj4rPPQ

SHA-256:
c645ac45c5a638bf10dd7c214ecbc4c9c19f4118b381239191f5316b42915ac6
```

The target prefix was empty before creation.

## Temporary Athena table

Table:

```text
opslens_dev.nvd_cve_versions_symlink_spike_65e286bd
```

The table used:

```text
ParquetHiveSerDe
SymlinkTextInputFormat
HiveIgnoreKeyTextOutputFormat
NVD Silver v1 explicit schema
```

DDL query:

```text
QueryExecutionId:
f97d440a-c313-4492-b5dd-f4bd6bd5cfb9

State:
SUCCEEDED

DataScannedInBytes:
0

EngineExecutionTimeInMillis:
789

TotalExecutionTimeInMillis:
1465

QueryQueueTimeInMillis:
622
```

## Cardinality query

Query:

```text
QueryExecutionId:
170f046a-f349-4a09-8a03-1931923ffa43

State:
SUCCEEDED

DataScannedInBytes:
94751

EngineExecutionTimeInMillis:
982

TotalExecutionTimeInMillis:
1221

QueryQueueTimeInMillis:
130
```

PyArrow reference:

```text
row_count:
6749

distinct_cves:
6749

min_last_modified_at:
2026-08-18 09:16:47.450000+00:00

max_last_modified_at:
2026-08-25 23:17:59.860000+00:00
```

Athena result:

```text
row_count:
6749

distinct_cves:
6749

min_last_modified_at:
2026-08-18 09:16:47.450

max_last_modified_at:
2026-08-25 23:17:59.860
```

Results:

```text
NVD_2_3G_PARQUET_CARDINALITY=PASS
NVD_2_3G_ATHENA_ROW_COUNT=PASS
NVD_2_3G_ATHENA_DISTINCT_CVES=PASS
```

## Complex-type query

Deterministic PyArrow reference row:

```text
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

Athena returned the same values through nested Parquet structures.

Query:

```text
QueryExecutionId:
1ea5c7f3-1311-428c-8550-f8f3ea9b9aa9

State:
SUCCEEDED

DataScannedInBytes:
372530

EngineExecutionTimeInMillis:
892

TotalExecutionTimeInMillis:
1125

QueryQueueTimeInMillis:
101
```

Results:

```text
NVD_2_3G_COMPLEX_CVE=PASS
NVD_2_3G_COMPLEX_STATUS=PASS
NVD_2_3G_COMPLEX_CWE=PASS
NVD_2_3G_COMPLEX_CVSS_FAMILY=PASS
NVD_2_3G_COMPLEX_CVSS_VERSION=PASS
NVD_2_3G_COMPLEX_CVSS_SCORE=PASS
NVD_2_3G_PARQUET_ATHENA_CROSSCHECK_GATE=PASS
```

The proof therefore covered primitive columns, `array<string>`, and nested `array<struct<...>>` CVSS data.

## Cost boundary

The existing Athena workgroup cutoff remained unchanged at 10 MiB per query.

Measured scans:

```text
count/distinct/min/max:
94751 bytes

selected complex row:
372530 bytes
```

Both completed below the current cutoff.

Result:

```text
NVD_2_3G_SCAN_LIMIT_GATE=PASS
```

## Post-query authority check

After both analytical queries, the Silver source key was re-read and independently hashed.

Observed:

```text
before VersionId:
f.L5xLSzp1eabl4R9VA8ebt6ReWEp9cm

after VersionId:
f.L5xLSzp1eabl4R9VA8ebt6ReWEp9cm

after SHA-256:
d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8
```

Results:

```text
NVD_2_3G_SOURCE_STABILITY=PASS
NVD_2_3G_SOURCE_POST_VERSION=PASS
NVD_2_3G_SOURCE_POST_SHA256=PASS
NVD_2_3G_AUTHORITY_ONLY_GATE=PASS
```

This proves that the compatibility run happened while the key still resolved to the exact authoritative version.

It does not make a key-only symlink intrinsically version-pinned.

## Cleanup

Temporary table deletion:

```text
QueryExecutionId:
10e99822-cc33-4339-b091-64e7726c5b94

State:
SUCCEEDED
```

Glue then returned `EntityNotFoundException` for the table.

The exact temporary symlink VersionId was deleted and the prefix subsequently listed no current objects.

Result:

```text
NVD_2_3G_TEMP_TABLE_CLEANUP=PASS
NVD_2_3G_TEMP_SYMLINK_CLEANUP=PASS
```

## Compatibility result

All intended compatibility gates passed:

```text
NVD_2_3G_EXACT_SOURCE_EVIDENCE_GATE=PASS
NVD_2_3G_MIXED_PREFIX_REJECTION_GATE=PASS
NVD_2_3G_SYMLINK_PARQUET_READ_GATE=PASS
NVD_2_3G_SCHEMA_COMPATIBILITY_GATE=PASS
NVD_2_3G_COMPLEX_TYPE_GATE=PASS
NVD_2_3G_PARQUET_ATHENA_CROSSCHECK_GATE=PASS
NVD_2_3G_SCAN_LIMIT_GATE=PASS
NVD_2_3G_AUTHORITY_ONLY_GATE=PASS
```

`SymlinkTextInputFormat` is therefore technically compatible with the current NVD Silver v1 format.

## Why symlink is not selected as the permanent authority layer

The proof surfaced an important distinction:

```text
analytics addressability
    !=
exact-version authority
```

The OpsLens authority contract names an exact S3 VersionId and SHA-256. A normal S3 object read without a version ID resolves the current version. The symlink contains an S3 key URI and therefore depends on whatever version that key resolves to at query time.

The current NVD Silver writer itself is strongly append-only at the application boundary: it persists deterministic Parquet keys with `IfNoneMatch="*"`, and its runtime IAM grants `s3:PutObject` but not `s3:DeleteObject`. This reduces accidental runtime mutation, but it does not turn the Athena symlink URI into an exact-version reference.

AWS also recommends using `SymlinkTextInputFormat` only when necessary because the extra indirection adds S3 round trips.

Permanent symlink adoption is therefore rejected for this evidence-first path.

## Next candidate: immutable exact-version analytics projection

The next bounded proof will materialize the exact authorized Silver version into a clean Parquet-only analytics prefix.

Candidate flow:

```text
authoritative watermark event
    -> load exact committed watermark VersionId
    -> validate silver_complete_promotion
    -> verify exact source key + VersionId + SHA-256
    -> CopyObject from that exact source VersionId
    -> conditionally create deterministic analytics Parquet key
    -> verify CopySourceVersionId
    -> verify destination VersionId + SHA-256
    -> Athena reads clean Parquet-only analytics prefix
```

Amazon S3 supports copying a specific source object version by including `versionId` in the copy source. S3 also returns the source version copied and a destination VersionId. `CopyObject` supports `If-None-Match: *` for conditional destination creation.

This introduces deliberate Parquet duplication, but it converts exact-version authority into a clean append-only analytics object whose key can be safely addressed by a normal Athena Parquet table.

The permanent runtime is still deferred until this exact-version projection is proven against the same committed incremental evidence.

## Next boundary

```text
Phase 2.3G.2 Symlink compatibility: COMPLETE
    -> Phase 2.3G.3 exact-version projection proof
    -> permanent Glue table + projection runtime only after proof
```
