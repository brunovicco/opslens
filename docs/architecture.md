# OpsLens Architecture

_Last updated: 2026-09-06_

This document is the accumulated architecture baseline through **Phase 8 — Hybrid Retrieval: COMPLETE**.

The next product boundary is **Phase 9 — Public Analyze Your Repository**.

## 1. Purpose

OpsLens is an open-source software-supply-chain and threat-intelligence platform on AWS.

Product goal:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, which findings should I prioritize, and what verified guidance can help me act on them?

Core invariant:

> **Agents reason. Code verifies evidence.**

Permanent boundaries:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

## 2. Architectural principles

Unless changed by explicit ADR:

- raw third-party evidence is preserved before enrichment or interpretation;
- exact source versions, immutable snapshots, and hashes participate in provenance;
- package normalization, version/range evaluation, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV, EPSS, CVSS, and Risk Policy facts remain deterministic;
- natural-language planners produce bounded proposals, never query/execution authority;
- SemanticQuery validation and SQL compilation remain deterministic;
- canonical corpus construction and checked-manifest identity remain deterministic;
- route authorization, evidence admission, required-evidence completeness, context assembly, canonical citation identity, output admission, and evaluation metric computation remain deterministic;
- retrieved text remains untrusted instruction content after provenance admission;
- model output is a proposal over already-admitted evidence, never a new structured truth source;
- syntactically valid citation identity does not prove semantic support;
- structured and semantic evidence remain different authority classes;
- runtime exposure is not inferred from repository risk;
- schema, provenance, authority, completeness, or content-addressed identity mismatches fail closed;
- IAM follows least privilege and real runtime responsibility boundaries;
- AWS services are introduced only for concrete requirements, not certification coverage;
- cost and observability are architecture requirements;
- first-run evidence is preserved before optimization;
- a negative experiment is preserved rather than tuned until it passes.

## 3. Current system shape

### 3.1 Structured vulnerability and risk authority

```text
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
 -> source-preserving threat evidence
 -> deterministic PyPI identity / PEP 440 applicability
 -> immutable repository snapshot + inert uv.lock evidence
 -> deterministic vulnerability correlation
 -> RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> RiskPrioritizationResult
```

No LLM decides vulnerability applicability, KEV/EPSS/CVSS truth, risk score/tier, or runtime exposure.

### 3.2 Structured natural-language query path

```text
natural-language factual question
 -> bounded Bedrock planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured result evidence
```

The planner has no arbitrary SQL authority. ADRs 0020 and 0021 freeze this boundary.

### 3.3 Explanatory / remediation semantic path

```text
explicitly authorized official source pins
 -> deterministic canonical corpus
 -> deterministic S3 publication
 -> customer-managed Bedrock Knowledge Base ingestion
 -> Titan Text Embeddings V2 / 1024 / FLOAT32
 -> Amazon S3 Vectors / cosine
 -> direct bounded Retrieve
 -> checked-corpus provenance/hash admission
 -> bounded deterministic context assembly
 -> deterministic pre-model authority
 -> bounded non-streaming Bedrock Converse synthesis
 -> deterministic citation identity
 -> explicit support / groundedness evaluation
```

`RetrieveAndGenerate` remains deliberately unused so retrieval and synthesis stay separately measurable.

### 3.4 Hybrid evidence path

```text
EvidenceNeed[] proposal
 -> deterministic hybrid route authority
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> deterministic evidence-class acquisition/admission
 -> need-level ALL_REQUIRED completeness
 -> HybridEvidenceEnvelope
 -> deterministic F* structured-fact projection
 -> deterministic S* semantic-citation projection
 -> route-aware bounded synthesis
 -> deterministic output admission
 -> independent quality/runtime metrics
```

Hybrid Retrieval means hybrid **evidence routing and composition**. It does not imply keyword + vector search.

## 4. AWS foundation

```text
environment:             dev
primary workload Region: us-east-1
AWS account:             487757851499
IaC:                     Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

Primary storage:

```text
Data:       opslens-dev-data-487757851499-us-east-1
Artifacts:  opslens-dev-artifacts-487757851499-us-east-1
TF state:   opslens-dev-tfstate-487757851499-us-east-1
```

Analytics:

```text
Glue database:    opslens_dev
Athena workgroup: opslens-dev
scan cutoff:      10,485,760 bytes
```

Human administration uses temporary IAM Identity Center credentials. GitHub Actions uses OIDC; persistent AWS access keys are not stored in GitHub.

## 5. Deterministic structured authorities — Phases 2–6

### Threat Intelligence Data Lake

NVD, KEV, EPSS, and GHSA remain source-local evidence with explicit provenance and time semantics.

### Vulnerability Correlation

```text
package/version/purl
 + exact vulnerable-range evidence
 -> deterministic PEP 440 evaluation
 -> affected | not_affected | unsupported
 -> CVE/GHSA/NVD reconciliation
 -> content-addressed evidence
```

### Repository Intelligence

```text
public repository
 -> immutable repository/commit/tree identity
 -> bounded GitHub read-only acquisition
 -> inert uv.lock bytes
 -> deterministic TOML parsing
 -> canonical dependencies
 -> deterministic applicability
 -> RepositoryAnalysisResult
```

Repository findings do not prove runtime presence or exploitability.

### Risk Prioritization

```text
RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> factor contributions
 -> priority score + tier
 -> completeness / review_required
```

The priority value is an OpsLens policy score, not exploit probability, CVSS, EPSS, or runtime exposure.

### Semantic Query

```text
question
 -> bounded Bedrock planner
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded Athena execution
```

No unrestricted text-to-SQL is allowed.

## 6. Phase 7 controlled Knowledge Retrieval

Frozen corpus:

```text
manifest id: knowledge-corpus-manifest:v1
documents:   6
chunks:      9
sha256:      98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Knowledge Base baseline:

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
chunking:              NONE
embedding model:       amazon.titan-embed-text-v2:0
embedding dimensions:  1024
embedding data type:   FLOAT32
vector store:          Amazon S3 Vectors
distance:              cosine
canonical vectors:     9
```

Direct retrieval admission verifies expected source location, canonical manifest identity, text hash/byte count, metadata, and deterministic rank before a `RetrievedChunk` exists.

Frozen retrieval baseline:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Both negative cases still returned vector neighbors, proving:

```text
non-empty retrieval != sufficient evidence != authority to answer
```

## 7. Phase 7 bounded synthesis and citation authority

Synthesis profile:

```text
Region:              us-east-1
API:                 bedrock-runtime / Converse
model/profile:       us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:           no
temperature:         0.0
provider maxTokens:  2048
tools:               none
```

Prompt trust classes stay separated:

```text
trusted system instructions
untrusted user question
untrusted but source-verified retrieved evidence
```

Citation IDs are projected only from admitted evidence. The model may select them; it may not author canonical source identity.

Frozen Gate 7.7 baseline:

```text
decision accuracy:                 1.0
citation target precision:         0.2857142857142857
citation target recall:            0.5
claim supportedness rate:          0.8461538461538461
unsupported claim rate:            0.15384615384615385
citation correctness rate:         0.8461538461538461
abstention precision:              1.0
abstention recall:                 1.0
```

The preserved isolation failure demonstrates:

```text
retrieval success != citation attribution success != semantic groundedness
```

## 8. Phase 8 deterministic hybrid routing

ADR 0025 freezes `hybrid-routing:v1`.

Recognized needs:

```text
vulnerability_facts
risk_priority
remediation_guidance
runtime_exposure
```

Policy:

```text
vulnerability_facts and/or risk_priority -> STRUCTURED
remediation_guidance                      -> SEMANTIC
structured + remediation                 -> HYBRID
runtime_exposure, alone or mixed         -> UNSUPPORTED
```

Intent/evidence-need classification may be a proposal. The route decision is deterministic authority.

Supported routes require `ALL_REQUIRED` evidence. Runtime exposure is valid-but-unavailable rather than mapped to repository risk.

## 9. Phase 8 deterministic hybrid evidence

ADR 0026 freezes `hybrid-evidence:v1`.

The envelope retains separate collections:

```text
structured_evidence[]
semantic_evidence[]
authority_decision
provenance_by_class
satisfied_needs
completeness
content-addressed identity
```

No generic `Evidence[]` erases authority class.

Structured evidence may satisfy only supported structured needs. Semantic evidence may satisfy only remediation guidance. Extra/unrequested evidence, duplicates, malformed ranks, or incomplete required classes are rejected.

Semantic rank/score are provenance and measurement data, never truth.

## 10. Phase 8 frozen evaluation contract

ADR 0027 freezes:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Case types:

```text
structured_only_factual
semantic_only_remediation
true_hybrid
unsupported_out_of_authority
partial_structured_evidence
semantic_retrieval_noise
```

Metric dimensions:

```text
route_accuracy
structured_fact_correctness
semantic_groundedness
citation_correctness
abstention
latency
cost
```

No composite score is allowed.

The semantic-noise case intentionally places a non-supporting admitted chunk at rank 1 and the expected support target at rank 2.

## 11. Phase 8 route-aware bounded synthesis

ADR 0028 freezes `hybrid-synthesis:v1`.

```text
STRUCTURED
 -> deterministic F1/F2/... facts
 -> 0 model calls

SEMANTIC
 -> admitted S1/S2/... evidence
 -> <=1 model call

HYBRID
 -> deterministic facts + admitted semantic evidence
 -> <=1 model call

UNSUPPORTED
 -> explicit abstention
 -> 0 model calls

incomplete evidence
 -> reject_before_synthesis
 -> 0 model calls
```

Structured facts remain code-owned. The model cannot alter them or promote authored values into canonical facts.

Every model explanatory claim must reference at least one admitted S citation ID. Optional F IDs provide structured context only. Unknown IDs fail closed.

The runtime adapter preserves bounded failure categories for provider invocation, response contract, stop reason, output contract, and clock anomalies.

## 12. Gate 8.4 real hybrid baseline

Immutable evidence:

```text
labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json
```

Measured execution:

```text
complete:                            true
planned_case_count:                  6
synthesis_invocation_attempt_count:  3
admitted_model_execution_count:      3
route_accuracy:                      1.0
structured_fact_correctness:         1.0
semantic_groundedness:               0.6666666666666666
citation_correctness:                0.6666666666666666
abstention:                          1.0
latency_ms:                          2959.3333333333335
cost:                                UNMEASURED / null
```

Token totals:

```text
input:   4150
output:   289
total:   4439
```

The semantic-noise case emitted the correct rank-two S2 claim and an ancillary rank-one S1 claim. Output admission accepted both because both IDs were admitted; independent evaluation correctly reduced question-specific groundedness/citation correctness.

## 13. Gate 8.5 measured optimization governance

H8.5-01 was a single predeclared prompt-only candidate:

```text
experiment: hybrid-optimization:h8.5-01-v1
candidate:  hybrid-synthesis-prompt:h8.5-01-v1
```

It changed only trusted synthesis instructions about minimal sufficient answers and direct question relevance.

All upstream/downstream authority contracts, fixture targets, semantic evidence, model profile, Region, inference settings, output schema, and call budget remained unchanged.

Real-run evidence:

```text
labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json
```

Result:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2997.0
cost:                         UNMEASURED / null
```

The exact semantic-noise weakness persisted. Decision:

```text
H8.5-01 = REJECT
```

The candidate also increased input tokens by 306 and total tokens by 280 while reducing output tokens by 26.

The default therefore remains:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

No second run or post-result mutation of H8.5-01 is authorized. A materially different intervention requires a new hypothesis and predeclared acceptance rule.

## 14. Failure taxonomy

Current diagnosis is stage-oriented:

```text
routing / authority failure
structured evidence failure
semantic provider retrieval failure
semantic evidence-admission failure
hybrid completeness failure
structured fact projection failure
semantic relevance / selection failure
synthesis provider invocation failure
synthesis response-contract failure
synthesis stop-reason failure
synthesis output-admission failure
citation-attribution failure
semantic groundedness failure
optimization-decision failure
```

Provider success must not hide semantic failure, and a retrieval/citation issue must not be mislabeled as a structured-authority failure.

## 15. Runtime IAM boundary

No deployed public application compute principal exists at Phase 8 closeout.

Therefore Phase 8 creates no speculative runtime role.

For the already-proven semantic path, ADR 0024 records the future least-privilege shape:

```text
bedrock:Retrieve
 -> exact Knowledge Base BTVJ2PBR2A

bedrock:InvokeModel
 -> exact approved inference profile and required foundation-model resources
```

Hybrid route/evidence/projection logic itself requires no broader Bedrock entitlement.

The structured path retains bounded read-only Athena authority. Runtime-exposure IAM is deferred because runtime exposure remains unsupported.

The policy must be revalidated against current AWS documentation immediately before real Phase 9 deployment.

## 16. Cost-accounting boundary

Cost drivers remain separate:

```text
structured Athena execution / bytes scanned
query-time embeddings
S3 Vectors request / processed / returned units
model input tokens
model output tokens
```

Gate 8.4 and Gate 8.5 correctly report `cost = UNMEASURED / null`. Token evidence is not a complete AWS bill.

Any future USD estimate must use an explicit versioned pricing contract or bill-level reconciliation rather than silently mixing stale rates with runtime data.

## 17. Observability boundary

Current hybrid lab/runtime evidence captures:

```text
route and case identity
expected/observed behavior
synthesis invocation attempt
bounded failure category/diagnostic
provider request ID
model/profile and Region
token/cache counts
Bedrock latency and client elapsed time
SDK retries
stop reason
request/prompt/envelope/catalog/result hashes
structured F projections
semantic S citation/chunk mappings
independent quality metrics
optimization decision/rejection reasons
```

Phase 8 does not claim:

```text
production SLOs
continuous deployed hybrid metrics
public-user distributed traces
production alert thresholds
high-volume percentiles/error rates
complete request-level AWS bill attribution
```

Those require a deployed public runtime and measured workload.

Automatic model-invocation content logging remains inappropriate because prompts contain user/source text; content-free metadata and hashes are preferred.

## 18. Phase 9 entry boundary

Public Analyze Your Repository may begin only with these invariants frozen:

```text
1. public repository acquisition stays bounded GET-only; repository code is never executed
2. immutable repository snapshot identity precedes dependency analysis
3. vulnerability applicability and risk remain deterministic structured truth
4. hybrid route authority remains deterministic
5. supported routes require ALL_REQUIRED evidence
6. runtime exposure remains explicit UNSUPPORTED until a separate runtime authority exists
7. model synthesis receives only admitted evidence and cannot author canonical provenance/structured truth
8. structured-only, unsupported, and incomplete cases preserve zero-model-call behavior
9. hybrid-synthesis-prompt:v1 remains the runtime default; H8.5-01 stays rejected evidence
10. public inputs, request size, provider calls, output size, timeout, concurrency, and cost budgets are bounded
11. provider/evidence/output/citation failures remain fail closed
12. telemetry avoids automatic user/source prompt-content logging
13. abuse/rate/cost controls exist before public launch
14. production SLOs/alerts are based on deployed workload, not lab samples
15. a runtime IAM identity is created only when the Phase 9 compute boundary is concrete
16. new prompt/retrieval/reranking/vector changes require new versioned hypotheses
```

Phase 9 should expose the already-governed evidence system rather than introducing agentic complexity by default.

## 19. Deferred decisions

Not adopted merely because Phase 8 is complete:

```text
reranking
keyword + vector hybrid search
OpenSearch Serverless
alternative embeddings/vector store
runtime cache
similarity thresholds
new synthesis policy
agents
MCP
AgentCore
A2A
runtime exposure / Inspector integration
```

These remain future phases or separately measured hypotheses.

The long-lived Governed LLM Gateway PR #89 remains deferred for the later Phase 14 Case 3 integration and is not part of Phase 8.

## 20. Architecture records

Key current ADRs:

```text
0020 no unrestricted text-to-SQL
0021 bounded Bedrock Semantic Query planner
0022 customer-managed Bedrock Knowledge Base with S3 Vectors
0023 bounded Bedrock knowledge synthesis
0024 future Phase 7/runtime IAM boundary
0025 deterministic hybrid routing authority
0026 deterministic hybrid evidence envelope
0027 frozen hybrid evaluation contract
0028 bounded route-aware hybrid synthesis
```

Historical implementation details and exact runtime evidence remain in `labs/` and `labs/evidence/` rather than being rewritten into the current architecture baseline.
