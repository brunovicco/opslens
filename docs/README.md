# OpsLens Documentation

OpsLens documentation is organized around current architecture, implementation state, incremental roadmap, ADRs, gate laboratories, and immutable evaluation/runtime evidence.

## Primary documents

- [`architecture.md`](architecture.md) — accumulated architecture baseline through **Phase 9 — Public Analyze Your Repository**; Phase 10 decisions extend it through ADRs/gate labs while the phase remains in progress.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture baseline synchronized with the English version.
- [`current-state.md`](current-state.md) — exact implementation checkpoint and next authorized action.
- [`roadmap.md`](roadmap.md) — incremental phase/gate plan and completion status.
- [`adr/`](adr/) — accepted architecture decisions.
- [`../labs/`](../labs/) — gate laboratories and immutable evidence references.

## Current implementation checkpoint

```text
Phase 0  AWS Foundation                         COMPLETE
Phase 1  EPSS Vertical Slice                    COMPLETE
Phase 2  Threat Intelligence Data Lake          COMPLETE
Phase 3  Vulnerability Correlation Engine       COMPLETE
Phase 4  Repository Intelligence                COMPLETE
Phase 5  Risk Prioritization Engine             COMPLETE
Phase 6  Semantic Query Layer                   COMPLETE
Phase 7  Knowledge Retrieval with Bedrock       COMPLETE
Phase 8  Hybrid Retrieval                       COMPLETE
Phase 9  Public Analyze Your Repository         COMPLETE
Phase 10 Observability & Operational Excellence IN PROGRESS
  Gate 10.1 Content-Minimized Telemetry         COMPLETE / MERGED
  Gate 10.2 Governed Orchestration Instrumentation COMPLETE / MERGED
  Gate 10.3 CloudWatch EMF Adapter Boundary     NEXT
```

Phase 9 closes at a governed **application boundary**, not at a fictional public runtime:

```text
application boundary validated != public runtime deployed
```

Phase 10 preserves that distinction while adding content-minimized operational evidence and deterministic stage instrumentation. No public HTTP endpoint or runtime principal is claimed.

## Phase 10 architecture records

- [`adr/0032-content-minimized-operational-telemetry-contract.md`](adr/0032-content-minimized-operational-telemetry-contract.md) — operational telemetry is bounded evidence, not business or execution authority.
- [`adr/0033-governed-operational-orchestration-instrumentation.md`](adr/0033-governed-operational-orchestration-instrumentation.md) — instrument the governed Phase 9 path without moving authority into telemetry.

Frozen telemetry contract:

```text
operational-telemetry:v1
operation: analyze_public_repository
```

Operational stages:

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

Authority boundary:

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
telemetry delivery accounting != permission to invent evidence identities
```

The event contract has no arbitrary attribute bag and admits only content-addressed Phase 9 identity references. Metric projection is limited to `OperationalStageCount` and `OperationalStageLatency` with `ContractVersion`, `Operation`, `Stage`, and `Outcome` dimensions.

### Gate 10.1 validation

```text
PR #135 final head:           7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
Operational Observability CI: run 34135197989 / PASS
Ruff:                         PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
pytest:                       14 passed
merge SHA:                    665b86f6e527a0096d7c3db522f4bd2c95b177aa
issue #134:                   CLOSED / COMPLETED
```

### Gate 10.2 validation

Gate 10.2 instruments the five governed application stages with an injected monotonic clock and best-effort `OperationalEventSink`. Failed/rejected stages are terminal; sink failure never changes application/route authority; undelivered accounting accepts only already-admitted event identities.

```text
PR #138 final head:           24b2affdf464e2548d94273e41007bb3256b561e
Python CI run:                34141496326 / PASS
uv lock --check:              PASS
Ruff:                         PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
Public Analysis pytest:       70 passed
merge SHA:                    346b223d9566a5d04d84e279f30793ad52a35b67
issue #137:                   CLOSED / COMPLETED
```

Phase 10 laboratories:

- [`../labs/phase-10-gate-10-1-operational-telemetry-contract.md`](../labs/phase-10-gate-10-1-operational-telemetry-contract.md)
- [`../labs/phase-10-gate-10-2-governed-orchestration-instrumentation.md`](../labs/phase-10-gate-10-2-governed-orchestration-instrumentation.md)

Neither Gate 10.1 nor 10.2 deployed a public runtime, AWS telemetry exporter/backend, dashboard, alarm, or production SLO.

## Phase 9 architecture records

- [`adr/0029-public-repository-request-admission.md`](adr/0029-public-repository-request-admission.md) — public repository requests become validated coordinates, not arbitrary fetch URLs.
- [`adr/0030-public-semantic-planning-authority.md`](adr/0030-public-semantic-planning-authority.md) — public semantic planning remains proposal-only and cannot redefine product scope or execution authority.
- [`adr/0031-phase9-public-analysis-closeout.md`](adr/0031-phase9-public-analysis-closeout.md) — Phase 9 closes at the governed application boundary and explicitly defers deployment/runtime IAM until a concrete workload exists.

## Phase 9 laboratories

- [`../labs/phase-9-gate-9-1-public-request-admission.md`](../labs/phase-9-gate-9-1-public-request-admission.md) — public request grammar/admission boundary.
- [`../labs/phase-9-gate-9-3-bounded-semantic-planning.md`](../labs/phase-9-gate-9-3-bounded-semantic-planning.md) — bounded semantic proposal/admission handoff and exact-head CI evidence.
- [`../labs/phase-9-gate-9-4-closeout.md`](../labs/phase-9-gate-9-4-closeout.md) — Phase 9 authority/failure/runtime/IAM/cost/observability closeout and Phase 10 entry criteria.

Phase 9 frozen contracts:

```text
public-analysis-request:v1
public-repository-evidence:v1
public-semantic-planning:v1
public-analysis-handoff:v1
```

Gate 9.4 closeout merge:

```text
PR #132
f27c278db1039d31bd8410a2e51d14b77f6c1f0b
issue #131: CLOSED / COMPLETED
```

## Phase 8 architecture records

- [`adr/0025-deterministic-hybrid-routing-authority.md`](adr/0025-deterministic-hybrid-routing-authority.md) — deterministic `STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED` route authority.
- [`adr/0026-deterministic-hybrid-evidence-envelope.md`](adr/0026-deterministic-hybrid-evidence-envelope.md) — authority-separated structured/semantic evidence envelope and completeness.
- [`adr/0027-frozen-hybrid-evaluation-contract.md`](adr/0027-frozen-hybrid-evaluation-contract.md) — six-case evaluation fixture and independent metrics frozen before synthesis.
- [`adr/0028-bounded-route-aware-hybrid-synthesis.md`](adr/0028-bounded-route-aware-hybrid-synthesis.md) — bounded synthesis behind deterministic hybrid route/evidence authority.

## Phase 8 evidence

Frozen dataset:

```text
hybrid-evaluation-golden:v1
sha256: 68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Independent metrics:

```text
route_accuracy
structured_fact_correctness
semantic_groundedness
citation_correctness
abstention
latency
cost
```

No composite score exists.

Gate 8.4 first complete real Bedrock baseline:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

Gate 8.5 measured `H8.5-01` exactly once. The prompt-only candidate preserved deterministic guardrails but did not improve semantic groundedness or citation correctness, so the predeclared decision was `REJECT`. The Gate 8.4 prompt remains the runtime default.

Evidence and closeout documents:

- [`../labs/phase-8-gate-8-4-bounded-hybrid-synthesis.md`](../labs/phase-8-gate-8-4-bounded-hybrid-synthesis.md)
- [`../labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json`](../labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json)
- [`../labs/phase-8-gate-8-5-measured-optimization.md`](../labs/phase-8-gate-8-5-measured-optimization.md)
- [`../labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json`](../labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json)
- [`../labs/phase-8-gate-8-6-closeout.md`](../labs/phase-8-gate-8-6-closeout.md)

## Phase 7 architecture records

- [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md) — customer-managed vector Knowledge Base and S3 Vectors.
- [`adr/0023-bounded-bedrock-knowledge-synthesis.md`](adr/0023-bounded-bedrock-knowledge-synthesis.md) — bounded non-streaming Bedrock knowledge synthesis after deterministic context admission.
- [`adr/0024-phase7-runtime-iam-boundary.md`](adr/0024-phase7-runtime-iam-boundary.md) — future least-privilege application runtime entitlement, intentionally documented before compute exists.

Detailed Phase 7 evidence remains in `../labs/phase-7-gate-7-*` and is not rewritten by later closeouts.

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

The model may plan and synthesize inside typed, bounded contracts. Deterministic code owns structured truth, public request/product-scope admission, route authority, required-evidence completeness, evidence admission, canonical citations, output admission, evaluation metric computation, and operational telemetry admission semantics.

## Next authorized gate

```text
Phase 10 Gate 10.3 — CloudWatch EMF Telemetry Adapter Boundary
```

Gate 10.3 should adapt the frozen event/metric semantics to deterministic CloudWatch Embedded Metric Format through an injected writer boundary. It must be fake-writer/offline first, preserve the exact low-cardinality dimension set, and make no CloudWatch-delivery, production-runtime, dashboard, alarm, p95/p99, or SLO claim without separately deployed AWS evidence.

## Documentation update rule

Every material gate should leave behind:

```text
architecture decision / rationale
implementation evidence
success evidence
failure evidence
IAM / trust boundary
observability evidence
cost reasoning
CI evidence
next authorized gate
```

Top-level documents describe the current baseline. Historical detail stays in labs and ADRs so stale gate status does not leak into the current project overview.
