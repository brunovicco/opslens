# OpsLens Architecture

_Last updated: 2026-09-07_

This document is the accumulated architecture baseline through **Phase 9 — Public Analyze Your Repository: COMPLETE after Gate 9.4 merge**.

The next phase is **Phase 10 — Observability & Operational Excellence**.

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
- public request admission, public product scope, repository snapshot/file binding, semantic-plan admission, and public handoff admission remain deterministic;
- retrieved text remains untrusted instruction content after provenance admission;
- model output is a proposal over already-admitted evidence, never a new structured truth source;
- syntactically valid citation identity does not prove semantic support;
- structured and semantic evidence remain different authority classes;
- runtime exposure is not inferred from repository risk;
- schema, provenance, authority, completeness, request/source binding, or content-addressed identity mismatches fail closed;
- IAM follows least privilege and real runtime responsibility boundaries;
- AWS services are introduced only for concrete requirements, not certification coverage;
- cost and observability are architecture requirements;
- first-run evidence is preserved before optimization;
- a negative experiment is preserved rather than tuned until it passes;
- a validated application contract is not represented as a deployed production runtime.

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

### 3.5 Public analysis application boundary

```text
untrusted public JSON
 -> strict <=2048-byte request admission
 -> validated GitHub owner/name/ref coordinates
 -> source-confirmed public repository metadata
 -> immutable commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic uv.lock parser
 -> deterministic Phase 3 PyPI normalization
 -> PublicRepositoryEvidenceExecution
 -> <=2048-byte metadata-only semantic planning request
 -> <=1024-byte untrusted semantic-plan proposal
 -> deterministic exact public-v1 evidence-scope admission
 -> existing Phase 8 hybrid route authority
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

The public v1 operation is fixed to:

```text
analyze_public_repository
```

Deterministic public policy requires exactly:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

The planner cannot redefine that scope. Successful public handoff additionally requires the existing Phase 8 route authority to return:

```text
HYBRID
ALL_REQUIRED
STRUCTURED + SEMANTIC
```

The planner receives no raw repository URL, lockfile bytes, dependency names/versions, arbitrary repository text/instructions, SQL, credentials, provider/model/tool selection, or executable repository content.

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

Knowledge retrieval baseline:

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
embedding model:       amazon.titan-embed-text-v2:0
embedding dimensions:  1024
embedding data type:   FLOAT32
vector store:          Amazon S3 Vectors
distance:              cosine
chunking:              NONE
canonical chunks:      9
synthesis profile:     us.anthropic.claude-haiku-4-5-20251001-v1:0
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

Preserved distinction:

```text
retrieval success != citation attribution success != semantic groundedness
```

## 7. Phase 8 hybrid authority

ADR 0025 freezes `hybrid-routing:v1`:

```text
vulnerability_facts and/or risk_priority -> STRUCTURED
remediation_guidance                      -> SEMANTIC
structured + remediation                 -> HYBRID
runtime_exposure, alone or mixed         -> UNSUPPORTED
```

Supported routes require `ALL_REQUIRED` evidence. Intent/evidence-need classification may be a proposal; route authority is deterministic.

ADR 0026 freezes `hybrid-evidence:v1`. Structured and semantic evidence remain separate collections, and semantic rank/score remain metadata rather than truth.

ADR 0027 freezes:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
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

No composite score is allowed.

ADR 0028 freezes `hybrid-synthesis:v1`:

```text
STRUCTURED  -> deterministic F* facts / 0 model calls
SEMANTIC    -> admitted S* evidence / <=1 model call
HYBRID      -> F* + S* evidence / <=1 model call
UNSUPPORTED -> explicit abstention / 0 model calls
incomplete  -> reject_before_synthesis / 0 model calls
```

Every model explanatory claim must reference admitted semantic evidence. Unknown IDs fail closed.

## 8. Phase 8 measured baseline and optimization governance

Gate 8.4 real baseline:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

The semantic-noise case preserved the distinction:

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct question-specific citation target
```

H8.5-01 tested one predeclared prompt-only candidate exactly once. It did not improve semantic groundedness or citation correctness and increased total tokens by 280.

Decision:

```text
H8.5-01 = REJECT
```

Runtime default remains:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

## 9. Phase 9 public request admission

ADR 0029 freezes `public-analysis-request:v1`.

```text
untrusted request bytes
 -> strict UTF-8 / JSON / duplicate-key / known-field admission
 -> exact HTTPS github.com repository-root URL grammar
 -> owner/name/ref validators
 -> content-addressed PublicAnalysisRequest
```

The raw user URL never becomes fetch authority.

Preserved distinction:

```text
public request admitted
 != repository proven public
 != repository snapshot resolved
 != repository analyzed
```

## 10. Phase 9 immutable repository evidence

Gate 9.2 freezes `public-repository-evidence:v1`:

```text
PublicAnalysisRequest
 -> source-confirmed public repository metadata
 -> exact commit/tree snapshot
 -> exact-commit inert uv.lock evidence
 -> deterministic parser
 -> deterministic Phase 3 PyPI normalization
 -> PublicRepositoryEvidenceExecution
```

Source-confirmed canonical coordinates own reads after the initial lookup. Null refs use the source-declared default branch; explicit refs are resolved to immutable commit/tree identity before file acquisition.

Request/snapshot/file/parser/normalization drift fails closed. Third-party repository code is never executed.

## 11. Phase 9 semantic planning and handoff

ADR 0030 freezes:

```text
public-semantic-planning:v1
public-analysis-handoff:v1
```

Semantic planning is proposal-only. The fixed public v1 operation means deterministic code owns required evidence scope.

Planner request bound:

```text
<= 2048 UTF-8 bytes
```

Planner response bound:

```text
<= 1024 bytes
```

Application planner budget:

```text
<= 1 invocation per orchestration
0 adaptive application retries
```

Fail-closed admission rejects malformed output, unknown/duplicate needs, omitted mandatory needs, `runtime_exposure`, request-hash replay, source-execution rebinding, and disagreement with Phase 8 route/completeness/class authority.

Gate 9.3 exact-head evidence:

```text
PR #129 head:                    34cea42a0ce37cbfa06b33d57f081403edba2552
Python CI #358 / run 34082791753: PASS
Public Analysis Pyright strict:  0 errors / 0 warnings / 0 informations
Public Analysis pytest:          57 passed
merge SHA:                       6f53537c227cade688091187eac1074645e11bf0
```

Gate 9.3 used fake repository/planner ports and made zero real provider/model calls.

## 12. Phase 9 failure taxonomy

Current public-analysis diagnosis is stage-oriented:

```text
request byte/UTF-8/JSON admission failure
request duplicate/unknown-field failure
repository URL grammar failure
repository metadata/visibility failure
ref/default-branch resolution failure
immutable commit/tree resolution failure
exact-commit file evidence failure
file/parser/normalization provenance mismatch
semantic planning request binding failure
planner invocation failure
planner response size/UTF-8/JSON/schema failure
unknown/duplicate/out-of-authority evidence need
under-scoped public-v1 proposal
runtime_exposure proposal
proposal replay/request-hash mismatch
source-execution rebinding
Phase 8 route/completeness/class mismatch
handoff identity mismatch
```

A failed stage produces no later authority object.

## 13. Phase 9 runtime / IAM boundary

ADR 0031 closes Phase 9 at the governed application boundary.

At closeout:

```text
public HTTP compute:      NOT DEPLOYED
public endpoint:          NOT DEPLOYED
public runtime principal: DOES NOT EXIST
new Phase 9.4 IAM:        NONE
new Phase 9.4 AWS:        NONE
```

This is intentional least privilege:

```text
no concrete compute principal
 -> no runtime role
 -> no speculative permissions
```

Previously proven service permissions remain separate responsibilities and must not be automatically aggregated into a broad public role.

## 14. Cost-accounting boundary

Cost drivers remain separate:

```text
structured Athena execution / bytes scanned
query-time embeddings
S3 Vectors request / processed / returned units
model input tokens
model output tokens
future public runtime infrastructure
```

Gate 8.4 and Gate 8.5 correctly report `cost = UNMEASURED / null` for hybrid USD cost. Gate 9.3 used fake ports and zero real provider/model calls, so Phase 9 closeout adds no synthetic public-request price.

Any future USD estimate must use an explicit versioned pricing contract or bill-level reconciliation and include infrastructure, concurrency, abuse, and retry assumptions.

## 15. Observability boundary

Current evidence includes:

```text
request/snapshot/file/parser/normalization IDs and hashes
route/admission decisions
planning request/proposal/handoff identities
bounded failure categories
provider request/token/latency evidence where real provider stages were run
exact-head CI evidence
```

OpsLens still does not claim:

```text
public-user distributed traces
production request volume
production p95/p99 latency
production error/throttle rates
production request-level AWS cost
production SLO/alert compliance
```

Those require a deployed runtime and measured workload.

Automatic logging of user/source/model content remains inappropriate by default; content-free metadata and hashes are preferred.

## 16. Public-launch prerequisites

Before a real public launch, a concrete design and measured validation are still required for:

```text
public HTTP compute / endpoint
runtime identity and least-privilege IAM
request timeout budget
concurrency limits
rate limiting
abuse controls
quota enforcement
cache policy if justified
kill switch / disable path
cost guardrails and attribution
request-level telemetry
production error/latency distributions
workload-derived SLOs and alerts
rollback / incident procedures
```

Phase 9 completion does not waive these requirements.

## 17. Phase 10 entry boundary

Phase 10 may begin only with these invariants frozen:

```text
1. Phase 9 contracts remain versioned boundaries
2. public input never becomes arbitrary fetch, SQL, tool, provider/model, or execution authority
3. third-party repository code is never executed
4. repository risk remains distinct from runtime exposure
5. Phase 8 remains hybrid route/evidence authority
6. semantic planning remains proposal-only and content-minimized
7. failure at any admission stage prevents downstream execution
8. IAM is introduced only for a concrete runtime identity
9. production SLO/alert claims require deployed workload evidence
10. observability must not weaken privacy/provenance/content-minimization boundaries
11. new runtime/provider/retrieval changes require separately versioned hypotheses and exact-head validation
12. Governed LLM Gateway PR #89 remains deferred until separately re-evaluated
```

If Phase 10 needs a small deployed runtime slice to produce real telemetry, that runtime must be explicit about compute, IAM, request limits, abuse controls, rollback, and cost evidence.

## 18. Deferred decisions

Not adopted merely because Phase 9 is complete:

```text
public compute runtime
runtime cache
reranking
keyword + vector hybrid search
OpenSearch Serverless
alternative embeddings/vector store
new synthesis policy
agents
MCP
AgentCore
A2A
runtime exposure / Inspector integration
Governed LLM Gateway merge
```

These remain later phases or separately measured hypotheses.

## 19. Architecture records

Key current ADRs:

```text
0020 no unrestricted text-to-SQL
0021 bounded Bedrock Semantic Query planner
0022 customer-managed Bedrock Knowledge Base with S3 Vectors
0023 bounded Bedrock knowledge synthesis
0024 future semantic/runtime IAM boundary
0025 deterministic hybrid routing authority
0026 deterministic hybrid evidence envelope
0027 frozen hybrid evaluation contract
0028 bounded route-aware hybrid synthesis
0029 public repository request admission
0030 public semantic planning proposal authority
0031 Phase 9 public analysis closeout boundary
```

Historical implementation details and exact runtime evidence remain in `labs/` and `labs/evidence/` rather than being rewritten into the current architecture baseline.
