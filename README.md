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
| Phase 12 | Multi-Agent Architecture | ✅ Complete |
| Phase 13 | MCP | ▶️ Next |

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), the [Phase 11 closeout](labs/phase-11-gate-11-6-closeout.md), and the complete [Phase 12 closeout](labs/phase-12-gate-12-5-multi-agent-closeout.md).

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

### 9. Deterministic multi-agent comparison authority

Phase 12 Gate 12.2 freezes:

```text
multi-agent-comparison:v1
```

The comparison contract is intentionally frozen before a second real model invocation exists:

```text
frozen synthetic comparison fixture
 -> admitted SingleAgentTask
 -> synthetic untrusted MultiAgentHandoffProposal
 -> Gate 12.1 deterministic admission
 -> HANDOFF | ABSTAINED | REJECTED
 -> deterministic decomposed scoring
 -> content-addressed report
 -> runtime measurements remain null / unmeasured
 -> STOP
```

Exact Phase 11 reference binding:

```text
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Frozen Gate 12.2 evidence:

```text
dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
total / passed:                        6 / 6
handoff / abstention cases:             4 / 2
source capability slots for handoffs: 16
specialist capability slots:            8
capability slots removed:               8
offline capability executions:          0
```

The `6/6` result is synthetic evaluator/contract conformance, not triage-model quality, specialist-model quality, or a real multi-agent baseline.

Because Gate 12.2 invokes no model, model invocation count, tokens, provider/client latency, SDK retries, and inference cost are explicitly `null` rather than manufactured zeros.

### 10. Measured multi-agent experiment and retention

Gate 12.3 introduced the first authenticated bounded two-model experiment while preserving deterministic handoff and capability-authorization authority.

Historical evidence:

```text
labs/evidence/phase-12-gate-12-3-first-real-two-model-comparison-v1.json
```

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

Gate 12.4 compared that result with the Phase 11 reference:

```text
quality:                    6/6 -> 6/6      no lift
model invocations:          6 -> 10         +66.67%
total tokens:               3395 -> 5982    +76.20%
provider latency median:    809.5 -> 1694   +109.26%
client elapsed median:      977.5 -> 2135   +118.41%
derived cost:               0.0041921 -> 0.0074338 USD  +77.33%
SDK retries:                0 -> 0
capability executions:      0 -> 0
```

Frozen retention decision:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
new rescue/tuning experiment:                   NOT AUTHORIZED WITHOUT NEW HYPOTHESIS
```

Phase 12 therefore closes around the architecture that survived measurement, not around the most complex experiment.

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

## Phase 12 merge evidence

```text
Gate 12.1  PR #166  merge eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
Gate 12.2  PR #169  merge 865ba70c813711cb88da9ac7308c8966ff983fd0
Gate 12.3  PR #172  merge f51cb70ad070716e774419b8d2c62918d3e65210
Gate 12.4  PR #175  merge fabe8128d1d6077e8de92225991b5e26c1b72ab3
Gate 12.5  PR #178  merge aca4264e9c98f81c239b44b55c8772ef02debc4c
```

Gate 12.5 exact closeout validation:

```text
PR final head:          3d9ad6a6d302299fb8209b40c7232bc18555c2dd
PR merge test commit:   f2de18db9a2b23413be4977e3f4b21a5846ed837
Multi-Agent CI:         34220492021 / run #34 / PASS
job:                    102042205489
Pyright strict:         0 errors / 0 warnings / 0 informations
pytest:                 33 passed in 0.35s
new model invocations:  0
new inference cost:     USD 0.00
```

Closeout evidence:

```text
labs/evidence/phase-12-closeout-v1.json
```

Phase 12 adds no public agent runtime, AgentCore runtime, MCP runtime, A2A runtime, runtime-exposure authority, or model-owned authorization authority.

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
- Synthetic fixture conformance is not model quality.
- Raw model output is not canonical evidence.
- Provider/model selection and retry/fallback policy remain code-owned.
- Unsupported runtime exposure is not inferred from repository risk.
- IAM least privilege, observability, failure diagnosis, and cost accounting are architecture requirements.

## What Phase 12 does not prove

```text
multi-agent capability execution in a deployed runtime
public/deployed agent runtime
production request volume or agent SLOs
Amazon Bedrock AgentCore runtime behavior
MCP interoperability
A2A interoperability
runtime exposure / Amazon Inspector evidence
universal superiority of multi-agent architecture
model-owned handoff admission
model-owned capability authorization
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
- [Phase 11 closeout](labs/phase-11-gate-11-6-closeout.md)
- [Phase 12 Gate 12.1 bounded handoff](labs/phase-12-gate-12-1-bounded-specialization-handoff.md)
- [Phase 12 Gate 12.2 comparison contract](labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md)
- [Phase 12 Gate 12.3 real two-model experiment](labs/phase-12-gate-12-3-first-bounded-real-two-model-comparison.md)
- [Phase 12 Gate 12.4 retention decision](labs/phase-12-gate-12-4-measured-multi-agent-retention-decision.md)
- [Phase 12 closeout](labs/phase-12-gate-12-5-multi-agent-closeout.md)

## Next — Phase 13: MCP

The next phase may expose already-bounded OpsLens capabilities through explicit MCP contracts.

> **MCP is an interoperability boundary, not new business authority.**

Phase 13 must preserve deterministic capability authorization, typed invocation/result admission, evidence provenance, fail-closed schema/tool handling, and least privilege. It must not introduce arbitrary executable args/kwargs, SQL, URLs, shell commands, credentials, hidden provider selection, or runtime-exposure claims.

Amazon Bedrock AgentCore and A2A remain separate later architecture decisions.

The long-lived Governed LLM Gateway PR #89 remains deferred cross-project work and must be re-evaluated separately against the current OpsLens architecture before any merge.

---

OpsLens is intentionally built as an evidence system first and an agentic system only where measured evidence justifies the added complexity.