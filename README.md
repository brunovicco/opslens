<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Agentic Cloud & Software Supply Chain Intelligence on AWS

**Threat Intelligence · Software Supply Chain · Deterministic Evidence · AWS Serverless · Security Automation**

</div>

OpsLens is an open-source software supply chain intelligence platform built on AWS.

It is designed to answer:

> Given the software I actually use, which vulnerabilities represent material risk, why, and what should I do about them?

The project intentionally builds deterministic evidence, correlation, security boundaries, observability, and failure recovery before adding generative or agentic reasoning.

## Status

| Phase | Scope | Status |
| --- | --- | --- |
| Phase 0 | AWS Foundation | ✅ Complete |
| Phase 1 | EPSS Vertical Slice | ✅ Complete |
| Phase 2.1 | CISA KEV Bronze Ingestion | ✅ Complete |
| Phase 2.2 | CISA KEV Silver + Analytics | ✅ Complete |
| Phase 2.3 | NVD / CVE | ▶️ Next |

Phase 2.2 now provides the complete CISA KEV evidence path:

- immutable Bronze source evidence;
- exact-version Bronze-to-Silver processing;
- deterministic normalization;
- typed Parquet Silver persistence;
- idempotent event-driven processing;
- bounded asynchronous failure recovery;
- AWS Glue Data Catalog registration;
- injected `snapshot_date` partition projection;
- deterministic Amazon Athena queries;
- independent Parquet-to-Athena evidence cross-checks;
- explicit temporal-query enforcement;
- measured Athena scan and latency evidence.

The next Phase 2 major vertical slice is NVD/CVE ingestion and normalization.

## Current architecture

OpsLens currently has two threat-intelligence paths.

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
    |
    v
S3 ObjectCreated
    |
    v
EPSS Silver Lambda
    |
    v
S3 Silver / Parquet
    |
    v
AWS Glue Data Catalog
    |
    v
Amazon Athena
```

### CISA KEV

```text
CISA KEV JSON
    |
    v
EventBridge Scheduler
    |
    v
KEV Ingestion Lambda
    |
    +--> source validation
    +--> SHA-256 provenance
    +--> conditional S3 PutObject
    |
    v
S3 Bronze
    |
    v
S3 ObjectCreated:Put
    |
    v
KEV Silver Lambda
    |
    +--> exact VersionId read
    +--> event / S3 evidence verification
    +--> deterministic normalization
    +--> typed Parquet serialization
    +--> conditional Silver PutObject
    |
    v
S3 Silver / Parquet
    |
    +--> duplicate delivery: already_exists
    +--> exhausted async failure: SQS OnFailure
    |
    v
AWS Glue Data Catalog
opslens_dev.kev_entries
    |
    v
Amazon Athena
opslens-dev
```

The S3 notification is scoped to the KEV Bronze prefix and canonical filename. KEV Silver writes to a separate `silver/kev/` prefix, avoiding recursive invocation.

## Core principles

- Deterministic evidence and correlation first; generative reasoning second.
- Agents reason. Code verifies evidence.
- Not every question is a RAG problem.
- Never execute third-party repository code during analysis.
- Repository risk and runtime exposure are separate concepts.
- Raw source evidence is preserved before transformation.
- Derived analytical results must remain reproducible.
- Duplicate delivery is expected and must be safe.
- IAM least privilege is an architectural requirement.
- Deployment identities and runtime identities remain separate.
- Cost controls, observability, and failure recovery are part of the design.
- AWS services are introduced only when they solve a concrete requirement.

## AWS foundation

Current environment:

```text
Environment:             dev
Primary workload Region: us-east-1
Infrastructure as Code:  Terraform
Human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC
Terraform state:         Amazon S3
Observability:           CloudWatch + X-Ray
Analytics:               AWS Glue + Amazon Athena
```

GitHub Actions stores no persistent AWS access keys.

The GitHub deployment role is assumed through OIDC and its trust relationship is constrained to the repository deployment boundary.

## Data lake

### EPSS Bronze

Canonical object:

```text
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
```

Properties:

- original compressed FIRST artifact preserved;
- deterministic key;
- SHA-256 provenance;
- source metadata;
- S3 versioning;
- conditional writes.

### EPSS Silver

Canonical object:

```text
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

Schema:

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

Silver is deterministic and serialized as Parquet.

### CISA KEV Bronze

Canonical object:

```text
bronze/kev/snapshot_date=YYYY-MM-DD/known_exploited_vulnerabilities.json
```

`snapshot_date` represents the UTC date on which OpsLens observed the source. It is intentionally distinct from the CISA catalog `dateReleased` and vulnerability-level `dateAdded`.

The Bronze ingestion validates HTTP success, bounded response size, UTF-8 JSON, the top-level object contract, `catalogVersion`, `dateReleased`, `count`, `vulnerabilities`, and `count == len(vulnerabilities)`.

Unknown source fields remain allowed, and the exact source bytes are preserved.

### CISA KEV Silver

Canonical object:

```text
silver/kev/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

Physical Parquet columns:

```text
cve
vendor_project
product
vulnerability_name
date_added
short_description
required_action
due_date
known_ransomware_campaign_use
notes
cwes
catalog_version
catalog_date_released
source
source_sha256
retrieved_at
```

Partition:

```text
snapshot_date string
```

The Silver transformation:

- reads the exact Bronze object version referenced by the S3 event;
- cross-checks `VersionId`, ETag, size, and Bronze provenance metadata;
- fails closed on transport or provenance mismatches;
- rejects duplicate CVEs and unsupported ransomware values;
- preserves deterministic source ordering;
- writes Parquet with an explicit Arrow schema;
- uses conditional persistence so duplicate delivery cannot create a second Silver version.

## Validated EPSS analytical path

Validated snapshot:

```text
snapshot_date: 2026-08-16
model_version: v2026.06.15
source rows:   360399
EPSS > 0.7:    2457
```

Supported structured question:

> Which CVEs have EPSS greater than 0.7 for a specific snapshot?

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

Measured execution:

```text
Athena engine:          version 3
data scanned:           6084428 bytes
total execution:        1501 ms
estimated query cost:   USD 0.00005000
```

The result was independently cross-checked against both Silver Parquet and the raw FIRST Bronze source.

## Validated CISA KEV pipeline

Validated Bronze snapshot:

```text
snapshot_date:  2026-08-17
catalogVersion: 2026.08.14
records:         1665
source bytes:    1583171
SHA-256:         52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

Validated Silver artifact:

```text
key:             silver/kev/snapshot_date=2026-08-17/part-00000.parquet
rows:            1665
columns:         16
size:            257331 bytes
schema version:  1
Known ransomware:   349
Unknown ransomware: 1316
empty CWE lists:     171
```

The Silver object was independently downloaded and inspected with PyArrow.

A replay of the exact same Bronze event returned `already_exists`, while the versioned S3 object remained at one version with the same `VersionId`.

## Validated CISA KEV analytical path

Validated snapshot:

```text
snapshot_date: 2026-08-17
rows:          1665
table:         opslens_dev.kev_entries
workgroup:     opslens-dev
```

Supported structured question:

> Was CVE X present in CISA KEV for a specific snapshot?

The validation CVE was selected directly from the persisted Silver Parquet artifact rather than from memory:

```text
CVE-2002-0367
vendor_project: Microsoft
product: Windows
date_added: 2022-03-03
due_date: 2022-03-24
catalog_version: 2026.08.14
source: cisa-kev
source_sha256: 52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

Athena returned the same evidence as the persisted Parquet artifact.

Observed Athena executions:

| Validation | Data scanned | Total execution |
| --- | ---: | ---: |
| Record count | 0 bytes | 744 ms |
| CVE membership | 24,911 bytes | 621 ms |
| Empty CWE arrays | 3,002 bytes | 842 ms |
| Timestamp compatibility | 13,826 bytes | 945 ms |

The record-count query returned `1665`, the CWE validation returned `171` empty arrays, and both `catalog_date_released` and `retrieved_at` were read successfully through Athena engine version 3.

The Glue table uses injected partition projection for `snapshot_date`. A query that intentionally omitted `snapshot_date` failed with `CONSTRAINT_VIOLATION`, enforcing explicit temporal evidence instead of implicitly treating an unspecified dataset version as "latest".

## Failure recovery

EPSS Silver, CISA KEV ingestion, and CISA KEV Silver use bounded Lambda asynchronous processing with `maximum event age = 3600`, `retry attempts = 2`, and source-specific SQS OnFailure destinations.

A controlled KEV ingestion source failure validated three execution attempts, `KevSourceUnavailableError`, `RetriesExhausted`, an enriched SQS destination record, and successful recovery after restoring the canonical source.

A separate controlled KEV Silver failure supplied a parser-valid event with an intentionally incorrect ETag. The runtime:

- read the exact Bronze `VersionId`;
- detected the event/S3 evidence mismatch;
- raised `KevBronzeEvidenceMismatchError`;
- retried until `approximateInvokeCount = 3`;
- produced an SQS OnFailure record with `condition = RetriesExhausted`;
- created no additional Silver object version.

This validates the fail-closed rule: S3 event metadata is treated as evidence to verify, not as trusted authority.

## Scheduling

CISA KEV ingestion is scheduled through EventBridge Scheduler:

```text
group:           opslens-dev-kev
schedule:        opslens-dev-kev-daily
expression:      cron(30 23 * * ? *)
timezone:        UTC
flexible window: OFF
```

Scheduler delivery retries are bounded to 3600 seconds and 2 retries.

The Scheduler execution role can perform only `lambda:InvokeFunction` against `opslens-dev-kev-ingestion`.

Scheduler delivery retries and Lambda asynchronous processing retries are separate failure boundaries.

## Security boundaries

```text
Human bootstrap
    |
    v
AWS IAM Identity Center

GitHub Actions
    |
   OIDC
    |
    v
OpsLensGitHubDeployRole
    |
    v
Terraform-managed infrastructure

Runtime identities
    |
    +-- EPSS ingestion role
    +-- EPSS Silver role
    +-- EPSS Scheduler role
    +-- KEV ingestion role
    +-- KEV Silver role
    +-- KEV Scheduler role
```

The KEV Silver role is intentionally narrow:

```text
s3:GetObjectVersion -> bronze/kev/*
s3:PutObject        -> silver/kev/*
sqs:SendMessage     -> KEV Silver failure queue
CloudWatch Logs     -> KEV Silver log group
X-Ray telemetry     -> tracing APIs
```

It does not receive generic `s3:GetObject`, `s3:ListBucket`, delete permissions, or broad SQS access.

S3 is allowed to invoke the KEV Silver Lambda only from the expected data bucket and AWS account.

## Observability

The runtime uses AWS Lambda Powertools, structured CloudWatch Logs, custom CloudWatch Metrics, AWS Lambda platform metrics, AWS Scheduler metrics, and AWS X-Ray.

The first real KEV Silver transformation observed:

```text
configured memory:  1024 MB
max memory used:     176 MB
duration:             795.365 ms
billed duration:      2112 ms
rows transformed:     1665
```

A warm idempotent replay observed a maximum of 194 MB used. Right-sizing is intentionally deferred until additional natural runtime evidence is available.

## Cost discipline

The architecture avoids services that do not yet solve a demonstrated requirement.

Current examples:

- no Glue crawler for EPSS or CISA KEV;
- no Step Functions in current ingestion/transformation paths;
- no DynamoDB idempotency store;
- no Iceberg requirement yet;
- no Scheduler DLQ for KEV at this stage;
- KEV Glue/Athena resources were introduced only after the Bronze-to-Silver runtime was proven.

Athena uses a 10 MiB bytes-scanned cutoff in the development workgroup.

The controlled three-attempt KEV Silver failure lab consumed approximately `2.283 GB-s` of Lambda compute before free-tier effects, demonstrating that the current dev workload remains negligible relative to the project cost target.

## Repository structure

```text
.
├── .github/
├── docs/
│   ├── adr/
│   ├── labs/
│   ├── README.md
│   └── architecture.md
├── infra/
│   ├── bootstrap/
│   └── environments/dev/
├── scripts/
├── src/
│   └── opslens/
├── tests/
├── README.md
├── README.pt-br.md
├── pyproject.toml
└── uv.lock
```

## Quality gates

The repository uses Ruff, Google-style docstrings, strict Pyright, Pytest, Terraform fmt and validate, TFLint, Checkov, GitHub Actions, canonical Terraform plans before apply, and post-deployment no-change plans.

## Documentation

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/adr/README.md`](docs/adr/README.md)
- [`docs/labs/phase-0-iam-oidc-failure.md`](docs/labs/phase-0-iam-oidc-failure.md)
- [`docs/labs/phase-0-cloudwatch-authorization-failure.md`](docs/labs/phase-0-cloudwatch-authorization-failure.md)
- [`docs/labs/phase-1-epss-athena-query.md`](docs/labs/phase-1-epss-athena-query.md)
- [`docs/labs/phase-2-kev-async-failure-recovery.md`](docs/labs/phase-2-kev-async-failure-recovery.md)
- [`docs/labs/phase-2-kev-silver-runtime.md`](docs/labs/phase-2-kev-silver-runtime.md)
- [`docs/labs/phase-2-kev-athena-query.md`](docs/labs/phase-2-kev-athena-query.md)
- [`docs/README.md`](docs/README.md)

## Roadmap

```text
Phase 2.1  CISA KEV Bronze ingestion                         COMPLETE
Phase 2.2  CISA KEV Silver runtime                          COMPLETE
Phase 2.2  CISA KEV Glue + Athena                           COMPLETE
Phase 2.3  NVD / CVE                                        NEXT
Phase 2.4  GitHub Security Advisories                       NOT STARTED
Phase 2.5  historical EPSS                                  NOT STARTED
```

The proven EPSS architecture is reused where appropriate, but it is not treated as a mandatory template for every source.

## KEV daily snapshot semantics

The Phase 2.1 KEV Bronze contract preserves one immutable observation per UTC `snapshot_date`.

The first successful write for a date becomes the canonical Bronze evidence:

```text
first successful observation
        |
        v
conditional PutObject
If-None-Match: "*"
        |
        v
canonical immutable object
```

Any later CISA update observed during the same UTC date resolves to the same object key and produces the expected `already_exists` result.

The scheduled validation on `2026-08-17` demonstrated this behavior directly:

```text
03:52 UTC observation
catalogVersion: 2026.08.14
records:        1665

23:30 UTC observation
catalogVersion: 2026.08.17
records:        1666

canonical Bronze after both observations
catalogVersion: 2026.08.14
records:        1665
S3 versions:    1
```

Therefore, `snapshot_date` means **the UTC date on which OpsLens first successfully preserved the source**, not necessarily the final CISA revision published during that date.

Capturing intraday source revisions is intentionally outside the Phase 2.1 contract.

## License

Apache License 2.0.
