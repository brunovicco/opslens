# Phase 2.4F-2 — Cross-source Proof Coordinate Discovery

_Date: 2026-08-30_

_Status: COMPLETE_

## Purpose

Freeze the real AWS coordinates that will be used by the Phase 2.4F deterministic cross-source proof.

Discovery was performed read-only through `scripts/discover_cross_source_coordinates.py` using the human IAM Identity Center profile `opslens-bootstrap`.

No source data, Glue table, Athena workgroup, S3 object, or Terraform state was mutated.

## AWS identity

```text
account: 487757851499
region:  us-east-1
database: opslens_dev
```

## Athena workgroup

```text
name:                           opslens-dev
state:                          ENABLED
enforce_workgroup_configuration: true
engine:                         Athena engine version 3
bytes_scanned_cutoff_per_query: 10485760
encryption:                     SSE_S3
output_location:                s3://opslens-dev-data-487757851499-us-east-1/athena-results/
publish_cloudwatch_metrics:     true
```

The 10 MiB per-query cost guardrail remains unchanged.

## Explicit source coordinates

### FIRST EPSS

Latest independently discovered available snapshot:

```text
snapshot_date: 2026-08-30
prefix:        silver/epss/snapshot_date=2026-08-30/
Parquet count: 1
Parquet bytes: 5802969
```

Available snapshots discovered:

```text
2026-08-15 .. 2026-08-30
```

The proof will query EPSS with the explicit predicate:

```sql
snapshot_date = '2026-08-30'
```

### CISA KEV

Latest independently discovered available snapshot:

```text
snapshot_date: 2026-08-29
prefix:        silver/kev/snapshot_date=2026-08-29/
Parquet count: 1
Parquet bytes: 261838
```

Available snapshots discovered:

```text
2026-08-17 .. 2026-08-29
```

The proof will query KEV with the explicit predicate:

```sql
snapshot_date = '2026-08-29'
```

EPSS and KEV intentionally use different dates because those are the latest independently available snapshots at proof-discovery time. The cross-source bundle must preserve this fact rather than inventing a single global timestamp.

### NVD Bootstrap

Available permanent authoritative projection dates:

```text
2026-08-22
```

The Bootstrap scope is therefore:

```text
source_kind_partition = bootstrap
projection_date       = 2026-08-22
Parquet objects        = 1
physical bytes         = 36240684
```

### NVD Incremental

Available permanent authoritative projection dates:

```text
2026-08-26
2026-08-27
2026-08-28
2026-08-29
2026-08-30
```

Object counts by projection date:

```text
2026-08-26 -> 2
2026-08-27 -> 12
2026-08-28 -> 12
2026-08-29 -> 12
2026-08-30 -> 8
```

The Phase 2.4F proof scope uses the explicit set of all currently discovered permanent NVD projections:

```text
bootstrap:
  2026-08-22

incremental:
  2026-08-26
  2026-08-27
  2026-08-28
  2026-08-29
  2026-08-30
```

This scope is evidence inventory, not a hidden `latest CVE` rule. If more than one NVD observation exists for the selected CVE, the final bundle preserves the matching observations rather than collapsing them through `MAX(last_modified_at)`.

### GitHub Security Advisories

Authoritative Silver root:

```text
silver/ghsa/advisory_versions/schema_version=1/
```

Discovered authoritative content objects:

```text
Parquet object count: 10
```

The relation is historical exact-content evidence and remains unpartitioned in schema v1.

No GHSA `latest` version is inferred.

## Glue catalog read-back

The deployed analytical surfaces were re-read successfully:

```text
epss_scores
  columns:        7
  partition_keys: [snapshot_date]
  projection:     injected

kev_entries
  columns:        16
  partition_keys: [snapshot_date]
  projection:     injected

nvd_cve_versions
  columns:        32
  partition_keys: [source_kind_partition, projection_date]
  projection:     enum + date

ghsa_advisory_versions
  columns:        26
  partition_keys: []
  projection:     none
```

All four are `EXTERNAL_TABLE` Parquet analytical surfaces in `opslens_dev`.

## Candidate selection scope

The next gate selects a proof CVE from real GHSA evidence and measures source overlap against these exact coordinates.

Selection priority is deterministic:

```text
1. highest source overlap count across GHSA + NVD + KEV + EPSS
2. prefer a candidate with GHSA vulnerability/package evidence
3. lexical cve_id ASC tie-break
```

GHSA is the seed set because Phase 2.4F is the GHSA cross-source closeout. NVD, KEV, and EPSS presence are independently evaluated against the explicit coordinates above.

If no four-source overlap exists, the highest real overlap is accepted and the absent source is recorded rather than fabricated.

## Cost discipline

The candidate-selection query must remain below:

```text
10485760 bytes
```

The query must use explicit EPSS/KEV snapshot predicates and explicit NVD projection predicates. The workgroup cutoff must not be increased.

## Gates

```text
GHSA_CROSS_SOURCE_REAL_COORDINATES_GATE=PASS
GHSA_CROSS_SOURCE_EPSS_COORDINATE_GATE=PASS
GHSA_CROSS_SOURCE_KEV_COORDINATE_GATE=PASS
GHSA_CROSS_SOURCE_NVD_SCOPE_GATE=PASS
GHSA_CROSS_SOURCE_GHSA_INVENTORY_GATE=PASS
GHSA_CROSS_SOURCE_WORKGROUP_GUARDRAIL_GATE=PASS
GHSA_2_4F_2_GATE=PASS
```

## Next gate

```text
2.4F-3 — deterministically select one real proof CVE from the analytical data
```

The selection must be data-derived and retain Athena query identity, scan cost, and ranked overlap evidence.
