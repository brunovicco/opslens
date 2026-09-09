<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Verifiable Software Supply Chain & Threat Intelligence on AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Bounded Agent Reasoning · MCP · AgentCore · A2A · Deterministic Authority**

</div>

OpsLens is an open-source software-supply-chain intelligence platform built on AWS.

It is designed to answer:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, which findings should I prioritize, and what verified guidance can help me act on them?

The project deliberately separates deterministic truth, evidence admission, model reasoning, authorization, handoff admission, interoperability, execution, result disclosure, hosting/runtime behavior, and runtime exposure.

> **Agents reason. Code verifies evidence.**

> **Repository Risk != Runtime Exposure.**

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
| Phase 11 | Single-Agent Baseline | ✅ Complete |
| Phase 12 | Multi-Agent Architecture | ✅ Complete |
| Phase 13 | MCP | ✅ Complete — bounded offline interoperability retained |
| Phase 14 | Amazon Bedrock AgentCore | ✅ Complete — optional lab target retained; standing experiment IAM removed |
| Phase 15 | A2A | ✅ Complete — bounded offline reference interoperability + official SDK conformance retained |
| Phase 16 | Runtime Exposure with Amazon Inspector | ▶️ Next / Planned |
| Phase 17 | Security Hardening | ⏳ Planned |
| Phase 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), the [ADR index](docs/adr/README.md), and the [Phase 15 closeout](labs/phase-15-closeout.md).

## Core architecture

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

### 2. Bounded semantic query

```text
natural-language factual question
 -> bounded model planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured evidence
```

No unrestricted text-to-SQL authority is granted to the model.

### 3. Grounded retrieval on Bedrock

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
 -> groundedness evaluation
```

`RetrieveAndGenerate` is deliberately not used. Retrieval, evidence admission, synthesis, citations, and evaluation remain independently testable.

### 4. Hybrid evidence authority

```text
EvidenceNeed[]
 -> deterministic route authority
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> authority-separated evidence composition
 -> completeness checks
 -> HybridEvidenceEnvelope
 -> bounded route-aware synthesis
 -> deterministic output admission
```

Structured vulnerability/risk facts and semantic remediation evidence remain separate authority classes.

### 5. Bounded agent reasoning

Phase 11 remains the default/reference measured reasoning path:

```text
SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> one bounded model invocation
 -> untrusted action proposal
 -> deterministic parser
 -> authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | rejection
```

Measured six-case reference:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived inference cost:     USD 0.0041921
```

Phase 12 retained deterministic specialization/handoff but rejected the measured two-model topology as the default because it produced no quality lift while increasing calls, tokens, latency, and cost.

## Interoperability and runtime experiments

### MCP — Phase 13

Retained contracts:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
mcp-result-projection:v1
```

MCP remains a bounded offline interoperability layer over existing typed capability authority.

```text
MCP tool name != capability authorization
MCP call admission != capability execution
MCP result projection != public runtime exposure
```

A public/network MCP runtime is not currently retained.

### Amazon Bedrock AgentCore — Phase 14

Phase 14 measured one bounded HTTP/SigV4 Runtime experiment.

```text
Gate 14.2 replay:          6 / 6 PASS
AgentCore Runtime cost:    USD 0.002380345136128484
Bedrock inference cost:    USD 0.0041921
total observed cost:       USD 0.006572445136128483
runtime cleanup:           RESOURCE_NOT_FOUND
Gate 14.4 IAM cleanup:     0 add / 0 change / 4 destroy
```

Final retention:

```text
Phase 11 direct Bedrock reasoning:          RETAIN / DEFAULT
AgentCore implementation/evidence:          RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:        DO NOT RETAIN
standing AgentCore Runtime resources:        NONE
standing experiment-specific GitHub IAM:    REMOVED
Gate 14.2 PUBLIC exception:                  NOT RETAINED
```

### A2A — Phase 15

Phase 15 evaluated A2A without assuming that protocol adoption requires another network runtime.

Authoritative protocol baseline:

```text
A2A release:                 1.0.0
standard bindings:           JSONRPC / GRPC / HTTP+JSON
first OpsLens binding:       JSONRPC
selected operation:          SendMessage
```

Retained bounded path:

```text
pre-admitted SpecialistAgentTask
 -> content-addressed A2AReference
 -> code-owned local reference registry
 -> strict A2A 1.0 JSON-RPC SendMessage projection
 -> duplicate-key / exact-shape validation
 -> code-owned reference resolution
 -> Message or terminal completed Task metadata
 -> deterministic OpsLens admission
 -> STOP before model/capability execution
```

Gate 15.2 measured:

```text
Agent Card bytes:          582
protocol requests:         2
request bytes total:       1308
response bytes total:      989
client elapsed sum:        0.353039 ms
handler elapsed sum:       0.239397 ms
retries:                   0
model invocations:         0
capability executions:     0
new AWS resources:         0
new IAM roles/policies:    0
incremental AWS cost:      USD 0.00
```

Gate 15.3 verified the frozen profile against the official Python A2A SDK source:

```text
a2a-sdk version:             1.1.4
release tag:                 v1.1.4
source commit:               2d4d3048b245d2af854bad804f0e722ea9febc08
AgentCard conformance:       PASS
SendMessage request:         PASS
JSON-RPC construction:       PASS
Message response:            PASS
Task response:               PASS
project/runtime dependency:  0
protocol network requests:   0
```

The SDK is retained only as an exact-source CI conformance oracle.

Final Phase 15 decision:

```text
content-addressed A2AReference:                 RETAIN
strict raw JSON admission:                      RETAIN
A2A 1.0 JSONRPC SendMessage profile:            RETAIN
Message / terminal Task metadata admission:     RETAIN
A2A fixtures / CI:                              RETAIN
official exact-source SDK oracle:               RETAIN FOR CI
public/network A2A runtime:                      DO NOT CREATE
standing A2A cloud resources / IAM:             NONE
A2A capability/business-result authority:        DO NOT CREATE
a2a-sdk project/runtime dependency:              DO NOT ADD
```

```text
A2A SDK acceptance != OpsLens admission authority
A2A transport success != business/evidence truth
A2A protocol binding != business authority
```

## What is deliberately not claimed

OpsLens currently does **not** claim:

```text
public MCP production runtime
AgentCore as the default/production OpsLens runtime
PUBLIC AgentCore networking as a production decision
public/network A2A runtime
A2A-derived capability authorization
A2A business-result authority
runtime exposure / Amazon Inspector evidence
production SLOs for the experimental runtime boundaries
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
reasoning profile:       us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:               no
tools in reasoning:      none
```

## Documentation and evidence

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Architecture — English](docs/architecture.md)
- [Architecture — Português](docs/architecture.pt-br.md)
- [ADR index](docs/adr/README.md)
- [Documentation index](docs/README.md)
- [Phase 11 closeout](labs/phase-11-gate-11-6-closeout.md)
- [Phase 12 closeout](labs/phase-12-gate-12-5-multi-agent-closeout.md)
- [Phase 13 MCP closeout](labs/phase-13-gate-13-5-mcp-closeout.md)
- [Phase 14 AgentCore retention decision](labs/phase-14-gate-14-3-agentcore-retention-decision.md)
- [Phase 14 IAM cleanup](labs/phase-14-gate-14-4-agentcore-iam-cleanup.md)
- [Phase 15 A2A closeout](labs/phase-15-closeout.md)
- [Phase 15 closeout evidence](labs/evidence/phase-15-closeout-v1.json)

## Next planned phase

```text
Phase 16 — Runtime Exposure with Amazon Inspector
```

Phase 16 will add an independent runtime-exposure authority while preserving:

> **Repository Risk != Runtime Exposure.**

No Phase 16 AWS mutation is authorized by Phase 15 closeout alone.

---

PR #89 / `feat/governed-gateway-semantic-planner` is unrelated Governed LLM Gateway work and remains intentionally outside this phase scope.
