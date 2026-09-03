<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Deterministic Software Supply Chain & Threat Intelligence on AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Deterministic Evidence · AWS Serverless**

</div>

OpsLens is an open-source software supply chain intelligence platform built on AWS.

It is designed to answer:

> Given the software I actually use, which vulnerabilities affect it, what evidence proves that, and which findings should I prioritize?

The project deliberately establishes deterministic evidence, provenance, package/version correlation, risk-policy enforcement, least-privilege boundaries, observability, failure recovery, and cost controls before introducing semantic, generative, or agentic reasoning.

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

Latest implementation checkpoint before the Phase 5 documentation closeout:

```text
81a2e78a3e8329aa811c20012bc565f35f1a87e5
```

See [Current State](docs/current-state.md) and [Roadmap](docs/roadmap.md) for detailed status.

## What OpsLens can do today

The current deterministic path can analyze a supported public GitHub repository snapshot without executing repository code, correlate locked PyPI dependencies to exact GHSA vulnerable ranges, enrich affected findings with source-preserving threat intelligence, and prioritize them through an explicit versioned policy.

```text
NVD / CVE -----------+
CISA KEV ------------+
FIRST EPSS ----------+----> source-preserving threat evidence
GitHub Advisories ---+
                              |
                              v
public GitHub repository
 -> immutable repository snapshot
 -> bounded GET-only acquisition
 -> exact inert uv.lock evidence
 -> deterministic tomllib parsing
 -> PyPI / PEP 440 / purl normalization
 -> GHSA vulnerable-range applicability
 -> exact NVD/CVSS enrichment
 -> complete-snapshot CISA KEV evidence
 -> explicit FIRST EPSS snapshot evidence
 -> content-addressed RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> factor contributions
 -> priority score / tier / completeness
 -> content-addressed RiskPrioritizationResult
```

No third-party repository code is executed.

## Core invariants

- Deterministic evidence and correlation first; model reasoning later.
- **No LLM decides vulnerability applicability.**
- **Risk policy evaluation is deterministic.**
- Raw source evidence is preserved before transformation.
- Exact source versions and content hashes participate in evidence identity.
- Unsupported or malformed semantics fail closed.
- Third-party repository code is never executed during analysis.
- Repository Risk is not Runtime Exposure.
- Missing evidence is not silently interpreted as benign evidence.
- Duplicate delivery is expected and replay must be safe.
- IAM least privilege and responsibility separation are architectural requirements.
- AWS services are introduced only for demonstrated requirements.
- Natural-language planning never receives unrestricted SQL authority.

## Threat Intelligence Data Lake — Phase 2

Phase 2 provides the deterministic threat-intelligence evidence consumed by later phases.

### FIRST EPSS

```text
FIRST EPSS
 -> EventBridge Scheduler
 -> Lambda ingestion
 -> S3 Bronze
 -> deterministic Silver / Parquet
 -> Glue Data Catalog
 -> Athena
```

The canonical Silver relation also contains the completed historical interval from `2021-04-14` through `2026-08-13` under a pinned historical archive commit.

### CISA KEV

```text
CISA KEV
 -> bounded ingestion
 -> immutable Bronze
 -> deterministic Silver
 -> Parquet
 -> Glue
 -> Athena
```

KEV presence or absence is meaningful only against an explicitly selected, fully validated catalog snapshot.

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
 -> immutable advisory-version Silver
 -> Silver COMPLETE
 -> Glue / Athena
```

GHSA package/range/fix evidence remains source-local even when the same CVE is independently observed by NVD.

## Vulnerability Correlation Engine — Phase 3

Phase 3 is complete for the first supported ecosystem: **PyPI**.

Implemented semantics include:

```text
PyPA package normalization
PEP 440 concrete versions
canonical PyPI purl
GHSA range operators: = < <= > >=
affected | not_affected | unsupported
first-patched-version evidence
exact GHSA occurrence provenance
CVE/GHSA/NVD reconciliation
correlation:v1@sha256:<digest>
```

`first_patched_version` is remediation evidence. It never replaces vulnerable-range applicability.

See [Phase 3 correlation closeout](docs/labs/phase-3-correlation-engine-closeout.md).

## Repository Intelligence — Phase 4

The v1 repository scope is intentionally narrow:

```text
provider:        public GitHub
repository file: root-level uv.lock
supported deps:  canonical PyPI records
transport:       read only
code execution:  never
```

The repository authority is an immutable GitHub numeric repository identity plus exact commit SHA. Dependency reads are bound to that commit, not to a moving branch name.

The final Phase 4 aggregate identity is:

```text
repository-analysis:v1@sha256:<digest>
```

A repository commit alone is not a safe future cache key because selected KEV/EPSS evidence is temporal. Phase 4 therefore deferred cache infrastructure until a measured workload justifies storage, invalidation, IAM, observability, and cost.

See [Phase 4 Repository Intelligence closeout](docs/labs/phase-4-repository-intelligence-closeout.md).

## Risk Prioritization Engine — Phase 5

Phase 5 is complete with a separate deterministic **Risk Policy v1**.

The policy consumes only facts already established by Phase 4:

```text
KEV present                         +40
EPSS >= 0.70 / 0.30 / 0.10          +30 / +20 / +10
max supported CVSS >= 9 / 7 / 4     +20 / +10 / +5
known fixed version                 +10
maximum                              100
```

Priority tiers:

```text
P0 >= 80
P1 >= 60
P2 >= 30
P3 < 30
```

This is an OpsLens **priority score**. It is not exploit probability, a CVSS replacement, a KEV/EPSS rewrite, or a runtime-exposure score.

The CVSS maximum is an explicit downstream policy aggregation. Original NVD CVSS observations remain preserved.

Missing evidence remains explicit:

```text
complete negative evidence
  KEV absent in complete catalog
  EPSS score absent in complete snapshot

partial / review_required
  CVE unavailable
  no supported CVSS evidence
  unsupported future CVSS family
```

Content-addressed policy identities:

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

Equal-score findings use a stable opaque ID only as a deterministic tie breaker; the tie breaker carries no risk semantics.

Phase 5 added **zero AWS resources, zero IAM permissions, and zero model calls**.

See [Phase 5 Risk Policy closeout](docs/labs/phase-5-risk-policy-closeout.md) and [ADR 0019](docs/adr/0019-deterministic-risk-policy-v1.md).

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

The architecture deliberately avoids services that have not yet solved a measured requirement.

Examples:

- no Glue crawler where explicit schemas are sufficient;
- no Step Functions merely for orchestration aesthetics;
- no DynamoDB/cache backend before a demonstrated reuse workload;
- no Iceberg requirement yet;
- no vector database before a retrieval phase needs one;
- no Bedrock call in deterministic applicability or prioritization;
- no unrestricted text-to-SQL;
- Athena dev workgroup enforces a `10,485,760` byte scan cutoff.

## Quality gates

Dedicated deterministic CI slices now cover:

```text
Correlation
Repository Intelligence
Risk Policy
```

Phase 5 closeout validation:

```text
Risk Policy Ruff:                 PASS
Risk Policy Pyright:              0 errors / 0 warnings
Risk Policy pytest:               31 passed
Repository Intelligence pytest:   174 passed
Correlation pytest:               116 passed
```

AWS-bearing changes additionally use Terraform fmt/validate, TFLint, Checkov, canonical plans, deployment verification, and post-apply convergence checks.

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

Phase 6 introduces the first FM planner in the current roadmap sequence:

```text
User question
 -> Bedrock planner
 -> typed SemanticQuery
 -> deterministic validation
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured evidence
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

Before Phase 6 code is written, current official Amazon Bedrock and Athena documentation must be checked for APIs, model availability, IAM behavior, limits, and pricing. The first implementation should freeze a deliberately small typed semantic-query contract before any API, UI, RAG, or agent integration.

---

OpsLens is intentionally built as an evidence system first and an agentic system later.
