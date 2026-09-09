<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Verifiable Software Supply Chain & Threat Intelligence on AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Public Analysis · Operational Evidence · Bounded Agent Reasoning · MCP Interoperability · AgentCore Runtime Evidence · Deterministic Authority**

</div>

OpsLens is an open-source software-supply-chain intelligence platform built on AWS.

It is designed to answer:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, which findings should I prioritize, and what verified guidance can help me act on them?

The project deliberately separates deterministic truth, evidence admission, model reasoning, authorization, handoff admission, interoperability, execution, result disclosure, hosting/runtime behavior, and runtime exposure.

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
| Phase 13 | MCP | ✅ Complete — bounded offline MCP retained |
| Phase 14 | Amazon Bedrock AgentCore | ✅ Complete — optional lab target retained; standing experiment IAM removed |
| Phase 15 | A2A | ▶️ Next / planned |
| Phase 16 | Runtime Exposure with Amazon Inspector | ⏳ Planned |
| Phase 17 | Security Hardening | ⏳ Planned |
| Phase 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), the [Phase 13 MCP closeout](labs/phase-13-gate-13-5-mcp-closeout.md), and the [Phase 14 Gate 14.4 closeout](labs/phase-14-gate-14-4-agentcore-iam-cleanup.md).

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

Structured vulnerability/risk facts and semantic remediation evidence remain separate authority classes. Runtime exposure remains `UNSUPPORTED` until an independent runtime authority exists.

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

Measured reference:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived six-case cost:      USD 0.0041921
```

### 8. Bounded multi-agent handoff authority

Phase 12 retains deterministic specialization and handoff admission:

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

The measured two-model topology was not retained as the default because it produced no quality lift while increasing model calls, tokens, latency, and cost.

Retained decision:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
```

### 9. Bounded MCP interoperability and result disclosure

Phase 13 freezes:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
mcp-result-projection:v1
```

Closed one-to-one MCP surface:

```text
opslens.structured_security_query   -> structured_security_query
opslens.knowledge_guidance          -> knowledge_guidance
opslens.hybrid_security_answer      -> hybrid_security_answer
opslens.public_repository_analysis  -> public_repository_analysis
```

Retained path:

```text
existing typed Phase 11 capability authority
 -> closed MCP tool identity
 -> official MCP SDK reference-only adapter
 -> raw exact-key-set argument refusal
 -> deterministic invocation resolution + admission
 -> exactly one existing typed executor attempt
 -> existing typed result admission
 -> explicit result projection for structured_security_query only
 -> bounded CVE + EPSS rows
 -> STOP before public/network runtime
```

MCP does not author `SemanticQuery`, SQL, URLs, shell commands, credentials, provider/model selection, retry/fallback policy, or arbitrary executable arguments. Public/network MCP hosting remains a non-claim.

### 10. Measured AgentCore Runtime experiment

Phase 14 Gate 14.1 authorized one bounded Runtime experiment only. Gate 14.2 hosted the retained Phase 11 reasoning boundary without adding capability execution authority:

```text
AgentCore Runtime HTTP / IAM SigV4
 -> exact request admission
 -> retained SingleAgentTask authority
 -> one fixed Bedrock reasoning invocation
 -> deterministic parser
 -> existing authorize_agent_action(...)
 -> metadata-only AgentCoreReasoningProjection
 -> STOP before capability execution
```

Terminal successful run #11:

```text
source main:                e5072ec68b421677359cebb1eb449578ef7d5b49
workflow run:               34378942784 / SUCCESS
runtime:                    opslens_dev_bounded_runtime-Cl8aNBDGzh
protocol:                   HTTP
network:                    PUBLIC — dev-only experiment exception
artifact SHA256:            a846034ad646c4f6383ac08e47d9ed065b4a9f3349c14104db49a2d510b3ec88
replay:                     6 / 6 PASS
input/output/total tokens:  3291 / 104 / 3395
SDK retries:                0
capability executions:      0
transport elapsed sum:      19981 ms
deployment-role invocation: AccessDeniedException / HTTP 403
cleanup verifier:           RESOURCE_NOT_FOUND
```

Observed experiment cost:

```text
AgentCore Runtime:  USD 0.002380345136128484
Bedrock inference:  USD 0.004192100000000000
TOTAL:              USD 0.006572445136128483
```

Attempts #1–#10 remain preserved as measured IAM/lifecycle remediation evidence. The successful run does not rewrite those failures away.

Gate 14.2 did **not** approve AgentCore or `PUBLIC` networking for production, establish a production SLO, create runtime-exposure truth, or authorize capability execution.

## Phase 14 retention and closeout

Gate 14.3 compared the measured AgentCore result with the retained Phase 11 reference using only comparable evidence.

Final retention decision:

```text
overall decision:                         RETAIN WITH CHANGES
Phase 11 direct Bedrock reasoning:        RETAIN / DEFAULT
AgentCore implementation/evidence:        RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:      DO NOT RETAIN
PUBLIC network mode:                      DO NOT RETAIN
standing AgentCore Runtime resources:     DO NOT RETAIN
standing experiment-specific GitHub IAM: REMOVE
```

The six-case quality, model-count, and token evidence was identical between Phase 11 and the AgentCore-hosted replay. The underlying Bedrock inference cost remained USD 0.0041921; AgentCore added USD 0.002380345136128484 of measured Runtime compute, or 56.78168784448091% relative to the inference component for this experiment.

Raw latency boundaries are preserved but not normalized into a comparative percentage because they are not sufficiently controlled to support that claim.

### Gate 14.4 standing-IAM cleanup

Repository cleanup was protected-merged in PR #225:

```text
merge SHA:                 9913c3cbf5f2239d6445042a139a9cca890590c8
exact-head AgentCore CI:   34396085154 / run #63 / PASS
exact-head Terraform CI:   34396085123 / run #267 / PASS
```

Human bootstrap result:

```text
reviewed plan:          0 add / 0 change / 4 destroy
apply:                  0 add / 0 change / 4 destroy
post-apply convergence: NO CHANGES
```

Independent IAM verification:

```text
OpsLensAgentCoreReplayRole:                 ABSENT / NoSuchEntity
OpsLensAgentCoreDeployDevAccess:            ABSENT / NoSuchEntity
AgentCore deploy policy attachment:         []
OpsLensGitHubDeployRole:                    PRESENT
AWSServiceRoleForBedrockAgentCoreRuntimeIdentity:
                                            PRESENT / intentionally retained
```

The Runtime Identity service-linked role remains protected because safe account-level deletion has not been proven. It is AWS-service scoped and is not equivalent to standing GitHub experiment authority.

The historical AgentCore workflow/code remains reproducible lab material, but it is intentionally non-operational until a future evidence-backed re-bootstrap of minimum authority. The Gate 14.2 `PUBLIC` exception is not inherited by any future experiment.

## Security and authority invariants

- Raw third-party evidence is preserved before transformation.
- Exact source versions and hashes participate in evidence identity.
- Package normalization, version/range matching, vulnerability applicability, KEV/EPSS/CVSS evidence, and Risk Policy remain deterministic.
- Third-party repository code is never executed.
- Public request admission never grants arbitrary fetch authority.
- Natural-language planning cannot emit unrestricted SQL authority.
- Retrieval output is evidence, not deterministic truth.
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
- MCP capability execution is not business-result transport authority.
- MCP result projection is not public runtime exposure.
- AgentCore hosting is not business authorization.
- Runtime authentication is not capability authorization.
- Runtime execution role is not model/tool authority.
- Runtime telemetry is not business truth.
- Runtime deployment is not runtime-exposure truth.
- Provider/model selection and retry/fallback policy remain code-owned.
- Unsupported runtime exposure is not inferred from repository risk.
- IAM least privilege, observability, failure diagnosis, and cost accounting are architecture requirements.

## What the current agentic/runtime evidence does not prove

```text
generic business-result serialization
knowledge-guidance business-result transport
hybrid-security-answer business-result transport
public-repository-analysis business-result transport
persistent invocation/result registry
public MCP endpoint
production MCP network SLOs
AgentCore as the default/production OpsLens runtime
PUBLIC AgentCore networking as a production decision
production AgentCore SLOs or security posture
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
AgentCore retained state: optional disabled-by-default lab target; no standing experiment GitHub IAM
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
- [Gate 14.2 measured AgentCore experiment](labs/phase-14-gate-14-2-bounded-agentcore-runtime.md)
- [Gate 14.3 AgentCore retention decision](labs/phase-14-gate-14-3-agentcore-retention-decision.md)
- [Gate 14.4 standing-IAM cleanup](labs/phase-14-gate-14-4-agentcore-iam-cleanup.md)
- [ADR 0054 — retain AgentCore only as optional lab target](docs/adr/0054-retain-agentcore-only-as-optional-lab-target.md)
- [ADR 0055 — remove standing AgentCore experiment IAM](docs/adr/0055-remove-standing-agentcore-experiment-iam.md)
- [Gate 14.4 post-apply evidence](labs/evidence/phase-14-gate-14-4-agentcore-iam-cleanup-postapply-v1.json)

## Next — Phase 15 A2A

Phase 15 begins with capability fit, not implementation by default.

The first architectural question is:

> Which existing agent/service boundary has a concrete interoperability problem that justifies A2A, and what identity, message, provenance, replay, failure, observability, cost, and authority contracts must be frozen before any network transport exists?

Permanent Phase 15 constraints:

```text
A2A message != capability authorization
A2A peer identity != business authority
A2A transport success != business/evidence truth
A2A handoff proposal != handoff admission
A2A must not assume AgentCore hosting
A2A must not promote MCP into a public runtime as a side effect
```

The long-lived Governed LLM Gateway PR #89 remains deferred cross-project work and must be re-evaluated separately against the current OpsLens architecture before any merge.

---

OpsLens is intentionally built as an evidence system first and an agentic/interoperability system only where measured evidence justifies the added complexity.
