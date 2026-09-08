<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Verifiable Software Supply Chain & Threat Intelligence on AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Public Analysis · Operational Evidence · Bounded Agent Reasoning · Deterministic Authority**

</div>

OpsLens is an open-source software-supply-chain intelligence platform built on AWS.

It is designed to answer:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, which findings should I prioritize, and what verified guidance can help me act on them?

The project deliberately separates deterministic truth, evidence admission, model reasoning, authorization, handoff admission, and execution.

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
| Phase 11 | Single-Agent Baseline | ✅ Complete |
| Phase 12 | Multi-Agent Architecture | 🚧 In progress — Gate 12.1 complete |

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), the [Phase 11 closeout](labs/phase-11-gate-11-6-closeout.md), and the [Gate 12.1 handoff lab](labs/phase-12-gate-12-1-bounded-specialization-handoff.md).

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

Hard bounds:

```text
maximum handoffs per source task:       1
maximum specialist capability surface:  2
real model calls in Gate 12.1:           0
capability executions in Gate 12.1:      0
```

The `4 -> <=2` specialist capability reduction is a reasoning-surface narrowing property, not a runtime privilege-reduction claim. Models still have no execution authority.

The handoff proposal cannot carry arbitrary messages/context, capability selection, args/kwargs, SQL, URLs, shell commands, credentials, provider/model selection, retry/fallback policy, or execution results.

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

Preserved evidence:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
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

The first authenticated runtime attempt exposed a provider constraint: Bedrock structured outputs rejected JSON Schema `oneOf`. The adapter was corrected to a flat closed schema while ACT/ABSTAIN cross-field consistency remained deterministic application authority.

The six-case result is an acceptance-corpus result, not a universal model-correctness claim.

## Measured optimization decision

Gate 11.5 intentionally retained the implementation unchanged:

```text
optimization decision: NO-CHANGE / NO-EXPERIMENT
```

Prompt compression, model switching, prompt caching, retry/fallback expansion, and capability expansion were not justified by a material measured target.

This project treats **not optimizing** as a valid engineering result when evidence does not justify additional complexity or risk.

## Gate 12.1 merge evidence

```text
PR:                     #166
final head:             567cdbde81f058d9545328ca78b718c24d79c9fb
Multi-Agent CI:         34172909750 / run #3 / PASS
multi-agent pytest:     10 passed in 0.39s
Single-Agent CI:        34172909748 / run #48 / PASS
single-agent pytest:    56 passed in 0.44s
merge SHA:              eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
```

Gate 12.1 adds no AWS resource, IAM permission, model call, capability execution, AgentCore, MCP, A2A, public runtime, or runtime-exposure authority.

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
- Raw model output is not canonical evidence.
- Provider/model selection and retry/fallback policy remain code-owned.
- Unsupported runtime exposure is not inferred from repository risk.
- IAM least privilege, observability, failure diagnosis, and cost accounting are architecture requirements.

## What Phase 12 Gate 12.1 does not prove

```text
multi-agent quality improvement
triage-model routing accuracy
specialist-model reasoning quality
multi-agent token / latency / inference cost
multi-agent runtime reliability
runtime privilege reduction
capability execution through multi-agent flow
public/deployed agent runtime
AgentCore runtime behavior
MCP interoperability
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
- [Phase 8 closeout](labs/phase-8-gate-8-6-closeout.md)
- [Phase 9 closeout](labs/phase-9-gate-9-4-closeout.md)
- [Phase 10 closeout](labs/phase-10-gate-10-4-closeout.md)
- [Phase 11 Gate 11.4 real baseline](labs/phase-11-gate-11-4-bounded-model-reasoning-baseline.md)
- [Phase 11 Gate 11.5 optimization decision](labs/phase-11-gate-11-5-measured-optimization-decision.md)
- [Phase 11 closeout](labs/phase-11-gate-11-6-closeout.md)
- [Phase 12 Gate 12.1 bounded handoff](labs/phase-12-gate-12-1-bounded-specialization-handoff.md)

## Next — Phase 12 Gate 12.2: Comparative Multi-Agent Evaluation Contract

Before a second model call is introduced, OpsLens must freeze the comparison protocol against the Phase 11 reference.

```text
routing/proposal quality
bounds compliance
specialist capability-surface width
model invocation count
tokens
provider/client latency
SDK retries
inference cost
capability executions
```

The metric authority remains deterministic; no LLM judge owns acceptance. A two-model topology is retained only if measured specialization value justifies its additional latency, token usage, cost, failure surface, and architectural complexity.

AgentCore, MCP, and A2A remain separate future architecture decisions.

The long-lived Governed LLM Gateway PR #89 remains deferred cross-project work and must be re-evaluated separately against the current OpsLens architecture before any merge.

---

OpsLens is intentionally built as an evidence system first and an agentic system only where measured evidence justifies the added complexity.
