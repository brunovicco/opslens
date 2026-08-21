# OpsLens Architecture

_Last updated: 2026-08-21_

## Overview

OpsLens is an open-source software supply chain intelligence platform on AWS.

The implemented architecture currently covers:

- AWS identity and deployment foundation;
- daily FIRST EPSS ingestion;
- immutable EPSS Bronze evidence;
- deterministic EPSS Silver transformation;
- Parquet, AWS Glue Data Catalog, and Amazon Athena for EPSS;
- CISA KEV Bronze ingestion;
- NVD CVE JSON 2.0 Bootstrap Bronze ingestion;
- deterministic incremental NVD CVE API 2.0 Bronze contract;
- deterministic CISA KEV Silver transformation and Parquet persistence;
- exact S3 object-version evidence verification for KEV Silver;
- idempotent conditional writes for Bronze and Silver;
- S3 event-driven Bronze-to-Silver processing;
- bounded Lambda asynchronous retries and source-specific SQS OnFailure recovery;
- dedicated EventBridge Scheduler and runtime IAM boundaries;
- CloudWatch, custom metrics, and X-Ray observability;
- Terraform-managed infrastructure with post-apply convergence checks;
- explicit cost controls and service-adoption discipline.

The platform intentionally puts deterministic evidence and structured correlation before generative reasoning.

The core invariant is:

> **Agents reason. Code verifies evidence.**

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
    +--> event/S3 transport evidence verification
    +--> Bronze provenance verification
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

The KEV Silver dataset and its Glue/Athena analytical path are implemented and validated.

---

## Architectural principles

- Raw evidence is preserved before enrichment or interpretation.
- Deterministic facts remain authoritative; models may explain them but do not establish them.
- AWS SDK and runtime details remain outside the core domain model where practical.
- Human bootstrap, GitHub deployment, ingestion, transformation, Scheduler, and analytics responsibilities use separate IAM boundaries.
- Duplicate delivery is expected; Bronze and Silver writes use conditional object creation rather than `HEAD -> PUT`.
- Operational boundaries emit structured logs, metrics, and traces.
- Repository risk and runtime exposure remain separate concepts.
- AWS services are introduced only when they solve a concrete requirement.
- Cost and observability are architectural requirements, not post-processing concerns.
- Third-party repository code is data to inspect, never code to execute.
- Natural-language planning must not receive unrestricted SQL authority.

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

## Threat intelligence data platform

Threat-intelligence sources are integrated source by source rather than forced into one generic ingestion design.

Current status:

```text
FIRST EPSS                 IMPLEMENTED through Athena
CISA KEV                   IMPLEMENTED through Athena
NVD / CVE                  BOOTSTRAP + INCREMENTAL BRONZE CONTRACT IMPLEMENTED
GitHub Security Advisories NOT STARTED
EPSS historical expansion  PENDING PHASE 2 WORK
```

Logical flow:

```text
external source
    |
    v
source-specific ingestion
    |
    v
S3 Bronze
immutable source evidence
    |
    v
deterministic validation / normalization
    |
    v
S3 Silver
analytical Parquet
    |
    v
Glue Data Catalog
    |
    v
Athena
```

Not every source is required to use the same schedule, Lambda shape, transformation engine, retry pattern, or partition model.

---

## NVD CVE Bootstrap Bronze

Phase 2.3B implements immutable Bronze bootstrap ingestion for NVD CVE JSON 2.0 yearly feeds.

The runtime path is:

```text
NVD yearly-feed META
    |
    v
NVD Bootstrap Lambda
    |
    +--> bounded META fetch
    +--> META contract validation
    |
    v
NVD yearly-feed GZ
    |
    +--> bounded gzip fetch
    +--> compressed-size verification
    +--> streaming decompression
    +--> uncompressed-size verification
    +--> source SHA-256 verification
    |
    v
deterministic feed revision
    |
    v
conditional S3 PutObject
    |
    +--> exact yearly-feed gzip
    +--> exact META bytes
    |
    v
completion manifest written last
```

Canonical Bronze layout:

```text
bronze/nvd/cve/bootstrap/
    feed_year=YYYY/
        feed_revision=<source-revision>/
            nvdcve-2.0-YYYY.json.gz
            nvdcve-2.0-YYYY.meta
            manifest.json
```

The feed revision combines the normalized NVD source modification timestamp with the source SHA-256.

The completion manifest binds the logical ingestion result to the exact immutable S3 `VersionId` values of the feed and META objects.

Bronze writes use:

```text
PutObject If-None-Match: *
```

A `412 PreconditionFailed` is treated as a possible duplicate, not automatically as success. The runtime reads the existing object metadata and verifies expected size and cryptographic evidence before returning `already_exists`.

The validated 2026 feed revision is:

```text
feed year:           2026
source modified:     2026-08-18T07:00:12Z
source SHA-256:      10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f
gzip bytes:          23938173
uncompressed bytes:  282112001
```

The first real AWS ingestion created exactly three object versions. A same-source replay returned `already_exists` for all three objects while preserving the same `VersionId` values and creating no additional S3 object versions.

The first real deployment also exposed an HTTP content-negotiation incompatibility: the NVD gzip endpoint returned HTTP `406` for `Accept: application/octet-stream`. The adapter was corrected to use `Accept: */*`; integrity remains independently enforced through gzip, size, and SHA-256 verification.

Validated Lambda configuration:

```text
function:  opslens-dev-nvd-bootstrap-ingestion
runtime:   python3.13
memory:    1024 MB
timeout:   180 seconds
X-Ray:     Active
```

Phase 2.3C adds the deterministic incremental CVE API 2.0 Bronze contract.

The logical application path is:

```text
committed boundary T0
    |
    v
closed lastModified window [T0, T1]
    |
    v
NVD CVE API 2.0 pages
    |
    +--> bounded HTTP retrieval
    +--> polite request pacing
    +--> bounded retry for transient failures
    |
    v
complete pagination validation
    |
    +--> stable totalResults
    +--> contiguous startIndex
    +--> duplicate-CVE rejection
    +--> complete terminal coverage
    |
    v
immutable Bronze response pages
    |
    v
COMPLETE manifest written last
    |
    v
Bronze-complete watermark candidate
    |
    X
authoritative watermark is not advanced yet
```

Canonical incremental Bronze layout:

```text
bronze/nvd/cve/updates/
    update_id=<deterministic-window-identity>/
        page_start=000000/
            response.json
        page_start=002000/
            response.json
        ...
        manifest.json
```

The logical `update_id` is derived only from the normalized closed
last-modified window. Runtime timestamps, Lambda invocation identifiers,
ETags, and persistence outcomes do not participate in logical identity.

Each response page preserves the exact API bytes and SHA-256 evidence.
Bronze persistence uses conditional S3 object creation. A replay collision
is valid only after the existing object size, content type, provenance
metadata, SHA-256, and exact S3 `VersionId` have been verified.

The COMPLETE manifest binds the run to every persisted page key, SHA-256,
byte size, source pagination evidence, and exact S3 `VersionId`. It is
written only after all validated pages have been created or verified.

Phase 2.3C deliberately separates Bronze completion from authoritative
watermark commitment. The resulting candidate is `bronze_complete` and
proposes `T1`, but committed state must remain at `T0` until deterministic
Silver processing succeeds.

No new Lambda, EventBridge Scheduler, Terraform runtime, Glue table, or
Athena resource is introduced by Phase 2.3C. Runtime deployment remains
deferred to the later NVD runtime increment.

Not yet implemented:

```text
NVD versioned Silver contract
authoritative watermark promotion after Silver success
incremental AWS runtime deployment
NVD Glue tables
NVD Athena queries
```

The next increment is Phase 2.3D — Versioned Silver Contract.

---

## CISA KEV ingestion

The CISA Known Exploited Vulnerabilities JSON catalog is ingested independently from the EPSS transformation path.

The ingestion Lambda:

- performs a bounded HTTP fetch;
- validates UTF-8 JSON;
- validates the top-level source contract;
- requires `catalogVersion`, `dateReleased`, `count`, and `vulnerabilities`;
- verifies `count == len(vulnerabilities)`;
- calculates SHA-256 over the exact source bytes;
- preserves the exact source bytes in Bronze;
- writes with `If-None-Match: *` for idempotency.

Canonical key:

```text
bronze/kev/snapshot_date=YYYY-MM-DD/known_exploited_vulnerabilities.json
```

For KEV, `snapshot_date` is the UTC date on which OpsLens first successfully preserved the source. It is distinct from CISA `dateReleased` and vulnerability-level `dateAdded`.

Validated 2026-08-17 canonical snapshot:

```text
catalogVersion: 2026.08.14
records:        1665
bytes:          1583171
SHA-256:        52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

Repeated ingestion returns `already_exists` without creating another object version.

### Daily snapshot semantics

The first successful observation for a UTC date becomes the canonical Bronze evidence for that date:

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

The 2026-08-17 validation demonstrated:

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

Capturing intraday source revisions is intentionally outside the current Phase 2.1 contract.

---

## CISA KEV Silver transformation

KEV Silver converts validated Bronze evidence into a deterministic analytical dataset.

Canonical key:

```text
silver/kev/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

The runtime path is:

```text
S3 ObjectCreated:Put event
    |
    v
parse and validate event
    |
    v
read exact Bronze VersionId
    |
    v
verify bucket/key/version/ETag/size
    |
    v
verify Bronze metadata and payload provenance
    |
    v
normalize deterministic KEV records
    |
    v
serialize explicit Arrow schema to Parquet
    |
    v
conditional Silver PutObject
```

### Exact-version evidence

The KEV Silver runtime uses `s3:GetObjectVersion` for the exact `VersionId` referenced by the S3 event.

It does not read an unversioned “latest object” and then assume it is the event source.

The adapter cross-validates:

```text
bucket
object key
VersionId
ETag
content length
Bronze metadata
source SHA-256
```

Any mismatch fails closed before Silver persistence.

### Silver idempotency

Silver persistence uses:

```text
PutObject If-None-Match: *
```

Result semantics:

```text
created
    -> success

412 PreconditionFailed
    -> already_exists
    -> safe duplicate delivery

409 or unexpected S3 failure
    -> error
```

The bucket is versioned, so idempotency is verified by comparing S3 object-version counts, not merely by checking whether a key exists.

A replay of the validated Bronze event returned `already_exists` while the Silver object remained at one version with the same `VersionId`.

---

## CISA KEV Silver contract

The validated Silver record contains 16 physical Parquet columns. `snapshot_date` remains in the S3 partition path rather than the Parquet payload.

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

Contract rules include:

- canonical CVE syntax;
- canonical CWE syntax when present;
- empty CWE lists are allowed;
- duplicate CVEs in one source snapshot fail closed;
- unsupported `known_ransomware_campaign_use` values fail closed;
- additive source fields may be ignored until explicitly adopted;
- source order is preserved;
- Bronze metadata and payload provenance must agree.

Validated 2026-08-17 Silver artifact:

```text
rows:               1665
columns:            16
size:               257331 bytes
schema version:     1
Known ransomware:   349
Unknown ransomware: 1316
empty CWE lists:    171
```

The persisted object was downloaded from S3 and independently inspected with PyArrow.

---

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

The dedicated Scheduler execution role can invoke only the KEV ingestion Lambda.

Its trust relationship is constrained by:

- `scheduler.amazonaws.com`;
- exact AWS account;
- exact KEV schedule-group ARN.

Scheduler delivery retries and Lambda asynchronous processing retries are separate failure boundaries.

---

## S3 event wiring

The data bucket has one Terraform-managed bucket-notification configuration containing both EPSS and KEV Silver routes.

```text
bronze/epss/*
    -> EPSS Silver Lambda

bronze/kev/*known_exploited_vulnerabilities.json
    -> KEV Silver Lambda
```

The KEV rule uses:

```text
event:  s3:ObjectCreated:Put
prefix: bronze/kev/
suffix: known_exploited_vulnerabilities.json
```

The Silver output is written under `silver/kev/`, preventing a recursive notification loop.

S3 can invoke the KEV Silver Lambda only from the expected data bucket and AWS account.

---

## Failure recovery

EPSS Silver, KEV ingestion, and KEV Silver use bounded Lambda asynchronous processing with source-specific SQS OnFailure destinations.

### KEV ingestion failure lab

A controlled invalid same-origin source URL produced:

```text
3 Lambda attempts
KevSourceUnavailableError
RetriesExhausted
SQS OnFailure record
preserved correlation data
successful recovery after restoring the canonical source
```

### KEV Silver fail-closed lab

A parser-valid event was submitted with the correct Bronze `VersionId` but an intentionally incorrect ETag.

The runtime:

```text
accepted asynchronous invocation
    |
    v
read exact Bronze object version
    |
    v
detected event/S3 ETag mismatch
    |
    v
KevBronzeEvidenceMismatchError
    |
    v
initial attempt + 2 retries
    |
    v
RetriesExhausted
approximateInvokeCount = 3
    |
    v
SQS OnFailure invocation record
```

The failure record preserved the original request payload and reported:

```text
condition:       RetriesExhausted
functionError:   Unhandled
errorType:       KevBronzeEvidenceMismatchError
```

The Silver object remained unchanged:

```text
versions before: 1
versions after:  1
VersionId:       unchanged
```

This demonstrates the core rule:

> Event metadata is evidence to verify, not trusted authority.

The KEV Silver runtime role may send to the exact failure queue but cannot receive, delete, or purge messages from it.

---

## Current storage model

```text
S3 data bucket
|
+-- bronze/
|   +-- epss/
|   |   +-- snapshot_date=YYYY-MM-DD/
|   |       +-- epss_scores.csv.gz
|   +-- kev/
|   |   +-- snapshot_date=YYYY-MM-DD/
|   |       +-- known_exploited_vulnerabilities.json
|   +-- nvd/
|       +-- cve/
|           +-- bootstrap/
|               +-- feed_year=YYYY/
|                   +-- feed_revision=<source-revision>/
|                       +-- nvdcve-2.0-YYYY.json.gz
|                       +-- nvdcve-2.0-YYYY.meta
|                       +-- manifest.json
|
+-- silver/
|   +-- epss/
|   |   +-- snapshot_date=YYYY-MM-DD/
|   |       +-- part-00000.parquet
|   +-- kev/
|       +-- snapshot_date=YYYY-MM-DD/
|           +-- part-00000.parquet
|
+-- athena-results/
```

Bronze preserves source-native or minimally altered immutable evidence.

Silver uses typed Parquet where analytical access benefits from columnar storage.

Apache Iceberg is not a default choice and will be introduced only if later update/delete/schema-evolution requirements justify the added complexity.

---

## IAM architecture

IAM follows least privilege and separates deployment from runtime identities.

Current pattern:

```text
GitHub OIDC role
    -> infrastructure deployment permissions

Ingestion Lambda role
    -> exact Bronze write scope
    -> failure destination send
    -> telemetry

Silver Lambda role
    -> exact Bronze read scope
    -> exact Silver write scope
    -> exact failure destination send
    -> telemetry

Scheduler execution role
    -> exact Lambda InvokeFunction
```

### NVD Bootstrap runtime role

The NVD Bootstrap runtime role is source-scoped:

```text
s3:GetObject -> bronze/nvd/cve/bootstrap/*
s3:PutObject -> bronze/nvd/cve/bootstrap/*
CloudWatch Logs
X-Ray telemetry
```

`s3:GetObject` is required to verify an existing object after a conditional-write collision.

It does not receive:

```text
s3:ListBucket
s3:DeleteObject
s3:*
Glue permissions
Athena permissions
Scheduler permissions
```

### KEV Silver runtime role

The KEV Silver role is intentionally narrow:

```text
s3:GetObjectVersion -> bronze/kev/*
s3:PutObject        -> silver/kev/*
sqs:SendMessage     -> KEV Silver failure queue
CloudWatch Logs     -> KEV Silver log group
X-Ray telemetry     -> tracing APIs
```

It does not receive:

```text
s3:GetObject
s3:ListBucket
s3:DeleteObject
s3:*
sqs:*
```

---

## Observability

The runtime uses:

- AWS Lambda Powertools;
- structured CloudWatch Logs;
- custom CloudWatch Metrics;
- AWS Lambda platform metrics;
- EventBridge Scheduler metrics;
- AWS X-Ray.

The first real KEV Silver transformation observed:

```text
configured memory:  1024 MB
max memory used:     176 MB
duration:             795.365 ms
billed duration:      2112 ms
rows transformed:     1665
```

A warm idempotent replay observed a maximum of 194 MB used.

Right-sizing is intentionally deferred until additional natural runtime evidence is available.

Telemetry should support diagnosis without indiscriminate sensitive-data capture.

Avoid full prompt, retrieved-chunk, or model-response logging by default in later GenAI phases.

---

## Cost architecture

Portfolio budget target:

```text
normal:       USD 15-30 / month
warning:      ~USD 30 / month
hard concern: USD 40-50 / month
```

Current architectural controls include:

- serverless/on-demand services where appropriate;
- S3 lifecycle policies;
- Parquet;
- partition pruning;
- Athena scan limits;
- bounded asynchronous retries;
- bounded concurrency where appropriate;
- controlled log retention;
- no unnecessary Step Functions, DynamoDB, Iceberg, or Glue crawlers.

The controlled three-attempt KEV Silver failure lab consumed approximately:

```text
2.283 GB-s of Lambda compute
```

before free-tier effects, which is negligible relative to the project budget target.

---

## Structured retrieval architecture

Structured facts belong in the analytical data plane.

Examples:

- Is CVE X in CISA KEV?
- What is the EPSS score for CVE X on a selected date?
- How has EPSS changed over time?
- What is the CVSS severity?
- Which advisories reference a CVE?

The future natural-language path must not provide unrestricted SQL authority:

```text
User question
    |
    v
LLM planner
    |
    v
Typed Semantic Query
    |
    v
Deterministic Validator
    |
    v
Application-owned SQL Compiler
    |
    v
Athena Workgroup
```

Controls must include:

- metric allowlist;
- dimension allowlist;
- typed filters;
- explicit sort and limit rules;
- partition pruning;
- Athena scan limits;
- read-only IAM;
- bounded query count.

---

## Deterministic correlation engine

Package-to-vulnerability applicability is application logic, not model reasoning.

Target flow:

```text
ecosystem
+ package
+ version
+ purl
    |
    v
normalization
    |
    v
alias resolution
    |
    v
version-range matching
    |
    v
affected / not affected
    |
    v
match evidence
```

The engine must emit evidence such as:

```text
normalized package identity
observed version
matched vulnerability identifier
matched vulnerable range
known fixed version
source identifiers
```

LLMs may explain the result but cannot determine applicability.

---

## Repository intelligence boundary

Repository analysis is a data-reading workflow.

Never execute third-party repository code as part of analysis:

```text
git clone + build
pip install
uv sync
npm install
make
Dockerfile
pytest
setup.py
repository scripts
repository GitHub Actions
```

Prefer bounded API-based evidence such as:

```text
GitHub API
    |
    v
repository metadata
    |
    v
dependency graph / SPDX SBOM
```

Initial repository boundary:

- GitHub only;
- public repositories only;
- one repository per analysis;
- default branch preferred;
- no arbitrary source URL fetching;
- repository content treated as untrusted input.

Repository risk must remain distinct from runtime exposure evidence.

---

## Knowledge and hybrid retrieval

Text-centric evidence such as remediation guidance, release notes, and advisory documentation belongs in a knowledge-retrieval path.

Future preferred pattern:

```text
Retrieve
+ application-owned context assembly
+ application-owned synthesis
```

Hybrid retrieval should constrain semantic retrieval with structured evidence whenever possible:

```text
structured facts
    -> narrow CVE/package scope
    -> semantic retrieval
    -> deterministic evidence validation
    -> synthesis
```

This reduces irrelevant retrieval and limits the amount of untrusted text presented to the model.

---

## Evidence validation

Evidence Validator is deterministic code, not an agent.

It verifies claims such as:

```text
Does the CVE exist?
Does the repository dependency exist?
Does the version match?
Does KEV status match the selected snapshot/source?
Does EPSS match the selected snapshot?
Does the advisory exist?
Does the Inspector finding exist?
Does every cited source exist?
```

Target position:

```text
retrieval / tools
    |
    v
evidence assembly
    |
    v
Evidence Validator
    |
    +-- valid -> synthesis
    +-- invalid -> reject / degrade / repair
```

---

## Agent architecture boundary

Multi-agent architecture is intentionally deferred until a single bounded agent baseline has been evaluated.

Potential future specializations include:

```text
Exposure Agent
Threat Intelligence Agent
Remediation Agent
Supervisor
```

The deterministic Evidence Validator remains outside the agent authority boundary.

A2A and MCP are future protocol choices for real service/capability boundaries, not replacements for ordinary local function calls.

```text
A2A = agent-to-agent communication
MCP = agent-to-capability communication
```

Amazon Bedrock AgentCore is also a later-phase integration and must not replace explicit application control over authorization, evidence validation, limits, observability, identity, or protocol boundaries.

---

## Runtime exposure boundary

Amazon Inspector belongs to a separate evidence plane.

```text
Repository Risk
repository -> dependencies -> vulnerabilities -> risk intelligence

Runtime Exposure
AWS workload -> Inspector finding -> exposure evidence
```

Repository evidence may say a dependency version appears vulnerable.

OpsLens must not claim that the vulnerable component is deployed in production without separate runtime evidence.

---

## What is intentionally not implemented yet

- CISA KEV Glue/Athena analytical registration;
- NVD/CVE ingestion;
- GitHub Security Advisory ingestion;
- historical EPSS expansion required for Phase 2 closure;
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
- Amazon Inspector runtime exposure;
- public repository-analysis API boundary.

---

## Phase boundary

Completed:

```text
Phase 0 — AWS Foundation
Phase 1 — EPSS Vertical Slice
```

Phase 2 — Threat Intelligence Data Lake is in progress:

```text
CISA KEV Bronze ingestion:          COMPLETE
CISA KEV Silver contract/runtime:   COMPLETE
CISA KEV AWS operationalization:    COMPLETE
CISA KEV Glue/Athena registration:  NEXT
NVD/CVE source slice:               NOT STARTED
GitHub Security Advisories:         NOT STARTED
EPSS historical expansion:          PENDING
```

The next architecture increment is the KEV analytical contract in Glue/Athena.

Questions to answer before implementation:

```text
What exact Glue schema represents the validated Parquet contract?
How is snapshot_date projected?
How does a query explicitly select temporal evidence?
How is query scan bounded by the existing Athena workgroup?
What query proves deterministic KEV membership for a CVE?
How is the Athena result cross-checked against the persisted Parquet?
What scan and cost evidence are recorded?
```

The first target structured question is:

> Is CVE X present in CISA KEV for a specific snapshot?

Do not start all remaining Phase 2 sources simultaneously.

---

## Target end-state

```text
Threat Intelligence Sources
        |
        v
Threat Intelligence Data Platform
S3 -> Glue -> Athena
        |
        +--------------------+
        |                    |
        v                    v
Structured Retrieval     Knowledge Retrieval
        |                    |
        +---------+----------+
                  |
                  v
          Hybrid Evidence
                  |
                  v
     Deterministic Evidence Validator
                  |
                  v
           Bounded Agent Layer
                  |
                  v
      Public investigation interface
```

Cross-cutting concerns remain:

```text
IAM / authorization
security
observability
cost controls
evaluation
failure recovery
```

The sequencing matters:

```text
evidence
    -> deterministic normalization
    -> structured analytics
    -> correlation
    -> risk policy
    -> retrieval
    -> evidence validation
    -> bounded generative reasoning
    -> agents only when justified
```

That ordering is intentional: OpsLens should never depend on an LLM to establish facts that deterministic code and source evidence can prove.
