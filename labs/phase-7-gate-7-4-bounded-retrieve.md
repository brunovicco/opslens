# Phase 7 — Gate 7.4: Real Bounded Retrieve Adapter

_Date: 2026-09-06_

## Status

**IN PROGRESS — REAL RETRIEVE SUCCESS PROVEN / INTENTIONAL PROVIDER FAILURE + CLOSEOUT PENDING.**

Gate 7.3 was squash-merged to `main` at:

```text
1337950ddb5948943bf361dba4c3cdc40dafaf2b
```

The real dev Knowledge Base remains populated with exactly nine canonical chunks:

```text
knowledge base id: BTVJ2PBR2A
data source id:    IEL1LBE026
vector count:      9
embedding model:   amazon.titan-embed-text-v2:0
vector store:      Amazon S3 Vectors
chunking:          NONE
```

## Goal

Implement and validate the first real retrieval-only runtime for Phase 7.

```text
RetrievalRequest
 -> bounded Bedrock Knowledge Base Retrieve
 -> raw provider response
 -> deterministic provenance/content admission
 -> RetrievedChunk[]
 -> RetrievalEvidence
```

This gate does **not** generate answers and does **not** use `RetrieveAndGenerate`.

Permanent rule:

> Retrieval output is evidence, not deterministic truth.

## Why Retrieve directly

AWS provides a direct Knowledge Base `Retrieve` operation through the
`bedrock-agent-runtime` client. This keeps retrieval independently measurable from
synthesis, preserves the Gate 7.5 Recall@K/MRR baseline, and prevents generation
quality from hiding retrieval defects.

The OpsLens v1 request surface is intentionally smaller than the provider API:

```text
knowledgeBaseId: fixed configured KB
retrievalQuery.text: validated request.query
retrievalConfiguration.vectorSearchConfiguration.numberOfResults: request.top_k
```

No provider DSL is accepted from the caller. No search-type override, reranking,
implicit pagination, or generation configuration is sent.

## Search behavior

OpsLens uses Amazon S3 Vectors, so the v1 baseline is semantic retrieval only.
Do not send `overrideSearchType=HYBRID` and do not add reranking before Gate 7.5
measures the raw semantic baseline.

## Boundaries inherited from Gate 7.1

```text
query:         non-blank, <= 1,000 chars
top_k:         1..10
default top_k: 5
source_types:  typed allowlist only
provider DSL:  none
```

The AWS API allows a broader `numberOfResults` range. OpsLens intentionally retains
the stricter `1..10` product boundary already frozen in Gate 7.1.

The first real vertical slice is unfiltered. If a caller supplies any typed Gate 7.1
scope before a reviewed deterministic Bedrock-filter translation exists, the
application fails before the provider call rather than silently discarding scope.

## Deterministic checked-corpus catalog — 7.4b COMPLETE

`application/retrieval_catalog.py` derives runtime lookup authority only from the
checked Gate 7.2 manifest.

Published content keys remain content-addressed:

```text
knowledge/corpus/v1/bedrock/chunks/<chunk_content_sha256>.txt
```

The catalog resolves a returned S3 object key to checked chunk/document/source
identity and fails closed on malformed, unknown, out-of-prefix, or ambiguous keys.
Canonical content keys, chunk digests, and chunk IDs must be globally unique.

## Provider response admission — 7.4c COMPLETE

Admission requires:

1. result count <= `request.top_k`;
2. `TEXT` content only;
3. finite relevance score when present;
4. exact expected S3 bucket and content-addressed key;
5. key resolution to exactly one checked manifest chunk;
6. exact returned UTF-8 text SHA-256 and byte count;
7. required canonical metadata equality against checked corpus authority;
8. unknown non-provider metadata rejection;
9. Bedrock-reserved metadata treated as non-authoritative and cross-checked when it
   restates source/data-source identity;
10. deterministic rank assignment from provider response order.

Bedrock `documentId` and provider-owned chunk identifiers are not canonical OpsLens
identity.

`nextToken` and guardrail intervention fail closed in v1.

## Real provider metadata discrepancy discovered and bounded

The first real provider response failed closed before admission with:

```text
retrieval metadata field 'section_path' disagrees with checked corpus evidence
```

A metadata-only diagnostic call showed that Bedrock preserved `section_path` as a
list but returned each string as a JSON-quoted scalar. Example provider shape:

```json
{
  "section_path": [
    "\"Secure installs\"",
    "\"Hash-checking Mode\""
  ]
}
```

The checked manifest authority is:

```json
{
  "section_path": [
    "Secure installs",
    "Hash-checking Mode"
  ]
}
```

The adapter now normalizes **only** this empirically observed representation: a
quoted element must parse as one JSON string and the decoded value must then equal
the checked manifest value exactly. Plain canonical strings remain valid. Malformed
quoted strings, non-string values, extra nesting, or decoded mismatches still fail
closed.

The real response also exposed the Bedrock-reserved metadata field
`x-amz-bedrock-kb-source-file-modality=TEXT`; provider-reserved fields remain
non-authoritative.

Regression tests cover the observed quoted `section_path` representation.

## Runtime adapter and CLI — 7.4d COMPLETE

`adapters/bedrock_retrieval.py` sends exactly one direct semantic request and captures
provider request ID, retry attempts, client elapsed milliseconds, result count,
ranks, and provider relevance scores.

`cli/run_bedrock_retrieve.py` uses the checked local hash-only manifest rather than
replaying external sources in the retrieval hot path. Region is frozen to
`us-east-1`; `top_k` remains 1..10.

CLI output intentionally contains no retrieved source text and no raw query. It emits
query SHA-256, KB/request telemetry, ranked canonical IDs/hashes/provenance, and
provider relevance scores.

## First real admitted Retrieve — SUCCESS

Real query used:

```text
How can I make pip dependency installation more secure using hashes?
```

Operational evidence:

```text
knowledge base:         BTVJ2PBR2A
region:                 us-east-1
requested top_k:        5
returned/admitted:      5
provider request id:    e92d67f1-18fa-4537-8ff4-c2e02ab813e0
retrieval id:           bedrock-retrieve:e92d67f1-18fa-4537-8ff4-c2e02ab813e0
query sha256:           5b398fe871d0cb51eaacb4f42a11b2ec402b5fdb4c523d2b7bca85e84dff3d0d
client elapsed:         1257 ms
SDK retry attempts:     0
```

Ranked admitted evidence:

```text
1  knowledge-chunk:pypa-secure-installs:hashes:v1
   score 0.8649594783782959

2  knowledge-chunk:pypa-dependency-management:transitive-review:v1
   score 0.6561284065246582

3  knowledge-chunk:pypa-dependency-management:upgrade:v1
   score 0.6397770941257477

4  knowledge-chunk:dependency-remediation-validation:isolation:v1
   score 0.6031656265258789

5  knowledge-chunk:dependency-remediation-validation:post-change:v1
   score 0.5829733312129974
```

The query's directly relevant secure-installs/hash-checking chunk was rank 1. This is
useful single-query evidence only; aggregate retrieval quality conclusions belong to
Gate 7.5.

All five provider results passed deterministic S3 location, content hash, byte count,
metadata, and checked-corpus provenance admission.

## Runtime IAM boundary — 7.4e REVIEW COMPLETE / ATTACHMENT DEFERRED

Current AWS documentation allows `bedrock:Retrieve` to be scoped to the exact
Knowledge Base ARN:

```text
arn:aws:bedrock:us-east-1:487757851499:knowledge-base/BTVJ2PBR2A
```

A future deployed OpsLens retrieval runtime should receive only the retrieval
authority it needs and must not inherit source writes, vector writes/deletes,
ingestion, PassRole, or infrastructure provisioning permissions merely for retrieval.

No deployed application runtime principal exists yet. Creating an unattached role or
policy solely to satisfy this gate would add dead IAM surface, so the final runtime
attachment remains deferred until a real compute/runtime principal exists. The real
lab call uses temporary Identity Center/bootstrap authority and is not the production
runtime identity.

## Error behavior proven offline

Tests cover fail-closed behavior for unimplemented typed filters, pagination, result
breadth, non-text content, wrong bucket/key, content hash/byte-count mismatch,
canonical metadata mismatch, unknown non-provider metadata, reserved metadata
contradictions, non-finite scores, guardrail intervention, unknown provider fields,
and bounded provider error diagnostics.

## Quality evidence

The provider-compatibility regression head is:

```text
c08234167ca3101fa144b59715c02909ccdc585d
Python CI #224: SUCCESS
Ruff: PASS
Pyright strict: PASS
pytest: PASS
regressions: PASS
```

## Observability

Gate 7.4 records provider-neutral retrieval evidence sufficient for evaluation before
synthesis: knowledge base reference, requested top-k, returned count, ranked checked
chunk identities, provider relevance scores, client elapsed time, provider request
ID, SDK retry count, and bounded failure category.

Provider scores are evidence only and are not interpreted as calibrated confidence.

## Cost

Gate 7.4 adds retrieval-query cost only; no synthesis-model cost belongs here. The
closeout records the number of real provider calls and current published pricing
assumptions without fabricating an exact per-query charge not exposed in the response.

## Evaluation handoff

Gate 7.5 owns aggregate quality measurement over the frozen fixture:

```text
Recall@1
Recall@3
Recall@5
Recall@10
MRR
provenance/source correctness
latency distribution
retrieval cost
```

## Increment plan

```text
7.4a  freeze direct-Retrieve request/response authority boundary       COMPLETE
7.4b  deterministic checked-corpus S3-key lookup                      COMPLETE
7.4c  Bedrock Retrieve adapter + fake-client admission tests          COMPLETE
7.4d  bounded real CLI/runtime evidence                               COMPLETE
7.4e  least-privilege retrieval IAM boundary review                   COMPLETE / ATTACHMENT DEFERRED
7.4f  real Retrieve success + intentional real failure                SUCCESS PROVEN / FAILURE NEXT
7.4g  observability/cost/docs closeout + logical merge                PENDING
```

## Exit criteria

- [x] Gate 7.3 squash-merged before implementation;
- [x] current official AWS Retrieve documentation revalidated;
- [x] direct `Retrieve`, not `RetrieveAndGenerate`, retained for the baseline;
- [x] semantic-only S3 Vectors behavior recorded;
- [x] Gate 7.1 `top_k <= 10` retained;
- [x] checked-corpus lookup maps returned content keys to canonical identity;
- [x] Bedrock adapter implemented with no arbitrary provider DSL;
- [x] response provenance/content admission deterministic and fail-closed;
- [x] pagination behavior explicitly bounded;
- [x] checked manifest loader avoids external replay in the retrieval hot path;
- [x] bounded real CLI emits content-free operational evidence;
- [x] retrieval-only IAM boundary reviewed;
- [x] provider-specific `section_path` representation diagnosed and bounded;
- [x] real Retrieve call succeeds against `BTVJ2PBR2A`;
- [x] first real success latency/request/rank/score evidence recorded;
- [ ] one intentional real provider failure is diagnosed;
- [ ] retrieval cost assumptions recorded;
- [ ] project state/docs synchronized with real evidence;
- [ ] final PR CI green;
- [ ] PR squash-merged.

## Next authorized step

Run one intentional, read-only provider failure through the same bounded CLI using a
deliberately nonexistent but syntactically valid Knowledge Base ID. The purpose is to
prove real provider error categorization without changing IAM or AWS resources.

Do not repeat the failure call, mutate IAM, start synthesis, or begin Gate 7.5 until
that evidence is inspected.

## Official AWS references revalidated

- Amazon Bedrock — Retrieve data and generate AI responses with knowledge bases:
  https://docs.aws.amazon.com/bedrock/latest/userguide/kb-how-retrieval.html
- Amazon Bedrock — Test a knowledge base with Retrieve:
  https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-retrieve.html
- Amazon Bedrock — Configure and customize queries:
  https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-config.html
- Amazon Bedrock API — KnowledgeBaseRetrievalResult:
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_KnowledgeBaseRetrievalResult.html
- Botocore — `bedrock-agent-runtime.retrieve`:
  https://docs.aws.amazon.com/botocore/latest/reference/services/bedrock-agent-runtime/client/retrieve.html
- Amazon Bedrock — Knowledge Base runtime permissions:
  https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-prereq-permissions-general.html
