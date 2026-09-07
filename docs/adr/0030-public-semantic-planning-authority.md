# ADR 0030 — Public Semantic Planning Is a Proposal Boundary, Not Product Authority

- Status: Accepted
- Date: 2026-09-07
- Phase: 9 — Public Analyze Your Repository
- Gate: 9.3 — Bounded Semantic Planning + Admission Handoff

## Context

Gate 9.1 froze the public operation as a narrow request to analyze one public GitHub repository. The request intentionally contains no arbitrary natural-language question, model selection, provider selection, tool choice, SQL, or user-defined analysis mode.

Gate 9.2 then binds that admitted request to source-confirmed public repository metadata, an immutable commit/tree snapshot, exact-commit inert `uv.lock` evidence, deterministic parsing, and Phase 3 PyPI normalization. The result is `PublicRepositoryEvidenceExecution`.

Phase 8 already owns deterministic hybrid route authority through `hybrid-routing:v1`. Its supported evidence needs are typed and its route decision is deterministic.

Adding a semantic planner at the public boundary creates a risk: if the model can decide what the fixed product operation means, the planner silently becomes product-scope and execution authority. That would violate the existing boundary:

> **Intent classification != execution authority.**

It would also allow a planner to omit required analysis, request unsupported runtime exposure, or broaden downstream execution without a versioned product-contract change.

## Decision

Gate 9.3 introduces a semantic planner only as a **bounded proposal boundary**.

The deterministic public-analysis v1 policy owns the mandatory evidence scope:

```text
vulnerability_facts
risk_priority
remediation_guidance
```

The planner may propose evidence needs, but deterministic admission requires exactly that complete set before any handoff can exist.

The planner cannot authorize:

- repository identity or visibility;
- dependency identity;
- vulnerability applicability;
- CVE/GHSA/NVD reconciliation;
- KEV, EPSS, CVSS, or Risk Policy facts;
- runtime exposure;
- route selection;
- SQL generation or Athena execution;
- retrieval evidence admission;
- model/provider/tool selection;
- downstream execution.

The existing Phase 8 `route_evidence_request` remains route authority. After deterministic public-v1 admission, the exact required evidence set must resolve to:

```text
route: HYBRID
completeness: ALL_REQUIRED
required classes: STRUCTURED + SEMANTIC
```

Any disagreement fails closed.

## Planner input boundary

The planner receives a serialized, bounded, metadata-only `PublicSemanticPlanningRequest`.

It may contain deterministic binding metadata such as:

- source execution ID and SHA-256;
- public request ID;
- immutable snapshot ID;
- immutable file evidence ID;
- bounded dependency accounting;
- contract/operation identifiers;
- the allowed v1 evidence-need catalog.

It does **not** contain:

- the raw user `repository_url`;
- `uv.lock` bytes;
- dependency names or versions;
- arbitrary repository text;
- repository instructions/prompts;
- executable repository content;
- credentials or secrets;
- SQL;
- provider/model selection.

The immutable file evidence ID may encode the allowlisted path name as provenance. This is identity metadata, not repository content.

This boundary reduces indirect-prompt-injection surface: third-party repository content cannot become planner control input in Gate 9.3.

## Output admission

Planner output is untrusted bytes and is admitted through a strict JSON contract:

```text
planning_request_sha256
evidence_needs
```

Admission rejects:

- invalid UTF-8 or JSON;
- non-object responses;
- duplicate or unknown fields;
- oversized output;
- request-hash mismatch/replay;
- empty evidence needs;
- unknown or duplicate evidence needs;
- omitted mandatory public-v1 needs;
- unsupported `runtime_exposure`;
- any source-execution rebinding;
- route/completeness/class disagreement.

No adaptive application retry or re-prompt occurs in this gate.

## Handoff

A successful proposal produces a content-addressed `PublicAnalysisAdmissionHandoff` that binds only exact identities:

```text
PublicRepositoryEvidenceExecution
PublicSemanticPlanningRequest
PublicSemanticPlanProposal
HybridRouteDecision
```

The handoff is not downstream evidence itself. Gate 9.3 stops before vulnerability enrichment, risk prioritization, retrieval, synthesis, Athena, or any public HTTP runtime.

## Why no real Bedrock call in Gate 9.3

The architecture must first prove the proposal/admission boundary independently of provider behavior.

Because the v1 public operation has a fixed deterministic required evidence scope, a real model invocation is not needed to establish product semantics or route authority. Gate 9.3 therefore uses an injected fake planner in CI and makes zero real Bedrock/model calls.

A later real planner adapter would require a separately bounded runtime decision and evidence. It must not silently broaden this ADR.

## Consequences

### Positive

- product semantics remain deterministic and versioned;
- a model cannot omit mandatory risk/remediation analysis;
- runtime exposure remains explicitly unsupported;
- Phase 8 remains the single route authority;
- repository content is isolated from the planner control plane;
- replay/source-rebinding failures are explicit;
- planner output can be evaluated independently from downstream execution;
- zero provider dependency is required to validate Gate 9.3.

### Trade-offs

The v1 planner is intentionally constrained and may appear redundant because deterministic admission requires one exact evidence-need set. That redundancy is acceptable: the gate validates the future proposal/admission architecture without sacrificing authority boundaries.

If OpsLens later supports arbitrary user questions or multiple public analysis modes, that is a new product contract. It must introduce a new versioned request/planning policy and evaluation evidence rather than widening `public-semantic-planning:v1` in place.

## Alternatives rejected

### Let the planner choose any Phase 8 evidence need

Rejected because it would allow omission of required analysis and unsupported runtime exposure to influence execution scope.

### Let the planner choose the route directly

Rejected because Phase 8 already has deterministic route authority and route selection must not be laundered through model output.

### Send repository content to the planner

Rejected for Gate 9.3 because it is unnecessary for the fixed v1 operation and would introduce avoidable indirect-prompt-injection and data-volume risk.

### Add a real Bedrock adapter immediately

Rejected for this gate because provider execution is not required to prove the authority contract and would mix contract design with runtime/provider validation.

## Security properties

```text
planner proposal != execution authority
public request identity != repository truth
repository evidence != runtime exposure
semantic planning != SQL authority
admission failure -> zero downstream execution
READ, NEVER EXECUTE third-party repository code
```

## AIP-C01 learning notes

This decision demonstrates several production GenAI principles relevant to AIP-C01:

- separate model reasoning/proposals from deterministic authorization;
- minimize model context to the data required for the task;
- treat model output as untrusted input requiring schema and semantic validation;
- preserve provenance and request binding across model boundaries;
- reuse deterministic routing/evidence contracts instead of duplicating authority inside prompts;
- introduce provider/runtime complexity only when the architecture has a measured need for it.
