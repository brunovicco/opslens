# ADR 0019 — Deterministic Risk Policy v1

- Status: Accepted
- Date: 2026-09-03
- Phase: 5 — Risk Prioritization Engine

## Context

Phase 4 closes with `RepositoryAnalysisResult`: a content-addressed projection of immutable repository dependency evidence, deterministic GHSA applicability, exact CVE/NVD/CVSS evidence, complete-snapshot CISA KEV evidence, and an explicitly selected FIRST EPSS snapshot.

Phase 4 intentionally does not assign a risk score or priority. Source facts and prioritization policy are different authorities.

OpsLens now needs to answer questions such as:

> Which findings should I prioritize and why?

The ranking must remain deterministic and explainable. An LLM may later explain an already-produced policy result, but it must not be required to establish the rank.

## Decision

Create a separate `opslens.risk_policy` domain and freeze **Risk Policy v1** as a deterministic prioritization policy over existing Phase 4 evidence.

The policy consumes only currently proven factors:

```text
CISA KEV membership
FIRST EPSS score at the selected snapshot
supported NVD CVSS base-score observations
known GHSA fixed-version availability
```

The policy does not consume factors that Phase 4 does not yet prove, including:

```text
direct vs transitive dependency
runtime deployment presence
runtime package activation
exploit reachability
business criticality
asset criticality
internet exposure
```

Those factors require new deterministic evidence before a later policy version may use them.

## Risk Policy v1 score

Risk Policy v1 emits a **priority score**, not a vulnerability probability and not a replacement for CVSS, EPSS, KEV, or source severity.

Maximum score: `100`.

### KEV contribution

```text
present                         +40
absent in complete snapshot      +0
CVE unavailable                  +0 + partial evidence / review required
```

A KEV `absent` state is valid negative evidence only because Phase 4 proves membership against a complete validated catalog snapshot.

`cve_unavailable` is not interpreted as KEV absence.

### EPSS contribution

Risk Policy v1 uses the exact score from the selected Phase 4 EPSS snapshot.

```text
EPSS >= 0.70                   +30
EPSS >= 0.30 and < 0.70       +20
EPSS >= 0.10 and < 0.30       +10
EPSS < 0.10                     +0
score absent in full snapshot    +0
a CVE unavailable                +0 + partial evidence / review required
```

The thresholds are policy semantics. They do not redefine the EPSS score.

### CVSS contribution

Phase 4 intentionally preserves all supported NVD CVSS observations rather than selecting a winner.

Risk Policy v1 introduces the explicit policy aggregation:

```text
max supported observed CVSS base score
```

Then:

```text
score >= 9.0                  +20
score >= 7.0 and < 9.0       +10
score >= 4.0 and < 7.0        +5
score < 4.0                    +0
```

This maximum is a prioritization-policy value. It does not replace or mutate any source CVSS observation.

If Phase 4 reports an unsupported future CVSS family, Risk Policy v1 assigns **zero CVSS points** and marks the evaluation as partial/review-required. It does not silently use an older supported metric while claiming complete evaluation.

If no supported CVSS evidence exists, the CVSS factor is also partial/review-required.

### Fixed-version contribution

```text
known first patched version    +10
no known first patched version  +0
```

This is an explicit **actionability bonus**. It does not affect vulnerability applicability. A missing fixed version is not interpreted as evidence that the vulnerability is unfixable.

## Priority tiers

```text
P0  score >= 80
P1  score >= 60 and < 80
P2  score >= 30 and < 60
P3  score < 30
```

The score and tier are policy outputs only.

## Evidence completeness

Risk Policy v1 separately emits:

```text
complete
partial
```

and:

```text
review_required: true | false
```

Evidence is partial when a required threat factor cannot be evaluated safely, including CVE-unavailable KEV/EPSS evidence, missing supported CVSS evidence, or unsupported CVSS families.

Missing evidence adds no risk points. This avoids fabricating risk. It also never becomes an implicit low-risk assertion because `partial` and `review_required` remain explicit outputs.

Proven source absence is different from missing evidence:

```text
KEV absent in a complete catalog -> complete negative evidence
EPSS score absent in a complete snapshot -> complete negative evidence
CVE unavailable -> missing identity/evidence, not negative evidence
```

## Ranking semantics

Findings are ordered by:

```text
1. priority_score descending
2. analysis_finding_id ascending
```

The second rule exists only to make equal-score ordering reproducible.

The tie breaker has **no risk semantics** and is recorded explicitly in aggregate evidence.

## Versioning and content addressing

The exact policy definition is canonical JSON and receives a SHA-256 identity:

```text
risk-policy:v1@sha256:<digest>
```

Each finding evaluation is independently content-addressed:

```text
risk-evaluation:v1@sha256:<digest>
```

The aggregate deterministic ranking is also content-addressed:

```text
risk-prioritization:v1@sha256:<digest>
```

Changing evidence changes evaluation identity. Changing policy semantics must create a new policy version; even before that, the exact policy bytes are protected by the policy SHA-256.

## Architecture boundary

```text
RepositoryAnalysisResult
 -> Phase 5 application bridge
 -> typed RiskFindingInput
 -> pure deterministic Risk Policy v1 evaluator
 -> factor contributions
 -> priority score + tier + completeness
 -> deterministic ranking
```

The risk-policy domain does not fetch GitHub, NVD, KEV, EPSS, AWS, or any external service.

The application bridge is responsible only for projecting already-validated Phase 4 fields into the risk-policy input contract.

## LLM boundary

No LLM or Bedrock model is required for:

```text
factor extraction
threshold evaluation
CVSS policy aggregation
score calculation
tier assignment
ranking
evidence completeness
```

A later LLM may explain these deterministic outputs in natural language, but the explanation must remain downstream of the policy evidence.

## AWS, IAM, cost, and observability

Gate 5.1 introduces:

```text
new AWS resources:     0
new IAM permissions:   0
model calls:           0
incremental AWS cost:  $0
```

There is no persistence or runtime workload yet, so DynamoDB, Lambda, Step Functions, SQS, and cache services are not justified by this gate.

Observability for a future runtime should report policy version, policy ID, evaluation ID, priority tier, score, factor reason codes, and evaluation latency without replacing the content-addressed evidence record.

## Security and failure behavior

The evaluator fails closed on structurally invalid policy inputs.

Unknown CVSS semantics do not inherit old policy behavior.

Missing source evidence is explicit rather than silently interpreted as a benign result.

Repository Risk remains separate from Runtime Exposure. Risk Policy v1 prioritizes repository findings only.

## Consequences

### Positive

- ranking is reproducible;
- every point has a stable factor-level reason;
- policy is separable from source truth;
- missing evidence stays visible;
- later LLM explanations can cite exact deterministic policy evidence;
- changing the policy does not require changing Phase 4 evidence contracts;
- no new AWS cost or runtime complexity is introduced prematurely.

### Trade-offs

- the weights and thresholds are an OpsLens v1 policy choice, not a universal vulnerability standard;
- `max supported CVSS base score` is intentionally conservative but may differ from another organization's scoring preference;
- fixed-version availability increases actionability priority and therefore the output should be described as a priority score, not pure threat severity;
- direct/transitive and runtime factors cannot be used until deterministic evidence exists.

## Next boundary

After Gate 5.1 is validated, evaluate the complete Phase 5 exit criteria. If further work is needed, the next gate should focus on benchmark/policy-change evidence or final Phase 5 projection/closeout, not on adding AWS infrastructure or an LLM.
