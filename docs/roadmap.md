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
| 6 | Semantic Query Layer | 🚧 Gate 6.4 implemented; final validation/PR/merge pending |
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

Established the real `dev` environment, Terraform remote state, IAM Identity Center human access, GitHub Actions OIDC deployment identity, budget/cost controls, CloudWatch, X-Ray, and intentional failure-path validation.

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

Completed NVD/CVE, CISA KEV, FIRST EPSS current/historical, and GitHub Security Advisory source-local deterministic evidence while preserving explicit provenance and time coordinates.

### Phase 3 — Vulnerability Correlation Engine

Completed deterministic PyPI v1 applicability:

```text
package/version/purl
 + GHSA range evidence
 -> PEP 440 applicability
 -> affected | not_affected | unsupported
 -> CVE/GHSA/NVD reconciliation
 -> content-addressed correlation record
```

Permanent rule:

> No LLM decides vulnerability applicability.

### Phase 4 — Repository Intelligence

Completed the read-only public GitHub repository slice:

```text
public GitHub repository
 -> immutable commit snapshot
 -> bounded GET-only acquisition
 -> exact inert uv.lock
 -> deterministic parser
 -> Phase 3 correlation
 -> NVD/CVSS + KEV + EPSS evidence
 -> RepositoryAnalysisResult
```

Repository code is never executed, and repository risk is not claimed as runtime exposure.

### Phase 5 — Risk Prioritization Engine

Completed deterministic Risk Policy v1:

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

Missing evidence remains `partial` / `review_required`; it does not silently become a confident low-risk result.

## Phase 6 — Semantic Query Layer — CLOSEOUT IN PROGRESS

### Goal

Convert bounded natural-language factual questions into a typed semantic query and deterministic Athena SQL without giving a model unrestricted SQL authority.

Target flow:

```text
User question
 -> bounded Bedrock planner
 -> structured planner proposal
 -> deterministic planner-output parser
 -> typed SemanticQuery
 -> deterministic validator
 -> deterministic SQL compiler
 -> exact compiler-shape admission
 -> bounded read-only Athena workgroup
 -> structured result evidence
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

### Gate 6.1 — Typed semantic-query contract + deterministic compiler — COMPLETE

First supported slice:

> Which CVEs have EPSS of at least 0.7 on an explicit snapshot date?

Contract:

```text
metric:          epss_score
dimension:       cve
snapshot_date:   required explicit date
minimum_score:   optional 0.0..1.0
order:           epss_score ASC|DESC + cve ASC tie break
limit:           1..100, default 20
```

Only deterministic application code owns database/table/columns/predicates/order/LIMIT.

ADR: [`adr/0020-no-unrestricted-text-to-sql.md`](adr/0020-no-unrestricted-text-to-sql.md).

### Gate 6.2 — Bounded read-only Athena execution — COMPLETE

Real dev boundary:

```text
database:    opslens_dev
workgroup:   opslens-dev
relation:    "opslens_dev"."epss_scores"
scan cutoff: 10 MiB enforced by workgroup
```

Executor controls fixed relation/workgroup, exact compiler-shape admission, validated execution-parameter shapes, bounded polling/pagination/results, metadata validation, and recorded scan/timing evidence.

Real success evidence:

```text
query_execution_id:         958fb573-1a69-4ce6-8a36-d9be45e71c79
row_count:                  20
data_scanned_bytes:         3,785,003 (~3.61 MiB)
engine_execution_time_ms:   973
total_execution_time_ms:    1,128
```

Intentional `limit=101` fails before Athena.

Closeout: [`../labs/phase-6-gate-6-2-athena-readonly-execution.md`](../labs/phase-6-gate-6-2-athena-readonly-execution.md).

### Gate 6.3 — Bounded planner contract + offline evaluation — COMPLETE

Frozen planner authority:

```text
input length:      <= 1,000 chars
decisions:         semantic_query | unsupported
metric:            epss_score
dimensions:        exactly [cve]
snapshot_date:     explicit YYYY-MM-DD
minimum_score:     null or inclusive >= threshold
order:             epss_score asc|desc
limit:             1..100
SQL field:         none
```

The deterministic parser rejects malformed/extra/missing fields, unsupported semantics, invalid values, relative/missing dates, and SQL injection attempts before rebuilding `SemanticQuery`.

Golden offline evaluation:

```text
18 total cases
  8 supported
 10 fail-closed unsupported
```

ADR: [`adr/0021-bounded-bedrock-semantic-query-planner.md`](adr/0021-bounded-bedrock-semantic-query-planner.md).

Closeout: [`../labs/phase-6-gate-6-3-planner-contract-evaluation.md`](../labs/phase-6-gate-6-3-planner-contract-evaluation.md).

### Gate 6.4 — Real Bedrock planner invocation — IMPLEMENTED / CLOSEOUT PENDING

Selected runtime boundary:

```text
model_id:       us.anthropic.claude-haiku-4-5-20251001-v1:0
client Region:  us-east-1
inference mode: US Geographic system-defined inference profile
streaming:      disabled
tools:          disabled
temperature:    0.0
maxTokens:      256
```

Implemented code:

```text
BedrockPlannerInvocationEvidence
BedrockPlannerResult
BedrockConverseClient Protocol
BedrockSemanticPlanner
ExecuteNaturalLanguageSemanticQuery
scripts/run_natural_language_semantic_query.py
```

The Bedrock adapter is injected with a client, performs one bounded Converse call, requires the expected non-streaming text shape, reparses the model text through `parse_planner_json()`, and records metadata-only invocation evidence. SDK/provider failures are wrapped at the adapter boundary while preserving their cause.

Real supported versioned E2E evidence on 2026-09-04:

```text
question:                       Which CVEs have EPSS of at least 0.7 on 2026-09-03?
decision:                       semantic_query
input/output/total:             942 / 79 / 1021 tokens
Bedrock latency:                1,632 ms
client elapsed:                 2,894 ms
retries:                        0
estimated planner cost:         ~$0.00147
Athena query_execution_id:      09a32501-a06c-4437-809c-ebcaf350cd1d
Athena rows:                    20
Athena data scanned:            3,785,003 bytes (~3.61 MiB)
Athena engine/total:            994 / 1,192 ms
```

Real fail-closed versioned evidence:

```text
question:         Which CVEs have EPSS of at least 0.7?
decision:         unsupported
reason:           missing_explicit_snapshot_date
athena_invoked:   false
input/output:     933 / 23 tokens
Bedrock latency:  878 ms
client elapsed:   2,145 ms
retries:          0
estimated cost:   ~$0.00115
```

A local IAM Identity Center token-expiry failure was also diagnosed before Bedrock invocation and did not reach Athena.

Closeout: [`../labs/phase-6-gate-6-4-real-bedrock-planner.md`](../labs/phase-6-gate-6-4-real-bedrock-planner.md).

### Phase 6 exit state

- [x] typed `SemanticQuery` contract;
- [x] explicit metric/dimension/filter allowlists;
- [x] invalid/unknown semantics fail closed;
- [x] deterministic SQL only;
- [x] bounded read-only Athena for the supported slice;
- [x] planner evaluation set with field-level metrics;
- [x] real bounded Bedrock invocation;
- [x] typed runtime invocation evidence;
- [x] real model/API/token/latency/cost evidence;
- [x] versioned natural-language question through model + parser + compiler + Athena;
- [x] versioned intentional semantic failure with `athena_invoked=false`;
- [x] diagnosable local authentication failure;
- [x] ADR rejecting unrestricted text-to-SQL;
- [x] ADR defining bounded planner authority;
- [ ] final targeted/regression validation + PR + green CI + merge;
- [deferred] final deployed runtime IAM least privilege until a runtime identity exists.

The local bootstrap/admin Identity Center profile is lab validation only and does not satisfy the future deployed-runtime IAM criterion.

Do not add RAG, Knowledge Bases, vector search, agents, MCP, or AgentCore to Phase 6.

## Next Phase after Phase 6 merge

### Phase 7 — Knowledge Retrieval with Bedrock

Add a controlled RAG path for remediation/documentation questions with separately testable retrieval, citations, chunking/metadata decisions, and retrieval-quality evaluation.

This is deliberately separate from the structured Phase 6 path: not every question is RAG.

## Future phases

### Phase 8 — Hybrid Retrieval

Combine deterministic structured threat intelligence with semantic retrieval, preferably using validated CVE/GHSA/package evidence to scope knowledge retrieval first.

### Phase 9 — Public Analyze Your Repository

Expose a bounded public demo only after repository intelligence, risk policy, structured query, and retrieval boundaries are stable.

### Phase 10 — Observability & Operational Excellence

Make the end-to-end system diagnosable through stage latency, errors, throttling, queue/DLQ state, Athena bytes, model tokens/latency, retrieval latency, and estimated investigation cost.

### Phase 11 — Single-Agent Baseline

Build one bounded agent over existing deterministic tools before introducing multi-agent complexity. Measure quality, latency, cost, tool calls, and failure modes.

### Phase 12 — Multi-Agent Architecture

Introduce specialization only where it demonstrably improves the single-agent baseline.

### Phase 13 — MCP

Expose controlled OpsLens capabilities through typed, authorized, observable MCP tools with allowlists and prompt/tool-injection tests.

### Phase 14 — Amazon Bedrock AgentCore

Evaluate/adopt AgentCore only after a working bounded agent baseline exists and there is a concrete need for runtime, gateway, identity, memory, or observability capabilities.

### Phase 15 — A2A

Introduce agent-to-agent interoperability only after internal agent contracts and authority boundaries are stable.

### Phase 16 — Runtime Exposure with Amazon Inspector

Add deployed-runtime/package evidence so OpsLens can distinguish repository risk from real runtime exposure rather than infer one from the other.

### Phase 17 — Security Hardening

Expand identity, authorization, abuse-case, data-handling, supply-chain, prompt/tool-injection, red-team, and denial-of-wallet controls.

### Phase 18 — Evaluation, Cost & Portfolio Readiness

Close the program with reproducible evaluation, measured cost, architecture/runbooks, portfolio documentation, and explicit evidence for deterministic, retrieval, and agentic trade-offs.
