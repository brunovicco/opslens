# Phase 8 Gate 8.1 — Offline Hybrid Routing + Authority Contract

_Date: 2026-09-06_

## Objective

Freeze the first provider-independent routing authority for Phase 8 before any new AWS call or hybrid synthesis.

Gate 8.1 answers only:

> Given already-admitted typed evidence needs, which evidence authority classes may execute?

It does **not** classify raw natural language and does not execute Athena, Bedrock Retrieve, S3 Vectors, or a model.

## Starting point

```text
main: 61fc092d920793da243a360119034b7c8e914704
issue: #104
branch: feat/phase8-hybrid-routing-contract
```

The branch was confirmed identical to `main` before implementation.

## Domain contract

```text
HybridRoutingRequest
  evidence_needs[]
  request_sha256

HybridRouteDecision
  route
  evidence_needs[]
  required_evidence_classes[]
  completeness
  reason
  identity_sha256
  decision_id
```

Frozen route outcomes:

```text
STRUCTURED
SEMANTIC
HYBRID
UNSUPPORTED
```

Frozen evidence classes:

```text
STRUCTURED
SEMANTIC
```

Frozen completeness semantics:

```text
ALL_REQUIRED
NOT_APPLICABLE
```

## V1 routing matrix

| Evidence needs | Route | Required evidence | Completeness | Reason |
|---|---|---|---|---|
| `vulnerability_facts` | `STRUCTURED` | `STRUCTURED` | `ALL_REQUIRED` | `structured_evidence_required` |
| `risk_priority` | `STRUCTURED` | `STRUCTURED` | `ALL_REQUIRED` | `structured_evidence_required` |
| both structured needs | `STRUCTURED` | `STRUCTURED` | `ALL_REQUIRED` | `structured_evidence_required` |
| `remediation_guidance` | `SEMANTIC` | `SEMANTIC` | `ALL_REQUIRED` | `semantic_evidence_required` |
| structured need + `remediation_guidance` | `HYBRID` | `STRUCTURED`, `SEMANTIC` | `ALL_REQUIRED` | `all_required_hybrid_evidence` |
| `runtime_exposure` | `UNSUPPORTED` | none | `NOT_APPLICABLE` | `runtime_exposure_authority_unavailable` |
| `runtime_exposure` mixed with another need | `UNSUPPORTED` | none | `NOT_APPLICABLE` | `runtime_exposure_authority_unavailable` |

## Fail-closed behavior

The contract rejects:

- an empty evidence-needs tuple;
- duplicate evidence needs;
- non-`EvidenceNeed` runtime values;
- route/evidence-class mismatches;
- semantic relabeling of structured truth;
- a hybrid decision that is not `ALL_REQUIRED`;
- an unsupported decision that authorizes downstream evidence execution;
- values that bypass `HybridRoutingRequest` admission.

A known out-of-authority request is different from malformed input:

```text
runtime_exposure
 -> valid recognized need
 -> UNSUPPORTED decision
 -> zero downstream evidence classes authorized

unknown string / malformed tuple
 -> validation error
 -> no route decision
```

## Deterministic identity

Evidence needs are canonically ordered before hashing. Equivalent proposals therefore produce the same request hash and route decision identity regardless of caller ordering.

The decision hash includes:

```text
contract version
canonical evidence needs
route
required evidence classes
completeness
reason code
```

This gives later evaluation/observability a stable identifier without using provider IDs or raw user text as authority.

## Boundary preserved

```text
future classifier/model proposal
 -> EvidenceNeed[]
 -> deterministic HybridRoutingRequest admission
 -> deterministic route_evidence_request
 -> authoritative HybridRouteDecision
 -> only then may a later gate execute authorized evidence paths
```

Therefore:

```text
intent classification != execution authority
```

## AWS / IAM / cost

Gate 8.1 is offline-only:

```text
AWS resources created: 0
IAM permissions added: 0
AWS API calls required by implementation: 0
model calls: 0
retrieval calls: 0
Athena calls: 0
```

## Quality gate

Dedicated CI slice added:

```text
Hybrid retrieval quality gates
 -> uv lock --check
 -> Ruff
 -> Pyright strict
 -> pytest tests/unit/hybrid_retrieval
```

Path filters include:

```text
src/opslens/hybrid_retrieval/**/*.py
tests/unit/hybrid_retrieval/**/*.py
tests/fixtures/hybrid_retrieval/**
```

CI evidence will be recorded after the draft PR runs against the final executable head.

## Architectural record

See ADR 0025 — Deterministic Hybrid Routing and Authority Contract.

## Next authorized work

Do not start Gate 8.2 until Gate 8.1 is CI-green, reviewed, ready, and squash-merged.

Gate 8.2 may then define a provider-independent hybrid evidence envelope that carries already-validated structured evidence and already-admitted semantic evidence without flattening them into one authority class.
