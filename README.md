<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Verifiable Software Supply Chain & Threat Intelligence on AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Deterministic Authority**

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
| Phase 9 | Public Analyze Your Repository | ⏳ Next |

Phase 8 closes with deterministic hybrid routing/evidence authority, route-aware bounded synthesis, a frozen six-case evaluation contract, a real Bedrock baseline, and one measured optimization experiment whose candidate was correctly **rejected** because it did not improve groundedness or citation correctness.

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), and the [Phase 8 closeout](labs/phase-8-gate-8-6-closeout.md).

## Implemented system

OpsLens now has three cooperating evidence paths while preserving different authority semantics.

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

No public application runtime role exists yet. Gate 8.6 adds no AWS resources or IAM permissions. The future semantic runtime boundary remains scoped to direct `bedrock:Retrieve` for the exact Knowledge Base plus non-streaming `bedrock:InvokeModel` for the approved inference profile/resources. Public-runtime IAM will be created only when Phase 9 defines real compute.

## Security and authority invariants

- Raw third-party evidence is preserved before transformation.
- Exact source versions and hashes participate in evidence identity.
- Package normalization, version/range matching, vulnerability applicability, KEV/EPSS/CVSS evidence, and Risk Policy remain deterministic.
- Third-party repository code is never executed.
- Natural-language planning cannot emit unrestricted SQL authority.
- Retrieval output is evidence, not deterministic truth.
- Retrieved text remains untrusted instruction content after provenance validation.
- Hybrid routing and required-evidence completeness are deterministic.
- Structured and semantic evidence remain separate authority classes.
- Citation IDs come only from admitted evidence.
- A valid citation ID proves identity admission, not question-specific semantic support.
- Missing evidence is not silently interpreted as benign evidence.
- Unsupported runtime exposure is not inferred from repository risk.
- First-run evidence is preserved before optimization.
- Negative experiments are preserved rather than tuned away.
- IAM least privilege, observability, failure diagnosis, and cost accounting are architecture requirements.

## Cost discipline

OpsLens does not invent costs that runtime evidence cannot support.

Phase 7 has directly computable model/S3-Vectors components for one grounded evaluation, while the Gate 8.4/8.5 hybrid runtime deliberately reports:

```text
cost: UNMEASURED / null
```

Token counts remain valid cost-pressure evidence, but they are not silently converted to a full request price without a deterministic versioned pricing contract.

## Quality gates

Dedicated Python CI slices cover:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
Hybrid Retrieval
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
│   └── hybrid_retrieval/
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
- [Phase 7 closeout](labs/phase-7-gate-7-8-closeout.md)
- [Phase 8 Gate 8.4 bounded synthesis](labs/phase-8-gate-8-4-bounded-hybrid-synthesis.md)
- [Phase 8 Gate 8.5 measured optimization](labs/phase-8-gate-8-5-measured-optimization.md)
- [Phase 8 closeout](labs/phase-8-gate-8-6-closeout.md)

## Next — Phase 9: Public Analyze Your Repository

Phase 9 may expose the governed evidence system as a bounded public demo. It must preserve immutable repository acquisition, deterministic structured truth, hybrid route/evidence authority, fail-closed output admission, zero-model-call behavior for unsupported/incomplete paths, and bounded cost/abuse controls.

A public surface does not justify introducing agents, AgentCore, MCP, A2A, rerankers, or a new vector technology by default. Those remain later phases or new measured hypotheses.

The long-lived Governed LLM Gateway PR #89 remains deferred and outside Phase 8.

---

OpsLens is intentionally built as an evidence system first and an agentic system later.
