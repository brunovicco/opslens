# OpsLens

Agentic Cloud & Software Supply Chain Intelligence on AWS.

OpsLens is an open-source software supply chain intelligence platform designed to answer:

> Given the software I actually use, which vulnerabilities represent material risk, why, and what should I do about them?

## Status

**Phase 0 — AWS Foundation: complete.**
**Phase 1 — EPSS Vertical Slice: complete.**
**Next:** Phase 2 — Threat Intelligence Data Lake.

Phase 0 established the AWS identity, infrastructure, CI/CD, security, and observability foundation.

Phase 1 delivered the first real end-to-end intelligence path using FIRST EPSS:

```text
FIRST EPSS
    |
    v
EventBridge Scheduler
    |
    v
Ingestion Lambda
    |
    v
S3 Bronze
    |
    v
S3 ObjectCreated
    |
    v
Silver Lambda
    |
    v
S3 Silver / Parquet
    |
    v
Glue Data Catalog
    |
    v
Athena
```

The first supported structured question is now implemented and validated:

> Which CVEs have EPSS greater than 0.7 for a specific snapshot?

For snapshot `2026-08-16`, the validated answer contains `2457` CVEs.

## Core principles

- Deterministic evidence and correlation first; generative reasoning second.
- Not every question is a RAG problem.
- Never execute third-party repository code.
- Repository risk and runtime exposure are separate concepts.
- IAM least privilege, cost controls, failure recovery, and observability are architectural requirements.
- AWS services are added only when they solve a concrete OpsLens requirement.
- Raw source evidence is preserved before transformation.
- Derived analytical results must be reproducible and cross-checkable against source data.

## AWS foundation

The deployment currently uses one real environment:

- Environment: `dev`
- Primary workload Region: `us-east-1`
- Infrastructure as Code: Terraform
- Human bootstrap access: AWS IAM Identity Center
- CI/CD identity: GitHub Actions OIDC
- Remote Terraform state: Amazon S3
- Runtime observability: CloudWatch Logs, CloudWatch Metrics, X-Ray
- Structured analytics: AWS Glue Data Catalog and Amazon Athena

GitHub Actions does not store persistent AWS access keys.

The deployment role is assumed through OIDC, and its trust policy is restricted to the repository's `main` branch subject.

Deployment permissions and runtime permissions are kept separate.

## Current data path

### Bronze

The ingestion Lambda downloads the daily FIRST EPSS dataset and preserves the original compressed source artifact.

Canonical key:

```text
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
```

Bronze properties:

- source bytes preserved;
- deterministic object key;
- source metadata preserved;
- SHA-256 recorded;
- S3 versioning enabled;
- conditional object creation prevents duplicate snapshot writes.

### Silver

An S3 `ObjectCreated` event triggers the Silver transformation Lambda.

Canonical key:

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

The transformation is deterministic and rejects invalid or duplicate CVE records.

### Analytics

Silver Parquet data is cataloged through AWS Glue:

```text
database: opslens_dev
table:    epss_scores
```

Athena uses injected partition projection for `snapshot_date`.

Queries therefore provide an explicit snapshot date, which makes the analytical evidence temporally reproducible and avoids daily Glue partition registration.

Athena workgroup:

```text
opslens-dev
```

The workgroup enforces:

- configured result location;
- SSE-S3 result encryption;
- expected bucket owner;
- CloudWatch metrics;
- a 10 MiB per-query scan cutoff.

## Phase 1 validation

Validated snapshot:

```text
snapshot_date:   2026-08-16
model_version:   v2026.06.15
source rows:     360399
EPSS > 0.7:      2457
```

Validated query:

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

Measured Athena execution:

```text
query execution id:  cd0f145b-59e4-435f-9e42-7c836c56bbef
engine:              Athena engine version 3
data scanned:        6084428 bytes
total execution:     1501 ms
estimated query cost: USD 0.00005000
```

Correctness gates:

```text
BRONZE_TO_SILVER_DATA_GATE=PASS
NO_SILVER_RECURSION_GATE=PASS
ATHENA_PARQUET_CROSSCHECK_GATE=PASS
ATHENA_BRONZE_SOURCE_CROSSCHECK_GATE=PASS
ATHENA_QUERY_COST_GATE=PASS
```

The Athena result was independently cross-checked against:

1. the Silver Parquet dataset;
2. the raw FIRST Bronze source.

Both comparisons returned the same `2457` CVEs with matching EPSS and percentile values.

## Idempotency and failure recovery

Repeated delivery is expected and supported.

For the same Bronze snapshot:

```text
first ingestion     -> created
later ingestion     -> already_exists
duplicate S3 event  -> safe Silver conditional write
```

Silver asynchronous processing uses:

```text
maximum event age: 3600 seconds
retry attempts:    2
OnFailure:         SQS Standard
```

A real intentional failure validated:

- three Lambda invocation attempts;
- structured error context;
- successful OnFailure delivery to SQS;
- no destination delivery failure.

## Security boundaries

The current implementation keeps responsibilities separated:

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

Runtime roles
    |
    +-- ingestion: write EPSS Bronze
    |
    +-- Silver: read EPSS Bronze
                write EPSS Silver
                send failure record to exact SQS queue
```

The GitHub deployment role does not serve as a runtime query identity.

No unrestricted Athena data-plane runtime identity has been introduced.

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
├── pyproject.toml
└── uv.lock
```

## Documentation

Architecture:

- [`docs/architecture.md`](docs/architecture.md)

Architecture Decision Records:

- [`docs/adr/README.md`](docs/adr/README.md)

Operational and validation labs:

- [`docs/labs/phase-0-iam-oidc-failure.md`](docs/labs/phase-0-iam-oidc-failure.md)
- [`docs/labs/phase-0-cloudwatch-authorization-failure.md`](docs/labs/phase-0-cloudwatch-authorization-failure.md)
- [`docs/labs/phase-1-epss-athena-query.md`](docs/labs/phase-1-epss-athena-query.md)

Documentation index:

- [`docs/README.md`](docs/README.md)

## Quality gates

The repository uses:

- Ruff formatting and linting
- Google-style docstrings
- strict Pyright
- Pytest
- Terraform fmt and validate
- TFLint
- Checkov

Python domain and application layers remain independent from AWS SDK concerns where appropriate.

## Phase 0 evidence

Phase 0 demonstrated:

- remote Terraform state;
- GitHub OIDC authentication without persistent AWS keys;
- branch-constrained IAM trust;
- least-privilege authorization troubleshooting;
- real Terraform deployment from GitHub Actions;
- CloudTrail correlation for federation events;
- Terraform static/security gates;
- CloudWatch operational evidence.

## Phase 1 evidence

Phase 1 demonstrated:

- real FIRST EPSS ingestion;
- immutable Bronze evidence;
- deterministic Silver transformation;
- Parquet serialization;
- event-driven Bronze -> Silver processing;
- idempotent repeated delivery;
- failure retries and SQS OnFailure recovery;
- Glue catalog integration;
- Athena structured analytics;
- partition pruning through explicit snapshot selection;
- bytes-scanned and approximate query cost measurement;
- independent Athena-to-Parquet cross-check;
- independent Athena-to-source cross-check;
- reproducible query documentation.

## Next milestone

Phase 2 expands the intelligence lake beyond EPSS.

Planned sources:

- CISA KEV
- NVD/CVE
- GitHub Security Advisories
- EPSS history

The target is deterministic structured correlation across vulnerability identity, exploitation evidence, severity, probability, advisories, affected packages, and known fixes.

Architecture decisions for Phase 2 will be made source by source instead of assuming every dataset needs the same ingestion pattern.
