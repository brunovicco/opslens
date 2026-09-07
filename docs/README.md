# OpsLens Documentation

OpsLens documentation is organized around current architecture, implementation state, incremental roadmap, ADRs, gate laboratories, and immutable evaluation/runtime evidence.

## Primary documents

- [`architecture.md`](architecture.md) — accumulated architecture baseline through **Phase 9 — Public Analyze Your Repository**; Phase 10 is frozen through ADRs 0032–0035 and its gate labs.
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
Phase 10 Observability & Operational Excellence COMPLETE
Phase 11 Single-Agent Baseline                  NEXT
```

Phase 9 closes at a governed **application boundary**, not at a fictional public runtime:

```text
application boundary validated != public runtime deployed
```

Phase 10 adds provider-neutral operational evidence, deterministic instrumentation, low-cardinality metrics, and a bounded CloudWatch EMF representation while preserving that boundary.

```text
EMF document created != CloudWatch ingestion proven
```

No public HTTP endpoint/runtime principal, CloudWatch ingestion, production dashboard/alarm, or production SLO is claimed.

## Phase 10 architecture records

- [`adr/0032-content-minimized-operational-telemetry-contract.md`](adr/0032-content-minimized-operational-telemetry-contract.md) — operational telemetry is bounded evidence, not business or execution authority.
- [`adr/0033-governed-operational-orchestration-instrumentation.md`](adr/0033-governed-operational-orchestration-instrumentation.md) — instrument the governed Phase 9 path without moving authority into telemetry.
- [`adr/0034-bounded-cloudwatch-emf-telemetry-adapter.md`](adr/0034-bounded-cloudwatch-emf-telemetry-adapter.md) — adapt admitted events into deterministic AWS CloudWatch EMF without deploying runtime authority.
- [`adr/0035-phase10-observability-closeout.md`](adr/0035-phase10-observability-closeout.md) — close Phase 10 at the proven observability boundary and defer production-runtime claims.

Frozen provider-neutral contract:

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

Low-cardinality metrics:

```text
OperationalStageCount      Count
OperationalStageLatency    Milliseconds
```

Exact metric dimensions:

```text
ContractVersion
Operation
Stage
Outcome
```

Frozen AWS-native representation:

```text
cloudwatch-emf:v1
namespace: OpsLens/Operational
storage resolution: 60 seconds
maximum canonical document: 16 KiB
```

High-cardinality correlation IDs remain metadata-only and never become metric dimensions.

## Phase 10 authority boundary

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
telemetry delivery accounting != permission to invent evidence identities
provider serialization != execution authority
EMF document created != CloudWatch ingestion proven
```

Phase 10 closes without adding a public runtime or runtime IAM.

## Phase 10 validation

### Gate 10.1

```text
PR #135 final head:           7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
Operational Observability CI: 34135197989 / PASS
pytest:                       14 passed
merge SHA:                    665b86f6e527a0096d7c3db522f4bd2c95b177aa
```

### Gate 10.2

```text
PR #138 final head:           24b2affdf464e2548d94273e41007bb3256b561e
Python CI:                    34141496326 / PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
Public Analysis pytest:       70 passed
merge SHA:                    346b223d9566a5d04d84e279f30793ad52a35b67
```

### Gate 10.3

```text
PR #141 final head:           632e778d36ada833505342708379603a1080d390
Operational Observability CI: 34143908297 / run #9 / PASS
Ruff:                         PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
pytest:                       26 passed
merge SHA:                    0c5bf6bab39a3980c063fcb44f657c412111fefa
```

Gate 10.3 made zero CloudWatch API calls and created zero AWS/IAM resources.

## Phase 10 laboratories

- [`../labs/phase-10-gate-10-1-operational-telemetry-contract.md`](../labs/phase-10-gate-10-1-operational-telemetry-contract.md)
- [`../labs/phase-10-gate-10-2-governed-orchestration-instrumentation.md`](../labs/phase-10-gate-10-2-governed-orchestration-instrumentation.md)
- [`../labs/phase-10-gate-10-3-cloudwatch-emf-adapter.md`](../labs/phase-10-gate-10-3-cloudwatch-emf-adapter.md)
- [`../labs/phase-10-gate-10-4-closeout.md`](../labs/phase-10-gate-10-4-closeout.md)

## Phase 9 architecture records

- [`adr/0029-public-repository-request-admission.md`](adr/0029-public-repository-request-admission.md)
- [`adr/0030-public-semantic-planning-authority.md`](adr/0030-public-semantic-planning-authority.md)
- [`adr/0031-phase9-public-analysis-closeout.md`](adr/0031-phase9-public-analysis-closeout.md)

Phase 9 frozen contracts:

```text
public-analysis-request:v1
public-repository-evidence:v1
public-semantic-planning:v1
public-analysis-handoff:v1
```

## Phase 8 architecture records

- [`adr/0025-deterministic-hybrid-routing-authority.md`](adr/0025-deterministic-hybrid-routing-authority.md)
- [`adr/0026-deterministic-hybrid-evidence-envelope.md`](adr/0026-deterministic-hybrid-evidence-envelope.md)
- [`adr/0027-frozen-hybrid-evaluation-contract.md`](adr/0027-frozen-hybrid-evaluation-contract.md)
- [`adr/0028-bounded-route-aware-hybrid-synthesis.md`](adr/0028-bounded-route-aware-hybrid-synthesis.md)

Frozen dataset:

```text
hybrid-evaluation-golden:v1
sha256: 68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

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

Gate 8.5 measured `H8.5-01` exactly once and rejected the candidate because the target quality metrics did not improve.

## Phase 7 architecture records

- [`adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md`](adr/0022-customer-managed-bedrock-kb-with-s3-vectors.md)
- [`adr/0023-bounded-bedrock-knowledge-synthesis.md`](adr/0023-bounded-bedrock-knowledge-synthesis.md)
- [`adr/0024-phase7-runtime-iam-boundary.md`](adr/0024-phase7-runtime-iam-boundary.md)

Detailed Phase 7 evidence remains in `../labs/phase-7-gate-7-*` and is not rewritten by later closeouts.

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

## Next authorized phase

```text
Phase 11 — Single-Agent Baseline
```

Phase 11 should freeze one bounded agent contract over already-governed capabilities before selecting managed runtime infrastructure or introducing multi-agent complexity.

The entry boundary is:

```text
agent reasoning may select/use already-authorized capabilities
agent reasoning does not acquire deterministic truth or execution authority
```

PR #89 remains deferred cross-project integration work and is not made mergeable by Phase 10 closeout.

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
next authorized gate/phase
```

Top-level documents describe the current baseline. Historical detail stays in labs and ADRs so stale gate status does not leak into the project overview.
