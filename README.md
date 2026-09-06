<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Verifiable Software Supply Chain & Threat Intelligence on AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Deterministic Evidence**

</div>

OpsLens is an open-source software supply-chain intelligence platform built on AWS.

It is designed to answer:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, which findings should I prioritize, and what verified guidance can help me act on them?

The project deliberately keeps deterministic truth separate from model reasoning.

> **Agents reason. Code verifies evidence.**

Additional permanent boundaries:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

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
| Phase 8 | Hybrid Retrieval | ⏳ Next |

Phase 7 completed at the measured Gate 7.7 baseline and Gate 7.8 architecture closeout. The closeout intentionally does **not** tune the prompt against the observed baseline.

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), and [Architecture](docs/architecture.md).

## Implemented system

OpsLens now has two complementary evidence paths.

### Structured authority path

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
 -> bounded SemanticQuery planning
 -> deterministic SQL compilation
 -> bounded read-only Athena
```

The model never decides vulnerability applicability, risk-policy truth, or arbitrary SQL.

### Explanatory / remediation knowledge path

```text
immutable official source pins
 -> deterministic canonical corpus
 -> customer-managed Amazon Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> direct bounded Retrieve
 -> deterministic checked-corpus admission
 -> bounded deterministic context assembly
 -> one bounded Bedrock Converse synthesis
 -> deterministic C1..Cn citation authority
 -> structured claim/citation proposal
 -> human-reviewed support evidence
 -> deterministic groundedness metrics
```

`RetrieveAndGenerate` is deliberately not used. Retrieval and generation remain separately observable and separately testable.

## Phase 7 measured baseline

### Retrieval quality

Frozen `knowledge-retrieval-golden:v1`:

```text
10 cases: 8 positive + 2 negative/out-of-authority
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Both negative cases still returned vector neighbors. Similarity score or non-empty retrieval is therefore evidence, not answerability authority.

### Groundedness / citation quality

Frozen `knowledge-grounding-golden:v1`:

```text
decision accuracy:          1.0
citation target precision:  0.2857142857142857
citation target recall:     0.5
claim supportedness:        0.8461538461538461
unsupported claim rate:     0.15384615384615385
citation correctness:       0.8461538461538461
abstention precision:       1.0
abstention recall:          1.0
```

The most useful failure was preserved: one case retrieved the correct evidence at rank 1, yet the model cited an adjacent chunk. OpsLens treats this as a citation-attribution / groundedness failure rather than hiding it behind retrieval success.

The exact out-of-evidence TLS-cipher case correctly returned `insufficient_evidence` despite non-empty vector retrieval.

## Phase 7 AWS baseline

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

No Phase 7 application runtime role has been created. The future runtime IAM boundary is documented before compute exists: direct `bedrock:Retrieve` is scoped to the specific Knowledge Base, while non-streaming model invocation uses the exact US Geographic inference profile and its required regional foundation-model resources. `RetrieveAndGenerate`, streaming inference, Knowledge Base administration, and direct vector-store access are not part of the runtime entitlement.

See [ADR 0024](docs/adr/0024-phase7-runtime-iam-boundary.md).

## Security and authority invariants

- Raw third-party evidence is preserved before transformation.
- Exact source versions and hashes participate in evidence identity.
- Package normalization, version/range matching, vulnerability applicability, KEV/EPSS/CVSS evidence, and Risk Policy remain deterministic.
- Third-party repository code is never executed.
- Natural-language planning cannot emit unrestricted SQL authority.
- Retrieval output is evidence, not deterministic truth.
- Retrieved text remains untrusted instruction content even after provenance validation.
- Citation IDs come only from already-admitted context.
- A valid citation ID proves citation coverage, not semantic support.
- Missing evidence is not silently interpreted as benign evidence.
- First-run evaluation evidence is preserved before optimization.
- IAM least privilege, observability, failure diagnosis, and cost accounting are architecture requirements.

## Cost discipline

OpsLens does not invent costs that runtime evidence cannot support.

The first four-case grounded evaluation directly accounted for:

```text
model input:             $0.0129074
model output:            $0.0035475
model subtotal:          $0.0164549
4 S3 Vectors requests:   $0.0000100
computable total:        $0.0164649
```

This is deliberately not called the full AWS bill because query-embedding and S3 Vectors data-processed/data-returned units are not exposed by the runtime artifact.

## Quality gates

Dedicated Python CI slices cover:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
```

The project uses Ruff, strict Pyright, pytest, and regression slices. AWS-bearing changes additionally use Terraform validation, TFLint, Checkov, canonical plans, deployment verification, and post-apply convergence checks.

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
├── knowledge/
├── labs/
│   └── evidence/
├── scripts/
├── src/opslens/
│   ├── correlation/
│   ├── repository_intelligence/
│   ├── risk_policy/
│   ├── semantic_query/
│   └── knowledge_retrieval/
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
- [Phase 7 Gate 7.8 closeout](labs/phase-7-gate-7-8-closeout.md)

## Next — Phase 8: Hybrid Retrieval

Phase 8 will not mean “concatenate SQL rows and vector chunks.” It begins by freezing an explicit routing and authority contract between structured evidence and semantic evidence.

The starting rule is:

```text
structured vulnerability/risk facts -> structured deterministic authority
explanatory/remediation guidance    -> bounded semantic retrieval
combined answer                     -> explicit provenance by evidence class
```

Any new reranker, keyword/vector hybrid mode, extra vector technology, or prompt change must be justified by a measured quality/cost/failure requirement rather than certification coverage.

---

OpsLens is intentionally built as an evidence system first and an agentic system later.
