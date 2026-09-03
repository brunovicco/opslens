# Phase 5 — Risk Prioritization Engine Closeout

Date: 2026-09-03

Status: **COMPLETE**

Implementation PR: **#80 — `feat(risk): introduce deterministic Risk Policy v1`**

Implementation merge commit:

```text
81a2e78a3e8329aa811c20012bc565f35f1a87e5
```

Validated implementation head:

```text
12a464676e3048c5b7bfa52879b1736b7f5c7100
```

Final CI run:

```text
33810836040 — SUCCESS
```

## 1. Goal

Phase 5 converts already-proven Phase 4 repository findings into deterministic, versioned, explainable priority decisions.

The authority boundary is:

```text
Phase 0–4
facts + immutable evidence
        |
        v
RepositoryAnalysisResult
        |
        v
Phase 5
Risk Policy v1
        |
        v
priority score + tier + factor evidence + completeness + deterministic rank
```

Risk Policy does not re-evaluate package applicability and does not mutate source evidence.

Permanent boundaries remain:

> **Agents reason. Code verifies evidence.**

> **Repository Risk != Runtime Exposure.**

## 2. Implemented architecture

```text
RepositoryAnalysisResult
        |
        v
Phase 5 application bridge
build_risk_finding_input(...)
        |
        v
RiskFindingInput
        |
        v
pure deterministic Risk Policy v1 evaluator
        |
        +--> KEV contribution
        +--> EPSS contribution
        +--> CVSS contribution
        +--> fixed-version actionability contribution
        |
        v
RiskFindingEvaluation
        |
        v
RiskPrioritizationResult
        |
        v
deterministic ranked findings
```

Implemented package:

```text
src/opslens/risk_policy/
  application/
  domain/
```

The risk-policy domain performs no network access and has no AWS, GitHub, NVD, KEV, EPSS, or model client.

## 3. Frozen Risk Policy v1

ADR:

```text
docs/adr/0019-deterministic-risk-policy-v1.md
```

Risk Policy v1 emits a **priority score**, not a vulnerability probability and not a replacement for CVSS, EPSS, KEV, or runtime-exposure evidence.

Maximum score:

```text
100
```

### CISA KEV

```text
present                         +40
absent in complete snapshot      +0
CVE unavailable                  +0 + partial/review_required
```

KEV absence remains valid only because Phase 4 proves non-membership against one complete validated catalog snapshot.

### FIRST EPSS

```text
EPSS >= 0.70                   +30
EPSS >= 0.30 and < 0.70       +20
EPSS >= 0.10 and < 0.30       +10
EPSS < 0.10                     +0
score absent in full snapshot    +0
CVE unavailable                  +0 + partial/review_required
```

The thresholds are explicit OpsLens policy semantics. They do not redefine the EPSS source score.

### NVD CVSS

Phase 4 preserves every supported NVD CVSS observation. Risk Policy v1 owns the explicit aggregation rule:

```text
selected score = max(supported observed CVSS base scores)
```

Contribution:

```text
CVSS >= 9.0                   +20
CVSS >= 7.0 and < 9.0        +10
CVSS >= 4.0 and < 7.0         +5
CVSS < 4.0                     +0
```

Unsupported future CVSS families do not inherit old behavior: the CVSS contribution becomes zero and the evaluation becomes partial/review-required.

Missing supported CVSS evidence is also explicit partial evidence.

### Fixed version

```text
known first patched version    +10
no known first patched version  +0
```

This is an explicit actionability contribution. It does not change vulnerability applicability and does not prove that a vulnerability without a published fixed version is unfixable.

## 4. Priority tiers

```text
P0  score >= 80
P1  score >= 60 and < 80
P2  score >= 30 and < 60
P3  score < 30
```

Repository findings are ranked by:

```text
1. priority_score descending
2. analysis_finding_id ascending
```

The opaque finding ID exists only as a stable deterministic tie-breaker and has no risk meaning.

## 5. Evidence completeness

The policy separates score from evidence completeness.

```text
complete
partial
```

and:

```text
review_required: true | false
```

Important distinction:

```text
KEV absent in complete catalog   -> known negative evidence
EPSS absent in complete snapshot -> known negative evidence
CVE unavailable                  -> missing evidence
unsupported CVSS family          -> unsupported evidence
```

Missing evidence contributes no fabricated points, but it also never silently becomes a complete low-risk assertion because `partial` and `review_required` remain explicit.

## 6. Content-addressed identities

The implementation preserves deterministic identity at every policy layer:

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

Consequences:

- same evidence + same policy reproduces the same evaluation identity;
- changing one scoring input changes evaluation identity;
- aggregate ranking is reproducible;
- policy evidence can later be cited by an LLM explanation without giving the model ranking authority.

## 7. Explicit non-goals

Risk Policy v1 does not infer or score:

```text
direct/transitive dependency status
runtime deployment presence
runtime package activation
exploit reachability
business criticality
asset criticality
internet exposure
Amazon Inspector runtime evidence
LLM judgment
```

Those factors require new deterministic evidence before a future policy version may consume them.

## 8. Quality and failure-path validation

A dedicated CI slice was added:

```text
uv lock --check
uv sync --frozen
ruff check src/opslens/risk_policy tests/unit/risk_policy
pyright src/opslens/risk_policy tests/unit/risk_policy
pytest tests/unit/risk_policy
```

The first CI attempt reached the new Risk Policy quality slice and failed on mechanical Ruff findings in import/export ordering and one bytes fixture representation:

```text
run 33810786432 -> FAILURE
```

The correction changed formatting/fixture representation only. Policy weights, thresholds, evidence states, scoring, completeness, and ranking semantics were not relaxed.

Final validation:

```text
run 33810836040 -> SUCCESS

uv lock --check:                   PASS
uv sync --frozen:                  PASS
Risk Policy Ruff:                  PASS
Risk Policy Pyright:               0 errors / 0 warnings
Risk Policy pytest:                31 passed
Repository Intelligence Ruff:      PASS
Repository Intelligence Pyright:   0 errors / 0 warnings
Repository Intelligence pytest:    174 passed
Correlation Ruff:                  PASS
Correlation Pyright:               0 errors / 0 warnings
Correlation pytest:                116 passed
```

The intentional failure/recovery satisfies the phase requirement that a meaningful quality failure be diagnosed rather than bypassed.

## 9. Phase 5 exit criteria

### Same evidence always produces the same priority

**PASS.** Canonical policy/evaluation/prioritization records are content-addressed and tests assert identity reproduction.

### Factor-level explanation is available

**PASS.** Each contribution records factor, points, maximum points, observed value, and a stable reason code.

### Policy version is recorded

**PASS.** Risk Policy v1 has explicit versioned canonical policy evidence and a `risk-policy:v1@sha256:...` identity.

### LLM is not required for ranking

**PASS.** Ranking is pure deterministic Python domain/application logic.

### Tests demonstrate priority changes when factors change

**PASS.** Unit tests isolate KEV, EPSS, CVSS, fixed-version, tier boundaries, completeness, identity changes, and deterministic tie-breaking.

### Missing/unsupported evidence has explicit semantics

**PASS.** Partial evidence and `review_required` are first-class outputs; unsupported CVSS semantics fail closed.

### Repository Risk remains distinct from Runtime Exposure

**PASS.** No runtime deployment/exposure evidence is inferred or consumed.

## 10. AWS, IAM, observability, and cost

Phase 5 introduces no AWS runtime.

```text
new AWS resources:      0
new IAM permissions:    0
model calls:            0
new persistence/cache:  0
incremental AWS cost:   $0
```

This is intentional. The requirement is deterministic policy evaluation, so Lambda, DynamoDB, SQS, Step Functions, Bedrock, or another service would add cost and failure surface without solving a current problem.

Future runtime observability should expose policy version, policy ID, evaluation ID, factor reason codes, score/tier, completeness, and evaluation latency.

## 11. Trade-off to carry forward

The v1 weights and thresholds are explicit **OpsLens prioritization policy choices**, not universal vulnerability-management standards.

The current implementation is acceptable as the deterministic v1 baseline because the semantics are transparent, versioned, independently testable, and cannot rewrite Phase 4 facts.

The appropriate next validation is evaluation against historical/reproducible security cases. That evaluation may justify a future `Risk Policy v2`; it should not silently mutate v1.

## 12. Next boundary

Phase 5 is complete.

The next roadmap boundary is:

> **Phase 6 — Semantic Query Layer**

Target flow:

```text
User question
 -> Bedrock planner
 -> typed semantic query
 -> deterministic validation
 -> code-owned SQL compiler
 -> bounded read-only Athena workgroup
```

Permanent guardrail:

> **No unrestricted text-to-SQL.**

Phase 6 should begin by freezing the smallest typed semantic-query contract and SQL-compiler authority before introducing Bedrock planner calls.
