# OpsLens Architecture

## Overview

OpsLens is an open-source software supply chain intelligence platform on AWS.

The implemented architecture currently covers:

1. AWS identity and deployment foundation;
2. daily FIRST EPSS ingestion;
3. immutable Bronze evidence storage;
4. event-driven deterministic Silver transformation;
5. Parquet-based analytical storage;
6. AWS Glue cataloging;
7. Amazon Athena structured analytics;
8. runtime observability, idempotency, and failure recovery.

The platform intentionally puts deterministic evidence and structured correlation before generative reasoning.

## Implemented architecture

```text
                         CONTROL / DEPLOYMENT PLANE

Human
  |
  v
AWS IAM Identity Center
  |
  +--------------------------+
                             |
GitHub Actions               |
  |                          |
 OIDC                        |
  |                          |
  v                          v
OpsLensGitHubDeployRole   Terraform bootstrap/admin path
  |
  v
Terraform
  |
  +------------------------------------------------------+
  |                                                      |
  v                                                      v
AWS runtime infrastructure                       Analytics infrastructure


                              DATA PLANE

FIRST EPSS
    |
    v
EventBridge Scheduler
    |
    v
EPSS Ingestion Lambda
    |
    | HTTP fetch
    |
    v
FIRST current EPSS source
    |
    v
validate + parse provenance
    |
    v
conditional S3 PutObject
    |
    v
S3 Bronze
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
    |
    | s3:ObjectCreated:*
    v
EPSS Silver Lambda
    |
    +--> validate S3 event
    |
    +--> read Bronze
    |
    +--> deterministic transform
    |
    +--> Parquet serialization
    |
    +--> conditional S3 PutObject
    |
    v
S3 Silver
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
    |
    v
AWS Glue Data Catalog
opslens_dev.epss_scores
    |
    v
Amazon Athena
workgroup: opslens-dev
    |
    v
Deterministic SQL result
```

## Architectural principles

### Deterministic evidence before reasoning

Raw evidence is preserved before enrichment or interpretation.

For EPSS, the original compressed FIRST artifact is stored in Bronze.

Silver is derived deterministically from Bronze.

Athena results are independently cross-checkable against both Silver and the raw source.

### Hexagonal boundaries

The Python implementation separates:

```text
domain
  ^
  |
application
  ^
  |
ports
  ^
  |
adapters / runtime composition
```

AWS SDK, Lambda, S3, Powertools, and Parquet implementation details remain outside the core domain model where practical.

### Least privilege

Deployment and runtime responsibilities are not shared through one broad role.

The architecture currently separates:

- human bootstrap access;
- GitHub deployment access;
- ingestion runtime access;
- Silver transformation runtime access;
- analytics infrastructure management.

A general-purpose runtime Athena query identity has not been introduced.

### Idempotency

The pipeline assumes duplicate delivery can occur.

Bronze and Silver writes use conditional object creation instead of `HEAD -> PUT` sequences.

This avoids time-of-check/time-of-use races and makes retries safe.

### Observable failure

Operational boundaries emit structured telemetry.

The implemented runtime uses:

- CloudWatch Logs;
- CloudWatch Metrics;
- X-Ray;
- AWS Lambda Powertools.

Silver asynchronous failure recovery uses an SQS OnFailure destination.

## Identity and deployment

### Human bootstrap

Human administrative access uses AWS IAM Identity Center.

Primary workload Region:

```text
us-east-1
```

### GitHub Actions

GitHub Actions assumes:

```text
OpsLensGitHubDeployRole
```

through OIDC.

There are no persistent AWS access keys stored in GitHub.

The trust relationship is restricted to the repository `main` branch subject.

### Terraform

Terraform manages:

```text
infra/bootstrap/
infra/environments/dev/
```

Remote state is stored in S3.

Deployment permissions are intentionally distinct from application runtime permissions.

## EPSS ingestion

The ingestion path begins with the current FIRST EPSS dataset.

The ingestion Lambda:

1. retrieves the source artifact;
2. validates gzip and CSV structure;
3. extracts FIRST metadata;
4. calculates SHA-256 over the compressed source bytes;
5. derives `snapshot_date` from source metadata;
6. writes the raw artifact to Bronze.

Bronze key:

```text
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
```

The key is deterministic.

For a snapshot that already exists, conditional `PutObject` returns the expected idempotent `already_exists` outcome.

## Bronze storage

The data bucket currently uses:

- S3 versioning;
- SSE-S3;
- Block Public Access;
- BucketOwnerEnforced;
- noncurrent-version lifecycle cleanup;
- multipart upload cleanup.

Current Bronze and Silver evidence is not automatically expired.

Bronze is treated as canonical source evidence.

## Silver transformation

S3 emits `ObjectCreated` events only for the EPSS Bronze prefix relevant to the Silver transformation.

The Silver Lambda validates:

- event shape;
- source service;
- source bucket;
- source prefix.

It also handles S3 `s3:TestEvent` messages explicitly.

The transformation:

1. reads Bronze without refetching FIRST;
2. parses each EPSS row;
3. validates CVE identity;
4. rejects duplicate CVEs;
5. validates score ranges;
6. emits a normalized record;
7. serializes records to Parquet;
8. writes a deterministic Silver object.

Silver key:

```text
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

Silver schema:

```text
cve             string
epss            double
percentile      double
model_version   string
score_timestamp timestamp
source          string
source_sha256   string
```

Partition:

```text
snapshot_date string
```

## Parquet contract

Silver Parquet is written with a stable physical contract.

The current implementation uses:

- Parquet;
- Snappy compression;
- dictionary encoding;
- statistics;
- UTC microsecond timestamps;
- deterministic column ordering.

The source SHA-256 remains present as provenance in every Silver record.

## S3 eventing

The data bucket notification listens for:

```text
s3:ObjectCreated:*
```

with prefix:

```text
bronze/epss/
```

The Silver output prefix is different:

```text
silver/epss/
```

This prevents direct Silver-to-Silver recursion.

Because S3 event notifications use at-least-once semantics, the runtime must remain safe under duplicate delivery.

## Failure recovery

The Silver Lambda uses asynchronous invocation settings:

```text
maximum event age: 3600 seconds
retry attempts:    2
```

On exhausted retries, the invocation record is sent to:

```text
opslens-dev-epss-silver-failures
```

The runtime role can send messages to that exact queue.

It cannot:

- receive messages;
- delete messages;
- purge the queue.

The failure path was validated with an intentional invalid source event.

Observed evidence included:

- three total Lambda attempts;
- unhandled validation error;
- enriched failure destination record;
- successful SQS delivery;
- zero destination delivery failures.

## Glue Data Catalog

Silver EPSS is exposed as:

```text
database: opslens_dev
table:    epss_scores
```

The table is external and points to:

```text
s3://opslens-dev-data-487757851499-us-east-1/silver/epss/
```

The table uses partition projection for:

```text
snapshot_date
```

with projection type:

```text
injected
```

No Glue crawler or daily physical partition registration is required.

## Why injected partition projection

The current Phase 1 requirement is deterministic analysis of a known snapshot.

Injected projection requires consumers to supply the partition value explicitly.

Example:

```sql
WHERE snapshot_date = '2026-08-16'
```

Benefits for the current scope:

- no daily partition registration;
- no crawler;
- lower operational complexity;
- explicit temporal evidence;
- predictable partition pruning.

The trade-off is that consumers cannot omit the snapshot value and expect Athena to infer a "latest" partition.

Resolving "latest snapshot" belongs in a later query/service layer rather than being hidden inside the Phase 1 table contract.

## Athena

Workgroup:

```text
opslens-dev
```

The workgroup enforces:

- its own configuration;
- CloudWatch metrics;
- SSE-S3 result encryption;
- expected bucket owner;
- result location;
- 10 MiB bytes-scanned cutoff.

Query results are written under:

```text
athena-results/
```

Lifecycle:

```text
current query results:    7 days
noncurrent result versions: 1 day
```

Athena results are derived artifacts, not canonical evidence.

## Validated analytical flow

Validated snapshot:

```text
snapshot_date:   2026-08-16
source rows:     360399
model_version:   v2026.06.15
score_timestamp: 2026-08-16T12:03:43Z
```

Validated question:

> Which CVEs have EPSS greater than 0.7 for snapshot 2026-08-16?

Query:

```sql
SELECT
    cve,
    epss,
    percentile
FROM epss_scores
WHERE snapshot_date = '2026-08-16'
  AND epss > 0.7
ORDER BY epss DESC, cve;
```

Result:

```text
2457 rows
```

Execution evidence:

```text
QueryExecutionId:
cd0f145b-59e4-435f-9e42-7c836c56bbef

Engine:
Athena engine version 3

Data scanned:
6084428 bytes

Total execution:
1501 ms

Estimated query cost:
USD 0.00005000
```

The estimate reflects the validated Phase 1 pricing calculation and should not be treated as a permanent future price assertion.

## Correctness model

Phase 1 validates correctness at multiple boundaries.

### Bronze -> Silver

```text
BRONZE_TO_SILVER_DATA_GATE=PASS
```

The validated snapshot had:

```text
Bronze rows: 360399
Silver rows: 360399
```

The Silver schema, row count, null constraints, uniqueness, score ranges, source metadata, timestamp, and SHA provenance were validated.

### Athena -> Parquet

```text
ATHENA_PARQUET_CROSSCHECK_GATE=PASS
```

Athena and an independent local Parquet evaluation returned the same:

- row count;
- CVEs;
- EPSS values;
- percentiles;
- predicate result;
- ordering.

### Athena -> raw source

```text
ATHENA_BRONZE_SOURCE_CROSSCHECK_GATE=PASS
```

The Athena result was independently compared directly with the decompressed raw FIRST Bronze CSV.

Both sides returned:

```text
2457 rows
```

with matching:

- CVEs;
- EPSS values;
- percentile values.

## Current storage model

```text
S3 data bucket
|
+-- bronze/
|   |
|   +-- epss/
|       |
|       +-- snapshot_date=YYYY-MM-DD/
|           |
|           +-- epss_scores.csv.gz
|
+-- silver/
|   |
|   +-- epss/
|       |
|       +-- snapshot_date=YYYY-MM-DD/
|           |
|           +-- part-00000.parquet
|
+-- athena-results/
```

Deployment artifacts are stored in a separate artifact bucket.

## Current observability

The runtime emits structured logs and metrics at external boundaries.

Relevant evidence includes:

- Lambda invocation status;
- application processing status;
- FIRST HTTP fetch;
- S3 write outcomes;
- S3 read outcomes;
- transformation completion;
- retries;
- failure destination delivery;
- Athena scanned bytes and execution statistics.

## Current security posture

Implemented controls include:

- temporary human AWS credentials;
- OIDC-based GitHub deployment;
- branch-constrained trust;
- deployment/runtime IAM separation;
- S3 Block Public Access;
- S3 BucketOwnerEnforced;
- SSE-S3;
- versioned source evidence;
- exact-prefix runtime access where applicable;
- exact failure queue send permission;
- no unrestricted query role;
- no third-party repository code execution.

## What is intentionally not implemented yet

The current architecture does not yet include:

- CISA KEV ingestion;
- NVD/CVE ingestion;
- GitHub Security Advisory ingestion;
- historical EPSS ingestion;
- repository SBOM/dependency graph acquisition;
- vulnerability-to-package correlation;
- repository applicability evidence;
- deterministic risk policy;
- Bedrock knowledge retrieval;
- unrestricted natural-language-to-SQL;
- multi-agent architecture;
- MCP;
- A2A;
- AgentCore;
- Amazon Inspector runtime exposure.

These belong to later roadmap phases.

## Next architecture increment

Phase 2 expands the structured threat-intelligence lake.

Planned sources:

```text
CISA KEV
NVD / CVE
GitHub Security Advisories
EPSS history
```

The architecture will be evolved incrementally per source.

The Phase 1 EPSS pattern is a proven reference, not a requirement that every source use the same ingestion, update, partitioning, transformation, or failure-recovery strategy.
