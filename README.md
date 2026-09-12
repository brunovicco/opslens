<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Verifiable Software Supply Chain & GenAI Architecture on AWS

**Threat Intelligence · Repository Intelligence · Deterministic Risk · Bedrock RAG · Hybrid Retrieval · Agentic AI · MCP · AgentCore · A2A · Security · Evaluation · Cost Engineering**

</div>

OpsLens is an open-source AWS architecture lab and software-supply-chain intelligence project built around one principle:

> **Agents reason. Code verifies evidence.**

It answers a practical question:

> Given the software actually used by a repository, which vulnerabilities affect it, what exact evidence proves that, what should be prioritized, and what verified guidance can help act on those findings?

OpsLens deliberately separates probabilistic reasoning from deterministic authority for package identity, version applicability, vulnerability correlation, KEV/EPSS/CVSS evidence, risk policy, semantic-query admission, SQL compilation, evidence admission, tool authorization, and execution/resource limits.

> **Repository Risk != Runtime Exposure.**

## Current status

**Phases 0–18 are complete. Phase 19 is the final V1 closeout phase.**

The historical phase selected after Phase 18 remains **Phase 19 — Bounded Public Runtime & Productization**. Gate 19.9 narrows V1 completion to a demonstration-focused closeout without rewriting that retained decision.

Current protected checkpoint:

```text
main: e538fa3e96c29cf76dd3aa83a9967e090587b6fb
Gate 19.8: COMPLETE
protected merge: PR #375
post-merge CodeQL: 34713360403 / run #393 / success
Gate 19.9: IN PROGRESS / issue #376
```

Retained Gate 19.1/19.2 historical decision markers:

```text
19.1  Public Runtime Hypothesis & Launch Contract       COMPLETE
historical decision: DEFERRED_PENDING_MEASUREMENT
public-analysis-workload:v1
19.2  Representative Workload Measurement              COMPLETE
ASYNC_SUBMIT_STATUS_RESULT
```

Those markers describe the historical decision path; later Gates 19.2–19.8 superseded the pending measurement state without rewriting it.

The retained async AWS runtime has already been materialized and converged, but it remains intentionally disabled and non-public:

```text
runtime materialized: YES
public endpoint enabled: NO
submit enabled: NO
worker enabled: NO
event-source mapping enabled: NO
provider-heavy public execution: NO
```

```text
materialized != enabled
```

## V1 scope

OpsLens V1 is intentionally a **demonstration and architecture lab**, not a production SaaS.

The V1 reviewer target is:

```text
clone
 -> setup
 -> one deterministic offline demo command
 -> evidence-backed result
```

V1 completion prioritizes reproducibility, provenance, architecture clarity, meaningful failure paths, and portfolio presentation. It does **not** require Internet-facing production operations.

See [V1 Demonstration Scope](docs/v1-demonstration-scope.md) and [V1 Completion Checklist](docs/v1-completion-checklist.md).

## Architecture at a glance

```text
NVD / CISA KEV / FIRST EPSS / GitHub Security Advisories
        |
        v
source-preserving threat evidence
        |
public repository -> immutable snapshot -> inert dependency evidence
        |
        v
deterministic package/version applicability
        |
        v
GHSA/NVD/CVSS + KEV + EPSS enrichment
        |
        v
RepositoryAnalysisResult -> deterministic Risk Policy

structured fact question
        |
        v
bounded Bedrock proposal -> deterministic SemanticQuery admission
        |
        v
typed SQL compiler -> bounded read-only Athena

knowledge/remediation question
        |
        v
Bedrock Knowledge Base -> checked evidence -> bounded synthesis + citations

admitted structured + semantic evidence
        |
        v
deterministic authorization -> bounded agent reasoning
        |
        v
admitted result
```

The model may explain, classify, plan, route, or synthesize over admitted evidence. It does not own package identity, vulnerability applicability, provenance, risk policy, arbitrary SQL, or execution authorization.

## Public repository safety boundary

OpsLens treats repository content as untrusted data.

```text
READ, NEVER EXECUTE third-party repository code.
```

The project does not run package managers, builds, tests, setup hooks, Dockerfiles, workflows, or repository scripts as part of repository analysis.

## Phase 19 lineage

```text
19.1  Public Runtime Hypothesis & Launch Contract              COMPLETE
19.2  Representative Workload Measurement                     COMPLETE
19.3  Concrete Async Topology Contract                         COMPLETE
19.4  Disabled Async Runtime Implementation                    COMPLETE
19.5  Immutable Async Deployment Artifacts                     COMPLETE
19.6  Exact Terraform Plan & Offline Admission                 COMPLETE
19.7  Controlled Disabled Runtime Materialization              COMPLETE
19.8  Request-time Threat Evidence Authority Contract          COMPLETE
19.9  V1 Demonstration Closeout Contract                       IN PROGRESS
19.10 Deterministic End-to-End Demo Runner                     PLANNED
19.11 Curated Demo Scenarios + Deterministic Evaluation        PLANNED
19.12 Minimal Local Visual Demo                                PLANNED
19.13 Portfolio / README / Architecture Polish                 PLANNED
19.14 V1 Closeout + Release Readiness                          PLANNED
```

### Retained Phase 19 AWS topology

```text
HTTP API
 -> API Lambda
 -> DynamoDB job/idempotency authority
 -> SQS standard queue
 -> Lambda worker
 -> DynamoDB status/result
 -> SQS DLQ
```

That runtime shape is retained as architecture/deployment evidence. V1 does not require enabling it publicly.

## Request-time threat evidence authority

Gate 19.8 introduced a provider-neutral application boundary:

```text
PublicRepositoryEvidenceExecution
 -> PublicThreatEvidenceScope
 -> PublicThreatEvidenceRequest
 -> PublicThreatEvidenceAuthority
 -> exact GHSA/NVD/KEV/EPSS evidence + provenance
 -> deterministic correlation/enrichment
```

Important semantics:

```text
scope derives only from admitted repository evidence
incomplete package normalization -> fail closed
out-of-scope threat evidence -> reject
latest_complete = selection policy, not provenance
missing evidence != benign evidence
model authority for applicability/source truth = none
```

A provider-backed arbitrary request-time adapter remains a Post-V1 experiment because the canonical V1 demonstration is offline-first.

## Measured evidence

OpsLens separates measured, derived, configured, and unmeasured evidence.

The retained Phase 19 representative workload measured:

| Metric | Evidence |
| --- | ---: |
| End-to-end duration | 17,748 ms |
| Serialized result | 5,285 bytes |
| GitHub physical HTTP requests | 4 measured |
| Bedrock Retrieve calls | 1 measured |
| Bedrock Retrieve client elapsed | 4,148 ms |
| Bedrock model calls | 1 measured |
| Bedrock input tokens | 5,936 |
| Bedrock output tokens | 408 |
| Bedrock model client elapsed | 8,901 ms |
| Bedrock provider latency | 7,772 ms |
| Retries | 0 measured |
| Throttle count | UNMEASURED |

These are bounded experiment measurements, not production SLO or production TCO claims.

## What the project demonstrates

OpsLens includes retained evidence for:

- AWS foundations and least-privilege IAM;
- NVD, GitHub Advisories, CISA KEV, and FIRST EPSS source handling;
- immutable public-repository evidence;
- deterministic PyPI/PEP 440 vulnerability correlation;
- deterministic risk prioritization;
- bounded semantic query planning with deterministic SQL compilation;
- Bedrock Knowledge Bases and S3 Vectors;
- hybrid retrieval and grounded synthesis;
- single-agent and measured multi-agent experiments;
- MCP and A2A bounded interoperability experiments;
- AgentCore capability-fit experimentation;
- runtime exposure evidence with Amazon Inspector;
- observability and content-minimized telemetry;
- adversarial/security authority regression;
- evaluation and cost evidence;
- immutable Lambda deployment artifacts;
- exact Terraform plan admission;
- controlled runtime materialization and convergence;
- deterministic request-time threat-evidence authority contracts.

## V1 remaining work

The remaining work is intentionally small and demonstration-focused:

```text
Gate 19.9   freeze V1 contract and synchronize current state
Gate 19.10  canonical deterministic demo runner
Gate 19.11  three curated scenarios + regression evaluation
Gate 19.12  minimal local visual demo
Gate 19.13  final portfolio/architecture presentation polish
Gate 19.14  close Phase 19 and prepare v1.0.0 release
```

The planned canonical demo target is approximately:

```bash
uv sync --frozen
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
```

The exact command is owned by Gate 19.10 and may change before implementation is merged.

## V1 non-goals

The first release does not require:

```text
Internet-facing production runtime
authentication / OIDC / Cognito
multi-tenancy
commercial quotas or billing
custom public domain
WAF or production abuse controls
24x7 operations
production SLO/SLA
HA/DR program
production TCO claim
public worker/event-source enablement
```

See [Post-V1 / Experiments Backlog](docs/post-v1-backlog.md).

## Documentation

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [V1 Demonstration Scope](docs/v1-demonstration-scope.md)
- [V1 Completion Checklist](docs/v1-completion-checklist.md)
- [Demo Area](docs/demo/README.md)
- [Architecture](docs/architecture.md)
- [Portfolio Evidence](docs/portfolio-evidence.md)
- [AIP-C01 Learning Map](docs/aip-c01-learning-map.md)
- [Architecture Decision Records](docs/adr/README.md)

## Permanent engineering rules

```text
Agents reason. Code verifies evidence.
Not every question is a RAG problem.
Structured facts use structured retrieval.
No unrestricted text-to-SQL.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
retrieved content != instruction authority
model proposal != authorization
tool/protocol success != business truth
historical evidence != standing authority
missing evidence != benign evidence
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
artifact hash != S3 VersionId
publication success != deployment authorization
plan != apply
materialized != enabled
demonstration readiness != production readiness
AIP-C01 topic != product requirement
```

## License

Apache License 2.0.
