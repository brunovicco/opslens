# OpsLens Architecture

## Overview

OpsLens is an open-source software supply chain intelligence platform on AWS.

The implemented architecture currently covers AWS identity and deployment foundation, daily FIRST EPSS ingestion, immutable EPSS Bronze evidence, deterministic EPSS Silver transformation, Parquet, Glue, Athena, CISA KEV Bronze ingestion, KEV idempotency, Lambda asynchronous failure recovery through SQS OnFailure, a dedicated daily EventBridge Scheduler and execution role for KEV, observability, least privilege, and cost controls.

The platform intentionally puts deterministic evidence and structured correlation before generative reasoning.

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
    +--> duplicate snapshot: already_exists
    +--> exhausted async failure: SQS OnFailure
```

## Architectural principles

- Raw evidence is preserved before enrichment or interpretation.
- AWS SDK and runtime details remain outside the core domain model where practical.
- Human bootstrap, GitHub deployment, ingestion, transformation, Scheduler, and analytics responsibilities use separate IAM boundaries.
- Duplicate delivery is expected; Bronze and Silver writes use conditional object creation rather than `HEAD -> PUT`.
- Operational boundaries emit structured logs and metrics.

## CISA KEV ingestion

The CISA Known Exploited Vulnerabilities JSON catalog is ingested independently from the EPSS transformation path.

The ingestion Lambda performs a bounded HTTP fetch, validates UTF-8 JSON and the top-level source contract, requires `catalogVersion`, `dateReleased`, `count`, and `vulnerabilities`, verifies `count == len(vulnerabilities)`, calculates SHA-256 over the exact source bytes, and writes those original bytes to Bronze using conditional object creation.

Canonical key:

```text
bronze/kev/snapshot_date=YYYY-MM-DD/known_exploited_vulnerabilities.json
```

For KEV, `snapshot_date` is the UTC date on which OpsLens observed the source. It is distinct from CISA `dateReleased` and vulnerability-level `dateAdded`.

Validated 2026-08-17 snapshot:

```text
catalogVersion: 2026.08.14
records:        1665
bytes:          1583171
SHA-256:        52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

Repeated ingestion returns `already_exists` without creating another object version.

## KEV scheduling

```text
group:           opslens-dev-kev
schedule:        opslens-dev-kev-daily
cron:            cron(30 23 * * ? *)
timezone:        UTC
flexible window: OFF
```

Scheduler delivery retry policy:

```text
maximum event age: 3600 seconds
retry attempts:    2
```

The dedicated Scheduler execution role can invoke only the KEV ingestion Lambda. Its trust relationship is constrained by the Scheduler service principal, the exact AWS account, and the exact KEV schedule-group ARN.

## Failure recovery

EPSS Silver and KEV ingestion both use bounded Lambda asynchronous retry settings with source-specific SQS OnFailure destinations.

For KEV, a controlled invalid same-origin source URL produced three Lambda attempts, `KevSourceUnavailableError`, `RetriesExhausted`, an enriched SQS OnFailure record, preserved correlation data, and successful recovery after the canonical source was restored.

The KEV runtime role can send to the exact failure queue but cannot receive, delete, or purge messages from it.

## Current storage model

```text
S3 data bucket
|
+-- bronze/
|   +-- epss/
|   |   +-- snapshot_date=YYYY-MM-DD/
|   |       +-- epss_scores.csv.gz
|   +-- kev/
|       +-- snapshot_date=YYYY-MM-DD/
|           +-- known_exploited_vulnerabilities.json
|
+-- silver/
|   +-- epss/
|       +-- snapshot_date=YYYY-MM-DD/
|           +-- part-00000.parquet
|
+-- athena-results/
```

## What is intentionally not implemented yet

- CISA KEV Silver transformation;
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

## Next architecture increment

Phase 2.2 will add deterministic CISA KEV Silver normalization, Parquet, Glue, and Athena.

The first target structured question is:

> Is CVE X present in CISA KEV?

Later Phase 2 sources remain NVD/CVE, GitHub Security Advisories, and EPSS history.
