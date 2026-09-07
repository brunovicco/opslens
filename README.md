<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Verifiable Software Supply Chain & Threat Intelligence on AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Public Analysis Admission · Operational Evidence · Deterministic Authority**

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
| Phase 10 | Observability & Operational Excellence | 🚧 In progress — Gate 10.1 complete |

Phase 9 closes at a governed **application boundary**, not at a fictional production deployment. OpsLens has bounded public request admission, immutable public-repository evidence orchestration, proposal-only semantic planning, and a deterministic admission handoff through the existing Phase 8 hybrid route authority.

Phase 10 Gate 10.1 now adds a provider-neutral, content-minimized operational evidence contract without claiming that a public HTTP runtime or production telemetry backend has already been deployed.

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
```

Public compute, runtime IAM, rate/abuse controls, production telemetry delivery, and workload-derived SLOs remain explicit later implementation work.

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), the [Phase 9 closeout](labs/phase-9-gate-9-4-closeout.md), and [Phase 10 Gate 10.1](labs/phase-10-gate-10-1-operational-telemetry-contract.md).

## Implemented system

OpsLens now has governed structured, semantic, hybrid, public-admission, and operational-evidence paths while preserving different authority semantics.

### 1. Structured vulnerability / risk authority

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

The model never decides vulnerability applicability, risk-policy truth, KEV/EPSS/CVSS facts, or runtime exposure.

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

The planner does not receive arbitrary SQL authority.

### 3. Explanatory / remediation semantic path

```text
immutable official source pins
 -> deterministic canonical corpus
 -> customer-managed Amazon Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> direct bounded Retrieve
 -> deterministic checked-corpus admission
 -> bounded context assembly
 -> bounded non-streaming Bedrock Converse synthesis
 -> deterministic citation identity
 -> explicit support / groundedness evaluation
```

`RetrieveAndGenerate` is deliberately not used. Retrieval and generation remain independently testable and observable.

### 4. Public analysis application boundary

```text
untrusted public JSON
 -> <=2048-byte strict request admission
 -> validated GitHub owner/name/ref coordinates
 -> source-confirmed public repository identity
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic parser + PyPI normalization
 -> PublicRepositoryEvidenceExecution
 -> <=2048-byte metadata-only semantic planning request
 -> <=1024-byte untrusted planner proposal
 -> exact deterministic public-v1 scope admission
 -> existing Phase 8 hybrid route authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

Public v1 product scope is code-owned, not model-owned. The planner must propose exactly:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

and the existing route authority must resolve that set to:

```text
HYBRID
ALL_REQUIRED
STRUCTURED + SEMANTIC
```

The planner does not receive raw repository URL, lockfile bytes, dependency names/versions, arbitrary repository text/instructions, SQL, credentials, provider/model/tool selection, or executable repository content.

### 5. Operational evidence contract

Phase 10 Gate 10.1 freezes:

```text
operational-telemetry:v1
operation: analyze_public_repository
```

Bounded stages:

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

The event contract has no arbitrary attributes bag. It may carry only bounded operational semantics and already-admitted content-addressed Phase 9 identities (`public_request_id`, `source_execution_id`, `handoff_id`) at stages where those identities can already exist.

Low-cardinality metric projection is deterministic:

```text
OperationalStageCount      Count
OperationalStageLatency    Milliseconds
```

with only:

```text
ContractVersion
Operation
Stage
Outcome
```

as metric dimensions. Request/source/handoff IDs never become metric dimensions.

Gate 10.1 exact-head validation:

```text
PR #135 final head:           7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
Operational Observability CI: run 34135197989 / PASS
Ruff:                         PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
pytest:                       14 passed
merge SHA:                    665b86f6e527a0096d7c3db522f4bd2c95b177aa
issue #134:                   CLOSED / COMPLETED
```

## Phase 8 hybrid authority

Hybrid Retrieval means **hybrid evidence routing**, not automatically keyword + vector search.

```text
EvidenceNeed[]
 -> deterministic route authority
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> deterministic typed evidence assembly
 -> ALL_REQUIRED completeness
 -> HybridEvidenceEnvelope
 -> route-aware bounded synthesis
```

Authority is never flattened:

```text
structured vulnerability/risk facts
 -> deterministic structured authority

explanatory/remediation guidance
 -> admitted semantic evidence

combined response
 -> explicit provenance by evidence class
 -> no authority laundering
```

Runtime exposure remains `UNSUPPORTED` until a future independent runtime authority is implemented.

## Phase 8 frozen evaluation

Dataset:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Six frozen cases:

```text
structured_only_factual
semantic_only_remediation
true_hybrid
unsupported_out_of_authority
partial_structured_evidence
semantic_retrieval_noise
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

## Gate 8.4 real hybrid baseline

Immutable evidence:

```text
labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json
```

Measured result:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

The semantic-noise case intentionally preserves a useful failure: rank-one evidence was admitted but not question-supporting, while rank-two evidence was the correct target. The model used both.

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct citation target
```

## Gate 8.5 measured optimization

One predeclared prompt-only hypothesis, `H8.5-01`, was tested exactly once against the frozen fixture.

```text
candidate: hybrid-synthesis-prompt:h8.5-01-v1
result:    REJECT
```

The candidate preserved every deterministic guardrail but did not improve the two target metrics:

```text
semantic_groundedness: 0.6666666666666666
citation_correctness:  0.6666666666666666
```

It also increased total model tokens by 280 versus the Gate 8.4 baseline. The candidate was therefore not promoted.

Runtime default remains:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

Immutable experiment evidence:

```text
labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json
```

This is intentional evaluation governance: a plausible prompt revision is not an optimization unless its predeclared measured acceptance rule passes.

## Phase 9 contracts

```text
public-analysis-request:v1
public-repository-evidence:v1
public-semantic-planning:v1
public-analysis-handoff:v1
```

Key distinctions:

```text
public request admitted != repository proven public != repository analyzed
planner proposal != execution authority
repository evidence != runtime exposure
semantic planning != SQL authority
application boundary validated != public runtime deployed
```

Phase 9 exact-head evidence is recorded in its gate labs and PRs. Gate 9.3 completed with Public Analysis Ruff/Pyright green and `57 passed`, while making zero real provider/model calls.

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

No public application runtime role exists after Gate 10.1. Gate 10.1 adds no AWS resources or IAM permissions. A future public runtime role will be created only when a concrete compute boundary exists and its responsibilities can be translated into least-privilege permissions.

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
- A valid citation ID proves identity admission, not question-specific semantic support.
- Missing evidence is not silently interpreted as benign evidence.
- Unsupported runtime exposure is not inferred from repository risk.
- Operational telemetry does not become application or route authority.
- High-cardinality identifiers are not metric dimensions in `operational-telemetry:v1`.
- First-run evidence is preserved before optimization.
- Negative experiments are preserved rather than tuned away.
- IAM least privilege, observability, failure diagnosis, and cost accounting are architecture requirements.
- A validated application boundary is not represented as a deployed production runtime.

## Cost discipline

OpsLens does not invent costs that runtime evidence cannot support.

Phase 7 has directly computable model/S3-Vectors components for one grounded evaluation, while the Gate 8.4/8.5 hybrid runtime deliberately reports:

```text
cost: UNMEASURED / null
```

Token counts remain valid cost-pressure evidence, but they are not silently converted to a full request price without a deterministic versioned pricing contract.

Phase 9 closeout and Phase 10 Gate 10.1 add no synthetic public-request price. Future public-runtime cost must include concrete infrastructure, concurrency, abuse, and retry assumptions.

## Quality gates

Dedicated Python CI slices cover:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
Hybrid Retrieval
Public Analysis
Operational Observability
```

The project uses Ruff, strict Pyright, pytest, and regression slices. AWS-bearing changes additionally use Terraform validation, TFLint, Checkov, canonical plans, deployment verification, and post-apply convergence checks.

## Repository structure

```text
.
├── .github/
├── docs/
│   ├── adr/
│   ├── architecture.md
│   ├── architecture.pt-br.md
│   ├── current-state.md
│   ├── roadmap.md
│   └── README.md
├── infra/
├── knowledge/
├── labs/
│   └── evidence/
├── scripts/
├── src/opslens/
│   ├── correlation/
│   ├── repository_intelligence/
│   ├── risk_policy/
│   ├── semantic_query/
│   ├── knowledge_retrieval/
│   ├── hybrid_retrieval/
│   ├── public_analysis/
│   └── shared/observability/
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
- [Documentation index](docs/README.md)
- [Phase 8 closeout](labs/phase-8-gate-8-6-closeout.md)
- [Phase 9 Gate 9.1 request admission](labs/phase-9-gate-9-1-public-request-admission.md)
- [Phase 9 Gate 9.3 semantic planning](labs/phase-9-gate-9-3-bounded-semantic-planning.md)
- [Phase 9 closeout](labs/phase-9-gate-9-4-closeout.md)
- [Phase 10 Gate 10.1 operational telemetry](labs/phase-10-gate-10-1-operational-telemetry-contract.md)

## Next — Phase 10 Gate 10.2: Governed Orchestration Instrumentation

Gate 10.2 will wire `operational-telemetry:v1` into the existing governed public-analysis orchestration through injected provider-neutral boundaries. It must define deterministic event sequencing and sink-failure semantics without allowing telemetry to change business, route, or evidence authority.

A public runtime, production exporter, SLO, or alert remains a separate later step that requires explicit deployment and measured workload evidence.

The long-lived Governed LLM Gateway PR #89 remains deferred and must be re-evaluated separately against the then-current OpsLens architecture.

---

OpsLens is intentionally built as an evidence system first and an agentic system later.
