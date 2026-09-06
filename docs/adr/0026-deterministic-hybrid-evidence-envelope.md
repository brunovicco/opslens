# ADR 0026 — Deterministic Hybrid Evidence Envelope

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 8 — Hybrid Retrieval, Gate 8.2

## Context

Gate 8.1 froze which evidence classes may execute for each recognized evidence need. It deliberately did not define how already-admitted evidence from those authorities can coexist in one downstream object.

Phase 8 now needs a composition boundary that can represent:

```text
structured vulnerability/risk evidence
+
semantic remediation evidence
```

without turning the combination into a new undifferentiated truth source.

The main risk is **authority laundering**. A generic list of evidence objects could make semantic similarity look equivalent to deterministic vulnerability applicability or risk-policy output. Class-level completeness alone is also insufficient: a route that requests both `vulnerability_facts` and `risk_priority` cannot be considered complete merely because one arbitrary structured row exists.

## Decision

Gate 8.2 introduces a provider-independent `hybrid-evidence:v1` contract.

The envelope is built only after a valid Gate 8.1 `HybridRouteDecision` exists:

```text
HybridRouteDecision
 + StructuredEvidenceRow[]
 + SemanticEvidenceChunk[]
 -> HybridEvidenceEnvelope
```

The envelope carries separate collections rather than one generic evidence list:

```text
HybridEvidenceEnvelope
  authority_decision
  structured_evidence[]
  semantic_evidence[]
  provenance_by_class
  satisfied_evidence_needs
  completeness
  envelope_id
```

A successful v1 envelope is complete by construction. Missing required evidence does not create a partial envelope.

## Need-level completeness

Gate 8.1 authorizes evidence classes, but Gate 8.2 also verifies the exact evidence needs represented by admitted evidence.

For example:

```text
request:
  vulnerability_facts
  risk_priority

route:
  STRUCTURED
```

One vulnerability row is not sufficient merely because the required class `STRUCTURED` is present. The envelope requires evidence for both requested needs.

Therefore v1 validates:

```text
satisfied_evidence_needs == authority_decision.evidence_needs
```

No extra need may be smuggled into the envelope either.

## Structured authority provenance

Every structured row declares the deterministic authority that produced the already-validated source artifact and binds that source to an exact artifact ID and SHA-256 digest.

The initial v1 mapping is intentionally narrow:

```text
vulnerability_facts
 -> repository_analysis
 -> semantic_query

risk_priority
 -> risk_policy
```

`semantic_query` here names the existing Phase 6 bounded structured-query subsystem. It does **not** mean semantic/vector evidence. Its admitted result remains structured evidence because deterministic query validation and SQL compilation own the factual authority boundary.

A Risk Policy row cannot be relabeled as vulnerability applicability, and repository-analysis evidence cannot be relabeled as `risk_priority`.

Structured row field names are canonically ordered before hashing. Values are restricted to stable JSON scalar types; non-finite floats and arbitrary nested objects are rejected.

## Semantic evidence projection

Semantic evidence is projected from an already-admitted Phase 7 `RetrievalEvidence` operation. Gate 8.2 preserves:

- retrieval ID;
- rank;
- chunk/document/source identity;
- canonical URI;
- document and chunk content hashes;
- exact text;
- source type;
- optional provider relevance score;
- title and section path.

The provider relevance score remains provenance/measurement evidence only. It does not establish answerability, applicability, risk, or authority.

For v1, one semantic evidence set must originate from exactly one retrieval operation and keep contiguous ranks beginning at 1. Combining multiple unrelated retrieval operations is deferred until that behavior has an explicit versioned contract.

## Content-addressed identity

Structured rows and semantic chunks each receive deterministic content identities. The envelope identity is derived from:

```text
hybrid-evidence contract version
authority decision ID
completeness semantics
satisfied evidence needs
structured evidence IDs
semantic evidence IDs
```

Canonical ordering makes equivalent evidence sets produce the same envelope identity regardless of caller ordering.

The envelope ID is evidence identity, not semantic truth or model confidence.

## Failure behavior

Gate 8.2 fails closed when:

- the authority decision is malformed or `UNSUPPORTED`;
- a required evidence class is empty;
- evidence appears for a class the route did not authorize;
- one requested evidence need is missing;
- evidence appears for an unrequested need;
- structured authority does not match the evidence need;
- duplicate evidence IDs appear;
- semantic chunks mix retrieval operations;
- semantic ranks are non-contiguous;
- content/provenance hashes are malformed or inconsistent.

No best-effort fallback is introduced.

## Alternatives considered

### One generic `Evidence[]` collection

Rejected. It erases the distinction between deterministic structured authority and retrieved semantic evidence and makes downstream authority laundering easier.

### Class-level completeness only

Rejected. Multiple evidence needs can belong to the same class. Presence of one structured row cannot prove that every requested structured need is satisfied.

### Partial hybrid envelopes

Rejected for v1. Gate 8.1 froze `ALL_REQUIRED`; representing a partial envelope as a normal success object would weaken that contract. Partial-result semantics require a separate future decision and evaluation.

### Copy provider-specific response objects into the envelope

Rejected. AWS/provider transports and DSLs are not business authority. Gate 8.2 projects only the provenance needed by the provider-independent evidence contract.

### Merge multiple retrieval operations automatically

Rejected for v1. Unversioned merging can change rank meaning and provenance semantics. One admitted retrieval operation is the bounded semantic unit for this gate.

## Security consequences

The design keeps the permanent boundary:

> **Agents reason. Code verifies evidence.**

A model cannot manufacture an envelope, broaden an authorized route, substitute semantic evidence for structured truth, or silently downgrade an `ALL_REQUIRED` request.

The envelope is a deterministic composition artifact, not a new source of truth.

## IAM, AWS, and cost

Gate 8.2 is offline-only.

```text
AWS resources:     0
IAM changes:       0
Athena calls:      0
Bedrock calls:     0
S3 Vectors calls:  0
model calls:       0
```

No new runtime permission is justified by this gate.

## Observability

Useful low-cardinality audit/evaluation fields now include:

```text
authority decision ID
envelope ID
route
required evidence classes
satisfied evidence needs
structured evidence count
semantic evidence count
completeness
```

Exact evidence IDs provide drill-down provenance without changing authority semantics.

## AIP-C01 relevance

This decision exercises grounding and provenance design, deterministic validation around generative-AI evidence, fail-closed orchestration, evaluation-ready identities, and separation of deterministic data authority from semantic retrieval. It also illustrates why successful retrieval or a relevance score is not enough to authorize a factual answer.

## Consequences

Positive:

- structured and semantic evidence remain visibly separate;
- completeness is verified by need as well as by class;
- downstream synthesis can receive one bounded object without losing provenance;
- deterministic identities support reproducible evaluation and audit;
- no new AWS dependency is introduced.

Trade-offs:

- v1 does not represent partial success;
- v1 semantic evidence is limited to one retrieval operation;
- structured field projection is intentionally scalar and bounded;
- provider-specific metadata not required for provenance remains outside the envelope.

## Follow-up

Gate 8.3 must freeze hybrid evaluation fixtures and metrics against this contract before Gate 8.4 permits any hybrid model synthesis.
