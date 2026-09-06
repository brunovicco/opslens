# Phase 8 Gate 8.2 — Deterministic Hybrid Evidence Envelope

_Date: 2026-09-06_

## Objective

Freeze the provider-independent composition contract that carries already-admitted structured and semantic evidence without flattening their authority classes.

Gate 8.2 starts only after the Gate 8.1 routing authority is merged.

## Starting point

```text
main:   0110f48cebe04b049626197dc7cca0852c99123f
issue:  #107
branch: feat/phase8-hybrid-evidence-envelope
```

No AWS execution is required for this gate.

## Contract

```text
HybridRouteDecision
 + StructuredEvidenceRow[]
 + SemanticEvidenceChunk[]
 -> HybridEvidenceEnvelope
```

Contract version:

```text
hybrid-evidence:v1
```

The envelope exposes:

```text
authority_decision
structured_evidence[]
semantic_evidence[]
provenance_by_class
satisfied_evidence_needs
completeness
identity_sha256
envelope_id
```

## Structured evidence

Each structured row keeps:

```text
evidence_need
authority
source_artifact_id
source_artifact_sha256
row_key
canonical scalar fields[]
evidence_id
```

Initial authority mapping:

| Evidence need | Authorized structured authority |
|---|---|
| `vulnerability_facts` | `repository_analysis`, `semantic_query` |
| `risk_priority` | `risk_policy` |

The Phase 6 `semantic_query` subsystem is a structured factual authority after deterministic query validation/SQL compilation; its name does not make its output semantic/vector evidence.

Structured rows cannot satisfy `remediation_guidance` or `runtime_exposure`.

## Semantic evidence

Already-admitted Phase 7 `RetrievalEvidence` is projected rather than treated as structured truth.

Preserved fields include:

```text
retrieval ID
rank
chunk/document/source IDs
source type
canonical URI
document/chunk hashes
exact text
optional relevance score
title/section path
```

For v1:

```text
one envelope semantic set
 -> exactly one retrieval operation
 -> contiguous ranks starting at 1
```

The relevance score remains measurement/provenance only.

## Completeness

Class-level checks:

```text
required STRUCTURED -> non-empty structured evidence
required SEMANTIC   -> non-empty semantic evidence
unrequested class   -> must be empty
```

Need-level check:

```text
satisfied evidence needs
 ==
authority decision evidence needs
```

This prevents a request for two structured needs from being marked complete by one unrelated structured row.

All successful v1 envelopes inherit `ALL_REQUIRED`. `UNSUPPORTED` routes cannot produce an envelope.

## Deterministic identity

Canonical ordering is applied to:

- structured fields;
- structured evidence rows;
- semantic evidence chunks;
- evidence IDs within class provenance.

The envelope hash binds the exact Gate 8.1 authority decision to the exact admitted evidence IDs.

## Failure tests

The Gate 8.2 unit suite covers:

```text
structured-only success
semantic-only success
true hybrid success
multiple structured needs with missing need-level coverage
missing structured class
missing semantic class
unrequested structured class
unrequested semantic class
unrequested structured evidence need
unsupported route
structured authority laundering
structured remediation laundering
duplicate evidence
multiple semantic retrieval operations
non-contiguous semantic ranks
non-finite structured scalar
canonical ordering / stable identities
invalid authority object
semantic provenance projection
```

## AWS / IAM / cost

```text
AWS resources created: 0
IAM permissions added: 0
Athena calls:          0
Bedrock calls:         0
S3 Vectors calls:      0
model calls:           0
```

## CI

The existing path-filtered job is the explicit Gate 8.2 quality slice:

```text
Hybrid retrieval quality gates
 -> uv lock --check
 -> Ruff
 -> Pyright strict
 -> pytest tests/unit/hybrid_retrieval
```

No CI expansion is needed because the existing paths already cover all Gate 8.2 executable files and tests.

Final CI run/head will be recorded in the PR after validation.

## Architecture record

See:

```text
docs/adr/0026-deterministic-hybrid-evidence-envelope.md
```

## Next authorized work

Do not start Gate 8.3 until Gate 8.2 is CI-green, reviewed, ready, and squash-merged.

Gate 8.3 may then freeze hybrid evaluation fixtures and metrics before any Gate 8.4 model synthesis.
