# Phase 5 — Risk Prioritization Engine Closeout

Date: 2026-09-03

Status: **COMPLETE**

Implementation PR: **#80 — `feat(risk): introduce deterministic Risk Policy v1`**

Implementation merge checkpoint:

```text
81a2e78a3e8329aa811c20012bc565f35f1a87e5
```

## Objective

Phase 5 introduces a deterministic prioritization authority over the factual repository evidence produced by Phase 4.

The phase answers:

> Given already-proven repository findings and exact threat-intelligence evidence, which findings should OpsLens prioritize, and why?

The phase does **not** change package applicability, source evidence, or runtime-exposure truth.

## Architecture

```text
RepositoryAnalysisResult
 -> Phase 5 application bridge
 -> RiskFindingInput
 -> deterministic Risk Policy v1
 -> factor contributions
 -> priority score + tier
 -> evidence completeness / review_required
 -> deterministic ranking
 -> content-addressed RiskPrioritizationResult
```

The policy domain performs no network access and depends on no AWS runtime.

## Risk Policy v1

Maximum score: `100`.

```text
CISA KEV
present                                           +40
absent in a complete validated snapshot            +0
CVE unavailable                                    +0 + partial/review_required

FIRST EPSS
score >= 0.70                                     +30
score >= 0.30 and < 0.70                         +20
score >= 0.10 and < 0.30                         +10
score < 0.10                                       +0
score absent in a complete selected snapshot       +0
CVE unavailable                                    +0 + partial/review_required

NVD CVSS policy aggregation
max supported observed base score >= 9.0          +20
max supported observed base score >= 7.0          +10
max supported observed base score >= 4.0           +5
max supported observed base score < 4.0            +0
no supported CVSS evidence                          +0 + partial/review_required
unsupported future CVSS family                      +0 + partial/review_required

Actionability
known first patched version                        +10
no known first patched version                      +0
```

Priority tiers:

```text
P0  score >= 80
P1  score >= 60 and < 80
P2  score >= 30 and < 60
P3  score < 30
```

## Policy semantics

The emitted score is an **OpsLens priority score**.

It is not:

```text
an exploit probability
a replacement for EPSS
a replacement for CVSS
a replacement for KEV source truth
a runtime-exposure score
a universal vulnerability severity standard
```

The weights and thresholds are explicit versioned policy choices.

### Negative evidence vs missing evidence

Phase 5 preserves the distinction established by Phase 4:

```text
KEV absent in complete catalog       -> complete negative evidence
EPSS absent in complete snapshot     -> complete negative evidence
CVE unavailable                      -> missing identity/evidence
unsupported CVSS family              -> unsupported policy semantics
no CVSS observation                  -> missing policy input evidence
```

Missing/unsupported evidence adds no points because OpsLens does not fabricate risk. It also cannot masquerade as a low-confidence benign result because the evaluation emits:

```text
evidence_completeness = partial
review_required = true
```

### CVSS aggregation

Phase 4 preserves all supported NVD CVSS observations and deliberately chooses no winner.

Risk Policy v1 introduces one explicit downstream policy rule:

```text
max supported observed CVSS base score
```

This selected value exists only inside policy evidence. The original NVD metrics remain unchanged.

If a future unsupported CVSS family is present, v1 fails closed for the CVSS factor rather than silently scoring only older families while claiming a complete evaluation.

### Fixed-version factor

A known fixed version is worth `+10` as an explicit **actionability bonus**.

It does not change `affected` truth. Missing fix evidence is not interpreted as proof that no fix exists.

## Deterministic identities

The exact policy definition is canonical JSON and content-addressed:

```text
risk-policy:v1@sha256:<digest>
```

Each finding evaluation:

```text
risk-evaluation:v1@sha256:<digest>
```

The aggregate ranking:

```text
risk-prioritization:v1@sha256:<digest>
```

Changing source evidence or policy semantics changes the relevant content identity.

## Ranking semantics

Ranking is deterministic:

```text
1. priority_score descending
2. analysis_finding_id ascending
```

The second rule is only a stable tie breaker.

It has no risk meaning and is recorded as such in aggregate evidence.

## Deliberately excluded factors

Risk Policy v1 does not score evidence that OpsLens does not yet deterministically possess:

```text
direct vs transitive dependency
runtime deployment presence
runtime package activation
reachability
internet exposure
business criticality
asset criticality
```

A later policy version may use these only after an upstream deterministic evidence contract exists.

## Exit criteria matrix

| Roadmap exit criterion | Evidence | Result |
| --- | --- | --- |
| Same evidence always produces same priority | canonical policy/evaluation/result JSON plus reproducibility tests | PASS |
| Factor-level explanation available | four ordered `RiskFactorContribution` records with points, bounds, reason code, observed value | PASS |
| Policy version recorded | `RiskPolicyV1.version`, canonical policy bytes, SHA-256 and `risk-policy:v1@sha256:...` | PASS |
| LLM not required for ranking | pure Python domain evaluator; zero model calls | PASS |
| Tests demonstrate priority changes when factors change | KEV, EPSS, CVSS and fixed-version boundary/change tests | PASS |

Additional safeguards:

| Property | Result |
| --- | --- |
| Proven absence kept distinct from missing evidence | PASS |
| Unsupported future CVSS semantics fail closed | PASS |
| Repository Risk remains separate from Runtime Exposure | PASS |
| Applicability authority remains Phase 3/4 | PASS |
| Aggregate ranking tie behavior is deterministic | PASS |
| Duplicate source finding accounting fails closed | PASS |

## Validation

Final validated PR head:

```text
12a464676e3048c5b7bfa52879b1736b7f5c7100
```

GitHub Actions run:

```text
33810836040
```

Validation:

```text
uv lock --check:                  PASS
uv sync --frozen:                 PASS

Risk Policy Ruff:                 PASS
Risk Policy Pyright:              0 errors / 0 warnings
Risk Policy pytest:               31 passed

Repository Intelligence Ruff:     PASS
Repository Intelligence Pyright:  0 errors / 0 warnings
Repository Intelligence pytest:   174 passed

Correlation Ruff:                 PASS
Correlation Pyright:              0 errors / 0 warnings
Correlation pytest:               116 passed
```

### Failure path

The first CI run stopped in the new Risk Policy Ruff step on six mechanical findings:

```text
import ordering
__all__ ordering
one bytes-fixture UP012 rewrite
```

Correlation and Repository Intelligence regressions were already green.

Only import/export order and inert test-fixture representation changed. No policy weight, threshold, completeness rule, or ranking semantic was relaxed.

## AWS / IAM / cost boundary

Phase 5 introduces:

```text
new AWS resources:     0
new IAM permissions:   0
model calls:           0
incremental AWS cost:  $0
```

This is intentional.

Risk policy is currently pure deterministic computation over an already-built `RepositoryAnalysisResult`. Lambda, DynamoDB, SQS, Step Functions, Bedrock, API Gateway, or cache infrastructure would not solve a demonstrated Phase 5 requirement.

Runtime/persistence services should be introduced only when a later phase creates a concrete execution or public-serving requirement.

## Security boundary

Permanent rules remain unchanged:

> **Agents reason. Code verifies evidence.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

No model can override the policy calculation.

A later model may explain factor evidence in natural language but must remain downstream of the deterministic `RiskFindingEvaluation` / `RiskPrioritizationResult`.

## AIP-C01 learning value

This phase reinforces professional-level reasoning around:

- deterministic governance and explainability;
- source/evidence traceability;
- separating model reasoning from enforcement logic;
- explicit quality gates and regression tests;
- cost discipline by declining unnecessary managed services;
- responsible AI patterns where explanations are downstream of verifiable facts.

No AWS service was forced into the product solely for certification coverage.

## Phase conclusion

**Phase 5 is COMPLETE.**

The next roadmap boundary is:

```text
Phase 6 — Semantic Query Layer
```

Phase 6 is the first phase in this sequence expected to require an FM planner. Before implementation, current Amazon Bedrock and Athena APIs/features/pricing/limits must be checked against official AWS documentation.

The permanent guardrail is:

> **No unrestricted text-to-SQL.**
