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

## Query A — partition-bounded cardinality and lineage

The first data query will aggregate each exact authority independently using partition projection and exact source-batch predicates.

Expected Bootstrap cardinality:

```text
row_count=48293
distinct_cves=48293
source_kind=bootstrap
```

Expected Incremental cardinality:

```text
row_count=331
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
```

`min(last_modified_at)` / `max(last_modified_at)` and incremental distinct-CVE cardinality must be derived first from the exact permanent Parquet files and then compared with Athena rather than guessed.

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

One deterministic observation from the exact `qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl` Parquet must be selected locally first. Athena must then return the same:

```text
observation_id
cve_id
source_kind
source_batch_id
incremental_update_id
vuln_status
last_modified_at
```

using exact partition and source-batch predicates.

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
NVD_2_3G_4J_WORKGROUP_CUTOFF=PENDING
NVD_2_3G_4J_PERMANENT_GLUE_TABLE=PENDING
NVD_2_3G_4J_LOCAL_REFERENCE=PENDING
NVD_2_3G_4J_CARDINALITY_QUERY=PENDING
NVD_2_3G_4J_CARDINALITY_EQUIVALENCE=PENDING
NVD_2_3G_4J_BOOTSTRAP_NESTED_QUERY=PENDING
NVD_2_3G_4J_BOOTSTRAP_NESTED_EQUIVALENCE=PENDING
NVD_2_3G_4J_INCREMENTAL_OBSERVATION_QUERY=PENDING
NVD_2_3G_4J_INCREMENTAL_OBSERVATION_EQUIVALENCE=PENDING
NVD_2_3G_4J_SCAN_LIMIT=PENDING
NVD_2_3G_4J=IN_PROGRESS
```

## Next boundary

After 4J is complete, Phase 2.3G.4K will close failure/replay/observability evidence for the permanent analytics path and prepare Phase 2.3G for final review/merge. 4J does not authorize GHSA ingestion or Phase 3 work.
