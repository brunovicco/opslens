# Phase 7 — Gate 7.1: Corpus + Retrieval Contract

_Date: 2026-09-04_

## Purpose

Freeze the first provider-independent knowledge-retrieval authority boundary before creating any Bedrock Knowledge Base, vector index, embedding job, IAM role, or paid AWS retrieval/synthesis path.

Permanent rules:

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

The Phase 7 path is for explanatory/remediation knowledge. It does not become a second authority for NVD, CISA KEV, FIRST EPSS, CVSS, GHSA vulnerable-range applicability, repository package versions, or deterministic risk scores.

## Phase 6 dependency

Phase 6 is complete through PR #91 and squash merge commit:

```text
95db66e278059629ce6572b2950e9cca705c6498
```

The Phase 6 structured path remains separate:

```text
bounded factual question
 -> bounded Bedrock planner
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded read-only Athena
 -> structured result evidence
```

## Gate 7.1 architecture

```text
knowledge/remediation question
 -> RetrievalRequest
 -> future retrieval adapter
 -> RetrievedChunk[] + provenance
 -> RetrievalEvidence
 -> future deterministic context admission
 -> future bounded synthesis
 -> Citation[] projected from admitted evidence
```

No future provider response becomes authoritative merely because it was returned by semantic retrieval.

## Frozen contracts in this increment

### `KnowledgeDocument`

Represents one canonical explanatory/remediation source snapshot.

Required properties include:

- logical `document_id` and `source_id`;
- allowlisted `KnowledgeSourceType`;
- human-readable title;
- absolute HTTPS canonical provenance URI;
- exact canonical UTF-8 text;
- SHA-256 content identity verified against the text;
- optional explicit publication/update dates;
- optional typed vulnerability/ecosystem/package metadata.

The source identity and exact content identity are intentionally separate so that multiple observations of the same logical source can be distinguished if its contents change.

### `RetrievalRequest`

Bounded v1 authority:

```text
query:         non-blank, <= 1,000 characters
top_k:         integer 1..10
default top_k: 5
```

Typed optional scope is limited to allowlisted source types, vulnerability IDs, ecosystem, and package name. The domain exposes no arbitrary provider metadata/filter expression DSL.

### `RetrievedChunk`

Each admitted chunk carries:

- `chunk_id`;
- document/source identities;
- source type;
- canonical HTTPS provenance URI;
- exact document SHA-256 identity;
- exact chunk SHA-256 identity verified against chunk text;
- deterministic rank;
- optional finite provider relevance score;
- optional title/section path.

The provider relevance score is preserved as retrieval evidence only. It is not interpreted as a calibrated confidence probability.

### `RetrievalEvidence`

Represents one complete retrieval operation before synthesis.

It fails closed when:

- returned chunks exceed `request.top_k`;
- ranks are not contiguous and ordered from 1;
- chunk IDs are duplicated;
- request/chunk/backend values violate their typed contracts.

### `Citation`

Citation provenance is projected using `Citation.from_chunk(...)` from one already-admitted `RetrievedChunk`.

This prevents future model-authored URLs or source identifiers from becoming citation authority by themselves.

## Canonical metadata allowlist

Gate 7.1 freezes provider-independent canonical metadata only:

```text
source_id
source_type
canonical_uri
document_id
content_sha256
title
published_at
updated_at
vulnerability_ids
ecosystem
package_name
section_path
```

This is not yet the metadata projection for Bedrock, S3 Vectors, OpenSearch, or any other provider.

## Golden retrieval dataset

Fixture:

```text
tests/fixtures/knowledge_retrieval/golden_retrieval_v1.json
```

Current shape:

```text
10 cases
  8 positive remediation/documentation cases
  2 negative/out-of-scope cases
```

Each positive case records expected document and chunk identities so later real retrieval can compute metrics including:

```text
Recall@1
Recall@3
Recall@5
Recall@10
MRR
```

The fixture explicitly marks the corpus as:

```text
planned_for_gate_7_2
```

The IDs therefore freeze evaluation expectations without pretending that the canonical corpus has already been acquired or indexed.

## Current validation evidence

A local isolated validation of the new Phase 7 package and tests produced:

```text
Python:      3.13.5
pytest:      14 passed
compileall:  PASS
line length: 0 Python lines > 100 characters
```

The repository CI configuration now contains a dedicated `knowledge-retrieval-quality` job with:

```text
Ruff
Pyright strict
pytest
```

The current connector-authored commits do not automatically trigger GitHub Actions, so green Ruff/Pyright CI evidence remains pending and Gate 7.1 is not yet closed.

## AWS/resource evidence

For this Gate 7.1 increment:

```text
Bedrock Knowledge Base created: no
vector store/index created:      no
embedding model selected:        no
embedding job executed:          no
IAM role created:                no
paid AWS retrieval call:         no
paid AWS synthesis call:         no
```

## Gate 7.1 exit criteria

```text
[x] Phase 6 dependency confirmed
[x] corpus authority boundary encoded/documented
[x] provider-independent canonical metadata allowlist frozen
[x] KnowledgeDocument contract frozen
[x] RetrievalRequest contract frozen
[x] RetrievedChunk contract frozen
[x] RetrievalEvidence contract frozen
[x] Citation contract frozen
[x] malformed provenance/content identity fails closed
[x] golden retrieval fixture exists
[x] local unit tests pass
[x] no AWS resources or paid calls
[ ] Ruff quality gate demonstrated
[ ] Pyright strict quality gate demonstrated
[ ] final Gate 7.1 review/closeout
```

## Next action

Remain inside Gate 7.1.

Run the dedicated quality gate through GitHub Actions or an equivalent local environment with the repository's locked development dependencies. Resolve any findings, update this evidence, and only then decide whether Gate 7.2 may begin.
