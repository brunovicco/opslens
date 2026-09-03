<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Deterministic Software Supply Chain & Threat Intelligence on AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Deterministic Evidence · AWS Serverless · Security Automation**

</div>

OpsLens is an open-source software supply chain intelligence platform built on AWS.

It is designed to answer:

> Given the software I actually use, which vulnerabilities affect it, what evidence proves that, and which findings should I prioritize?

The project deliberately establishes deterministic evidence, provenance, package/version correlation, least-privilege boundaries, observability, failure recovery, and cost controls before introducing generative or agentic reasoning.

> **Agents reason. Code verifies evidence.**

## Current status

| Phase | Scope | Status |
| --- | --- | --- |
| Phase 0 | AWS Foundation | ✅ Complete |
| Phase 1 | EPSS Vertical Slice | ✅ Complete |
| Phase 2 | Threat Intelligence Data Lake | ✅ Complete |
| Phase 3 | Vulnerability Correlation Engine | ✅ Complete |
| Phase 4 | Repository Intelligence | ✅ Complete |
| Phase 5 | Risk Prioritization Engine | ✅ Complete |
| Phase 6 | Semantic Query Layer | 🚧 Next |

Latest implementation checkpoint:

```text
81a2e78a3e8329aa811c20012bc565f35f1a87e5
```

See [Current State](docs/current-state.md) and [Roadmap](docs/roadmap.md) for the detailed status.

## What OpsLens can do today

The implemented deterministic path can analyze a supported public GitHub repository snapshot without executing repository code and then prioritize its already-proven findings through a versioned deterministic policy:

```text
public GitHub repository
        |
        v
immutable repository identity
exact commit + tree SHA
        |
        v
bounded GET-only GitHub REST acquisition
        |
        v
exact inert uv.lock evidence
Git blob SHA-1 + independent SHA-256
        |
        v
deterministic tomllib parser
        |
        v
PyPI package / PEP 440 version / purl normalization
        |
        v
GHSA vulnerable-range applicability
        |
        v
CVE/GHSA <-> exact NVD evidence reconciliation
        |
        +--> all preserved NVD CVSS observations
        +--> complete-snapshot CISA KEV evidence
        +--> explicit-date FIRST EPSS evidence
        |
        v
content-addressed RepositoryAnalysisResult
        |
        v
Deterministic Risk Policy v1
        |
        v
priority score + tier + factor evidence + completeness + stable rank
```

A final repository finding can contain:

- dependency name and installed version;
- canonical purl;
- GHSA and CVE identifiers when published;
- exact matched vulnerable range;
- clause-level deterministic applicability evidence;
- first patched version when published;
- all preserved NVD CVSS observations;
- KEV state and exact positive record when present;
- EPSS state, snapshot coordinates, score and percentile when available;
- immutable repository, lockfile, advisory, NVD, KEV, and EPSS evidence references.

Phase 5 can deterministically add:

- factor-level KEV, EPSS, CVSS, and fixed-version contributions;
- priority score and P0–P3 tier;
- `complete` / `partial` evidence status;
- explicit `review_required` state;
- content-addressed policy/evaluation/prioritization identities;
- deterministic repository-level ranking.

The priority score is an explicit OpsLens policy output. It is **not** a vulnerability probability, a CVSS replacement, or runtime-exposure evidence.

## Core invariants

- Deterministic evidence and correlation first; generative reasoning second.
- **No LLM decides vulnerability applicability.**
- Risk-policy evaluation and ranking are deterministic and versioned.
- Raw source evidence is preserved before transformation.
- Exact source versions and content hashes participate in evidence identity.
- Unsupported or malformed semantics fail closed.
- Repository findings are content-addressed and reproducible.
- Third-party repository code is never executed during analysis.
- Repository Risk is not Runtime Exposure.
- Duplicate delivery is expected and replay must be safe.
- IAM least privilege and responsibility separation are architectural requirements.
- AWS services are introduced only for demonstrated requirements.
- Natural-language planning never receives unrestricted SQL authority.

## Threat Intelligence Data Lake

Phase 2 provides the deterministic threat-intelligence evidence used by later phases.

### FIRST EPSS

```text
FIRST EPSS
 -> EventBridge Scheduler
 -> EPSS ingestion Lambda
 -> S3 Bronze
 -> deterministic Silver / Parquet
 -> Glue Data Catalog
 -> Athena
```

The same canonical Silver relation also contains the completed historical EPSS interval from `2021-04-14` through `2026-08-13`, sourced from a pinned historical archive commit.

### CISA KEV

```text
CISA KEV
 -> bounded ingestion
 -> immutable Bronze
 -> exact-version Silver transformation
 -> Parquet
 -> Glue
 -> Athena
```

Presence and absence are meaningful only against an explicitly selected, fully validated catalog snapshot.

### NVD / CVE

```text
NVD yearly feeds + CVE API 2.0
 -> immutable Bronze
 -> deterministic versioned Silver
 -> Silver COMPLETE
 -> authoritative watermark
 -> permanent analytics projection
 -> Glue / Athena
```

Authority remains explicit:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

### GitHub Security Advisories

```text
GitHub reviewed advisories
 -> versioned Bronze pages + COMPLETE
 -> deterministic advisory normalization
 -> immutable one-row Parquet per advisory content version
 -> Silver COMPLETE
 -> Glue / Athena
```

GHSA source-local advisory/package/range/fix evidence remains distinct from NVD evidence even when both refer to the same CVE.

## Phase 3 — Vulnerability Correlation Engine

Phase 3 is complete for the first supported ecosystem: **PyPI**.

Implemented semantics include:

```text
PyPA package normalization
PEP 440 version parsing
canonical PyPI purl
GitHub range operators: = < <= > >=
comma-separated conjunctions
affected | not_affected | unsupported
explicit fixed-version evidence
GHSA source provenance
CVE/GHSA/NVD alias reconciliation
canonical correlation:v1@sha256:<digest> records
```

`first_patched_version` is remediation evidence. It never replaces vulnerable-range applicability.

See [Phase 3 correlation closeout](docs/labs/phase-3-correlation-engine-closeout.md).

## Phase 4 — Repository Intelligence

The current v1 repository scope is intentionally narrow:

```text
provider:        public GitHub
manifest:        uv.lock
supported deps:  canonical PyPI records
transport:       read only
code execution:  never
```

Phase 4 adds immutable repository identity, bounded GitHub transport, exact inert lockfile acquisition, deterministic parsing, Phase 3 normalization/correlation, and exact NVD/CVSS, KEV, and EPSS enrichment.

The final aggregate identity is:

```text
repository-analysis:v1@sha256:<digest>
```

This identity is also the safe future reuse/cache coordinate. A repository commit alone is insufficient because threat-intelligence evidence is temporal.

No cache backend was added in Phase 4 because no measured workload yet justifies the additional storage, invalidation, IAM, observability, and cost surface.

See [Phase 4 closeout](docs/labs/phase-4-repository-intelligence-closeout.md).

## Phase 5 — Risk Prioritization Engine

Risk Policy v1 consumes only structured evidence already proven by Phase 4.

Current contributions:

```text
CISA KEV present                    +40
EPSS >= 0.70 / 0.30 / 0.10         +30 / +20 / +10
max supported CVSS >= 9 / 7 / 4    +20 / +10 / +5
known first patched version         +10
```

Priority tiers:

```text
P0 >= 80
P1 >= 60
P2 >= 30
P3 < 30
```

The policy separately exposes evidence completeness and review requirements so missing evidence cannot silently become a low-risk conclusion.

Deterministic identities:

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

Risk Policy v1 introduces no AWS service, IAM permission, model call, persistence, or runtime cost.

See [Phase 5 closeout](docs/labs/phase-5-risk-prioritization-closeout.md) and [ADR 0019](docs/adr/0019-deterministic-risk-policy-v1.md).

## AWS foundation

```text
environment:             dev
primary workload Region: us-east-1
Infrastructure as Code:  Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
Terraform state:         Amazon S3
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

GitHub Actions stores no persistent AWS access keys. Deployment identities remain separate from runtime identities.

## Cost and security discipline

The current architecture deliberately avoids services that have not yet solved a measured requirement.

Examples:

- no Glue crawler where explicit schemas are sufficient;
- no Step Functions merely for orchestration aesthetics;
- no DynamoDB/cache backend before a demonstrated reuse workload;
- no Iceberg requirement yet;
- no vector database before a retrieval phase needs one;
- no unrestricted text-to-SQL;
- no model call in deterministic applicability, repository finding truth, or risk-policy ranking;
- Athena dev workgroup keeps a `10,485,760` byte scan cutoff.

## Quality gates

The repository currently uses:

```text
Ruff
strict Pyright
Pytest
Terraform fmt / validate
TFLint
Checkov
GitHub Actions
canonical Terraform plans
post-deployment convergence checks
```

Latest deterministic-slice validation:

```text
Risk Policy Ruff:                 PASS
Risk Policy Pyright:              0 errors / 0 warnings
Risk Policy pytest:               31 passed
Repository Intelligence Ruff:     PASS
Repository Intelligence Pyright:  0 errors / 0 warnings
Repository Intelligence pytest:   174 passed
Correlation Ruff:                 PASS
Correlation Pyright:              0 errors / 0 warnings
Correlation pytest:               116 passed
```

## Repository structure

```text
.
├── .github/
├── docs/
│   ├── adr/
│   ├── labs/
│   ├── architecture.md
│   ├── architecture.pt-br.md
│   ├── current-state.md
│   ├── roadmap.md
│   └── README.md
├── infra/
│   ├── bootstrap/
│   └── environments/dev/
├── scripts/
├── src/
│   └── opslens/
│       ├── correlation/
│       ├── repository_intelligence/
│       └── risk_policy/
├── tests/
├── README.md
├── README.pt-br.md
├── pyproject.toml
└── uv.lock
```

## Documentation

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Architecture — English](docs/architecture.md)
- [Architecture — Português](docs/architecture.pt-br.md)
- [ADR index](docs/adr/README.md)
- [Labs and operational evidence](docs/README.md)

## Next — Phase 6: Semantic Query Layer

Phase 6 introduces the first model-assisted structured-query planning boundary:

```text
User question
 -> Bedrock planner
 -> typed semantic query
 -> deterministic validation
 -> code-owned SQL compiler
 -> bounded read-only Athena workgroup
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

The first Phase 6 gate should freeze the typed semantic-query vocabulary and deterministic SQL compiler before Bedrock receives any planning authority.

---

OpsLens is intentionally built as an evidence system first and an agentic system later.
