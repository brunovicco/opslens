# OpsLens — Architecture

_Last updated: 2026-09-04_

## Purpose

OpsLens is an open-source software supply chain and threat-intelligence platform on AWS.

Product question:

> Given the software I actually use, which vulnerabilities affect it, what evidence proves that, what should I prioritize, and what remediation knowledge is relevant?

Core invariant:

> **Agents reason. Code verifies evidence.**

Additional permanent boundaries:

- Not every question is a RAG problem.
- Structured facts use structured retrieval.
- Semantic retrieval is scoped and evidence-preserving.
- No unrestricted text-to-SQL.
- READ, NEVER EXECUTE third-party repository code.
- Repository Risk != Runtime Exposure.
- Missing evidence is not silently converted into benign evidence.
- AWS services are introduced only for concrete needs.
- IAM least privilege, observability, bounded execution, and cost are architectural requirements.

## Current system shape

```text
NVD / CISA KEV / FIRST EPSS / GitHub Security Advisories
        |
        v
DETERMINISTIC CORRELATION
PyPI identity + PEP 440 + GHSA applicability + CVE/NVD evidence
        |
        v
REPOSITORY INTELLIGENCE
immutable GitHub snapshot + inert uv.lock
        |
        v
RISK PRIORITIZATION
Risk Policy v1
        |
        +------------------------------+
        |                              |
        v                              v
STRUCTURED QUESTION PATH          KNOWLEDGE PATH (Phase 7)
Bedrock bounded planner           controlled knowledge corpus
 -> deterministic parser          -> semantic retrieval
 -> typed SemanticQuery            -> typed retrieved chunks
 -> deterministic SQL              -> deterministic context assembly
 -> bounded Athena                 -> Bedrock synthesis
                                  -> explicit citations
```

## Deterministic vs generative authority

Deterministic code owns:

- package normalization and vulnerable-range matching;
- vulnerability applicability;
- alias reconciliation and source evidence;
- KEV/EPSS/CVSS lookups;
- Risk Policy v1;
- semantic-query validation and SQL compilation;
- retrieval-result validation and evidence identity;
- context-size/cost/tool/execution limits.

Models may plan, classify, synthesize, explain, and route over validated evidence. A model does not become an authority for vulnerability applicability, SQL, source truth, or runtime exposure.

## Phase 6 completed boundary

Phase 6 established:

```text
User question
 -> BedrockSemanticPlanner
 -> structured proposal
 -> deterministic parse_planner_json
 -> typed SemanticQuery
 -> deterministic compiler
 -> exact compiler-shape admission
 -> bounded read-only Athena
```

The runtime uses the US Geographic inference profile for Claude Haiku 4.5. Real success and fail-closed behavior were validated before merge in PR #91.

## Phase 7 target boundary

Phase 7 introduces retrieval for remediation/documentation questions only.

Target architecture:

```text
trusted/curated security knowledge sources
 -> canonical KnowledgeDocument records
 -> content-addressed corpus objects
 -> Bedrock Knowledge Base ingestion
 -> embedding model
 -> vector store
 -> Bedrock Retrieve API
 -> typed RetrievedChunk[] + RetrievalEvidence
 -> deterministic filtering/context assembly
 -> bounded Bedrock synthesis
 -> Answer + Citation[]
```

The exact Knowledge Base/vector-store configuration is not frozen before Phase 7 Gate 7.1. Current AWS capabilities, limits, IAM requirements, and pricing must be revalidated against official AWS documentation before infrastructure is selected.

### Corpus authority rule

Do not dump structured NVD/KEV/EPSS/GHSA analytics into RAG as a competing truth source. The initial corpus should focus on explanatory/remediation knowledge and preserve:

```text
source_id
source_type
canonical_uri
vulnerability_ids[] when applicable
package/ecosystem when applicable
published_at / updated_at when available
content_sha256
text
```

Structured factual claims should remain cross-checkable against deterministic authorities.

### Retrieval authority rule

Retrieval output is evidence, not truth. Retrieved chunks must carry source provenance, stable identifiers, and bounded metadata. Generation may only synthesize from admitted context and must produce explicit citations.

## Phase 7 IAM boundary

Two conceptual identities are expected if/when infrastructure is introduced:

```text
Knowledge Base service role
 -> read the approved corpus location
 -> invoke the selected embedding model
 -> access the selected vector store/index

OpsLens retrieval runtime identity
 -> invoke only the required Bedrock retrieval/generation APIs
 -> access only the approved Knowledge Base/model resources
```

Do not reuse bootstrap/admin permissions as final runtime IAM.

## Phase 7 evaluation boundary

Retrieval and generation must be evaluated separately.

Minimum retrieval metrics:

- Recall@K;
- MRR or equivalent rank-sensitive metric;
- metadata/source correctness.

Minimum generation metrics:

- groundedness;
- citation coverage/correctness;
- unsupported-claim rate;
- latency and token/cost evidence.

## Future boundary

Hybrid retrieval, agents, MCP, AgentCore/gateway integration, A2A, runtime exposure, and later security hardening remain later phases. PR #89 stays parked as later integration work and must not redefine Phase 7 scope.
