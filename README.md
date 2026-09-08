<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Verifiable Software Supply Chain & Threat Intelligence on AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Public Analysis · Operational Evidence · Bounded Agent Reasoning · MCP Interoperability · Deterministic Authority**

</div>

OpsLens is an open-source software-supply-chain intelligence platform built on AWS.

It is designed to answer:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, which findings should I prioritize, and what verified guidance can help me act on them?

The project deliberately separates deterministic truth, evidence admission, model reasoning, authorization, handoff admission, interoperability, and execution.

> **Agents reason. Code verifies evidence.**

> **MCP is an interoperability boundary, not new business authority.**

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
| Phase 11 | Single-Agent Baseline | ✅ Complete |
| Phase 12 | Multi-Agent Architecture | ✅ Complete |
| Phase 13 | MCP | 🚧 In progress — Gate 13.1 complete; Gate 13.2 next |

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), the [Phase 12 closeout](labs/phase-12-gate-12-5-multi-agent-closeout.md), and the [Gate 13.1 MCP exposure lab](labs/phase-13-gate-13-1-bounded-mcp-capability-exposure.md).

## Implemented governed system

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
 -> bounded model planner
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

Structured vulnerability/risk facts and semantic remediation evidence remain separate authority classes.

Runtime exposure remains `UNSUPPORTED` until an independent runtime authority exists.

### 5. Governed public-analysis boundary

```text
untrusted public JSON
 -> deterministic request admission
 -> immutable public GitHub evidence
 -> deterministic repository analysis
 -> proposal-only semantic planning
 -> deterministic public-v1 scope admission
 -> existing hybrid authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

Public v1 scope is code-owned, not model-owned.

### 6. Operational evidence

Phase 10 freezes:

```text
operational-telemetry:v1
cloudwatch-emf:v1
```

Operational evidence is content-minimized and low-cardinality. CloudWatch EMF serialization is a deterministic representation boundary, not proof of CloudWatch ingestion.

```text
telemetry evidence != business truth
telemetry evidence != route authority
EMF document created != CloudWatch ingestion proven
```

### 7. Bounded single-agent reasoning

Phase 11 freezes:

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

Permanent reasoning boundary:

```text
SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> one bounded model reasoning invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
```

The real Gate 11.4 model-quality baseline intentionally stops before capability execution. Typed capability execution remains a separate deterministic boundary.

### 8. Bounded multi-agent handoff authority

Phase 12 Gate 12.1 freezes:

```text
multi-agent-handoff:v1
```

Code-owned specialization partition:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

Handoff boundary:

```text
SingleAgentTask
 -> TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source-task binding
 -> code-owned specialization scope
 -> deterministic intersection with source allowed_capabilities
 -> empty intersection? FAIL CLOSED
 -> AuthorizedMultiAgentHandoff | MultiAgentHandoffAbstention
 -> narrowed SpecialistAgentTask
 -> STOP
```

The `4 -> <=2` specialist capability reduction is reasoning-surface narrowing, not runtime privilege reduction. Models still have no execution authority.

### 9. Deterministic multi-agent comparison authority

Phase 12 Gate 12.2 freezes:

```text
multi-agent-comparison:v1
```

The comparison contract was frozen before a second real model invocation existed. Its synthetic `6/6` result is evaluator/contract conformance, not model quality.

Exact evidence identities:

```text
Phase 11 corpus_sha256:   3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
Phase 11 report_sha256:   724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
Gate 12.2 dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
Gate 12.2 report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
```

### 10. Measured multi-agent experiment and retention

Gate 12.3 introduced the first authenticated bounded two-model experiment while preserving deterministic handoff and capability-authorization authority.

Observed result:

```text
quality:                           6/6
model invocations:                 10
input/output/total tokens:          5788 / 194 / 5982
provider latency median per task:  1694.0 ms
client elapsed median per task:    2135.0 ms
SDK retries:                       0
capability executions:             0
derived six-case cost:             USD 0.0074338
```

Gate 12.4 compared that result with the retained Phase 11 reference:

```text
quality:                    6/6 -> 6/6      no lift
model invocations:          6 -> 10         +66.67%
total tokens:               3395 -> 5982    +76.20%
provider latency median:    809.5 -> 1694   +109.26%
client elapsed median:      977.5 -> 2135   +118.41%
derived cost:               0.0041921 -> 0.0074338 USD  +77.33%
```

Frozen retention decision:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
```

Phase 12 therefore closes around the architecture that survived measurement, not around the most complex experiment.

### 11. Bounded MCP capability exposure

Phase 13 Gate 13.1 freezes:

```text
mcp-capability-exposure:v1
```

Closed one-to-one MCP tool surface:

```text
opslens.structured_security_query   -> structured_security_query
opslens.knowledge_guidance          -> knowledge_guidance
opslens.hybrid_security_answer      -> hybrid_security_answer
opslens.public_repository_analysis  -> public_repository_analysis
```

Authority path:

```text
existing AuthorizedAgentAction
 + existing typed AgentCapabilityInvocation
 -> closed McpToolName
 -> deterministic tool/capability match
 -> content-addressed McpToolCallAdmission
 -> STOP
```

The MCP layer does not create authorization, does not create typed invocation semantics, does not execute a capability, and does not receive arbitrary executable `args` / `kwargs` authority.

The existing `single-agent-execution:v1` typed invocation remains authoritative for `SemanticQuery`, synthesis requests, repository coordinates, and other executable input semantics. MCP cannot author SQL, arbitrary URLs, shell commands, credentials, provider/model selection, retry/fallback policy, or execution results.

Gate 13.1 adds no MCP SDK and no network/server runtime. The framework choice is deliberately deferred until the authority contract is frozen.

## Phase 11 real Bedrock baseline

Fixed reasoning provider:

```text
Amazon Bedrock Converse
region:          us-east-1
model/profile:   us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:     0.0
maxTokens:       96
tools:           disabled
```

Measured result:

```text
proposal quality:             6/6
bounds compliance:            6/6
SDK retries:                  0
capability executions:        0
input/output/total tokens:    3291 / 104 / 3395
provider latency median:      809.5 ms
client elapsed median:        977.5 ms
derived six-case cost:        USD 0.0041921
```

Preserved evidence:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

The six-case result is an acceptance-corpus result, not a universal model-correctness claim.

## Phase 13 Gate 13.1 merge evidence

```text
issue:                  #180
PR:                     #181
final head:             340f2d7beee3640bd14455de635fe3ee4b6cc5cc
PR merge test commit:   166e5626f52bdbabfd306b0e3152b02c1620ee5f
MCP CI:                 34223369166 / run #3 / PASS
job:                    102051514632
uv lock --check:        PASS
MCP import smoke:       PASS
Ruff:                   PASS
Pyright strict:         0 errors / 0 warnings / 0 informations
pytest MCP slice:       7 passed in 0.19s
review threads:         0
model invocations:      0
capability executions:  0
MCP SDK/runtime:        0
new AWS/IAM:            0
merge SHA:              322922aed4abec3b2266a18d15d8145df974a7d1
```

## Security and authority invariants

- Raw third-party evidence is preserved before transformation.
- Exact source versions and hashes participate in evidence identity.
- Package normalization, version/range matching, vulnerability applicability, KEV/EPSS/CVSS evidence, and Risk Policy remain deterministic.
- Third-party repository code is never executed.
- Public request admission never grants arbitrary fetch authority.
- Natural-language planning cannot emit unrestricted SQL authority.
- Retrieval output is evidence, not deterministic truth.
- Retrieved text remains untrusted instruction content after provenance validation.
- Hybrid routing and required-evidence completeness are deterministic.
- Citation IDs come only from admitted evidence.
- Agent action proposal is not capability authorization.
- Handoff proposal is not handoff admission.
- Handoff admission is not capability authorization.
- Authorized action is not capability invocation.
- Capability invocation is not execution result.
- MCP tool name is not capability authorization.
- MCP exposure is not executable argument authority.
- MCP admission is not capability execution.
- MCP transport success is not business/evidence truth.
- Raw model/provider/downstream output is not canonical authority merely because a protocol transported it.
- Provider/model selection and retry/fallback policy remain code-owned.
- Unsupported runtime exposure is not inferred from repository risk.
- IAM least privilege, observability, failure diagnosis, and cost accounting are architecture requirements.

## What Gate 13.1 does not prove

```text
real MCP protocol interoperability
MCP client/server serialization
MCP authentication or authorization transport
session lifecycle or network reliability
capability execution through MCP
MCP result transport
public/deployed MCP runtime
production MCP SLOs
Amazon Bedrock AgentCore runtime behavior
A2A interoperability
runtime exposure / Amazon Inspector evidence
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

## Documentation

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Architecture — English](docs/architecture.md)
- [Architecture — Português](docs/architecture.pt-br.md)
- [ADR index](docs/adr/README.md)
- [Documentation index](docs/README.md)
- [Phase 11 closeout](labs/phase-11-gate-11-6-closeout.md)
- [Phase 12 closeout](labs/phase-12-gate-12-5-multi-agent-closeout.md)
- [Phase 13 Gate 13.1 bounded MCP exposure](labs/phase-13-gate-13-1-bounded-mcp-capability-exposure.md)
- [ADR 0047 — Bounded MCP Capability Exposure](docs/adr/0047-bounded-mcp-capability-exposure.md)

## Next — Phase 13 Gate 13.2: Bounded MCP Protocol Adapter / Offline Interoperability

Gate 13.2 may introduce a real MCP protocol adapter only against the already-frozen Gate 13.1 authority contract.

Before adding an SDK dependency, the current official MCP Python SDK/API must be verified and the chosen dependency pinned deliberately.

Initial path:

```text
MCP protocol tool call
 -> exact closed tool identity
 -> bounded invocation reference
 -> deterministic server-side resolution to existing typed AgentCapabilityInvocation
 -> Gate 13.1 admit_mcp_tool_call(...)
 -> content-minimized admission response/evidence
 -> STOP before execute_authorized_capability(...)
```

The first interoperability proof should remain offline/in-process or stdio. No public network deployment, new AWS/IAM authority, capability execution, AgentCore, A2A, or runtime-exposure claim is authorized by this gate boundary.

The long-lived Governed LLM Gateway PR #89 remains deferred cross-project work and must be re-evaluated separately against the current OpsLens architecture before any merge.

---

OpsLens is intentionally built as an evidence system first and an agentic/interoperability system only where measured evidence justifies the added complexity.
