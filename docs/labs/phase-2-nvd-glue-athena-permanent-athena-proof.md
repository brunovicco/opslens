# Phase 2.3G.4J — Permanent NVD Athena Query / Cost / Lineage Proof

Status: **IN PROGRESS**

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

Every data query in this proof must independently complete below this unchanged 10 MiB cutoff. A query that reaches the cutoff is a failed proof; the cutoff must not be raised to make a query pass.

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

The physical object is larger than the workgroup cutoff. The earlier spike proved that bounded columnar queries can still remain below 10 MiB; 4J must re-prove that behavior against the permanent Glue table rather than the temporary spike table.

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

PyArrow derived the following exact values from the permanent projected bytes before Athena Query A was executed.

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

The proof is intentionally partition-bounded and evidence-driven:

```text
1. re-read workgroup cutoff and permanent Glue table configuration
2. establish local exact-Parquet reference values for Bootstrap and Incremental
3. run one partition-bounded cardinality/lineage query for both authorities
4. require result equivalence and record DataScannedInBytes
5. run one deterministic nested-field Bootstrap query already proven against the same exact bytes
6. require nested result equivalence and record DataScannedInBytes
7. run one deterministic Incremental observation query against the exact event-driven projected batch
8. require result equivalence and record DataScannedInBytes
9. prove every query stayed below 10,485,760 bytes
10. record QueryExecutionIds, engine/queue/total timings, and result evidence
```

Partition predicates are mandatory. Unbounded `SELECT *`, whole-table scans, and any attempt to relax the workgroup cutoff are outside this proof.

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

The query used both projected partition predicates and exact `source_batch_id` predicates for Bootstrap and Incremental.

Athena returned:

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

After UTC normalization of the Athena timestamp representation, every Query A value equals the exact PyArrow reference derived before execution.

The query scanned only:

```text
536071 / 10485760 bytes
```

which is approximately 5.1% of the workgroup cutoff and is well below the enforced guardrail despite the 36,240,684-byte Bootstrap physical object.

Formal Query A gates:

```text
NVD_2_3G_4J_CARDINALITY_QUERY=PASS
NVD_2_3G_4J_CARDINALITY_EQUIVALENCE=PASS
```

## Query B — deterministic Bootstrap nested-field equivalence

Because the permanent Bootstrap destination is byte-identical to the exact projection used in the earlier ordinary-Parquet proof, the deterministic observation remains:

```text
observation_id=b7bfa3f25e6cf5cce896e797804c39880ed6e2b72036468214b562eb19af454d
cve_id=CVE-2026-0005
vuln_status=Modified
cwe_ids=[CWE-200]
cvss_family=V31
cvss_version=3.1
cvss_base_score=6.2
```

The permanent-table query must include both partition predicates and this exact observation id. The result must equal the known exact-Parquet reference, and `DataScannedInBytes` must remain below the workgroup cutoff.

## Query C — deterministic Incremental observation equivalence

The exact local deterministic Incremental observation for this proof is now fixed as:

```text
observation_id=0010b63dd03980e09202e28f657964880be24a67ed6e9d9939e1d1c260aa01e7
cve_id=CVE-2026-79129
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
incremental_update_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
vuln_status=Undergoing Analysis
last_modified_at=2026-08-26 20:18:09.873000+00:00
```

Athena must return these exact values using both permanent projected partition predicates and the exact source-batch predicate.

## Evidence to retain per Athena query

For every executed query, retain:

```text
QueryExecutionId
State
DataScannedInBytes
EngineExecutionTimeInMillis
TotalExecutionTimeInMillis
QueryQueueTimeInMillis
Result rows
```

The query result S3 objects are ordinary Athena output artifacts and are not part of NVD source authority.

## Gate state

```text
NVD_2_3G_4J_WORKGROUP_CUTOFF=PASS
NVD_2_3G_4J_PERMANENT_GLUE_TABLE=PASS
NVD_2_3G_4J_LOCAL_REFERENCE=PASS
NVD_2_3G_4J_CARDINALITY_QUERY=PASS
NVD_2_3G_4J_CARDINALITY_EQUIVALENCE=PASS
NVD_2_3G_4J_BOOTSTRAP_NESTED_QUERY=PENDING
NVD_2_3G_4J_BOOTSTRAP_NESTED_EQUIVALENCE=PENDING
NVD_2_3G_4J_INCREMENTAL_OBSERVATION_QUERY=PENDING
NVD_2_3G_4J_INCREMENTAL_OBSERVATION_EQUIVALENCE=PENDING
NVD_2_3G_4J_SCAN_LIMIT=PENDING
NVD_2_3G_4J=IN_PROGRESS
```

## Next boundary

Complete Query B and Query C against the permanent table, then aggregate all three query scan measurements against the unchanged 10 MiB cutoff. After 4J is complete, Phase 2.3G.4K will close failure/replay/observability evidence for the permanent analytics path and prepare Phase 2.3G for final review/merge. 4J does not authorize GHSA ingestion or Phase 3 work.
