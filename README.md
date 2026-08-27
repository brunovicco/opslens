<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Agentic Cloud & Software Supply Chain Intelligence on AWS

**Threat Intelligence · Software Supply Chain · Deterministic Evidence · AWS Serverless · Security Automation**

</div>

OpsLens is an open-source software supply chain intelligence platform built on AWS.

It is designed to answer:

> Given the software I actually use, which vulnerabilities represent material risk, why, and what should I do about them?

The project intentionally builds deterministic evidence, provenance, correlation, least-privilege boundaries, observability, failure recovery, and cost controls before introducing generative or agentic reasoning.

> **Agents reason. Code verifies evidence.**

## Status

| Phase | Scope | Status |
| --- | --- | --- |
| Phase 0 | AWS Foundation | ✅ Complete |
| Phase 1 | EPSS Vertical Slice | ✅ Complete |
| Phase 2.1 | CISA KEV Bronze Ingestion | ✅ Complete |
| Phase 2.2 | CISA KEV Silver + Analytics | ✅ Complete |
| Phase 2.3A–2.3G | NVD / CVE Bronze, Silver, Watermark, Glue + Athena | ✅ Complete |
| Phase 2.4 | GitHub Security Advisories | ⏳ Not started |
| Phase 2.5 | Historical EPSS expansion | ⏳ Not started |
| Phase 3 | AI reasoning / agentic capabilities | ⏳ Not started |

The current milestone closes the complete NVD deterministic evidence path from immutable source ingestion through versioned Silver evidence, authoritative watermark promotion, permanent analytics projection, AWS Glue, and bounded Athena queries.

## Current architecture

OpsLens currently has three implemented threat-intelligence data paths.

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
    +--> typed Parquet serialization
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
```

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
                  promotion eligibility
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

The NVD authority boundary is explicit:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

Analytics is downstream-only. The analytics projector cannot advance the watermark, mutate Silver authority, list the bucket, delete objects, or write Glue partitions.

## Core principles

- Deterministic evidence and correlation first; generative reasoning second.
- Agents reason. Code verifies evidence.
- Raw source evidence is preserved before transformation.
- Exact S3 object versions are part of the evidence model.
- Derived analytical results must remain reproducible.
- Duplicate delivery is expected and must be safe.
- Fail closed on evidence, provenance, schema, or authority mismatches.
- Repository risk and runtime exposure are separate concepts.
- Never execute third-party repository code during analysis.
- IAM least privilege is an architectural requirement.
- Deployment identities and runtime identities remain separate.
- Cost, observability, and failure recovery are architectural concerns.
- AWS services are introduced only when they solve a concrete requirement.
- Natural-language planning never receives unrestricted SQL authority.

## AWS foundation

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

GitHub Actions stores no persistent AWS access keys. The deployment identity is separate from ingestion, transformation, scheduler, promotion, and analytics runtime identities.

## NVD implementation highlights

### Immutable Bronze

Bootstrap yearly feeds preserve the exact NVD gzip and META evidence under deterministic feed revisions:

```text
bronze/nvd/cve/bootstrap/
  feed_year=YYYY/
    feed_revision=<source-revision>/
      nvdcve-2.0-YYYY.json.gz
      nvdcve-2.0-YYYY.meta
      manifest.json
```

Incremental CVE API runs preserve exact response pages and a COMPLETE manifest under a deterministic update identity:

```text
bronze/nvd/cve/updates/
  update_id=<deterministic-window-identity>/
    page_start=000000/response.json
    page_start=000500/response.json
    ...
    manifest.json
```

### Versioned Silver

The NVD Silver contract separates:

```text
cve_id                  vulnerability identity
observed_cve_version_id exact source-CVE content identity
observation_id          exact immutable Bronze occurrence identity
```

The Silver v1 dataset preserves core CVE fields, descriptions, tags, CWE evidence, references, supported CVSS observations, canonical metric JSON, CPE configuration trees, and exact Bronze provenance.

Physical contract:

```text
dataset:           nvd_cve_versions
schema_version:    1
Parquet format:    1.0
data page version: 1.0
compression:       snappy
row group size:    5000
```

### Authoritative watermark

Incremental Bronze completion does not advance authority. A new committed boundary is published only after exact Silver COMPLETE evidence is verified and promotion succeeds.

This prevents a partially transformed or unverifiable incremental window from becoming authoritative.

### Permanent analytics projection

The analytics projector consumes exact committed authority and performs an exact-version conditional S3 copy into a clean append-only namespace:

```text
analytics/nvd/cve/schema_version=1/
  source_kind=<bootstrap|incremental>/
  projection_date=YYYY-MM-DD/
    <deterministic-batch-file>.parquet
```

Replay semantics are strict: `If-None-Match: *` can resolve to `already_projected` only after the existing destination object is re-verified against the authoritative source VersionId, SHA-256, size, metadata, and Parquet signature.

The runtime has no `s3:ListBucket`, delete permissions, watermark `PutObject`, or Glue partition mutation authority.

## Validated evidence

### EPSS

Validated snapshot:

```text
snapshot_date: 2026-08-16
model_version: v2026.06.15
source rows:   360399
EPSS > 0.7:    2457
```

Observed Athena execution:

```text
data scanned:    6084428 bytes
total execution: 1501 ms
```

The result was independently cross-checked against Silver Parquet and the raw FIRST source.

### CISA KEV

Validated snapshot:

```text
snapshot_date:  2026-08-17
catalogVersion: 2026.08.14
records:        1665
source bytes:   1583171
SHA-256:        52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

Validated Silver artifact:

```text
rows:           1665
columns:        16
size:           257331 bytes
schema version: 1
```

### NVD Bootstrap projection

Validated permanent Bootstrap projection:

```text
rows:                  48293
destination VersionId: NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba
SHA-256:               4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
replay:                already_projected with VersionId unchanged
```

### NVD Incremental projection

Validated event-driven incremental projection:

```text
committed_through_at:   2026-08-26T21:25:00Z
update_id:              fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
rows:                   331
destination VersionId:  qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
SHA-256:                3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
```

### NVD Athena proof

Permanent Athena queries reproduced exact local Parquet evidence while remaining below the dev workgroup cutoff of `10,485,760` bytes:

| Query | Purpose | Data scanned |
| --- | --- | ---: |
| A | Bootstrap + Incremental cardinality / lineage | 536,071 bytes |
| B | Bootstrap nested CVSS sample | 3,928,022 bytes |
| B2 | Exact CVSS source/type equivalence | 3,928,022 bytes |
| C | Deterministic Incremental observation | 43,880 bytes |

The Bootstrap CVSS sample correctly contained two distinct V3.1 observations with the same numeric vector: NVD `Primary` and CNA `Secondary` evidence. The Incremental sample reproduced the exact expected observation, batch, status, and timestamp.

## Failure recovery and observability

Runtime boundaries use structured CloudWatch logs, CloudWatch metrics, AWS X-Ray, bounded asynchronous retries, and source-specific SQS OnFailure destinations.

The NVD analytics runtime was validated with:

```text
replay status:             already_projected
replay destination version unchanged
invalid async invocation:  accepted with HTTP-style StatusCode 202
retry condition:           RetriesExhausted
approximate invoke count:  3
function error:            Unhandled
error type:                InvalidNvdAnalyticsProjectionInvocationError
failure queue after cleanup: 0 / 0 / 0
```

The invalid invocation was rejected before projection execution, proving the inbound boundary fails closed.

## Security boundaries

```text
Human administration
    -> AWS IAM Identity Center

GitHub Actions
    -> OIDC
    -> OpsLensGitHubDeployRole
    -> Terraform-managed deployment

Runtime identities
    -> source-specific ingestion roles
    -> source-specific Silver roles
    -> scheduler execution roles
    -> NVD promotion role
    -> NVD analytics projector role
```

The NVD analytics projector is intentionally narrower than the upstream authority path. It can read exact committed evidence and create deterministic analytics objects, but it cannot mutate the authoritative watermark or Silver state.

## Cost discipline

The architecture avoids services that do not yet solve a demonstrated requirement.

Current examples:

- no Glue crawler for EPSS, KEV, or NVD;
- no Step Functions requirement in the current data plane;
- no DynamoDB idempotency store;
- no Iceberg requirement yet;
- no unrestricted text-to-SQL path;
- Athena development workgroup enforces a 10 MiB bytes-scanned cutoff.

## Quality gates

The repository uses:

```text
Ruff
strict Pyright
Pytest
Terraform fmt / validate
TFLint
Checkov
GitHub Actions
canonical Terraform plans before apply
post-deployment convergence checks
```

The Phase 2.3G closeout passed Ruff, strict Pyright, the full Pytest suite, Terraform CI, Bootstrap Terraform convergence, and Phase 2.3G resource convergence.

A known pre-existing dev convergence exception remains on legacy EPSS / KEV / NVD Bootstrap Lambda artifact hashes. Those legacy artifact lifecycle boundaries are intentionally tracked separately from the completed NVD analytics milestone.

## Repository structure

```text
.
├── .github/
├── docs/
│   ├── adr/
│   ├── labs/
│   ├── README.md
│   ├── architecture.md
│   └── architecture.pt-br.md
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

## Documentation

- [Architecture — English](docs/architecture.md)
- [Arquitetura — Português](docs/architecture.pt-br.md)
- [ADR index](docs/adr/README.md)
- [Lab / evidence index](docs/README.md)

## Roadmap

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2.1  CISA KEV Bronze ingestion                          COMPLETE
Phase 2.2  CISA KEV Silver + Glue + Athena                    COMPLETE
Phase 2.3  NVD / CVE Bronze + Silver + Watermark + Analytics  COMPLETE
Phase 2.4  GitHub Security Advisories                          NOT STARTED
Phase 2.5  Historical EPSS                                     NOT STARTED
Phase 3    AI reasoning / agentic capabilities                 NOT STARTED
```

The proven patterns are reused where appropriate, but no source is forced into a generic ingestion design when its semantics differ.

## License

Apache License 2.0.
