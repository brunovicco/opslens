# Phase 2.4E — GHSA Glue / Athena Analytics Closeout

_Date completed: 2026-08-30_

_Status: COMPLETE_

## Outcome

Phase 2.4E is complete.

OpsLens now exposes the authoritative GHSA advisory-content Silver relation through an explicit AWS Glue external table and bounded Amazon Athena queries without introducing a second analytics projector, crawler, runtime partition writer, or duplicated Parquet namespace.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

The analytical relation is historical exact-content evidence. It does not fabricate a current/latest advisory state and it does not evaluate whether an installed package version satisfies a vulnerable version range.

## Permanent analytical boundary

```text
GitHub Global Security Advisories REST API
        |
        v
GHSA Bronze Lambda
        |
        v
versioned Bronze pages + COMPLETE
        |
        v
GHSA Silver Lambda
        |
        v
immutable one-row Parquet content objects
silver/ghsa/advisory_versions/schema_version=1/
        |
        v
AWS Glue Data Catalog
opslens_dev.ghsa_advisory_versions
        |
        v
Amazon Athena
workgroup: opslens-dev
```

Silver remains authoritative. Glue is metadata only. Athena is read-only analytics over the exact Silver bytes.

## Why no GHSA analytics projector

The authoritative GHSA content root contains only schema-compatible Parquet objects. Attempt COMPLETE JSON is isolated under `silver/ghsa/completions/`.

Unlike NVD, GHSA currently has no post-Silver authoritative watermark/promotion boundary. Therefore copying the same Parquet bytes into another analytics namespace would add operational state without resolving an authority problem.

Selected design:

```text
Silver authority == analytical source bytes
```

## Glue table

Permanent table:

```text
Database: opslens_dev
Table:    ghsa_advisory_versions
Type:     EXTERNAL_TABLE
Format:   Parquet / SNAPPY
Columns:  26
Location: s3://opslens-dev-data-487757851499-us-east-1/silver/ghsa/advisory_versions/schema_version=1/
```

The table has:

```text
0 Glue partition keys
0 partition projection properties
0 crawlers
0 runtime Glue partition writes
```

The application-owned Arrow/Parquet v1 schema is mapped explicitly in Terraform.

## Deployment IAM proof

The GitHub deployment policy was extended only for the exact GHSA table ARN:

```text
arn:aws:glue:us-east-1:487757851499:table/opslens_dev/ghsa_advisory_versions
```

The live Bootstrap Terraform plan showed:

```text
aws_iam_policy.github_actions_analytics will be updated in-place
Plan: 0 to add, 1 to change, 0 to destroy.
```

The exact saved plan applied cleanly:

```text
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

No deployment role, attachment, Athena workgroup, or unrelated resource was replaced.

## Glue live deployment proof

The dev Terraform plan showed only:

```text
aws_glue_catalog_table.ghsa_advisory_versions will be created
Plan: 1 to add, 0 to change, 0 to destroy.
```

The exact saved plan applied cleanly:

```text
aws_glue_catalog_table.ghsa_advisory_versions: Creation complete
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.
```

Live resource identity:

```text
487757851499:opslens_dev:ghsa_advisory_versions
```

## Athena proof A — identity and cardinality

Query execution:

```text
QueryExecutionId: fd155926-240e-4449-90da-50b026256e64
State:            SUCCEEDED
Database:         opslens_dev
Catalog:          awsdatacatalog
WorkGroup:        opslens-dev
Engine:           Athena engine version 3
```

Observed result:

```text
row_count:                     10
unique_content_versions:       10
unique_ghsa_ids:               10
rows_with_cve:                  9
vulnerability_entry_count:     18
```

Execution evidence:

```text
DataScannedInBytes:             6035
EngineExecutionTimeInMillis:     515
QueryPlanningTimeInMillis:        81
TotalExecutionTimeInMillis:      657
```

This proves the ten authoritative Silver content identities are visible exactly once through Athena.

## Athena proof B — nested schema and CVSS semantics

Query execution:

```text
QueryExecutionId: 43c7b74f-004d-4189-9e05-7b7ca92cc9b9
State:            SUCCEEDED
Database:         opslens_dev
Catalog:          awsdatacatalog
WorkGroup:        opslens-dev
Engine:           Athena engine version 3
```

Observed result:

```text
advisory_rows:                       10
identifier_rows:                     19
valid_identifier_rows:               19
cwe_rows:                            13
valid_cwe_rows:                      13
vulnerability_rows:                  18
valid_vulnerability_rows:            18
typed_cvss_rows:                     10
valid_typed_cvss_rows:               10
raw_cvss_v4_unavailable_rows:         7
unavailable_without_typed_v4:         7
cvss_v4_normalization_violations:     0
```

Execution evidence:

```text
DataScannedInBytes:            72077
EngineExecutionTimeInMillis:     837
QueryPlanningTimeInMillis:       332
TotalExecutionTimeInMillis:     1111
```

The query exercised `array<struct<...>>` values through Athena `UNNEST` and proved that all deserialized identifiers, CWEs, vulnerability entries, and typed CVSS metrics satisfy their required structural fields.

## Real CVSS placeholder proof through Athena

The earlier real GHSA transformation discovered GitHub advisories where a known `cvss_v4` family existed as an unavailable placeholder rather than a usable vector/score pair.

The permanent analytics path now independently reproduced that semantic boundary:

```text
raw CVSS v4 unavailable placeholders: 7
placeholders without typed v4 metric:  7
normalization violations:              0
```

Therefore:

```text
raw additive/unavailable source evidence is preserved
AND
unavailable CVSS evidence does not become a fabricated typed metric
```

Malformed known-family structures remain fail-closed in the transformation runtime.

## Cost boundary

The existing Athena development workgroup remains unchanged:

```text
bytes_scanned_cutoff_per_query = 10,485,760 bytes
```

Observed GHSA scans:

| Proof | Data scanned | Percent of 10 MiB cutoff |
| --- | ---: | ---: |
| Identity/cardinality | 6,035 bytes | ~0.06% |
| Nested/CVSS semantics | 72,077 bytes | ~0.69% |

No cutoff increase was required.

The one-row-Parquet/high-cardinality-directory shape may create planning/listing overhead at larger scale. Phase 2.4E deliberately records this as observable technical debt rather than introducing speculative compaction infrastructure.

## Historical relation semantics

`opslens_dev.ghsa_advisory_versions` represents exact observed advisory content versions.

It is not an authoritative `current` or `latest` advisory relation.

Phase 2.4E does not authorize selecting current state with only:

```sql
MAX(updated_at)
```

because source timestamps are evidence fields, not a complete observation-order authority contract.

## Phase 3 boundary preserved

Athena can expose deterministic source evidence including:

```text
CVE alias
package ecosystem
package name
vulnerable version range
first patched version
CVSS observations
withdrawal state
```

Phase 2.4E does not decide:

```text
installed version X is vulnerable
installed version X is fixed
repository dependency Y is exploitable
```

Concrete version-range evaluation remains Phase 3 deterministic correlation work.

## Gates

```text
GHSA_ANALYTICS_AUTHORITY_SOURCE_GATE=PASS
GHSA_ANALYTICS_NO_PROJECTOR_GATE=PASS
GHSA_ANALYTICS_EXPLICIT_SCHEMA_GATE=PASS
GHSA_ANALYTICS_NO_CURRENT_STATE_INFERENCE_GATE=PASS
GHSA_2_4E_1_GATE=PASS

GHSA_ANALYTICS_GLUE_SCHEMA_STATIC_GATE=PASS
GHSA_ANALYTICS_NO_PARTITION_GATE=PASS
GHSA_ANALYTICS_DEPLOYMENT_IAM_STATIC_GATE=PASS
GHSA_2_4E_3_GATE=PASS

GHSA_ANALYTICS_BOOTSTRAP_LIVE_PLAN_GATE=PASS
GHSA_ANALYTICS_BOOTSTRAP_LIVE_APPLY_GATE=PASS
GHSA_ANALYTICS_DEV_LIVE_PLAN_GATE=PASS
GHSA_ANALYTICS_SCHEMA_LIVE_PLAN_GATE=PASS
GHSA_ANALYTICS_NO_PARTITION_LIVE_PLAN_GATE=PASS
GHSA_ANALYTICS_DEV_LIVE_APPLY_GATE=PASS

GHSA_ANALYTICS_ATHENA_BASE_QUERY_GATE=PASS
GHSA_ANALYTICS_ATHENA_IDENTITY_GATE=PASS
GHSA_ANALYTICS_ATHENA_COST_GATE=PASS
GHSA_ANALYTICS_COMPLEX_TYPES_GATE=PASS
GHSA_ANALYTICS_CVSS_SEMANTIC_GATE=PASS
GHSA_2_4E_GATE=PASS
```

## Handoff

Phase 2.4E is closed.

Next authorized GHSA milestone:

```text
Phase 2.4F — cross-source deterministic evidence / GHSA closeout
```

Phase 2 remains open. Phase 3 must not begin until the remaining Phase 2 gates are complete or explicitly deferred, including Phase 2.4F and the planned historical EPSS work.

## References

- `docs/labs/phase-2-ghsa-glue-athena-design.md`
- `docs/labs/phase-2-ghsa-silver-runtime-closeout.md`
- `src/opslens/transformation/ghsa/serialization/schema.py`
- `infra/environments/dev/analytics_ghsa_glue.tf`
- `infra/bootstrap/github_analytics_permissions.tf`
