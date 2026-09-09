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
| Phase 14 | Amazon Bedrock AgentCore | 🚧 In progress — Gates 14.1 and 14.2 complete; retention decision pending |
| Phase 15 | A2A | ⏳ Planned |
| Phase 16 | Runtime Exposure with Amazon Inspector | ⏳ Planned |
| Phase 17 | Security Hardening | ⏳ Planned |
| Phase 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), the [Phase 13 MCP closeout](labs/phase-13-gate-13-5-mcp-closeout.md), and the [Gate 14.2 measured AgentCore experiment](labs/phase-14-gate-14-2-bounded-agentcore-runtime.md).

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

### 11. Bounded MCP interoperability and result disclosure

Phase 13 freezes three protocol-facing contracts:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
mcp-result-projection:v1
```

Closed one-to-one MCP tool surface:

```text
opslens.structured_security_query   -> structured_security_query
opslens.knowledge_guidance          -> knowledge_guidance
opslens.hybrid_security_answer      -> hybrid_security_answer
opslens.public_repository_analysis  -> public_repository_analysis
```

Retained Phase 13 path:

```text
existing typed Phase 11 capability authority
 -> closed MCP tool identity
 -> official MCP SDK reference-only adapter
 -> raw exact-key-set argument refusal
 -> deterministic invocation resolution + admission
 -> exactly one existing typed executor attempt
 -> content-addressed MCP execution bridge
 -> explicit mcp-result-projection:v1 for structured_security_query only
 -> bounded CVE + EPSS rows
 -> STOP before public/network runtime
```

The protocol input remains only `invocation_id` and `invocation_sha256`. MCP cannot author `SemanticQuery`, SQL, URLs, shell commands, credentials, provider/model selection, retry/fallback policy, or arbitrary executable `args`/`kwargs`.

The official MCP Python SDK is pinned as `mcp==2.2.0` in development dependencies only. Real interoperability testing showed that generated SDK/Pydantic argument coercion may ignore unexpected fields, so OpsLens validates the raw request key set before framework coercion. A separate dependency-placement experiment showed that moving MCP into runtime dependencies enlarged unrelated Lambda packages and tripped an existing package-size gate; deployment limits were not weakened.

Business-result disclosure is deliberately narrower than capability execution. Phase 13 transports business content only for `structured_security_query`, through an explicit projector that maps the already-admitted internal `("cve", "epss")` shape to bounded `cve` + `epss_score` rows. Knowledge, hybrid, and public-repository business-result transport remain unsupported.

Phase 13 closes at this bounded offline/in-process boundary. It does not create a public MCP runtime merely for completeness.

### 12. Measured bounded AgentCore Runtime experiment

Phase 14 Gate 14.1 authorized one bounded runtime experiment only. Gate 14.2 then hosted the retained Phase 11 reasoning boundary without adding capability execution authority:

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

Observed experiment cost after delayed AgentCore Runtime telemetry:

```text
AgentCore Runtime:  USD 0.002380345136128484
Bedrock inference:  USD 0.004192100000000000
TOTAL:              USD 0.006572445136128483
```

Attempts #1–#10 are preserved as measured remediation evidence for source-layout execution and AgentCore IAM/lifecycle dependencies. The successful run does not rewrite those failures away.

Gate 14.2 does **not** approve AgentCore or `PUBLIC` networking for production, establish a production SLO, create runtime-exposure truth, or authorize capability execution. The next retention decision remains intentionally open.

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

## Phase 13 closeout evidence

```text
issue:                  #192
PR:                     #193
final head:             99dd3d979a5205e38f2c1a4dfc84dc9f82d0e0c7
PR merge test commit:   7ec68aa12bc0a08b698ed0ddf76434e7bd97fe85
MCP CI:                 34250265151 / run #52 / PASS
job:                    102142600531
uv lock --check:        PASS
MCP SDK pin:            PASS
MCP import smoke:       PASS
Ruff:                   PASS
Pyright strict:         0 errors / 0 warnings / 0 informations
pytest MCP slice:       29 passed in 0.90s
review threads:         0
PR comments:            0
model invocations:      0
new AWS/IAM:            0
public MCP endpoint:    0
MCP deployed runtime:   0
merge SHA:              c449cfc8e18dfd240ceedbe6e8e4d143601f0254
```

Closeout artifacts:

```text
labs/evidence/phase-13-closeout-v1.json
labs/phase-13-gate-13-5-mcp-closeout.md
docs/adr/0051-phase13-mcp-closeout.md
```

## Gate 14.2 measured evidence

```text
workflow artifact: 10115123076
workflow digest:   sha256:7006a7c2bfda1658a9e66fcfe38f61b06dc64e6f54705ffbf6b02574870ef65c
repository evidence:
  labs/evidence/phase-14-gate-14-2-final-runtime-experiment-v1.json
lab:
  labs/phase-14-gate-14-2-bounded-agentcore-runtime.md
ADR:
  docs/adr/0053-bounded-agentcore-direct-code-public-network-experiment.md
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
- MCP capability execution is not business-result transport authority.
- MCP result admission is not protocol result-projection authority.
- MCP result projection is not public runtime exposure.
- MCP transport success is not business/evidence truth.
- AgentCore hosting is not business authorization.
- Runtime authentication is not capability authorization.
- Runtime execution role is not model/tool authority.
- Runtime telemetry is not business truth.
- Runtime deployment is not runtime-exposure truth.
- Raw model/provider/downstream output is not canonical authority merely because a protocol transported it.
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
MCP transport authentication or authorization
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
AgentCore Gate 14.2:     measured temporary HTTP/SigV4 runtime; cleaned up after run
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
- [Phase 13 MCP closeout](labs/phase-13-gate-13-5-mcp-closeout.md)
- [Gate 14.2 measured AgentCore experiment](labs/phase-14-gate-14-2-bounded-agentcore-runtime.md)
- [ADR 0053 — bounded AgentCore direct-code PUBLIC experiment](docs/adr/0053-bounded-agentcore-direct-code-public-network-experiment.md)

## Next — evidence-based AgentCore retention decision

Gate 14.2 is complete. The roadmap deliberately does not invent the next gate number until a concrete decision scope is formalized.

The next architectural question is:

> Does the measured AgentCore hosting/session/operational value justify its IAM, lifecycle, network, latency, cost, and operational surface for the retained OpsLens reasoning architecture?

The answer is not preselected. Retaining, changing, or rejecting AgentCore Runtime as the default all remain valid evidence-driven outcomes.

The long-lived Governed LLM Gateway PR #89 remains deferred cross-project work and must be re-evaluated separately against the current OpsLens architecture before any merge.

---

OpsLens is intentionally built as an evidence system first and an agentic/interoperability system only where measured evidence justifies the added complexity.
