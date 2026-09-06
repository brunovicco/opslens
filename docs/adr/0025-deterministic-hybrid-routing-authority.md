# ADR 0025 — Deterministic Hybrid Routing and Authority Contract

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 8 — Hybrid Retrieval, Gate 8.1

## Context

OpsLens already has two independently measured evidence paths:

```text
structured vulnerability/risk facts -> deterministic structured authority
explanatory/remediation knowledge    -> bounded semantic retrieval evidence
```

Phase 8 must combine those capabilities without laundering authority between them. A model may eventually classify a natural-language request or propose evidence needs, but model intent classification is not execution authority.

Gate 7.5 also proved that non-empty vector retrieval is not evidence of answerability, while Gate 7.7 proved that successful retrieval is not the same as correct citation attribution or semantic groundedness. The hybrid router therefore cannot use vector similarity, model confidence, or provider success as permission to execute or answer.

## Decision

Gate 8.1 introduces an offline, provider-independent routing contract with explicit typed evidence needs:

```text
vulnerability_facts
risk_priority
remediation_guidance
runtime_exposure
```

The deterministic v1 mapping is:

```text
vulnerability_facts and/or risk_priority
 -> STRUCTURED
 -> required evidence: STRUCTURED

remediation_guidance
 -> SEMANTIC
 -> required evidence: SEMANTIC

at least one structured need + remediation_guidance
 -> HYBRID
 -> required evidence: STRUCTURED + SEMANTIC
 -> completeness: ALL_REQUIRED

runtime_exposure, alone or mixed with any other need
 -> UNSUPPORTED
 -> no downstream evidence execution authorized
```

All supported v1 routes use `ALL_REQUIRED`. Phase 8 does not silently degrade a hybrid request into whichever authority happened to return evidence first.

`runtime_exposure` is a recognized but unavailable authority need. It remains `UNSUPPORTED` until OpsLens has actual runtime evidence in the later Amazon Inspector phase. Repository risk must not be promoted into runtime exposure.

The route decision also carries:

- explicit required evidence classes;
- completeness semantics;
- stable reason codes;
- canonical evidence-need ordering;
- a versioned, content-addressed SHA-256 identity.

No SQL, Athena expression, Bedrock Knowledge Base identifier, S3 Vectors query, model identifier, prompt, retrieval DSL, or provider transport belongs in the route domain contract.

## Authority boundary

A future classifier or planner may propose:

```text
EvidenceNeed[]
```

Deterministic code must validate that proposal and produce the authoritative route decision before any:

```text
Athena query
Bedrock Retrieve
S3 Vectors query
model invocation
hybrid synthesis
```

Therefore:

> **intent classification != execution authority**

and the permanent invariant remains:

> **Agents reason. Code verifies evidence.**

## Why `ALL_REQUIRED` for HYBRID v1

A true hybrid request means the user asked for information owned by different authority classes. Allowing best-effort fallback would create two unsafe substitutions:

1. semantic retrieval could be mistaken for structured vulnerability/risk truth;
2. structured rows could be presented as if they contained explanatory/remediation guidance.

The initial policy favors explicit incompleteness over a superficially complete answer. Partial-result semantics can be considered later only with a separate typed contract and evaluation evidence.

## Alternatives considered

### Model-controlled routing

Rejected. A model may classify intent, but permitting model output to directly authorize Athena, vector retrieval, or synthesis would collapse the deterministic authority boundary.

### Keyword/regex routing over raw user text

Rejected as the authority contract. Heuristics may later help produce an evidence-needs proposal, but raw-text matching is not a durable execution authority and is difficult to version as the supported question surface expands.

### One generic RAG route

Rejected. Structured KEV/EPSS/CVSS/applicability/risk facts already have deterministic authorities and must not be re-derived from vector similarity or synthesis.

### Best-effort hybrid fallback

Rejected for v1. It would silently change the meaning of a user request when one required evidence class is missing.

### Provider-specific route objects

Rejected. Provider identifiers and execution DSLs belong in adapters and later execution planning, not in the domain authority contract.

## Security and failure behavior

Unknown, malformed, empty, duplicate, or internally inconsistent semantics fail closed. A known `runtime_exposure` need produces `UNSUPPORTED` and authorizes no downstream evidence class.

This prevents:

- semantic-to-structured authority laundering;
- repository-risk-to-runtime-exposure laundering;
- silent model fallback for unknown semantics;
- partial execution of an unsupported mixed request;
- provider configuration from becoming business authority.

## IAM and cost

Gate 8.1 is offline-only. It creates no AWS resource, adds no IAM permission, and makes no paid AWS call.

The route contract is deliberately frozen before later execution identities are introduced so least-privilege permissions can be derived from explicit routes rather than broad runtime capability.

## Observability

The content-addressed `decision_id`, route, reason code, required evidence classes, and completeness semantics are suitable low-cardinality audit/evaluation fields. Raw user text is not required to identify the route decision contract.

## AIP-C01 relevance

This decision reinforces retrieval architecture, safe tool/service authorization, deterministic validation, grounding boundaries, and evaluation-oriented design. OpsLens uses the term **Hybrid Retrieval** here to mean hybrid **evidence routing**. It does **not** yet mean keyword + vector hybrid search; that search technique remains a measured optimization candidate for Gate 8.5 rather than a Gate 8.1 requirement.

## Consequences

Positive:

- authority boundaries are testable offline before provider integration;
- later AWS permissions and execution adapters can be constrained by a stable decision object;
- hybrid completeness is explicit rather than implicit;
- route behavior is deterministic and content-addressed;
- Phase 7 baselines remain untouched.

Trade-offs:

- the v1 surface is intentionally small;
- runtime-exposure questions remain unsupported;
- no partial hybrid response is allowed yet;
- natural-language classification is not implemented in this gate.

## Follow-up

Gate 8.2 may construct a deterministic hybrid evidence envelope only from evidence already produced and admitted by the authorities authorized here. It must preserve structured and semantic provenance as separate classes.
