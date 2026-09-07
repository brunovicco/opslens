<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Verifiable Software Supply Chain & Threat Intelligence on AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Public Analysis · Operational Evidence · Deterministic Authority**

</div>

OpsLens is an open-source software-supply-chain intelligence platform built on AWS.

It is designed to answer:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, which findings should I prioritize, and what verified guidance can help me act on them?

The project deliberately separates deterministic truth from model reasoning.

> **Agents reason. Code verifies evidence.**

Permanent boundaries:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

## Current status

| Phase | Scope | Status |
| --- | --- | --- |
| Phase 0 | AWS Foundation | ✅ Complete |
| Phase 1 | EPSS Vertical Slice | ✅ Complete |
| Phase 2 | Threat Intelligence Data Lake | ✅ Complete |
| Phase 3 | Vulnerability Correlation Engine | ✅ Complete |
| Phase 4 | Repository Intelligence | ✅ Complete |
| Phase 5 | Risk Prioritization Engine | ✅ Complete |
| Phase 6 | Semantic Query Layer | ✅ Complete |
| Phase 7 | Knowledge Retrieval with Bedrock | ✅ Complete |
| Phase 8 | Hybrid Retrieval | ✅ Complete |
| Phase 9 | Public Analyze Your Repository | ✅ Complete |
| Phase 10 | Observability & Operational Excellence | ✅ Complete |
| Phase 11 | Single-Agent Baseline | ▶️ Next |

Phase 9 closes at a governed **application boundary**, not at a fictional production deployment. Phase 10 makes that boundary diagnosable and adds an AWS-native telemetry representation without claiming a deployed public runtime or CloudWatch ingestion.

```text
application boundary validated != public runtime deployed
telemetry evidence != business truth
telemetry evidence != route authority
EMF document created != CloudWatch ingestion proven
```

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), and the [Phase 10 closeout](labs/phase-10-gate-10-4-closeout.md).

## Implemented system

### 1. Structured vulnerability and risk authority

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
 -> deterministic PyPI / PEP 440 / purl normalization
 -> deterministic vulnerable-range applicability
 -> NVD/CVSS + CISA KEV + FIRST EPSS enrichment
 -> content-addressed RepositoryAnalysisResult
 -> deterministic Risk Policy v1
```

The model never decides vulnerability applicability, Risk Policy truth, KEV/EPSS/CVSS facts, or runtime exposure.

### 2. Structured natural-language query path

```text
natural-language factual question
 -> bounded Bedrock planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured evidence
```

The planner never receives arbitrary SQL authority.

### 3. Grounded knowledge retrieval

```text
immutable official source pins
 -> deterministic canonical corpus
 -> Amazon Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> bounded Retrieve
 -> deterministic checked-corpus admission
 -> bounded context assembly
 -> bounded Bedrock Converse synthesis
 -> deterministic citation identity
 -> explicit groundedness evaluation
```

`RetrieveAndGenerate` is deliberately not used. Retrieval, context admission, synthesis, citations, and evaluation remain independently testable.

### 4. Hybrid evidence authority

```text
EvidenceNeed[]
 -> deterministic route authority
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> authority-separated evidence composition
 -> ALL_REQUIRED completeness
 -> HybridEvidenceEnvelope
 -> deterministic F* / S* projections
 -> bounded route-aware synthesis
 -> deterministic output admission
```

Structured vulnerability/risk facts and semantic remediation evidence never become one undifferentiated authority class.

Runtime exposure remains `UNSUPPORTED` until a future independent runtime authority exists.

### 5. Governed public-analysis boundary

```text
untrusted public JSON
 -> strict bounded request admission
 -> validated GitHub owner/name/ref coordinates
 -> source-confirmed public repository identity
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic parsing + PyPI normalization
 -> PublicRepositoryEvidenceExecution
 -> bounded metadata-only semantic planning proposal
 -> deterministic public-v1 scope admission
 -> existing Phase 8 hybrid route authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

Public v1 scope is code-owned, not model-owned.

### 6. Operational evidence and CloudWatch EMF representation

Phase 10 freezes:

```text
operational-telemetry:v1
operation: analyze_public_repository
```

Five bounded stages:

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

Exact dimensions:

```text
ContractVersion
Operation
Stage
Outcome
```

Gate 10.2 instruments the governed path through injected `MonotonicClock` and `OperationalEventSink` ports. Successful execution emits exactly five ordered events; rejected/failed stages are terminal.

Gate 10.3 adds deterministic AWS-native serialization:

```text
cloudwatch-emf:v1
namespace: OpsLens/Operational
storage resolution: 60 seconds
maximum canonical document: 16 KiB
```

```text
OperationalEvent
 -> existing project_operational_metrics(...)
 -> canonical CloudWatch EMF JSON
 -> content-addressed CloudWatchEmfDocument
 -> injected EpochMillisecondsClock
 -> injected EmfLineWriter
 -> STOP
```

High-cardinality `EventId`, `PublicRequestId`, `SourceExecutionId`, and `HandoffId` remain log metadata only and never become metric dimensions.

The adapter performs zero retries and attempts writer delivery at most once per `emit(...)`.

## Phase 10 closeout

Phase 10 proves:

```text
provider-neutral operational event contract
bounded deterministic stage instrumentation
content-minimized provenance/correlation identities
fixed low-cardinality metric projection
best-effort external sink semantics after mandatory in-process evidence
bounded content-free failure taxonomy
cloudwatch-emf:v1 deterministic serialization
separate monotonic-duration and epoch-millisecond clock semantics
zero adapter retries
content-addressed operational/EMF evidence
```

It does **not** prove:

```text
public HTTP runtime
CloudWatch ingestion
runtime principal / runtime IAM
public request volume
production distributed traces
production p95/p99
production error/throttle rates
production cost/request
production dashboards/alarms
production SLO compliance
```

### Exact Phase 10 validation

```text
Gate 10.1
  PR #135 head: 7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
  CI:           34135197989 / PASS
  pytest:       14 passed
  merge:        665b86f6e527a0096d7c3db522f4bd2c95b177aa

Gate 10.2
  PR #138 head: 24b2affdf464e2548d94273e41007bb3256b561e
  CI:           34141496326 / PASS
  Pyright:      0 errors / 0 warnings / 0 informations
  pytest:       70 passed
  merge:        346b223d9566a5d04d84e279f30793ad52a35b67

Gate 10.3
  PR #141 head: 632e778d36ada833505342708379603a1080d390
  CI:           34143908297 / run #9 / PASS
  Pyright:      0 errors / 0 warnings / 0 informations
  pytest:       26 passed
  merge:        0c5bf6bab39a3980c063fcb44f657c412111fefa
```

## Frozen hybrid evaluation

Dataset:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Gate 8.4 first complete real baseline:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

Gate 8.5 tested one predeclared prompt-only hypothesis exactly once and rejected it because the target quality metrics did not improve.

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct citation target
```

## AWS baseline

```text
environment:             dev
Region:                  us-east-1
knowledge base:          BTVJ2PBR2A
data source:             IEL1LBE026
vector store:            Amazon S3 Vectors
embedding model:         amazon.titan-embed-text-v2:0
dimensions:              1024
chunking:                NONE
canonical chunks:        9
synthesis API:           bedrock-runtime / Converse
synthesis profile:       us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:               no
tools:                   none
```

Phase 10 adds **zero** public runtime resources and **zero** runtime IAM permissions. In particular, it does not grant `logs:PutLogEvents` or `cloudwatch:PutMetricData`.

## Security and authority invariants

- Raw third-party evidence is preserved before transformation.
- Exact source versions and hashes participate in evidence identity.
- Package normalization, version/range matching, vulnerability applicability, KEV/EPSS/CVSS evidence, and Risk Policy remain deterministic.
- Third-party repository code is never executed.
- Public request admission never grants arbitrary fetch authority.
- Public semantic planning does not own product scope or execution authority.
- Natural-language planning cannot emit unrestricted SQL authority.
- Retrieval output is evidence, not deterministic truth.
- Retrieved text remains untrusted instruction content after provenance validation.
- Hybrid routing and required-evidence completeness are deterministic.
- Structured and semantic evidence remain separate authority classes.
- Citation IDs come only from admitted evidence.
- Unsupported runtime exposure is not inferred from repository risk.
- Operational telemetry does not become business or route authority.
- High-cardinality correlation IDs are not metric dimensions.
- Telemetry delivery accounting cannot invent evidence identities.
- EMF serialization is not represented as CloudWatch ingestion.
- First-run and negative evaluation evidence is preserved.
- IAM least privilege, observability, failure diagnosis, and cost accounting are architecture requirements.

## Cost discipline

OpsLens does not invent costs that runtime evidence cannot support.

```text
unmeasured cost != zero cost
```

Phase 10 proves a cardinality-control design but not production CloudWatch cost. Real observability cost requires workload volume, ingestion, retention, time-series count, retries, and runtime evidence.

## Documentation

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Architecture — English](docs/architecture.md)
- [Architecture — Português](docs/architecture.pt-br.md)
- [ADR index](docs/adr/README.md)
- [Documentation index](docs/README.md)
- [Phase 8 closeout](labs/phase-8-gate-8-6-closeout.md)
- [Phase 9 closeout](labs/phase-9-gate-9-4-closeout.md)
- [Phase 10 Gate 10.1](labs/phase-10-gate-10-1-operational-telemetry-contract.md)
- [Phase 10 Gate 10.2](labs/phase-10-gate-10-2-governed-orchestration-instrumentation.md)
- [Phase 10 Gate 10.3](labs/phase-10-gate-10-3-cloudwatch-emf-adapter.md)
- [Phase 10 closeout](labs/phase-10-gate-10-4-closeout.md)

## Next — Phase 11: Single-Agent Baseline

Phase 11 starts with **one bounded agent** over already-governed OpsLens capabilities before any multi-agent complexity.

```text
agent reasoning may select/use already-authorized capabilities
agent reasoning does not acquire deterministic truth or execution authority
```

The first Phase 11 gate must freeze the exact tool/capability surface, execution limits, failure/abstention semantics, evidence handoff, evaluation fixture, and Phase 10 observability mapping before selecting managed agent runtime infrastructure.

The long-lived Governed LLM Gateway PR #89 remains deferred and must be re-evaluated separately against the then-current OpsLens architecture.

---

OpsLens is intentionally built as an evidence system first and an agentic system later.
