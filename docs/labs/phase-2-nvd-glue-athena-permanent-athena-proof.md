# Phase 2.3G.4J — Permanent NVD Athena Query / Cost / Lineage Proof

Status: **COMPLETE**

## Objective

Prove that the permanent `opslens_dev.nvd_cve_versions` Glue table can query the exact-authority Bootstrap and event-driven Incremental analytics projections through ordinary Parquet while preserving the existing Athena cost guardrail and exact lineage semantics.

This proof is read-only. It does not mutate Silver, the authoritative watermark, analytics objects, Glue partitions, or the Athena workgroup.

## Permanent analytical boundary under test

```text
verified Silver / committed watermark authority
    -> exact-version permanent analytics projection
    -> projected Glue partitions
    -> bounded Athena SQL
    -> measured bytes scanned
    -> result equivalence with exact projected Parquet evidence
```

Permanent table:

```text
opslens_dev.nvd_cve_versions
```

Permanent clean root:

```text
s3://opslens-dev-data-487757851499-us-east-1/analytics/nvd/cve/schema_version=1/
```

Projected partition keys:

```text
source_kind_partition
projection_date
```

Partition projection remains:

```text
source_kind_partition -> enum(bootstrap,incremental)
projection_date       -> date(2026-01-01,NOW), yyyy-MM-dd, 1 DAY
```

The table uses the explicit 32-column NVD Silver v1 schema and ordinary Parquet input/serde configuration. No crawler or runtime Glue partition writes are involved.

## Permanent workgroup and catalog read-back — PASS

The deployed `opslens-dev` Athena workgroup was re-read before executing any 4J data query:

```text
State=ENABLED
EnforceWorkGroupConfiguration=true
BytesScannedCutoffPerQuery=10485760
OutputLocation=s3://opslens-dev-data-487757851499-us-east-1/athena-results/
Encryption=SSE_S3
```

The permanent Glue table was also re-read from AWS:

```text
Name=nvd_cve_versions
TableType=EXTERNAL_TABLE
Location=s3://opslens-dev-data-487757851499-us-east-1/analytics/nvd/cve/schema_version=1/
ColumnCount=32
PartitionKeys=[source_kind_partition,projection_date]
projection.enabled=true
projection.source_kind_partition.values=bootstrap,incremental
projection.projection_date.range=2026-01-01,NOW
storage.location.template=s3://opslens-dev-data-487757851499-us-east-1/analytics/nvd/cve/schema_version=1/source_kind=${source_kind_partition}/projection_date=${projection_date}/
```

This establishes the exact permanent analytical surface under test and confirms that the cost guardrail remained unchanged.

## Cost boundary

The permanent workgroup remains:

```text
opslens-dev
```

with enforced configuration and:

```text
bytes_scanned_cutoff_per_query=10485760
```

Every data query in this proof must independently complete below this unchanged 10 MiB cutoff. The cutoff was not relaxed for any query.

## Exact permanent evidence under test

### Bootstrap projection

```text
source_kind_partition=bootstrap
projection_date=2026-08-22
source_batch_id=feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68
row_count=48293
analytics VersionId=NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba
SHA-256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
physical_bytes=36240684
authority_state=bootstrap_verified_seed
```

The physical Bootstrap object is larger than the workgroup cutoff, so 4J specifically proves that partition-bounded and column-bounded Parquet queries stay within the existing analytical guardrail without changing source authority.

### Incremental projection

```text
source_kind_partition=incremental
projection_date=2026-08-26
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
row_count=331
analytics VersionId=qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
SHA-256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
physical_bytes=205462
authority_state=watermark_committed
```

The exact local files were re-hashed immediately before deriving reference values:

```text
Bootstrap SHA-256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
Incremental SHA-256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
```

## Exact local Parquet reference — PASS

PyArrow derived the following exact values from the permanent projected bytes before Athena execution.

Bootstrap:

```text
row_count=48293
distinct_cves=48293
min_last_modified_at=2026-01-03 04:15:50.813000+00:00
max_last_modified_at=2026-08-22 06:16:17.510000+00:00
source_kind=bootstrap
source_batch_id=feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68
```

Incremental:

```text
row_count=331
distinct_cves=331
min_last_modified_at=2026-08-26 19:25:08.083000+00:00
max_last_modified_at=2026-08-26 21:16:41.873000+00:00
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
```

The deterministic Incremental sample selected locally by minimum `observation_id` is:

```text
observation_id=0010b63dd03980e09202e28f657964880be24a67ed6e9d9939e1d1c260aa01e7
cve_id=CVE-2026-79129
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
incremental_update_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
vuln_status=Undergoing Analysis
last_modified_at=2026-08-26 20:18:09.873000+00:00
```

## Proof strategy

The proof remained partition-bounded and evidence-driven:

```text
1. re-read workgroup cutoff and permanent Glue table configuration
2. establish local exact-Parquet reference values for Bootstrap and Incremental
3. run a partition-bounded cardinality/lineage query for both authorities
4. require result equivalence and record DataScannedInBytes
5. run a deterministic nested-field Bootstrap query
6. diagnose nested cardinality rather than masking it with DISTINCT
7. require exact nested metric equivalence including source/type semantics
8. run a deterministic Incremental observation query
9. prove every executed query stayed below 10,485,760 bytes
10. retain QueryExecutionIds, timings, scan measurements, and result evidence
```

Partition predicates were mandatory. No unbounded `SELECT *`, whole-table scan, or cutoff relaxation was used.

## Query A — partition-bounded cardinality and lineage — PASS

QueryExecutionId:

```text
34cafd33-2c29-4de2-a557-a61105db08e6
```

Execution evidence:

```text
State=SUCCEEDED
DataScannedInBytes=536071
EngineExecutionTimeInMillis=1208
TotalExecutionTimeInMillis=1373
QueryQueueTimeInMillis=97
```

Athena returned exact Bootstrap and Incremental cardinality/lineage values:

```text
incremental
row_count=331
distinct_cves=331
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
min_last_modified_at=2026-08-26 19:25:08.083
max_last_modified_at=2026-08-26 21:16:41.873

bootstrap
row_count=48293
distinct_cves=48293
source_kind=bootstrap
source_batch_id=feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68
min_last_modified_at=2026-01-03 04:15:50.813
max_last_modified_at=2026-08-22 06:16:17.510
```

After UTC normalization of Athena timestamp formatting, every value equals the exact PyArrow reference.

Formal Query A gates:

```text
NVD_2_3G_4J_CARDINALITY_QUERY=PASS
NVD_2_3G_4J_CARDINALITY_EQUIVALENCE=PASS
```

## Query B — deterministic Bootstrap nested-field equivalence — PASS

Initial Query B:

```text
QueryExecutionId=090e5eb0-eb74-4eeb-a950-d76683005c09
State=SUCCEEDED
DataScannedInBytes=3928022
EngineExecutionTimeInMillis=1049
TotalExecutionTimeInMillis=1196
QueryQueueTimeInMillis=58
```

The deterministic Bootstrap observation was:

```text
observation_id=b7bfa3f25e6cf5cce896e797804c39880ed6e2b72036468214b562eb19af454d
cve_id=CVE-2026-0005
vuln_status=Modified
cwe_ids=[CWE-200]
cvss_family=V31
cvss_version=3.1
cvss_base_score=6.2
```

The first query returned two rows that appeared identical because its projection omitted the distinguishing CVSS metric fields. The proof did not use `DISTINCT` to hide this cardinality. Instead, the exact Bootstrap Parquet bytes were inspected directly.

PyArrow proved that the observation contains exactly two legitimate V31/3.1 metrics with equal numerical/vector values but different provenance semantics:

```text
metric 1
family=V31
version=3.1
source=nvd@nist.gov
type=Primary
vector_string=CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
base_score=6.2
base_severity=MEDIUM
exploitability_score=2.5
impact_score=3.6

metric 2
family=V31
version=3.1
source=134c704f-9b21-4f2e-91b3-4a467353bcc0
type=Secondary
vector_string=CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
base_score=6.2
base_severity=MEDIUM
exploitability_score=2.5
impact_score=3.6
```

A diagnostic exact-projection Query B2 then exposed `source`, `type`, `vector_string`, severity, exploitability, and impact fields instead of collapsing the two metrics conceptually.

Query B2:

```text
QueryExecutionId=f15eae38-9bfa-4dab-8f46-ad77c6db5a5b
State=SUCCEEDED
DataScannedInBytes=3928022
EngineExecutionTimeInMillis=1377
TotalExecutionTimeInMillis=1677
QueryQueueTimeInMillis=171
```

Athena returned exactly two rows:

```text
Secondary metric
source=134c704f-9b21-4f2e-91b3-4a467353bcc0
type=Secondary
family=V31
version=3.1
vector_string=CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
base_score=6.2
base_severity=MEDIUM
exploitability_score=2.5
impact_score=3.6

Primary metric
source=nvd@nist.gov
type=Primary
family=V31
version=3.1
vector_string=CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
base_score=6.2
base_severity=MEDIUM
exploitability_score=2.5
impact_score=3.6
```

This matches the exact PyArrow cardinality and field values. The apparent duplicate in the original Query B is therefore valid source semantics, not accidental duplication in the permanent analytics projection.

Formal Bootstrap nested gates:

```text
NVD_2_3G_4J_BOOTSTRAP_NESTED_QUERY=PASS
NVD_2_3G_4J_BOOTSTRAP_NESTED_EQUIVALENCE=PASS
```

## Query C — deterministic Incremental observation equivalence — PASS

QueryExecutionId:

```text
2fb0c702-cafe-4920-b28b-10f60ceb55f3
```

Execution evidence:

```text
State=SUCCEEDED
DataScannedInBytes=43880
EngineExecutionTimeInMillis=560
TotalExecutionTimeInMillis=831
QueryQueueTimeInMillis=99
```

Athena returned:

```text
observation_id=0010b63dd03980e09202e28f657964880be24a67ed6e9d9939e1d1c260aa01e7
cve_id=CVE-2026-79129
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
incremental_update_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
vuln_status=Undergoing Analysis
last_modified_at=2026-08-26 20:18:09.873
```

After timestamp normalization, every value equals the exact local Parquet reference.

Formal Incremental observation gates:

```text
NVD_2_3G_4J_INCREMENTAL_OBSERVATION_QUERY=PASS
NVD_2_3G_4J_INCREMENTAL_OBSERVATION_EQUIVALENCE=PASS
```

## Scan-limit aggregation — PASS

Every data query executed as part of the permanent proof stayed below the unchanged 10 MiB workgroup cutoff:

```text
Query A:  536071  / 10485760 bytes = PASS
Query B:  3928022 / 10485760 bytes = PASS
Query B2: 3928022 / 10485760 bytes = PASS
Query C:  43880   / 10485760 bytes = PASS
```

The largest query consumed approximately 37.5% of the enforced cutoff. The 36,240,684-byte Bootstrap physical Parquet object therefore remained queryable through bounded columnar access without increasing the workgroup limit.

Formal cost gate:

```text
NVD_2_3G_4J_SCAN_LIMIT=PASS
```

## Lineage conclusion

The permanent analytical path preserves the intended authority chain:

```text
Bootstrap verified seed
    -> exact-version Silver Parquet
    -> exact-version analytics projection
    -> projected Glue partition
    -> bounded Athena result

Incremental committed watermark
    -> exact-version Silver Parquet
    -> exact-version analytics projection
    -> projected Glue partition
    -> bounded Athena result
```

Athena is a downstream analytical surface only. Query result objects under `athena-results/` do not become NVD source authority and do not alter the authoritative watermark, Silver evidence, or analytics projection metadata.

## Final gate state

```text
NVD_2_3G_4J_WORKGROUP_CUTOFF=PASS
NVD_2_3G_4J_PERMANENT_GLUE_TABLE=PASS
NVD_2_3G_4J_LOCAL_REFERENCE=PASS
NVD_2_3G_4J_CARDINALITY_QUERY=PASS
NVD_2_3G_4J_CARDINALITY_EQUIVALENCE=PASS
NVD_2_3G_4J_BOOTSTRAP_NESTED_QUERY=PASS
NVD_2_3G_4J_BOOTSTRAP_NESTED_EQUIVALENCE=PASS
NVD_2_3G_4J_INCREMENTAL_OBSERVATION_QUERY=PASS
NVD_2_3G_4J_INCREMENTAL_OBSERVATION_EQUIVALENCE=PASS
NVD_2_3G_4J_SCAN_LIMIT=PASS
NVD_2_3G_4J=COMPLETE
```

## Next boundary

Phase 2.3G.4K may now close failure, replay, and observability evidence for the permanent analytics path and prepare Phase 2.3G for final review/merge.

4J does not authorize GHSA ingestion or Phase 3 work.
