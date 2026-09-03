# OpsLens — Incremental Roadmap

_Last updated: 2026-09-03_

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
| 5 | Risk Prioritization Engine | 🚧 Next |
| 6 | Semantic Query Layer | ⏳ Planned |
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

## Phase 5 — Risk Prioritization Engine — NEXT

### Goal

Prioritize already-proven repository findings with an explicit deterministic policy.

### Candidate factors

- affected status;
- direct/transitive evidence when available;
- CISA KEV;
- EPSS;
- CVSS;
- fix availability;
- future runtime-exposure evidence;
- evidence completeness.

### Deliverable

```text
Risk Policy v1
```

### Exit criteria

- the same evidence always produces the same priority;
- factor-level explanation is available;
- policy version is recorded with the decision;
- an LLM is not required for ranking;
- tests demonstrate expected priority changes when individual factors change;
- missing/unsupported evidence has explicit semantics rather than silent defaults;
- Repository Risk remains distinct from Runtime Exposure.

## Phase 6 — Semantic Query Layer

Convert natural language into a safe typed semantic query, validate it deterministically, compile SQL in code, and execute only through bounded Athena workgroups.

Guardrail:

> No unrestricted text-to-SQL.

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
