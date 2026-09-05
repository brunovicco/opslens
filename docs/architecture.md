# OpsLens Architecture

_Last updated: 2026-09-05_

This document is the accumulated architecture baseline through **Phase 7 — Gate 7.2: Reproducible Canonical Corpus**.

The next roadmap boundary is **Phase 7 — Gate 7.3: Knowledge Base + vector infrastructure**.

## 1. Purpose

OpsLens is an open-source software supply chain and threat-intelligence platform on AWS.

The product goal is:

> Given the software I actually use, which vulnerabilities affect it, what exact evidence proves that, and which findings should I prioritize?

The architecture deliberately establishes trustworthy deterministic evidence and policy enforcement before adding semantic, generative, retrieval, or agentic reasoning.

Core invariant:

> **Agents reason. Code verifies evidence.**

Additional permanent boundaries:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

## 2. Permanent architectural principles

Unless changed by an explicit ADR:

- raw third-party evidence is preserved before enrichment or interpretation;
- deterministic facts remain authoritative;
- exact source versions and content hashes participate in provenance;
- package identity normalization remains deterministic;
- version parsing and vulnerable-range matching remain deterministic;
- vulnerability applicability remains deterministic;
- CVE/GHSA/NVD reconciliation remains deterministic;
- KEV/EPSS/CVSS evidence remains deterministic and source-preserving;
- risk policy evaluation remains deterministic;
- semantic-query validation and SQL compilation remain deterministic;
- canonical corpus normalization, selection, and hashing remain deterministic;
- retrieval evidence validation and context admission remain deterministic;
- citation projection remains deterministic from admitted evidence;
- execution/tool/cost enforcement remains deterministic;
- LLMs may classify, plan, route, synthesize, and explain over validated evidence;
- LLMs do not replace package applicability, structured source evidence, or risk-policy enforcement;
- natural-language planning never receives unrestricted SQL authority;
- retrieved explanatory text never becomes a second authority for structured threat facts;
- third-party repository/source content is untrusted data to inspect, never code to execute;
- Repository Risk is not Runtime Exposure;
- missing evidence is not silently converted into benign evidence;
- duplicate delivery is expected and replay must be safe;
- schema, provenance, authority, or exact-evidence mismatches fail closed;
- IAM uses least privilege and responsibility separation;
- AWS services are introduced only for concrete requirements;
- cost and observability are architectural requirements;
- one real `dev` environment is preferred over fictional portfolio environments.

## 3. Current system shape

The implemented system now separates structured deterministic truth, bounded model planning, and canonical explanatory knowledge.

```text
THREAT INTELLIGENCE DATA
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
        |
        v
DETERMINISTIC CORRELATION
PyPI identity + PEP 440 + GHSA applicability + CVE/NVD evidence
        |
        v
REPOSITORY INTELLIGENCE
immutable public GitHub snapshot + inert uv.lock + deterministic findings
        |
        v
RepositoryAnalysisResult
        |
        v
RISK PRIORITIZATION
versioned Risk Policy v1 + factor evidence + deterministic ranking
        |
        v
RiskPrioritizationResult
```

The implemented Phase 6 semantic path is separate and bounded:

```text
natural-language factual question
 -> bounded Bedrock planner
 -> structured proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic validation + SQL compiler
 -> bounded read-only Athena
 -> structured result evidence
```

The planner has no arbitrary SQL authority.

The implemented Phase 7 knowledge foundation is also separate:

```text
explicitly authorized official sources
 -> immutable repository/commit/path pins
 -> bounded GET-only inert-text acquisition
 -> deterministic UTF-8/newline normalization
 -> exact line-aligned section selection
 -> content-addressed KnowledgeDocument + canonical chunks
 -> deterministic hash-only manifest
```

No vector infrastructure or live semantic retrieval exists yet. Gate 7.3 will decide that infrastructure only after current AWS architecture research.

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

Only one real environment exists: `dev`.

Human administration uses temporary IAM Identity Center credentials. GitHub Actions assumes AWS roles through OIDC; persistent AWS access keys are not stored in GitHub.

Terraform layout:

```text
infra/
  bootstrap/
  environments/
    dev/
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

Phase 3, Phase 4, Phase 5, Gate 7.1, and Gate 7.2 introduced no additional AWS resources or IAM permissions. Gate 7.2 introduced no AWS calls at all.

## 5. Threat Intelligence Data Lake — Phase 2

Phase 2 preserves source-local authority. NVD, KEV, EPSS, and GHSA are not flattened into one lossy universal vulnerability record.

### 5.1 FIRST EPSS

```text
FIRST EPSS
 -> EventBridge Scheduler
 -> EPSS ingestion Lambda
 -> immutable S3 Bronze
 -> deterministic Silver transformer
 -> Parquet
 -> Glue: opslens_dev.epss_scores
 -> Athena
```

Temporal selection is explicit through snapshot date.

The canonical Silver relation includes both the forward path and the completed historical interval:

```text
2021-04-14 .. 2026-08-13
```

The historical path is pinned to a specific archive commit and preserves exact source evidence. Missing historical source dates remain explicit rather than fabricated.

### 5.2 CISA KEV

```text
CISA KEV JSON
 -> bounded ingestion
 -> immutable Bronze
 -> exact-version source verification
 -> deterministic Silver normalization
 -> Parquet
 -> Glue: opslens_dev.kev_entries
 -> Athena
```

KEV absence is meaningful only against one complete validated catalog snapshot.

### 5.3 NVD / CVE

```text
NVD yearly feeds                  NVD CVE API 2.0
       |                                  |
       v                                  v
Bootstrap Bronze                  Incremental Bronze
       |                                  |
       +----------> versioned Silver <----+
                          |
                          v
                    Silver COMPLETE
                          |
                          v
                authoritative watermark
                          |
                          v
               permanent analytics projection
                          |
                          v
                 Glue + bounded Athena
```

Authority invariant:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

The analytics projector is downstream-only and cannot advance authoritative NVD state.

### 5.4 GitHub Security Advisories

```text
GitHub Global Security Advisories REST API
 -> reviewed-only Bronze pages + COMPLETE
 -> exact advisory content identity
 -> deterministic normalization
 -> immutable advisory-version Silver
 -> Silver COMPLETE
 -> Glue: opslens_dev.ghsa_advisory_versions
 -> Athena
```

Important identities remain distinct:

```text
sync_id                       logical source window
attempt_id                    exact physical source observation
observed_advisory_version_id  exact advisory content identity
vulnerability_entry_id        exact advisory vulnerability occurrence
```

GHSA package/range/fix evidence remains source-local even when a CVE alias is independently observed by NVD.

## 6. Vulnerability Correlation Engine — Phase 3

Phase 3 is complete for the supported **PyPI v1** scope.

### 6.1 Identity authority

```text
source ecosystem alias
 -> canonical ecosystem: pypi
package name
 -> PyPA normalization
version
 -> PEP 440 Version
package + version
 -> canonical pkg:pypi/... purl
```

Original source spelling and canonical identity are both preserved.

### 6.2 Vulnerable-range authority

Supported GHSA operators:

```text
=  <  <=  >  >=
```

Comma-separated clauses are deterministic conjunctions.

Result states:

```text
affected
not_affected
unsupported
```

Unsupported or malformed semantics never collapse to `not_affected`.

`first_patched_version` is remediation evidence only; it does not override the published vulnerable range.

### 6.3 GHSA/NVD reconciliation

GitHub's CVE assertion and NVD's exact observed CVE version remain independent source records.

Reconciliation states include:

```text
no_github_cve
github_asserted_only
nvd_observed
nvd_rejected
```

A matching NVD record creates an evidence edge; it does not replace GHSA provenance.

### 6.4 Correlation identity

Canonical correlation records use:

```text
correlation:v1@sha256:<digest>
```

Permanent rule:

> **No LLM decides vulnerability applicability.**

## 7. Repository Intelligence — Phase 4

Phase 4 analyzes a supported public GitHub repository without executing its code.

Current v1 scope:

```text
provider:             public GitHub repositories
repository evidence:  root-level uv.lock
supported packages:   canonical PyPI source records
network operation:    bounded read-only GitHub REST
code execution:       never
```

### 7.1 Immutable repository authority

Repository authority uses GitHub's numeric repository ID and an exact commit SHA.

```text
owner/name/ref
 -> canonical GitHub metadata
 -> exact commit SHA
 -> exact tree SHA
 -> immutable snapshot
```

Moving refs become provenance only after resolution.

### 7.2 Bounded GitHub transport

The acquisition boundary is intentionally narrow:

- HTTPS to the fixed GitHub API host;
- GET only;
- bounded request timeouts;
- bounded response bytes;
- no redirect following;
- no automatic retry loop;
- explicit rate-limit failures;
- no arbitrary caller-controlled absolute URL.

### 7.3 Immutable `uv.lock`

Only the allowlisted root `uv.lock` path is authorized in v1.

The exact file is read at `snapshot.commit_sha`, treated as inert bytes, bounded to 1 MiB decoded content, verified against Git blob SHA-1, and independently hashed with SHA-256.

No `uv`, package manager, build, test, Dockerfile, setup hook, workflow, or repository script is executed.

### 7.4 Deterministic parsing and normalization

The parser uses Python stdlib `tomllib` over already verified immutable bytes.

It preserves source record indexes and resolution markers, bounds logical records to 5,000, and keeps unsupported source kinds explicit.

Supported canonical-PyPI records are normalized only through the existing Phase 3 package/version/purl authority.

### 7.5 Repository vulnerability findings

Normalized dependencies are joined to exact GHSA PyPI vulnerability occurrences by canonical package identity before the Phase 3 applicability evaluator runs.

```text
locked dependency
 + exact GHSA occurrence
 -> canonical package join
 -> deterministic range evaluation
 -> affected | not_affected | unsupported
```

Only `affected` emits a repository finding.

Positive finding identity:

```text
repository-finding:v1@sha256:<digest>
```

A finding proves repository-risk evidence for an immutable dependency snapshot. It does not prove runtime presence or exploitability.

### 7.6 NVD/CVSS enrichment

Already-affected findings may be enriched with exact NVD evidence without changing applicability truth.

Every supported NVD CVSS observation is preserved. Phase 4 intentionally chooses no preferred/highest/merged CVSS score.

### 7.7 CISA KEV enrichment

KEV evidence is derived from one complete validated catalog snapshot.

States:

```text
present
absent
cve_unavailable
```

`absent` is valid only after complete-snapshot non-membership is proven.

### 7.8 FIRST EPSS enrichment

EPSS evidence is attached from exactly one explicitly selected current or historical snapshot.

States:

```text
score_present
score_absent
cve_unavailable
```

There is no automatic `latest`, max-score, trend, or nearest-date selection inside the evidence domain.

### 7.9 Final Phase 4 projection

`RepositoryAnalysisResult` derives a consumer-facing projection from the fully validated evidence chain.

It can expose dependency/version/purl, GHSA/CVE identifiers, matched range and clauses, fixed version, all CVSS observations, KEV evidence, EPSS evidence, and exact evidence references.

It intentionally does not expose a risk score or runtime-exposure claim.

Final identities:

```text
repository-analysis-finding:v1@sha256:<digest>
repository-analysis:v1@sha256:<digest>
```

## 8. Risk Prioritization Engine — Phase 5

Phase 5 introduces a **separate downstream policy authority** over Phase 4 facts.

It does not redefine any source or applicability evidence.

### 8.1 Architecture boundary

```text
RepositoryAnalysisResult
 -> application projection
 -> RiskFindingInput
 -> pure deterministic Risk Policy v1
 -> RiskFactorContribution[]
 -> priority score + tier
 -> completeness / review_required
 -> deterministic aggregate ranking
 -> RiskPrioritizationResult
```

The `risk_policy` domain performs no network calls and knows nothing about AWS adapters, GitHub, NVD APIs, KEV APIs, or EPSS APIs.

### 8.2 Risk Policy v1

Maximum score: `100`.

```text
KEV present                         +40

EPSS >= 0.70                        +30
EPSS >= 0.30 and < 0.70            +20
EPSS >= 0.10 and < 0.30            +10
EPSS < 0.10                          +0

max supported CVSS >= 9.0           +20
max supported CVSS >= 7.0           +10
max supported CVSS >= 4.0            +5
max supported CVSS < 4.0              +0

known fixed version                  +10
```

Priority tiers:

```text
P0  score >= 80
P1  score >= 60 and < 80
P2  score >= 30 and < 60
P3  score < 30
```

This value is explicitly an **OpsLens priority score**.

It is not exploit probability, a replacement for EPSS/CVSS/KEV, or a runtime-exposure score.

### 8.3 CVSS policy aggregation

Phase 4 preserves all supported NVD CVSS observations.

Risk Policy v1 introduces the downstream policy-only aggregation:

```text
max supported observed CVSS base score
```

The selected maximum is recorded only in policy evidence. Original source observations remain unchanged.

If a future unsupported CVSS family is present, v1 assigns no CVSS points and marks the evaluation partial/review-required instead of pretending the older supported subset is complete.

### 8.4 Missing evidence semantics

Risk Policy v1 preserves the distinction between negative evidence and unavailable evidence.

```text
KEV absent in complete catalog       -> complete negative evidence
EPSS absent in complete snapshot     -> complete negative evidence
CVE unavailable                      -> partial / review_required
no supported CVSS evidence           -> partial / review_required
unsupported CVSS family              -> partial / review_required
```

Missing evidence adds no fabricated points, but a low numerical score with partial evidence cannot be presented as a complete low-risk conclusion.

### 8.5 Fixed-version factor

A known first patched version is worth `+10` as an explicit actionability bonus.

It does not alter vulnerability applicability. No known fixed version does not prove that remediation is impossible.

### 8.6 Policy identities

The exact policy definition, each finding evaluation, and the aggregate ranking are content-addressed:

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

Same evidence + same policy reproduces the same IDs and priority.

### 8.7 Ranking semantics

```text
1. priority_score descending
2. analysis_finding_id ascending
```

The tie breaker provides reproducibility only and carries no risk semantics.

### 8.8 Excluded v1 factors

Risk Policy v1 does not score facts OpsLens cannot yet prove deterministically:

```text
direct vs transitive dependency
runtime deployment presence
runtime package activation
reachability
internet exposure
business criticality
asset criticality
```

A future policy version may use them only after upstream evidence contracts exist.

## 9. Semantic Query Layer — Phase 6

Phase 6 adds bounded natural-language planning without giving a model deterministic fact authority or unrestricted SQL access.

### 9.1 Authority boundary

```text
User question
 -> bounded Bedrock planner
 -> structured planner proposal
 -> deterministic planner-output parser
 -> typed SemanticQuery
 -> deterministic validator
 -> deterministic SQL compiler
 -> exact compiler-shape admission
 -> bounded read-only Athena workgroup
 -> structured result evidence
```

The first supported factual slice is EPSS-by-explicit-snapshot-date over CVE dimension.

The model proposes semantics only. Application code owns the schema, allowlists, dates, thresholds, order, row limit, SQL shape, database/table/column names, Athena workgroup, and admission bounds.

### 9.2 Real model boundary

```text
model_id:       us.anthropic.claude-haiku-4-5-20251001-v1:0
client Region:  us-east-1
inference mode: US Geographic system-defined inference profile
streaming:      disabled
tools:          disabled
temperature:    0.0
maxTokens:      256
```

A supported real E2E question passed through Bedrock planner -> deterministic parser/compiler -> bounded Athena. A missing explicit date returned `unsupported` and never invoked Athena.

The local IAM Identity Center profile used for lab validation is not the future deployed runtime identity.

### 9.3 ADRs

```text
0020 No unrestricted text-to-SQL
0021 Bounded Bedrock semantic-query planner
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

## 10. Knowledge Retrieval foundation — Phase 7 through Gate 7.2

Phase 7 creates a distinct explanatory/remediation path. It does not replace the structured Phase 6 path.

### 10.1 Gate 7.1 provider-independent retrieval contract

Gate 7.1 froze:

```text
KnowledgeDocument
RetrievalRequest
RetrievedChunk
RetrievalEvidence
Citation
```

Retrieval bounds:

```text
query:         non-blank, <= 1,000 chars
top_k:         1..10
default top_k: 5
provider DSL:  none
```

Canonical metadata and citation provenance remain provider-independent. Citations are projected from admitted chunks rather than accepted from model-authored URLs/source IDs.

### 10.2 Gate 7.2 canonical corpus authority

Gate 7.2 authorizes six explanatory/remediation sources through a checked-in registry and pins each source to:

```text
upstream_repository
full 40-hex upstream_commit_sha
upstream_path
```

Human-facing `canonical_uri` is provenance only. Acquisition authority is derived by code as:

```text
https://raw.githubusercontent.com/<owner>/<repo>/<commit>/<path>
```

Mutable refs, alternate hosts, redirects, path traversal, unexpected media types, compressed responses, empty responses, oversized responses, and ambiguous/missing section markers fail closed.

### 10.3 Deterministic canonicalization

Frozen v1 policy:

```text
UTF-8:        strict
BOM:          reject
NUL:          reject
newlines:     CRLF/CR -> LF
Unicode:      preserve
selection:    exact line-aligned start-inclusive/end-exclusive markers
document join: two LF
```

No HTML parser, semantic cleanup, Unicode normalization, or LLM transformation participates in corpus truth.

### 10.4 Content addressing and manifest

The checked-in manifest stores only provenance and hashes, not third-party source/chunk text.

```text
manifest_id: knowledge-corpus-manifest:v1
documents:   6
chunks:      9
manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

For each document the manifest preserves exact source byte count/SHA-256, canonical document UTF-8 byte count/SHA-256, and ordered chunk byte counts/SHA-256 values.

### 10.5 Replay semantics

The serial replay pipeline has explicit write/check modes:

```bash
PYTHONPATH=src uv run python -m opslens.knowledge_retrieval.cli.materialize_corpus --write
PYTHONPATH=src uv run python -m opslens.knowledge_retrieval.cli.materialize_corpus --check
```

`--check` regenerates the manifest from the same immutable pins and requires byte-for-byte equality without overwriting recorded evidence.

The first real replay found a duplicate PyPA section heading and failed closed. The selector was made more specific against the exact pinned source; uniqueness validation was preserved.

The corrected real replay wrote and immediately re-verified the same manifest SHA-256. CI then validated the committed manifest with Ruff, strict Pyright, 44 Knowledge Retrieval tests, and all existing regression jobs.

### 10.6 Retrieval-content trust boundary

A source being authorized and pinned does not turn its text into trusted instructions.

Later retrieval/context assembly must treat chunk text as untrusted evidence and must prevent retrieved instructions from changing system/tool/policy authority.

Structured NVD, KEV, EPSS, CVSS, GHSA applicability, repository-version, and Risk Policy truth remain outside RAG authority.

## 11. Evidence and cache boundary

Content-addressed analysis and prioritization identities include the selected threat-intelligence evidence.

Therefore:

```text
same repository commit
 + different temporal KEV/EPSS evidence
 -> potentially different RepositoryAnalysisResult
 -> potentially different RiskPrioritizationResult
```

A repository commit alone is not a safe cache key.

Likewise, canonical knowledge identity is not just a human-facing URL. It depends on exact pinned source bytes, deterministic selection policy, and canonical content hashes.

No runtime cache backend exists yet because a measured workload has not justified storage cost, invalidation semantics, IAM, observability, failure recovery, and retention policy.

## 12. Security boundaries

```text
Human administration
 -> AWS IAM Identity Center

GitHub Actions
 -> OIDC
 -> deployment role
 -> Terraform-managed AWS changes

Threat-intelligence runtimes
 -> source-specific least-privilege roles

Repository Intelligence
 -> bounded public GitHub read-only authority
 -> inert repository evidence only
 -> no third-party code execution

Risk Policy
 -> pure deterministic Phase 4 evidence input
 -> no network/model authority

Semantic Query planner
 -> bounded Bedrock planning authority only
 -> deterministic parser/compiler owns query truth
 -> bounded read-only Athena execution

Canonical Knowledge Corpus
 -> immutable allowlisted official source pins
 -> bounded GET-only raw-source acquisition
 -> inert untrusted text only
 -> deterministic normalization/selection/hashing
 -> no model or AWS authority
```

A deterministic repository priority remains a **repository-risk policy result**. Runtime Exposure remains a later independent evidence domain.

## 13. Cost discipline

Current examples:

- no Glue crawler where explicit schemas suffice;
- no DynamoDB repository cache before measured reuse;
- no Step Functions unless workflow semantics justify it;
- no Iceberg requirement yet;
- no vector database before Gate 7.3 architecture selection;
- no Bedrock call for deterministic applicability or risk prioritization;
- Athena dev workgroup enforces a 10 MiB scan cutoff;
- Gate 7.2 adds `$0` AWS cost because it creates no AWS resource or call.

Phase 5 incremental AWS cost is `$0`. Gate 7.1 and Gate 7.2 incremental AWS cost is also `$0`.

Phase 6 model/Athena usage is bounded and records tokens, latency, bytes scanned, and estimated cost as runtime evidence.

## 14. Quality gates

Dedicated deterministic CI slices exist for:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
```

The Python workflow also watches `knowledge/corpus/**`, so corpus registry/spec/manifest changes cannot bypass the Knowledge Retrieval gate.

Gate 7.2 final manifest validation:

```text
Python CI run: 33965739749
manifest commit: bb61f6766f9c52c167ac7d1a3a8bc734cd1a6307

Knowledge Retrieval Ruff:     PASS
Knowledge Retrieval Pyright:  0 errors / 0 warnings / 0 informations
Knowledge Retrieval pytest:   44 passed in 0.25s
Correlation regression:              PASS
Repository Intelligence regression:  PASS
Risk Policy regression:              PASS
Semantic Query regression:           PASS
```

AWS-bearing changes additionally use Terraform fmt/validate, TFLint, Checkov, canonical plan review, deployment verification, and post-apply convergence checks.

## 15. ADR baseline through Phase 7 Gate 7.2

The ADR series currently includes:

```text
0001 Terraform state strategy
0002 GitHub Actions OIDC
0003 AWS Region strategy
0004 NVD ingestion/versioning
0005 GHSA source/synchronization
0006 GHSA Silver content identity
0007 GHSA runtime credentials/retry
0008 PyPI correlation semantics
0009 immutable public repository snapshot
0010 bounded read-only GitHub REST transport
0011 immutable uv.lock evidence
0012 deterministic uv.lock parser
0013 Phase 3 PyPI normalization bridge
0014 deterministic repository vulnerability findings
0015 repository NVD/CVSS enrichment
0016 repository KEV snapshot enrichment
0017 repository EPSS snapshot enrichment
0018 repository analysis result projection
0019 deterministic Risk Policy v1
0020 no unrestricted text-to-SQL
0021 bounded Bedrock semantic-query planner
```

Gate 7.1/7.2 did not require a new AWS architecture ADR because they intentionally froze provider-independent contracts and a deterministic local corpus before selecting Knowledge Base/vector infrastructure. Gate 7.3 must create/update ADRs for material AWS architecture choices.

`docs/adr/README.md` is the canonical ADR index.

## 16. Explicit non-goals at the current boundary

The implemented system does not yet provide:

- private-repository analysis;
- arbitrary dependency-manifest support;
- ecosystems beyond the supported PyPI v1 path;
- runtime deployment/exposure truth;
- reachability analysis;
- business/asset criticality evidence;
- unrestricted text-to-SQL;
- live vector/semantic knowledge retrieval;
- Bedrock Knowledge Base integration;
- retrieval-driven synthesis;
- autonomous remediation;
- agent authority over deterministic evidence;
- arbitrary MCP/tool execution.

## 17. Next boundary — Gate 7.3 Knowledge Base + vector infrastructure

Gate 7.3 must connect the already frozen provider-independent retrieval/corpus contracts to AWS retrieval infrastructure without changing structured-truth authority.

Target decision flow:

```text
canonical corpus v1
 -> choose Bedrock Knowledge Base mode
 -> choose embedding model/dimensions
 -> choose vector store
 -> choose ingestion/chunking strategy
 -> project allowlisted provenance metadata
 -> define KB service role
 -> define separate future retrieval runtime identity
 -> provision minimal dev resources
 -> ingest/sync
 -> verify exact corpus/provenance mapping
```

Before implementation, current official AWS documentation must be re-checked for:

- Managed vs customer-managed Knowledge Base behavior;
- `Retrieve` APIs and result/provenance shape;
- current embedding models, dimensions, Regions, quotas, and pricing;
- S3 Vectors vs OpenSearch Serverless capabilities and cost model;
- chunking strategy constraints and immutability after data-source creation;
- metadata size/filter limits;
- service-role trust and least-privilege permissions;
- encryption/network requirements;
- ingestion/sync behavior, failure recovery, and rebuild semantics;
- observability and throttling;
- idle, ingestion, storage, and retrieval costs.

Candidate decisions from earlier research are **not pre-approved**. Gate 7.3 must revalidate them against current official documentation and measured OpsLens needs.

The first v1 retrieval path should prefer `Retrieve` independently from generation so retrieval quality can be evaluated before synthesis.

Do not use `RetrieveAndGenerate` as a shortcut for the initial evaluation path.
