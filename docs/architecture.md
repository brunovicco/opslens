# OpsLens Architecture

🇺🇸 **English** | 🇧🇷 [Português](architecture.pt-br.md)

_Last updated: 2026-08-30_

## Overview

OpsLens is an open-source software supply chain intelligence platform on AWS.

The implemented architecture currently covers:

- AWS identity and deployment foundation;
- FIRST EPSS Bronze, deterministic Silver, Glue, and Athena;
- CISA KEV Bronze, deterministic Silver, Glue, and Athena;
- NVD CVE yearly Bootstrap Bronze;
- NVD CVE API 2.0 incremental Bronze;
- NVD versioned Silver;
- NVD authoritative watermark promotion;
- permanent NVD analytics projection;
- NVD Glue Data Catalog and Athena analytics;
- GHSA reviewed-advisory Bronze ingestion with exact versioned COMPLETE evidence;
- GHSA immutable advisory-version Silver content objects and attempt-level COMPLETE provenance;
- explicit GHSA Glue catalog over authoritative Silver and bounded Athena nested-evidence analytics;
- exact S3 object-version evidence verification;
- idempotent conditional persistence;
- bounded asynchronous retries and SQS OnFailure recovery;
- CloudWatch, metrics, and X-Ray observability;
- Terraform-managed infrastructure with explicit cost controls.

The project intentionally puts deterministic evidence and structured correlation before generative reasoning.

The core invariant is:

> **Agents reason. Code verifies evidence.**

---

## Architectural principles

- Raw evidence is preserved before enrichment or interpretation.
- Deterministic facts remain authoritative; models may explain them but do not establish them.
- Exact S3 object versions participate in the evidence model.
- AWS SDK and runtime details remain outside the core domain model where practical.
- Human bootstrap, GitHub deployment, ingestion, transformation, scheduling, promotion, and analytics use separate IAM boundaries.
- Duplicate delivery is expected and must be safe.
- Operational boundaries emit structured logs, metrics, and traces.
- Repository risk and runtime exposure are separate concepts.
- AWS services are introduced only when they solve a demonstrated requirement.
- Cost and observability are architectural requirements, not afterthoughts.
- Third-party repository code is data to inspect, never code to execute.
- Natural-language planning never receives unrestricted SQL authority.

---

## AWS foundation

### Human administration

```text
AWS IAM Identity Center
    |
    v
temporary human credentials
    |
    v
opslens-bootstrap profile
```

### GitHub deployment

```text
GitHub Actions
    |
    v
OIDC
    |
    v
AWS STS
    |
    v
OpsLensGitHubDeployRole
```

No persistent AWS access keys are stored in GitHub.

The deployment identity is separate from all workload runtime identities.

### Terraform

```text
infra/
    bootstrap/
    environments/
        dev/
```

Only one real environment currently exists:

```text
dev
```

Terraform state is remote in Amazon S3. The project intentionally avoids fictional staging or production environments created only for portfolio appearance.

---

## Implemented data plane

### FIRST EPSS

```text
FIRST EPSS
    |
    v
EventBridge Scheduler
    |
    v
EPSS Ingestion Lambda
    |
    v
S3 Bronze
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
    |
    v
S3 ObjectCreated
    |
    v
EPSS Silver Lambda
    |
    v
S3 Silver / Parquet
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
    |
    v
AWS Glue Data Catalog
opslens_dev.epss_scores
    |
    v
Amazon Athena
```

EPSS preserves the original compressed FIRST artifact, SHA-256 provenance, S3 versioning, deterministic Silver transformation, and temporal analytics through `snapshot_date`.

### CISA KEV

```text
CISA KEV JSON
    |
    v
EventBridge Scheduler
opslens-dev-kev-daily
    |
    v
KEV Ingestion Lambda
    |
    +--> bounded HTTP fetch
    +--> source contract validation
    +--> SHA-256 provenance
    +--> conditional S3 PutObject
    |
    v
S3 Bronze
bronze/kev/snapshot_date=YYYY-MM-DD/known_exploited_vulnerabilities.json
    |
    v
S3 ObjectCreated:Put
    |
    v
KEV Silver Lambda
    |
    +--> exact VersionId read
    +--> event/S3 evidence verification
    +--> deterministic normalization
    +--> typed Arrow schema
    +--> Parquet serialization
    +--> conditional Silver PutObject
    |
    v
S3 Silver / Parquet
silver/kev/snapshot_date=YYYY-MM-DD/part-00000.parquet
    |
    v
AWS Glue Data Catalog
opslens_dev.kev_entries
    |
    v
Amazon Athena
opslens-dev
```

The KEV Silver runtime fails closed on transport or provenance mismatch and uses bounded Lambda retries with a dedicated SQS OnFailure destination.

### NVD CVE

```text
NVD yearly feeds                  NVD CVE API 2.0
       |                                  |
       v                                  v
Bootstrap ingestion                Incremental ingestion
       |                                  |
       +-------------> S3 Bronze <--------+
                       immutable evidence
                              |
                              v
                     NVD Silver runtime
                              |
                              v
                versioned Silver / Parquet
                              |
                              v
                  Silver COMPLETE evidence
                              |
                              v
                 promotion verification
                              |
                              v
               authoritative watermark
                              |
                              v
            NVD Analytics Projector Lambda
                              |
                              v
              clean analytics namespace
                              |
                              v
                   AWS Glue Data Catalog
                 opslens_dev.nvd_cve_versions
                              |
                              v
                       Amazon Athena
```

The NVD path deliberately separates source preservation, transformation completion, authority commitment, and analytical availability.

The authority invariant is:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

A Bronze-complete window cannot become authoritative until deterministic Silver evidence is complete and exact promotion checks pass. Analytics remains downstream-only and cannot mutate upstream authority.

---

## NVD Bronze

### Bootstrap yearly feeds

Canonical layout:

```text
bronze/nvd/cve/bootstrap/
    feed_year=YYYY/
        feed_revision=<source-revision>/
            nvdcve-2.0-YYYY.json.gz
            nvdcve-2.0-YYYY.meta
            manifest.json
```

The feed revision combines the normalized NVD source modification timestamp with the source SHA-256.

The runtime validates:

- bounded META retrieval;
- META contract;
- bounded gzip retrieval;
- compressed and uncompressed size;
- gzip decoding;
- source SHA-256;
- deterministic feed revision;
- exact persisted object VersionIds.

Persistence uses conditional S3 object creation. `412 PreconditionFailed` is treated only as a possible duplicate and succeeds after the existing object evidence is verified.

### Incremental CVE API 2.0

The incremental runtime advances through closed last-modified windows and preserves every exact API page.

The implemented identity model separates the logical synchronization window from the exact physical source observation:

```text
update_id
    logical incremental-window identity

attempt_id
    exact physical source-observation identity
```

Canonical layout:

```text
bronze/nvd/cve/updates/
    update_id=<logical-window-identity>/
        attempt_id=<exact-physical-observation>/
            page_start=000000/
                response.json
            page_start=000500/
                response.json
            ...
        manifest.json
```

This distinction protects replay semantics when the NVD API returns different exact bytes or response metadata for the same logical window.

The incremental contract validates:

- bounded HTTP responses;
- polite pacing;
- bounded retries for transient source failures;
- stable `totalResults`;
- contiguous pagination;
- terminal coverage;
- duplicate-CVE rejection;
- exact response bytes and SHA-256;
- exact persisted S3 VersionIds.

Bronze COMPLETE is written only after all pages have been created or exactly verified.

Bronze completion does not advance the authoritative watermark.

---

## NVD versioned Silver

The Silver contract separates three identities:

```text
cve_id
    vulnerability identity

observed_cve_version_id
    exact source-CVE content identity

observation_id
    exact immutable Bronze occurrence identity
```

The entire original NVD CVE object participates in deterministic content identity, allowing historical modifications, rejection, and unrejection to create new observed versions instead of overwriting history.

Silver v1 preserves:

- core CVE fields;
- localized descriptions and CVE tags;
- CWE / weakness evidence;
- references;
- supported CVSS v2, v3.0, v3.1, and v4 observations;
- canonical metric JSON;
- canonical CPE configuration trees;
- exact versioned Bronze provenance.

Known malformed metric or configuration structures fail closed. Unknown future metric families are not silently interpreted; immutable Bronze remains the source evidence.

Physical contract:

```text
dataset:           nvd_cve_versions
schema_version:    1
Parquet format:    1.0
data page version: 1.0
compression:       snappy
row group size:    5000
```

Silver COMPLETE binds the logical normalized record set to deterministic Parquet bytes, SHA-256, size, row count, and exact S3 VersionId.

For incremental batches:

```text
Silver row_count == verified Bronze total_results
```

A valid zero-result incremental window is supported.

---

## NVD authoritative watermark

The authoritative watermark represents the last committed incremental boundary.

Promotion is allowed only after exact evidence proves:

```text
Bronze COMPLETE
    -> exact Silver COMPLETE
    -> exact Silver Parquet VersionId + SHA-256
    -> logical record-set identity
    -> strictly advancing committed boundary
```

The promotion basis uses `kind = silver_complete_promotion` and binds the authoritative watermark to the exact Silver manifest and Parquet evidence.

This prevents Bronze success from being confused with transformation success and prevents transformation success from being confused with committed authority.

---

## Permanent NVD analytics projection

The permanent analytics path is intentionally a projection of committed authority, not a new authority source.

Incremental path:

```text
exact S3 watermark ObjectCreated VersionId
    -> strict canonical watermark validation
    -> exact Silver COMPLETE evidence
    -> exact Silver Parquet VersionId + SHA-256
    -> conditional CopyObject from exact source VersionId
    -> deterministic analytics destination
    -> exact destination verification
```

Bootstrap uses an explicit exact `bootstrap_seed` invocation rather than pretending a Bootstrap feed has an incremental watermark.

Permanent namespace:

```text
analytics/nvd/cve/schema_version=1/
    source_kind=<bootstrap|incremental>/
        projection_date=YYYY-MM-DD/
            <deterministic-batch-file>.parquet
```

Replay behavior:

```text
conditional CopyObject
If-None-Match: *
        |
        +--> created
        |
        +--> 412 existing destination
                |
                v
          exact current-object verification
                |
                +--> exact match -> already_projected
                +--> mismatch    -> fail closed
```

The projector verifies destination VersionId, byte size, content type, full metadata, SHA-256, and Parquet `PAR1` signature.

Runtime IAM intentionally excludes:

```text
s3:ListBucket
s3:DeleteObject
watermark PutObject
Silver mutation
Glue partition mutation
```

---

## NVD Glue and Athena

Permanent table:

```text
Database: opslens_dev
Table:    nvd_cve_versions
Type:     EXTERNAL_TABLE
Columns:  32 Silver v1 columns
```

Root location:

```text
s3://<data-bucket>/analytics/nvd/cve/schema_version=1/
```

Partition projection:

```text
source_kind_partition -> bootstrap,incremental
projection_date       -> 2026-01-01,NOW
```

No crawler and no runtime Glue partition writes are required.

The development Athena workgroup enforces:

```text
bytes-scanned cutoff: 10,485,760 bytes
result encryption:    SSE_S3
```

Validated permanent NVD queries:

| Query | Purpose | Data scanned |
| --- | --- | ---: |
| A | Bootstrap + Incremental cardinality / lineage | 536,071 bytes |
| B | Bootstrap nested CVSS sample | 3,928,022 bytes |
| B2 | Exact CVSS source/type equivalence | 3,928,022 bytes |
| C | Deterministic Incremental observation | 43,880 bytes |

All remained below the 10 MiB cutoff and reproduced exact local Parquet evidence.

---

## Validated NVD evidence

### Bootstrap permanent projection

```text
rows:                  48293
destination VersionId: NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba
SHA-256:               4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
replay:                already_projected
version after replay:  unchanged
```

### Incremental permanent projection

```text
watermark VersionId:   q9Zwn_4jdUZei_jqP6fytSy1aabtus7h
committed_through_at:  2026-08-26T21:25:00Z
update_id:             fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
rows:                  331
destination VersionId: qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
SHA-256:               3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
```

The event-driven invocation was correlated through CloudWatch by the exact watermark VersionId, update identity, destination VersionId, and request/trace context.

---

## GitHub Security Advisories

The implemented GHSA path now covers deterministic reviewed-advisory Bronze and immutable advisory-version Silver evidence.

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
  exact manifest/page VersionId reads
  attempt_id recomputation
  deterministic normalization
        |
        v
one immutable one-row Parquet object
per observed_advisory_version_id
        |
        v
Silver COMPLETE manifest
        |
        v
AWS Glue Data Catalog
opslens_dev.ghsa_advisory_versions
        |
        v
Amazon Athena
```

The content identity and physical-observation boundaries remain separate:

```text
observed_advisory_version_id -> exact advisory source content
sync_id                      -> logical source window
attempt_id                   -> exact physical Bronze observation
attempt_occurrence_id        -> exact source position inside that attempt
```

Silver content objects use create-only persistence and exact replay verification. The COMPLETE manifest is published only after every content object has been created or exactly verified. A real 10-advisory proof produced ten one-row Parquet objects and one COMPLETE manifest; replay preserved the same eleven S3 versions and created zero new versions.

The live workload also proved that GitHub may expose a known CVSS family as an unavailable placeholder. Such placeholders remain in canonical source JSON but do not create fabricated typed metrics. Malformed known-family structures still fail closed.

Phase 2.4E exposes the authoritative Silver relation directly as `opslens_dev.ghsa_advisory_versions`, with no projector, crawler, or Glue partitions. Real Athena proofs returned 10 unique content versions, 18 vulnerability entries, structurally valid nested identifiers/CWEs/CVSS/package evidence, seven unavailable CVSS v4 placeholders with zero fabricated typed metrics, and scans of 6,035 and 72,077 bytes under the unchanged 10 MiB cutoff. Package/version applicability remains deterministic Phase 3 work.

---

## Failure recovery

The platform treats scheduler delivery, Lambda asynchronous processing, evidence validation, and SQS recovery as separate failure boundaries.

Relevant runtime patterns include:

- bounded event age;
- two Lambda asynchronous retries;
- source-specific SQS OnFailure destinations;
- fail-closed parser and evidence validation;
- structured failure telemetry;
- replay-safe deterministic destinations.

The NVD analytics closeout validated:

```text
invalid async invocation accepted: StatusCode 202
condition:                         RetriesExhausted
approximateInvokeCount:            3
functionError:                     Unhandled
errorType:                         InvalidNvdAnalyticsProjectionInvocationError
failure queue after cleanup:       0 / 0 / 0
```

The invalid event never crossed into projection execution.

---

## Observability

The runtime uses:

- AWS Lambda Powertools Logger, Metrics, and Tracer;
- structured CloudWatch Logs;
- AWS Lambda platform metrics;
- EventBridge Scheduler metrics;
- AWS X-Ray.

For permanent NVD analytics, trigger evidence and completion evidence share the Lambda `request_id` and X-Ray context so an exact watermark event can be reconstructed through its projection result.

---

## Security boundaries

```text
Human administration
    |
    v
AWS IAM Identity Center

GitHub Actions
    |
    v
OIDC
    |
    v
OpsLensGitHubDeployRole
    |
    v
Terraform-managed infrastructure

Runtime identities
    |
    +-- EPSS ingestion / Silver / Scheduler
    +-- KEV ingestion / Silver / Scheduler
    +-- NVD Bootstrap ingestion
    +-- NVD Incremental ingestion / Scheduler
    +-- NVD Silver
    +-- NVD Promotion
    +-- NVD Analytics Projector
    +-- GHSA Bronze
    +-- GHSA Silver
```

Least privilege is evaluated against each runtime's responsibility rather than against the entire data lake.

---

## Cost discipline

The architecture avoids services without a demonstrated need.

Current examples:

- no Glue crawler for EPSS, KEV, or NVD;
- no Step Functions requirement in the current data plane;
- no DynamoDB idempotency store;
- no Iceberg requirement yet;
- no unrestricted natural-language-to-SQL path;
- Athena development workgroup capped at 10 MiB per query.

---

## Deployment artifact model

All currently deployed OpsLens Lambda runtimes follow the same immutable deployment-artifact lifecycle:

```text
source tree
    -> deterministic ZIP build
    -> SHA-256 identity
    -> content-addressed S3 object key
    -> exact S3 VersionId
    -> Terraform immutable pin
    -> Lambda CodeSha256 readback
```

The permanent NVD analytics projector was already using this model. PR #28 completed the migration of the remaining legacy EPSS, KEV, and NVD Bootstrap ingestion runtimes and corrected the artifact-bucket lifecycle so current content-addressed Lambda objects remain durable.

The final PR #28 environment closeout proved:

```text
No changes. Your infrastructure matches the configuration.
POST_APPLY_PLAN_RC=0
```

There is no remaining known global `dev` Terraform drift from the legacy Lambda artifact lifecycle at this checkpoint.

---

## Current implementation status

```text
FIRST EPSS                          IMPLEMENTED through Athena
CISA KEV                            IMPLEMENTED through Athena
NVD / CVE                           IMPLEMENTED through authoritative analytics + Athena
GitHub Security Advisories          IMPLEMENTED through immutable Silver; Glue/Athena next
EPSS historical expansion           NOT STARTED
Phase 3 Vulnerability Correlation   NOT STARTED
```

Detailed NVD phase status:

```text
Phase 2.3A — NVD Source Contract            COMPLETE
Phase 2.3B — NVD Bootstrap Bronze           COMPLETE
Phase 2.3C — NVD Incremental API Contract   COMPLETE
Phase 2.3D — NVD Versioned Silver Contract  COMPLETE
Phase 2.3E — NVD Silver AWS Runtime         COMPLETE
Phase 2.3F — NVD Authoritative Watermark    COMPLETE
Phase 2.3G — NVD Glue/Athena Analytics      COMPLETE
```

GHSA Phase 2.4A source contract, 2.4B advisory/Silver contract, 2.4C Bronze runtime, and 2.4D immutable Silver runtime are complete. Phase 2.4E — GHSA Glue/Athena Analytics — is the next implementation gate.

Package/version vulnerability applicability remains deterministic Phase 3 work. Phase 2 remains open until GHSA analytics/cross-source exit criteria and historical EPSS requirements are completed or explicitly deferred; no Bedrock, RAG, or agentic phase should begin as a substitute for those remaining deterministic data-plane milestones.
