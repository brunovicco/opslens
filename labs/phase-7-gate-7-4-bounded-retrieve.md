# Phase 7 — Gate 7.4: Real Bounded Retrieve Adapter

_Date: 2026-09-06_

## Status

**COMPLETE — REAL DIRECT RETRIEVE + FAIL-CLOSED PROVIDER EVIDENCE RECORDED.**

Gate 7.3 was squash-merged to `main` at:

```text
1337950ddb5948943bf361dba4c3cdc40dafaf2b
```

Real dev target:

```text
knowledge base id: BTVJ2PBR2A
data source id:    IEL1LBE026
source bucket:     opslens-dev-data-487757851499-us-east-1
vector count:      9
embedding model:   amazon.titan-embed-text-v2:0
vector store:      Amazon S3 Vectors
chunking:          NONE
```

## Goal

Implement and validate the first real retrieval-only runtime for Phase 7:

```text
RetrievalRequest
 -> bounded Bedrock Knowledge Base Retrieve
 -> raw provider response
 -> deterministic provenance/content admission
 -> RetrievedChunk[]
 -> RetrievalEvidence
```

This gate intentionally does **not** use `RetrieveAndGenerate` and does not synthesize an answer.

Permanent rule:

> Retrieval output is evidence, not deterministic truth.

## Frozen request boundary

OpsLens sends only:

```text
knowledgeBaseId: fixed configured KB
retrievalQuery.text: validated request.query
retrievalConfiguration.vectorSearchConfiguration.numberOfResults: request.top_k
```

Product bounds remain stricter than the provider:

```text
query:         non-blank, <= 1,000 chars
top_k:         1..10
default top_k: 5
provider DSL:  none
search mode:   semantic-only baseline
reranking:     disabled
synthesis:     absent
pagination:    not admitted in v1
```

Typed Gate 7.1 filters fail before the provider call until an explicit deterministic Bedrock-filter translation exists. They are never silently ignored.

## Deterministic checked-corpus authority

`application/retrieval_catalog.py` resolves provider-returned S3 content keys only against the checked Gate 7.2 manifest:

```text
returned S3 key
 -> content-addressed chunk SHA-256
 -> checked manifest chunk
 -> canonical chunk_id
 -> canonical document/source provenance
```

The provider does not own canonical `chunk_id`, `document_id`, source URL, source type, document hash, title, or section path.

Admission requires:

1. result count `<= request.top_k`;
2. text content only;
3. finite score when present;
4. exact expected S3 bucket and content-addressed key;
5. returned text SHA-256 equals the checked chunk hash;
6. returned UTF-8 byte count equals checked manifest evidence;
7. canonical metadata matches checked corpus authority;
8. unknown non-provider metadata is rejected;
9. Bedrock-reserved metadata remains non-authoritative and is cross-checked when it restates configured identity;
10. ranks are assigned deterministically from provider order;
11. `nextToken` and guardrail intervention fail closed in v1.

## Runtime provider compatibility finding

The first real call reached Bedrock successfully but local admission failed closed on `section_path`.

Observed provider representation:

```text
["\"Secure installs\"", "\"Hash-checking Mode\""]
```

Checked manifest authority:

```text
["Secure installs", "Hash-checking Mode"]
```

The adapter was changed only for this empirically observed representation. A section element is normalized only when it is a valid JSON-quoted string; the decoded value must still exactly equal the checked manifest value. Plain canonical strings remain valid, malformed quoting fails closed, and decoded mismatches fail closed.

The real response also exposed `x-amz-bedrock-kb-source-file-modality=TEXT`; it remains provider-reserved, non-authoritative evidence.

Regression tests cover the observed provider shape.

## Real admitted Retrieve — SUCCESS

Query SHA-256:

```text
5b398fe871d0cb51eaacb4f42a11b2ec402b5fdb4c523d2b7bca85e84dff3d0d
```

Runtime evidence:

```text
provider request id: e92d67f1-18fa-4537-8ff4-c2e02ab813e0
requested top_k:     5
returned/admitted:   5
client elapsed:      1257 ms
SDK retries:         0
```

Ranked admitted chunks:

```text
1  knowledge-chunk:pypa-secure-installs:hashes:v1                  0.8649594783782959
2  knowledge-chunk:pypa-dependency-management:transitive-review:v1 0.6561284065246582
3  knowledge-chunk:pypa-dependency-management:upgrade:v1           0.6397770941257477
4  knowledge-chunk:dependency-remediation-validation:isolation:v1  0.6031656265258789
5  knowledge-chunk:dependency-remediation-validation:post-change:v1 0.5829733312129974
```

The expected secure-install/hash-checking chunk was rank 1. This is single-query evidence only; aggregate Recall@K and MRR belong to Gate 7.5.

The CLI emitted no retrieved chunk text and no raw query text. It emitted only query hash, configured identifiers, provider request telemetry, ranked canonical identities/provenance, hashes, section paths, and provider relevance scores.

## Intentional real provider failure — SUCCESS

One read-only negative control used a deliberately nonexistent but syntactically valid Knowledge Base ID:

```text
knowledge base id: ZZZZZZZZZZ
top_k:             1
```

Observed result:

```text
ERROR: Bedrock Retrieve failed provider_code=ResourceNotFoundException
```

The adapter exposed only the safe provider error code. It did not copy provider response bodies, corpus text, or sensitive credential material into the operational error.

No AWS resource was mutated for this failure test.

## IAM boundary

Retrieval is a separate responsibility from Gate 7.3 ingestion/storage integration.

A future deployed OpsLens retrieval principal should receive only the exact Knowledge Base runtime authority required for retrieval and must not inherit merely for this path:

```text
s3:PutObject
s3vectors:PutVectors
s3vectors:DeleteVectors
bedrock:StartIngestionJob
iam:PassRole
Terraform/provisioning authority
```

No deployed application runtime principal exists yet. Creating an unattached role solely to satisfy this gate would add dead IAM surface, so the final attachment is deferred until a real compute/runtime principal exists. Temporary Identity Center/bootstrap credentials were used only as lab authority.

## Observability evidence

The runtime records content-free provider-neutral evidence:

```text
knowledge base reference
query SHA-256
requested top_k
returned/admitted count
ranked checked chunk identities
provider relevance scores
provider request id
SDK retry count
client elapsed milliseconds
safe failure category
```

Bedrock relevance scores are evidence, not calibrated probabilities.

## Cost evidence

Gate 7.4 incurred retrieval-only cost; no synthesis-model cost exists in this gate.

Observed real calls against the populated KB:

```text
1  first Retrieve: provider success, local section_path admission failed closed
1  diagnostic Retrieve: metadata-only inspection
1  admitted Retrieve: success
--------------------------------
3  real searches against the populated KB
```

The intentional nonexistent-KB failure is excluded from the S3 Vectors search estimate because it did not resolve to the configured vector index.

Current AWS S3 Vectors pricing for US East (N. Virginia) includes:

```text
query request fee:       $2.50 per 1,000,000 queries
first index tier:        $0.004 / TB of data processed
returned data:           first 512 KB per query free
```

For three populated-index searches, the request-fee component is therefore approximately:

```text
3 / 1,000,000 * $2.50 = $0.0000075
```

The additional processed-data component is negligible for this nine-vector laboratory index, but an exact total is intentionally not fabricated because the provider response does not expose billable query bytes or query-embedding token usage.

Knowledge Base retrieval also uses the configured embedding model to embed the query; model usage and S3 Vectors usage remain separate cost dimensions. Gate 7.5 will measure query volume/latency over the full fixture and report bounded assumptions rather than infer a billing total from incomplete telemetry.

Official pricing references:

- https://aws.amazon.com/s3/pricing/
- https://aws.amazon.com/bedrock/pricing/

## Quality evidence

Provider-compatibility fix head:

```text
c08234167ca3101fa144b59715c02909ccdc585d
Python CI #224: SUCCESS
Ruff:             PASS
Pyright strict:   PASS
pytest:            PASS
regressions:      PASS
```

The final documentation closeout commit must pass the same required PR checks before merge.

## Increment status

```text
7.4a  direct-Retrieve authority boundary                         COMPLETE
7.4b  deterministic checked-corpus S3-key lookup                COMPLETE
7.4c  Bedrock Retrieve adapter + fake-client admission tests    COMPLETE
7.4d  checked runtime manifest + bounded real CLI               COMPLETE
7.4e  least-privilege retrieval IAM review                      COMPLETE / ATTACHMENT DEFERRED
7.4f  real Retrieve success + intentional provider failure      COMPLETE
7.4g  observability/cost/docs closeout                           COMPLETE / FINAL CI PENDING
```

## Exit criteria

- [x] Gate 7.3 squash-merged before implementation;
- [x] direct `Retrieve`, not `RetrieveAndGenerate`, retained for the baseline;
- [x] semantic-only S3 Vectors baseline retained;
- [x] Gate 7.1 `top_k <= 10` retained;
- [x] checked-corpus lookup resolves provider S3 keys to canonical identity;
- [x] provider response admission is deterministic and fail-closed;
- [x] checked manifest loader avoids external corpus replay in the hot path;
- [x] pagination behavior explicitly bounded;
- [x] bounded CLI emits content-free operational evidence;
- [x] retrieval IAM responsibility boundary reviewed;
- [x] real provider metadata representation diagnosed and regression-tested;
- [x] real Retrieve succeeded against `BTVJ2PBR2A`;
- [x] real rank/score/request-id/retry/latency evidence recorded;
- [x] intentional real provider failure categorized safely;
- [x] retrieval cost assumptions recorded without fabricated billing precision;
- [x] documentation closeout prepared;
- [ ] final PR checks green;
- [ ] PR squash-merged.

## Handoff to Gate 7.5

Gate 7.5 owns aggregate retrieval quality evaluation over the frozen golden fixture:

```text
Recall@1
Recall@3
Recall@5
Recall@10
MRR
provenance/source correctness
latency distribution
retrieval-call count / bounded cost assumptions
```

Do not add synthesis, reranking, hybrid search, or arbitrary provider filters before the raw semantic baseline is measured.

## Official AWS references

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
- Amazon S3 pricing — S3 Vectors:
  https://aws.amazon.com/s3/pricing/
- Amazon Bedrock pricing:
  https://aws.amazon.com/bedrock/pricing/
