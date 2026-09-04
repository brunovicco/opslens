# OpsLens — Incremental Roadmap

_Last updated: 2026-09-04_

OpsLens advances in small, demonstrable, observable, and reversible gates.

Default engineering loop:

```text
concept
 -> architecture decision
 -> IAM / trust boundary when applicable
 -> implementation
 -> success test
 -> failure test
 -> observability
 -> cost
 -> documentation / ADR
 -> logical merge
```

## Current roadmap status

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | AWS Foundation | ✅ Complete |
| 1 | EPSS Vertical Slice | ✅ Complete |
| 2 | Threat Intelligence Data Lake | ✅ Complete |
| 3 | Vulnerability Correlation Engine | ✅ Complete |
| 4 | Repository Intelligence | ✅ Complete |
| 5 | Risk Prioritization Engine | ✅ Complete |
| 6 | Semantic Query Layer | 🚧 In progress — Gates 6.1 and 6.2 complete |
| 7 | Knowledge Retrieval with Bedrock | ⏳ Planned |
| 8 | Hybrid Retrieval | ⏳ Planned |
| 9 | Public Analyze Your Repository | ⏳ Planned |
| 10 | Observability & Operational Excellence | ⏳ Planned |
| 11 | Single-Agent Baseline | ⏳ Planned |
| 12 | Multi-Agent Architecture | ⏳ Planned |
| 13 | MCP | ⏳ Planned |
| 14 | Amazon Bedrock AgentCore | ⏳ Planned |
| 15 | A2A | ⏳ Planned |
| 16 | Runtime Exposure with Amazon Inspector | ⏳ Planned |
| 17 | Security Hardening | ⏳ Planned |
| 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

## Completed foundation

### Phase 0 — AWS Foundation

Established the real `dev` environment, Terraform remote state, IAM Identity Center human access, GitHub Actions OIDC deployment identity, least-privilege runtime roles, budget/cost controls, CloudWatch, X-Ray, and intentional failure-path validation.

### Phase 1 — EPSS Vertical Slice

Implemented the first complete threat-intelligence path:

```text
FIRST EPSS
 -> EventBridge Scheduler
 -> Lambda ingestion
 -> S3 Bronze
 -> deterministic Silver / Parquet
 -> Glue Data Catalog
 -> Athena
```

### Phase 2 — Threat Intelligence Data Lake

Completed:

```text
2.1 CISA KEV Bronze                         COMPLETE
2.2 CISA KEV Silver / Analytics             COMPLETE
2.3 NVD/CVE deterministic authority path    COMPLETE
2.4 GitHub Security Advisories              COMPLETE
2.5 Historical EPSS expansion               COMPLETE
```

Phase 2 preserves independent source authority and explicit temporal/provenance coordinates for NVD, KEV, EPSS, and GHSA.

### Phase 3 — Vulnerability Correlation Engine

Completed the deterministic PyPI v1 applicability authority:

```text
ecosystem/package/version/purl
 + exact GHSA package/range evidence
 -> deterministic package identity
 -> PEP 440 range evaluation
 -> affected | not_affected | unsupported
 -> CVE/GHSA/NVD alias evidence
 -> canonical content-addressed correlation record
```

Permanent rule:

> No LLM decides vulnerability applicability.

### Phase 4 — Repository Intelligence

Completed the read-only public GitHub repository slice:

```text
public GitHub repository
 -> immutable commit snapshot
 -> bounded read-only acquisition
 -> exact inert uv.lock
 -> deterministic parser
 -> Phase 3 normalization/correlation
 -> repository finding
 -> NVD/CVSS
 -> complete KEV snapshot
 -> explicit EPSS snapshot
 -> RepositoryAnalysisResult
```

Phase 4 never executes repository code and does not claim runtime exposure.

### Phase 5 — Risk Prioritization Engine

Completed **Risk Policy v1**, a separate deterministic priority authority over already-validated Phase 4 findings.

```text
RepositoryAnalysisResult
 -> typed policy facts
 -> deterministic Risk Policy v1
 -> factor contributions
 -> priority score + tier
 -> completeness / review_required
 -> deterministic ranking
 -> RiskPrioritizationResult
```

Risk Policy v1 currently uses only evidence that Phase 4 proves:

```text
KEV present                         +40
EPSS >= 0.70 / 0.30 / 0.10          +30 / +20 / +10
max supported CVSS >= 9 / 7 / 4     +20 / +10 / +5
known fixed version                 +10
```

Priority tiers:

```text
P0 >= 80
P1 >= 60
P2 >= 30
P3 < 30
```

Properties:

- same evidence + same policy reproduces the same priority;
- every contribution has a stable reason and observed value;
- the exact policy/evaluation/ranking are content-addressed;
- missing evidence remains `partial` / `review_required` rather than silently low risk;
- proven KEV/EPSS absence remains distinct from missing evidence;
- an LLM is not required for factor extraction, scoring, tiers, or ranking;
- Repository Risk remains distinct from Runtime Exposure.

Deterministic identities:

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

Phase 5 added no AWS resources, IAM permissions, or model calls.

Closeout: [`labs/phase-5-risk-policy-closeout.md`](labs/phase-5-risk-policy-closeout.md).

## Phase 6 — Semantic Query Layer — IN PROGRESS

### Goal

Convert natural-language factual questions into a safe typed query representation and deterministic Athena SQL without giving a model unrestricted SQL authority.

Target flow:

```text
User question
 -> bounded Bedrock planner
 -> typed SemanticQuery
 -> deterministic validator
 -> deterministic SQL compiler
 -> exact compiler-shape admission
 -> bounded read-only Athena workgroup
 -> structured result evidence
```

### Permanent guardrail

> **No unrestricted text-to-SQL.**

A future model may propose only a typed semantic query. Application code owns validation, SQL generation, execution limits, and evidence validation.

### Gate 6.1 — Typed semantic-query contract + deterministic compiler — COMPLETE

The first factual question was frozen from the real EPSS dataset rather than a broad hypothetical query surface:

> Which CVEs have EPSS of at least 0.7 on an explicit snapshot date?

Current allowlisted contract:

```text
metric
  epss_score

dimension
  cve

filters
  snapshot_date: required explicit calendar date
  minimum_score: optional finite value in 0.0..1.0

order
  epss_score ASC|DESC
  cve ASC deterministic tie break

limit
  1..100
  default 20
```

The compiler owns:

```text
database/table
selected columns
predicates
ordering
LIMIT
```

Only validated filter values become positional Athena execution parameters.

ADR: [`adr/0020-no-unrestricted-text-to-sql.md`](adr/0020-no-unrestricted-text-to-sql.md).

### Gate 6.2 — Bounded read-only Athena execution — COMPLETE

The first real AWS execution boundary is now proven through the existing dev analytics stack:

```text
database:    opslens_dev
workgroup:   opslens-dev
relation:    "opslens_dev"."epss_scores"
scan cutoff: 10 MiB, enforced by workgroup
```

Executor controls include:

- fixed database/workgroup/relation;
- exact Gate 6.1 compiler SQL grammar admission;
- validated execution-parameter literal shapes;
- SQL `LIMIT` equal to semantic result bound;
- synchronous bounded polling;
- cancellation on timeout or unknown state;
- bounded `GetQueryResults` pagination;
- continuation-token cycle detection;
- accumulated result row bound;
- stable metadata and row-width validation;
- recorded data-scanned and execution timings.

The first real smoke exposed a valid Athena pagination behavior that mocks had not represented. The implementation was corrected to treat `NextToken` as bounded transport behavior rather than broader query authority.

Real success evidence on 2026-09-04:

```text
query_execution_id:         958fb573-1a69-4ce6-8a36-d9be45e71c79
row_count:                  20
data_scanned_bytes:         3,785,003 (~3.61 MiB)
engine_execution_time_ms:   973
total_execution_time_ms:    1,128
```

Intentional fail-closed evidence:

```text
limit: 101
 -> SemanticQueryValidationError
 -> rejected before compilation and Athena
```

Gate 6.2 added no AWS resources and no model calls. A local IAM Identity Center profile was used only for validation; it does not satisfy the final runtime least-privilege role criterion.

Closeout: [`../labs/phase-6-gate-6-2-athena-readonly-execution.md`](../labs/phase-6-gate-6-2-athena-readonly-execution.md).

### Remaining Phase 6 work

The deterministic query foundation is complete, but Phase 6 is not complete. Remaining exit work includes:

```text
bounded natural-language planner contract
planner structured-output validation
planner evaluation dataset
metric/dimension/filter accuracy measurement
current Bedrock model/API selection
model IAM boundary
input/output token accounting
planner latency evidence
model invocation cost evidence
throttling/retry/failure diagnosis
at least one natural-language factual question end to end
intentional planner failure evidence
final runtime least-privilege boundary when a deployed runtime exists
```

Before the next implementation gate, current official AWS documentation must be rechecked for Bedrock API behavior, supported structured output, model availability, IAM, quotas, retry/throttling behavior, token accounting, and pricing.

Do not add RAG, Knowledge Bases, vector search, agents, MCP, or AgentCore to Phase 6.

### Phase 6 exit criteria

- [x] typed `SemanticQuery` contract exists;
- [x] metric/dimension/filter allowlists are explicit;
- [x] invalid or unknown semantics fail closed;
- [x] SQL is generated only by deterministic application code;
- [x] Athena execution is read-only and bounded for the supported slice;
- [ ] planner evaluation set measures semantic-field accuracy separately;
- [ ] at least one natural-language factual question runs end to end;
- [ ] model/API/token/latency/cost evidence is recorded;
- [ ] intentional planner failure can be diagnosed;
- [x] ADR explains why unrestricted text-to-SQL is not used;
- [ ] final runtime IAM is least privilege once a deployed runtime exists.

## Phase 7 — Knowledge Retrieval with Bedrock

Add a controlled RAG path for remediation/documentation questions with separately testable retrieval, citations, chunking/metadata decisions, and retrieval-quality evaluation.

## Phase 8 — Hybrid Retrieval

Combine structured threat intelligence with semantic retrieval, preferably scoping knowledge retrieval using deterministic CVE/GHSA/package evidence first.

## Phase 9 — Public Analyze Your Repository

Expose a bounded public demo only after repository intelligence and risk policy are stable.

Expected controls include validation, cache/reuse, per-client limits, global budget, reserved concurrency, size/duration limits, tool/LLM/Athena call limits, output-token limits, abuse tests, and a kill switch.

## Phase 10 — Observability & Operational Excellence

Make the end-to-end system diagnosable through stage latency, errors, throttling, queue/DLQ state, Athena bytes, model tokens/latency, retrieval latency, and estimated investigation cost.

## Phase 11 — Single-Agent Baseline

Build one bounded agent over existing deterministic tools before introducing multi-agent complexity. Measure quality, latency, cost, tool calls, and failure modes.

## Phase 12 — Multi-Agent Architecture

Introduce specialization only where it demonstrably improves the single-agent baseline.

Candidate roles:

- Supervisor;
- Exposure Agent;
- Threat Intelligence Agent;
- Remediation Agent.

## Phase 13 — MCP

Expose controlled OpsLens capabilities through typed, authorized, observable MCP tools with allowlists and prompt/tool-injection tests.

## Phase 14 — Amazon Bedrock AgentCore

Evaluate/adopt AgentCore only after a working bounded agent baseline exists and there is a concrete need for its runtime, gateway, identity, memory, or observability capabilities.

## Phase 15 — A2A

Introduce agent-to-agent interoperability only after internal agent contracts and authority boundaries are stable.

## Phase 16 — Runtime Exposure with Amazon Inspector

Add deployed-runtime/package evidence so OpsLens can distinguish repository risk from real runtime exposure rather than inferring one from the other.

## Phase 17 — Security Hardening

Expand abuse-case, identity, authorization, data-handling, supply-chain, prompt/tool-injection, red-team, and denial-of-wallet controls across the public and agentic surfaces.

## Phase 18 — Evaluation, Cost & Portfolio Readiness

Close the program with reproducible evaluation, measured cost, architecture/runbooks, portfolio documentation, and explicit evidence for the trade-offs made across deterministic, retrieval, and agentic paths.
