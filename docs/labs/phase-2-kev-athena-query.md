# Phase 2 — CISA KEV Glue/Athena Analytical Validation

## Purpose

Validate that the deterministic CISA KEV Silver Parquet dataset is correctly
registered in AWS Glue Data Catalog and queryable through Amazon Athena with
explicit temporal evidence.

The target question is:

> Was CVE X present in the CISA KEV catalog for a specific OpsLens snapshot?

This analytical path does not use an LLM. KEV membership remains deterministic
structured evidence.

## Architecture

```text
CISA KEV
  -> S3 Bronze
  -> KEV Silver Lambda
  -> S3 Silver / Parquet
  -> AWS Glue Data Catalog
  -> Amazon Athena
```

## Analytical resources

```text
Glue database:
opslens_dev

Glue table:
kev_entries

Athena workgroup:
opslens-dev

Silver location:
s3://opslens-dev-data-487757851499-us-east-1/silver/kev/

Partition:
snapshot_date string

Partition projection:
injected
```

The table contains 16 physical Parquet columns. `snapshot_date` is derived
from the S3 partition path and is not duplicated in the Parquet payload.

## Validated snapshot

```text
snapshot_date:
2026-08-17

rows:
1665

catalog_version:
2026.08.14

source:
cisa-kev

source_sha256:
52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

## Record-count validation

Query:

```sql
SELECT count(*) AS record_count
FROM kev_entries
WHERE snapshot_date = '2026-08-17';
```

Result:

```text
1665
```

Athena execution:

```text
QueryExecutionId:
aac5bc16-8563-4194-9c46-ba97856c508d

Engine:
Athena engine version 3

DataScannedInBytes:
0

TotalExecutionTimeInMillis:
744

ResultReuse:
false
```

The zero-byte scan is recorded as observed execution evidence only. OpsLens
does not depend on `COUNT(*)` producing a zero-byte scan.

## Deterministic membership validation

The validation CVE was selected directly from the persisted Silver Parquet
artifact rather than chosen from memory:

```text
CVE-2002-0367
```

Expected evidence from Parquet:

```text
vendor_project: Microsoft
product: Windows
date_added: 2022-03-03
known_ransomware_campaign_use: Unknown
due_date: 2022-03-24
catalog_version: 2026.08.14
source: cisa-kev
source_sha256:
52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

Athena returned the same values.

Query execution:

```text
QueryExecutionId:
fb027408-aa32-4998-87f9-bf171baa61a7

DataScannedInBytes:
24911

TotalExecutionTimeInMillis:
621

ResultReuse:
false
```

This proves that KEV membership is independently reproducible from the
persisted Silver evidence and the analytical surface.

## Complex-type validation

The Silver schema stores CWE values as:

```text
array<string>
```

Query:

```sql
SELECT count(*) AS empty_cwes
FROM kev_entries
WHERE snapshot_date = '2026-08-17'
  AND cardinality(cwes) = 0;
```

Result:

```text
171
```

Execution evidence:

```text
QueryExecutionId:
9d9cc3d2-d46c-472a-827b-5549c9f4e514

DataScannedInBytes:
3002

TotalExecutionTimeInMillis:
842

ResultReuse:
false
```

## Timestamp validation

The following Silver fields were validated through Athena:

```text
catalog_date_released
retrieved_at
```

Example result:

```text
CVE-2002-0367
catalog_date_released: 2026-08-14 16:34:49.039
retrieved_at:          2026-08-17 03:52:03.692
```

Execution:

```text
QueryExecutionId:
1ca3fa01-7f96-4523-8f5b-d430d2bff913

DataScannedInBytes:
13826

TotalExecutionTimeInMillis:
945

ResultReuse:
false
```

This validates Athena compatibility with the timestamp representation produced
by the KEV Silver PyArrow writer.

## Temporal-evidence failure test

The KEV table uses injected partition projection for `snapshot_date`.

The following query intentionally omits the required snapshot:

```sql
SELECT count(*)
FROM kev_entries;
```

Athena rejected the query:

```text
State:
FAILED

Reason:
CONSTRAINT_VIOLATION: For the injected projected partition column
snapshot_date, the WHERE clause must contain only static equality conditions,
and at least one such condition must be present.

DataScannedInBytes:
0
```

Query execution:

```text
bbd85da8-af04-4906-a7e3-ca83544073e4
```

This is a deliberate architectural property:

```text
KEV query
  + no explicit temporal evidence
  -> rejected
```

OpsLens therefore does not implicitly treat an unspecified dataset version as
"latest".

## Athena scan and cost evidence

Observed successful query scans:

| Query | Data scanned | Total execution time |
| --- | ---: | ---: |
| Record count | 0 bytes | 744 ms |
| CVE membership | 24,911 bytes | 621 ms |
| Empty CWE count | 3,002 bytes | 842 ms |
| Timestamp validation | 13,826 bytes | 945 ms |

Observed total:

```text
41,739 bytes
```

All successful queries remained far below the existing workgroup per-query
scan cutoff:

```text
10,485,760 bytes
```

Athena on-demand SQL pricing must be revalidated against current AWS pricing
before using these values for future cost estimates.

At the pricing applicable during this lab, small successful queries were
subject to the Athena minimum billable scan size, yielding an approximate order
of magnitude of USD 0.00005 per query.

S3 request and query-result storage charges are separate.

## Deterministic evidence model

The analytical contract preserves the OpsLens principle:

> Agents reason. Code verifies evidence.

KEV membership is determined from persisted, typed, source-attributed data:

```text
CISA KEV source
  -> immutable Bronze evidence
  -> deterministic normalization
  -> Silver Parquet
  -> Glue schema
  -> Athena query
  -> structured evidence
```

No model decides whether a CVE is present in KEV.

## Gates

```text
KEV_GLUE_D2_EXACT_SCHEMA_GATE=PASS
KEV_GLUE_D2_PARTITION_PROJECTION_GATE=PASS
KEV_GLUE_D2_POST_APPLY_NO_DRIFT_GATE=PASS

KEV_ATHENA_D3_COUNT_GATE=PASS
KEV_ATHENA_D3_MEMBERSHIP_GATE=PASS
KEV_ATHENA_D3_ARRAY_TYPE_GATE=PASS
KEV_ATHENA_D3_TIMESTAMP_TYPE_GATE=PASS
KEV_ATHENA_D3_MISSING_SNAPSHOT_FAILURE_GATE=PASS
```

## Result

CISA KEV is now available as deterministic structured threat-intelligence
evidence through:

```text
S3 Silver Parquet
  -> AWS Glue Data Catalog
  -> Amazon Athena
```

A CVE's KEV membership can be queried for an explicit snapshot and
cross-checked against the persisted Parquet evidence without model reasoning.

Agents may later reason over this evidence, but the analytical system remains
the authority for KEV membership.
