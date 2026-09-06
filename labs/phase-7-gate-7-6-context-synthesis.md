# Phase 7 — Gate 7.6: Deterministic Context Assembly + Synthesis

_Date: 2026-09-06_

## Status

**COMPLETE THROUGH 7.6f — REAL RETRIEVAL + SYNTHESIS SUCCESSFUL / 7.6g CLOSEOUT CI + MERGE PENDING.**

Gate 7.6 runs on PR #99 from merged Gate 7.5 main:

```text
b30af10a568cefa7175c253120499939f9ca18d8
```

Permanent boundary:

> **Retrieval candidates are evidence. Deterministic code decides what evidence may enter synthesis context and whether a model call is allowed.**

This extends:

> **Agents reason. Code verifies evidence.**

Retrieved text remains untrusted instruction content even after canonical source, content hash, byte count, and provenance admission.

## 7.6a — Deterministic context assembly — COMPLETE

```text
RetrievalEvidence
 -> deterministic contiguous rank-prefix assembly
 -> whole ContextEvidenceBlock[]
 -> AssembledContext
```

Frozen bounds:

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16,384 UTF-8 bytes
```

Rules:

- only Gate 7.4-admitted `RetrievedChunk` evidence may enter context;
- whole chunks only; never truncate source evidence;
- preserve one contiguous rank prefix from rank 1;
- stop at the first non-fitting chunk;
- never backfill with a smaller lower-ranked chunk;
- empty evidence fails closed;
- an oversized rank-1 chunk fails closed;
- provider relevance score is not projected into synthesis context;
- `context_sha256` binds query identity, limits, selected ranks, canonical provenance/content hashes, counts, and stop reason.

The byte limit is an application denial-of-wallet/input-growth bound, not a token estimate or model context-window claim.

## 7.6b — Synthesis contract + abstention — COMPLETE

Pre-model authority is deterministic:

```text
SUPPORTED
UNSUPPORTED
```

`UNSUPPORTED` cannot form a `SynthesisRequest` and therefore cannot invoke the model.

For an already-supported request the model can only propose:

```text
ANSWER
INSUFFICIENT_EVIDENCE
```

This keeps routing authority out of the model. `insufficient_evidence` is an allowed abstention inside an already-authorized explanatory/remediation domain.

Frozen application bounds:

```text
question:            <= 1,000 characters
model calls:         exactly 1 maximum
answer:              <= 4,000 characters
raw response parser: <= 65,536 characters
```

Prompt trust classes remain structurally distinct:

```text
trusted system instructions
untrusted user question
untrusted but source-verified retrieved evidence
```

The model output parser accepts exactly:

```json
{"decision":"answer","answer":"..."}
```

or:

```json
{"decision":"insufficient_evidence","answer":null}
```

Extra keys, malformed JSON, blank answers, invalid decisions, markdown wrappers, and answer text attached to `insufficient_evidence` fail closed.

## 7.6c — Bedrock model/API selection — COMPLETE

ADR 0023 freezes:

```text
Region:                  us-east-1
endpoint:                bedrock-runtime
API:                     Converse
streaming:               no
provider/model:          Anthropic Claude Haiku 4.5
US Geo profile:          us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:             0.0
provider maxTokens:      2,048
application model calls: 1 maximum
tools:                   none
structured output:       JSON Schema
```

The US Geographic profile may route from `us-east-1` to documented US destination Regions. Global inference is intentionally not selected.

Converse requires `bedrock:InvokeModel`. The non-streaming path does not require `bedrock:InvokeModelWithResponseStream`.

No deployed application runtime principal exists yet, so this gate does not create a synthetic runtime role merely for certification coverage.

Pricing baseline used for the measured call:

```text
Claude Haiku 4.5 US Geo input:  $1.10 / 1,000,000 tokens
Claude Haiku 4.5 US Geo output: $5.50 / 1,000,000 tokens
S3 Vectors request component:   $2.50 / 1,000,000 queries
```

## 7.6d — Offline provider adapter — COMPLETE

`BedrockKnowledgeSynthesizer` executes exactly one injected non-streaming `converse()` call and accepts only a complete `stopReason=end_turn` assistant text response that survives deterministic output parsing.

Successful runtime evidence is content-free and records:

```text
model/profile id
region
provider request id
stop reason
input/output/total tokens
cache read/write tokens
Bedrock latency
client elapsed
SDK retry count
request_sha256
prompt_sha256
context_sha256
```

Provider failures, missing/invalid metadata, non-end-turn stop reasons, wrong roles, multiple/non-text content blocks, malformed output, inconsistent token totals, timing drift, and request/evidence identity mismatch fail closed.

`insufficient_evidence` remains a valid synthesis outcome rather than a provider error.

## 7.6e — First bounded real retrieval + synthesis — SUCCESS

The first supported run was executed exactly once against the existing dev Knowledge Base and the frozen Claude Haiku 4.5 US Geo profile.

Execution result:

```text
exit code:              0
execution_complete:     true
authority_decision:     supported
retrieval_invoked:      true
model_invoked:          true
region:                 us-east-1
```

### Retrieval

```text
knowledge base:         BTVJ2PBR2A
requested top_k:        5
returned/admitted:      5
provider request id:    4835c5d0-4a4e-4f47-9610-482ab6ec1103
client elapsed:         1463 ms
SDK retries:            0
rank 1 chunk:           knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:           0.8649594783782959
```

All five results passed the existing checked-corpus location/hash/byte-count/metadata admission boundary.

### Context assembly

```text
retrieved chunks:       5
selected chunks:        5
selected UTF-8 bytes:   5828
stop reason:            exhausted_retrieval
context sha256:         bba245b46a1f8cbb2c42010b61e1ef397b2cde9c92fc0439ee0dc03197788445
```

All five retrieved chunks fit under the 16,384-byte application ceiling. The rank prefix was preserved exactly and no provider relevance score entered the synthesis context contract.

### Synthesis

```text
model/profile:
  us.anthropic.claude-haiku-4-5-20251001-v1:0

decision:               answer
answer characters:      1751
stop reason:            end_turn
input tokens:           2671
output tokens:          491
total tokens:           3162
cache read tokens:      0
cache write tokens:     0
Bedrock latency:        7217 ms
client elapsed:         7983 ms
SDK retries:            0
provider request id:    eee2a118-f806-40d5-8f53-57c88da8ad16
request sha256:         b25eb13aa908d7aa7cb614d4e0e2123aeb68fc0648d4394e16bdb450b7d44d35
prompt sha256:          4e6aad47a03946fad02356198f95e094256cceb1807e4c78fe249e3f9934bbc2
answer sha256:          eee35e23c7fa58502f871e3fb7df8e48664c7dd8350073fc3a58feba7bbf987a
result sha256:          675d661d73ac3844a2e4f53c24f2b919ab909953ee0af29c5912409d93bf792f
```

The response stayed below the 4,000-character application limit and the 2,048-token provider output ceiling.

No replay was performed after the successful first call.

## 7.6f — Quality, latency, token, and cost analysis — COMPLETE

### Manual single-run quality review

The question asks how to make pip dependency installation more secure using hashes. The highest-ranked evidence is the exact pinned PyPA `Hash-checking Mode` slice from:

```text
upstream repository: pypa/pip
commit:              173eb9b290e2924f0cd42b7714645b38b4df2e81
path:                docs/html/topics/secure-installs.md
chunk:               knowledge-chunk:pypa-secure-installs:hashes:v1
```

A manual comparison against that exact frozen source found the generated answer's seven substantive guidance items supported by the admitted rank-1 chunk:

- per-requirement `--hash` usage;
- SHA-256 recommendation and exclusion of weaker algorithms in hash-checking mode;
- hashes for all requirements and all dependencies;
- pinning through URL/path/`==`;
- `--require-hashes` enforcement;
- multiple hashes per package;
- pip 26.2+ `--no-require-hashes` selective-hashing compatibility escape hatch.

No structured vulnerability, repository exposure, KEV, EPSS, CVSS, or Risk Policy claim was introduced.

One quality nuance is intentionally retained rather than post-hoc tuned: `--no-require-hashes` weakens global hash enforcement and should be understood as an explicit compatibility exception, not the default secure posture. The model labeled it optional, and the underlying pinned PyPA source explicitly describes that behavior.

This is a **manual one-answer supportedness review**, not a groundedness benchmark. Gate 7.7 remains responsible for deterministic citations and measured citation correctness/coverage plus unsupported-claim evaluation.

### Latency

Measured components:

```text
retrieval client elapsed:  1463 ms
Bedrock model latency:     7217 ms
synthesis client elapsed:  7983 ms
```

A simple sequential sum of the two client-side stages is `9446 ms`; this is a derived stage sum, not a separately measured outer end-to-end stopwatch.

The first synthesis used a structured-output grammar. AWS documents possible additional first-use grammar compilation latency, so this first-run latency is preserved as observed evidence and is not represented as warmed steady-state performance. No extra call was made merely to improve the latency number.

### Observed model cost

At the frozen rate baseline:

```text
input:  2671 * $1.10 / 1,000,000 = $0.0029381
output:  491 * $5.50 / 1,000,000 = $0.0027005
model total:                         $0.0056386
```

One populated-index S3 Vectors request contributes exactly:

```text
1 * $2.50 / 1,000,000 = $0.0000025
```

Directly computable first-run components therefore total:

```text
$0.0056411
```

This is **not** presented as the complete bill. Bedrock Knowledge Base `Retrieve` does not expose the exact Titan query-embedding units or S3 Vectors data-processed/data-returned billable units needed to reconstruct those components. OpsLens does not fabricate them.

### Retry and failure evidence

```text
retrieval SDK retries: 0
synthesis SDK retries: 0
provider failures:     0
output admission:      success
```

The offline adapter suite already preserves provider, response-contract, stop-reason, output-contract, and timing failure categories separately. A successful first real call does not eliminate those failure paths.

## CI evidence

Implementation checkpoints:

```text
Python CI #245: SUCCESS — context assembly
Python CI #252: SUCCESS — synthesis contract
Python CI #256: SUCCESS — Bedrock request selection
Python CI #260: SUCCESS — offline synthesis adapter
Python CI #263: SUCCESS — real-run CLI
Python CI #264: SUCCESS — pre-run documentation head
```

The 7.6g documentation closeout commit must receive its own green final CI before PR #99 is marked ready and squash-merged.

## Gate checklist

```text
[x] 7.6a deterministic context assembly
[x] 7.6b synthesis request/output + abstention
[x] 7.6c Bedrock API/model/IAM/cost decision
[x] 7.6d offline provider adapter + failure tests
[x] 7.6e first supported real retrieval + synthesis run
[x] 7.6f quality/latency/token/cost analysis
[ ] 7.6g synchronized docs/state + final CI
[ ] mark PR #99 ready
[ ] squash merge against validated head SHA
```

## Next after Gate 7.6 merge

Gate 7.7 adds deterministic citation projection and groundedness evaluation. It must not trust model-authored URLs or source IDs and must not retroactively tune Gate 7.6 against this single successful answer.

References:

- ADR 0023: `../docs/adr/0023-bounded-bedrock-knowledge-synthesis.md`
- frozen source registry: `../knowledge/corpus/v1/source_registry.json`
- frozen corpus spec: `../knowledge/corpus/v1/corpus_spec.json`
