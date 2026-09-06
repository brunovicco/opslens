# Phase 7 — Gate 7.6: Deterministic Context Assembly + Synthesis

_Date: 2026-09-06_

## Status

**IN PROGRESS — 7.6a DETERMINISTIC CONTEXT ASSEMBLY COMPLETE / SYNTHESIS CONTRACT NEXT.**

Gate 7.5 was squash-merged to `main` at:

```text
b30af10a568cefa7175c253120499939f9ca18d8
```

Gate 7.6 begins from the measured real retrieval baseline rather than coupling generation directly to provider output.

## Permanent boundary

> Retrieval candidates are evidence. Deterministic code decides what evidence may enter synthesis context.

This extends the project rule:

> **Agents reason. Code verifies evidence.**

Retrieved text remains untrusted instruction content even after its source identity, hash, bytes, and canonical provenance have been admitted.

## Gate 7.5 evidence that constrains this design

Frozen real baseline:

```text
10 real Retrieve calls
8 positive cases
2 negative/out-of-authority cases
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
```

Both negative cases returned nine nearest-neighbor candidates, with rank-1 scores near `0.689`. Those values overlap scores observed for legitimate positive evidence.

Therefore Gate 7.6 does **not** use provider relevance score as:

- confidence probability;
- authority decision;
- route decision;
- context-admission threshold.

No global score threshold is derived from the frozen Gate 7.5 test set.

## 7.6a goal

Freeze a provider-independent, deterministic boundary between already-admitted `RetrievalEvidence` and any future synthesis provider request.

```text
RetrievalEvidence
 -> deterministic rank-prefix context assembly
 -> ContextEvidenceBlock[]
 -> AssembledContext
 -> future bounded synthesis request
```

No Bedrock generation call is part of 7.6a.

## Frozen v1 context limits

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16,384 UTF-8 bytes
```

The byte ceiling is an application-level denial-of-wallet/input-growth guardrail. It is deliberately **not** described as a token limit or a model context-window limit.

Model-specific input tokens, output tokens, prompt-format overhead, inference API, timeout, retry, and pricing limits remain a later 7.6 decision.

## Selection algorithm

Context assembly uses a whole-chunk contiguous retrieval-rank prefix.

For ranked admitted chunks `1..N`:

1. start with an empty context;
2. stop if `max_chunks` has already been reached;
3. project the next whole admitted chunk into a `ContextEvidenceBlock`;
4. stop if adding that entire block would exceed `max_utf8_bytes`;
5. otherwise admit it and continue.

Consequences:

- chunks are never split or truncated;
- retrieval order is never changed;
- a lower-ranked smaller chunk cannot bypass a higher-ranked chunk that does not fit;
- empty retrieval fails closed;
- if rank 1 alone cannot fit, assembly fails closed rather than truncating it;
- no provider/model call occurs during assembly.

The no-backfill rule is intentional: reordering or skipping based on size would create a second ranking policy that Gate 7.5 did not evaluate.

## ContextEvidenceBlock

Each selected block preserves canonical admitted evidence:

```text
retrieval_rank
chunk_id
document_id
source_id
source_type
canonical_uri
document_content_sha256
chunk_content_sha256
exact admitted text
UTF-8 byte count
title
section_path
```

Provider `relevance_score` is intentionally absent.

This prevents a non-calibrated similarity score from becoming an implicit synthesis instruction or confidence signal merely because it was included in the model context contract.

## AssembledContext identity

Operational context evidence contains:

```text
retrieval_id
query_sha256
limits
selected block evidence
retrieved_chunk_count
total selected UTF-8 bytes
stop_reason
context_sha256
```

The raw user query is not copied into the operational context identity; its SHA-256 is used instead.

`context_sha256` is calculated deterministically from canonical JSON containing:

- retrieval identity;
- query SHA-256;
- limits;
- selected rank/provenance/content-hash evidence;
- retrieved result count;
- deterministic stop reason.

The fingerprint does not need to duplicate retrieved source text because each selected block already carries and validates its exact content SHA-256.

## Stop reasons

```text
exhausted_retrieval
max_chunks
max_utf8_bytes
```

These are deterministic context-assembly evidence, not provider/model stop reasons.

## Fail-closed behavior

7.6a rejects:

```text
invalid context bounds
wrong runtime contract types
empty retrieval evidence
rank-1 chunk larger than context byte budget
non-contiguous selected rank prefix
duplicate/invalid block structures inherited from retrieval evidence
content hash mismatch
UTF-8 byte-count mismatch
context total mismatch
context fingerprint mismatch
inconsistent stop-reason shape
```

Gate 7.4 remains responsible for provider-to-canonical retrieval admission before this layer runs.

## Security boundary

Future synthesis must keep at least three logical channels distinct:

```text
system/developer instructions      trusted control
user question                      untrusted user input
admitted retrieved source text     untrusted evidence
```

Admission proves source/content identity. It does **not** make retrieved prose trusted instructions.

7.6a adds no IAM permissions, AWS resources, network calls, provider SDK calls, or model authority.

## Cost / observability impact

7.6a is pure local deterministic code:

```text
AWS calls:              0
new AWS resources:      0
new IAM permissions:    0
model tokens:           0
provider cost:          $0
```

Observable deterministic evidence available for later synthesis telemetry includes:

```text
context_sha256
query_sha256
selected block count
retrieved chunk count
selected UTF-8 byte count
stop reason
```

## Tests

Offline tests cover:

- default and maximum bounds;
- exact whole-block projection;
- provider score exclusion;
- contiguous rank-prefix selection;
- byte-budget stop without lower-rank backfill;
- chunk-count stop;
- empty retrieval failure;
- oversized rank-1 failure;
- score changes not affecting context identity;
- byte-total tampering rejection;
- context-fingerprint tampering rejection.

CI history:

```text
Python CI #243: FAIL — Ruff line-length only; corrected without semantic change
Python CI #244: FAIL — Pyright flagged direct isinstance checks on strongly typed values
Python CI #245: SUCCESS
  Ruff:             PASS
  Pyright strict:   PASS
  pytest:            PASS
  regressions:      PASS
```

The Pyright correction preserved runtime fail-closed checking through an `object`-typed helper rather than removing validation to satisfy static analysis. This mirrors the existing Gate 7.1 domain pattern.

## 7.6 increment plan

```text
7.6a deterministic context assembly contract                 COMPLETE
7.6b synthesis request/output + abstention contract           NEXT
7.6c Bedrock model/API selection + official pricing/IAM      PENDING
7.6d offline provider adapter tests                           PENDING
7.6e bounded real synthesis success/failure evidence          PENDING
7.6f quality/latency/token/cost analysis                      PENDING
7.6g docs/state closeout + final CI + squash merge            PENDING
```

## Next authorized step

Implement **7.6b offline first** before invoking Bedrock:

1. freeze the synthesis input/output contract;
2. define explicit insufficient/unsupported-evidence behavior;
3. define how untrusted context blocks are serialized separately from trusted instructions;
4. freeze output-length and call-count authority at the application contract level;
5. only then select the concrete Bedrock runtime API/model using current official AWS documentation.

Do not add real AWS synthesis calls merely to exercise a certification service.
