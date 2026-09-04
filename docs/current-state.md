# OpsLens — Current State

_Last updated: 2026-09-04_

This document is the public implementation checkpoint for the OpsLens repository.

## Status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2    Threat Intelligence Data Lake                       COMPLETE
Phase 3    Vulnerability Correlation Engine                    COMPLETE
Phase 4    Repository Intelligence                             COMPLETE
Phase 5    Risk Prioritization Engine                          COMPLETE
Phase 6    Semantic Query Layer                                IN PROGRESS
  Gate 6.1 Typed contract + deterministic SQL compiler         COMPLETE
  Gate 6.2 Bounded read-only Athena execution                  COMPLETE
  Gate 6.3 Bounded planner contract + offline evaluation       COMPLETE
  Gate 6.4 Real Bedrock planner invocation                     IMPLEMENTED / CLOSEOUT PENDING
```

Gate 6.4 implementation and real `dev` evidence are complete on branch:

```text
feat/phase6-bedrock-runtime-evidence
```

Final repository-wide validation, PR creation, green CI, and logical merge are still pending.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

Deterministic authorities remain responsible for:

- package identity normalization;
- version parsing and vulnerable-range matching;
- vulnerability applicability;
- CVE/GHSA/NVD alias reconciliation;
- KEV, EPSS, and CVSS evidence;
- risk policy evaluation;
- canonical evidence serialization and content addressing;
- planner-output parsing and validation;
- semantic-query validation and SQL compilation;
- Athena admission, execution bounds, and result validation;
- evidence validation;
- execution/tool/cost enforcement.

LLMs may classify, plan, synthesize, explain, and route over validated evidence. They do not decide vulnerability applicability and do not receive arbitrary SQL authority.

## Implemented deterministic stack

```text
1. Threat Intelligence Data Lake
   NVD / CISA KEV / FIRST EPSS / GitHub Security Advisories

2. Vulnerability Correlation Engine
   PyPI identity / PEP 440 applicability / GHSA / CVE-NVD evidence

3. Repository Intelligence
   immutable public GitHub snapshot / inert uv.lock / repository findings

4. Risk Prioritization Engine
   deterministic Risk Policy v1 / factor explanations / ranking

5. Semantic Query deterministic boundary
   typed SemanticQuery / allowlists / deterministic SQL / bounded Athena

6. Bounded Bedrock planner
   natural-language request / structured planner proposal /
   deterministic parser / typed runtime evidence / fail-closed composition
```

## Repository and risk path

```text
public GitHub repository
 -> immutable repository identity
 -> exact commit + tree SHA
 -> bounded GET-only GitHub REST acquisition
 -> exact inert uv.lock bytes
 -> deterministic TOML parsing
 -> PyPI package/version/purl normalization
 -> GHSA vulnerable-range applicability
 -> CVE/GHSA/NVD evidence reconciliation
 -> NVD/CVSS enrichment
 -> complete-snapshot CISA KEV evidence
 -> explicit-date FIRST EPSS evidence
 -> content-addressed RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> priority score + tier + completeness
 -> content-addressed RiskPrioritizationResult
```

No third-party repository code is executed.

## Risk Policy v1

```text
KEV present                         +40
EPSS >= 0.70 / 0.30 / 0.10          +30 / +20 / +10
max supported CVSS >= 9 / 7 / 4     +20 / +10 / +5
known fixed version                 +10
maximum                              100
```

Priority tiers:

```text
P0 >= 80
P1 >= 60
P2 >= 30
P3 < 30
```

This is an OpsLens priority score, not exploit probability, source severity, or runtime exposure.

Deterministic identities:

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

## Phase 6 — Semantic Query Layer

Target architecture:

```text
User question
 -> bounded Bedrock planner
 -> structured planner proposal
 -> deterministic planner-output parser
 -> typed SemanticQuery
 -> deterministic validation
 -> deterministic SQL compiler
 -> exact compiler-shape admission
 -> bounded read-only Athena workgroup
 -> structured result evidence
```

### Gate 6.1 — COMPLETE

First supported factual slice:

> Which CVEs have EPSS of at least 0.7 on an explicit snapshot date?

Contract:

```text
metric:       epss_score
dimension:    cve
filters:      explicit snapshot_date, optional minimum_score
order:        epss_score ASC|DESC, deterministic cve ASC tie break
limit:        1..100, default 20
```

The compiler owns database/table/columns/predicates/order/limit. Filter values become validated positional Athena execution parameters.

ADR: [`adr/0020-no-unrestricted-text-to-sql.md`](adr/0020-no-unrestricted-text-to-sql.md).

### Gate 6.2 — COMPLETE

Bounded real Athena boundary:

```text
database:    opslens_dev
workgroup:   opslens-dev
relation:    "opslens_dev"."epss_scores"
scan cutoff: 10 MiB via enforced workgroup configuration
```

Real Gate 6.2 evidence:

```text
query_execution_id:         958fb573-1a69-4ce6-8a36-d9be45e71c79
row_count:                  20
data_scanned_bytes:         3,785,003 (~3.61 MiB)
engine_execution_time_ms:   973
total_execution_time_ms:    1,128
```

Intentional `limit=101` fails before Athena.

Closeout: [`../labs/phase-6-gate-6-2-athena-readonly-execution.md`](../labs/phase-6-gate-6-2-athena-readonly-execution.md).

### Gate 6.3 — COMPLETE

Frozen bounded planner contract:

```text
question length: <= 1,000 chars
planner decisions: semantic_query | unsupported
supported metric: epss_score
supported dimension: exactly [cve]
required time: explicit YYYY-MM-DD
threshold semantics: inclusive >= only
order: epss_score asc|desc
limit: 1..100
SQL authority: none
```

The deterministic parser rejects extra/missing fields, invalid/relative dates, unsupported values, invalid score/limit values, and injected SQL before reconstructing the existing `SemanticQuery`.

Golden offline fixture:

```text
18 total cases
  8 supported
 10 fail-closed unsupported
```

ADR: [`adr/0021-bounded-bedrock-semantic-query-planner.md`](adr/0021-bounded-bedrock-semantic-query-planner.md).

Closeout: [`../labs/phase-6-gate-6-3-planner-contract-evaluation.md`](../labs/phase-6-gate-6-3-planner-contract-evaluation.md).

### Gate 6.4 — IMPLEMENTED / CLOSEOUT PENDING

Real model boundary:

```text
model_id:       us.anthropic.claude-haiku-4-5-20251001-v1:0
client Region:  us-east-1
inference mode: US Geographic system-defined inference profile
streaming:      disabled
tools:          disabled
temperature:    0.0
maxTokens:      256
```

Production code now contains:

- `BedrockPlannerInvocationEvidence` and `BedrockPlannerResult` typed contracts;
- injected `BedrockConverseClient` Protocol;
- `BedrockSemanticPlanner` outbound adapter;
- strict non-streaming response-shape validation;
- deterministic `parse_planner_json()` re-entry;
- provider/SDK failure wrapping while preserving the cause;
- `ExecuteNaturalLanguageSemanticQuery` application composition;
- versioned real entrypoint `scripts/run_natural_language_semantic_query.py`;
- fake-client/unit coverage for supported, unsupported, malformed evidence, and fail-closed behavior.

Real supported versioned E2E evidence on 2026-09-04:

```text
question:                       Which CVEs have EPSS of at least 0.7 on 2026-09-03?
planner decision:               semantic_query
model input/output/total:       942 / 79 / 1021 tokens
Bedrock latency:                1,632 ms
client elapsed:                 2,894 ms
retries:                        0
cache read/write input tokens:  0 / 0
estimated planner cost:         ~$0.00147
Athena query_execution_id:      09a32501-a06c-4437-809c-ebcaf350cd1d
Athena rows:                    20
Athena data scanned:            3,785,003 bytes (~3.61 MiB)
Athena engine time:             994 ms
Athena total time:              1,192 ms
```

Real versioned fail-closed semantic evidence:

```text
question:         Which CVEs have EPSS of at least 0.7?
decision:         unsupported
reason:           missing_explicit_snapshot_date
athena_invoked:   false
input/output:     933 / 23 tokens
Bedrock latency:  878 ms
client elapsed:   2,145 ms
retries:          0
estimated cost:   ~$0.00115
```

A real local IAM Identity Center token-expiry failure was also diagnosed before service invocation. It was an authentication failure during credential retrieval/signing, not a Bedrock model/inference-profile failure.

Closeout evidence: [`../labs/phase-6-gate-6-4-real-bedrock-planner.md`](../labs/phase-6-gate-6-4-real-bedrock-planner.md).

## Phase 6 exit state

```text
[x] typed SemanticQuery
[x] explicit metric/dimension/filter allowlists
[x] invalid/unknown semantics fail closed
[x] deterministic SQL only
[x] bounded read-only Athena supported slice
[x] planner evaluation set with field-level metrics
[x] natural-language factual question through real model + parser + compiler + Athena
[x] real model/API/token/latency/cost evidence recorded
[x] intentional real planner failure diagnosed
[x] ADR rejecting unrestricted text-to-SQL
[x] ADR defining bounded planner authority
[x] production Bedrock runtime adapter and typed invocation evidence
[x] automated runtime adapter/composition tests
[ ] final repository validation + PR + green CI + merge
[deferred] final deployed runtime IAM least privilege until a runtime identity exists
```

The final deployed runtime IAM criterion is explicitly deferred because no deployed semantic-query runtime identity exists yet. The local `opslens-bootstrap` IAM Identity Center profile is lab/bootstrap validation only and is not the final runtime role.

## AWS foundation

```text
environment:             dev
primary workload Region: us-east-1
IaC:                     Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

Persistent AWS access keys are not stored in GitHub.

## Current quality boundary

Dedicated Python CI slices exist for:

```text
src/opslens/correlation
src/opslens/repository_intelligence
src/opslens/risk_policy
src/opslens/semantic_query
```

A pre-existing repo-wide Ruff backlog outside these scoped deterministic slices remains separate technical debt.

## Next action

Before declaring Phase 6 complete:

```text
1. remove temporary local Bedrock marketplace-offer material if still present
2. run final targeted + regression validation
3. open the Gate 6.4 PR
4. require green CI
5. squash merge
6. update this checkpoint with the merged commit/PR
```

Do not add RAG, Knowledge Bases, agents, MCP, or AgentCore to Phase 6.
