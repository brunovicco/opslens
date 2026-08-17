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
| Phase 2.1 | CISA KEV Bronze Ingestion | 🟡 Final runtime validation |
| Phase 2.2 | CISA KEV Silver + Analytics | ⏭️ Next |

Phase 2.1 currently has:

- real CISA KEV ingestion;
- immutable raw Bronze storage;
- schema and source-contract validation;
- SHA-256 provenance;
- conditional S3 writes for idempotency;
- Lambda asynchronous retries;
- SQS OnFailure recovery;
- dedicated least-privilege runtime roles;
- daily EventBridge Scheduler at `23:30 UTC`;
- Terraform-managed infrastructure with canonical no-change convergence.

The remaining Phase 2.1 gate is the first naturally scheduled KEV execution.

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
    |
    +--> SHA-256 provenance
    |
    +--> conditional S3 PutObject
    |
    v
S3 Bronze
    |
    +--> success: immutable raw evidence
    |
    +--> duplicate: already_exists
    |
    +--> exhausted async failure: SQS OnFailure
```

KEV Silver transformation and analytics are intentionally deferred to Phase 2.2.

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

## Validated CISA KEV ingestion

Validated Bronze snapshot:

```text
snapshot_date: 2026-08-17
catalogVersion: 2026.08.14
records:        1665
source bytes:   1583171
SHA-256:        52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

A repeated ingestion produced `status: already_exists` without creating an additional S3 object version.

## Failure recovery

EPSS Silver and CISA KEV ingestion use bounded Lambda asynchronous processing with `maximum event age = 3600`, `retry attempts = 2`, and source-specific SQS OnFailure destinations.

A controlled KEV source failure validated three execution attempts, `KevSourceUnavailableError`, `RetriesExhausted`, an enriched SQS destination record, and successful recovery after restoring the canonical source.

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
    +-- KEV Scheduler role
```

The KEV Scheduler role is protected by `scheduler.amazonaws.com`, exact `aws:SourceAccount`, and exact KEV schedule-group `aws:SourceArn`. It has no S3, SQS, Glue, Athena, or general Lambda privileges.

## Observability

The runtime uses AWS Lambda Powertools, structured CloudWatch Logs, custom CloudWatch Metrics, AWS Lambda platform metrics, AWS Scheduler metrics, and AWS X-Ray.

## Cost discipline

The architecture avoids services that do not yet solve a demonstrated requirement. There is no Glue crawler for EPSS, no Step Functions in current ingestion paths, no DynamoDB idempotency store, no Iceberg requirement yet, no Scheduler DLQ for KEV at this stage, and no KEV Silver or Athena resources before the Bronze contract is proven.

Athena uses a 10 MiB bytes-scanned cutoff in the development workgroup.

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
- [`docs/README.md`](docs/README.md)

## Roadmap

```text
Phase 2.1  CISA KEV Bronze ingestion
Phase 2.2  CISA KEV Silver + Glue + Athena
Phase 2.x  NVD / CVE
Phase 2.x  GitHub Security Advisories
Phase 2.x  historical EPSS
```

The proven EPSS architecture is reused where appropriate, but it is not treated as a mandatory template for every source.

## License

Apache License 2.0.
