# OpsLens — Current State

_Last updated: 2026-09-06_

This document is the public implementation checkpoint for the OpsLens repository.

## Status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2    Threat Intelligence Data Lake                       COMPLETE
Phase 3    Vulnerability Correlation Engine                    COMPLETE
Phase 4    Repository Intelligence                             COMPLETE
Phase 5    Risk Prioritization Engine                          COMPLETE
Phase 6    Semantic Query Layer                                COMPLETE
Phase 7    Knowledge Retrieval with Bedrock                    IN PROGRESS
  Gate 7.1 Corpus + retrieval contract                         COMPLETE / MERGED
  Gate 7.2 Reproducible canonical corpus                       COMPLETE / MERGED
  Gate 7.3 Knowledge Base + vector infrastructure              COMPLETE / MERGED
  Gate 7.4 Real bounded Retrieve adapter                       COMPLETE / MERGED
  Gate 7.5 Retrieval evaluation                                COMPLETE / MERGED
  Gate 7.6 Context assembly + synthesis                        COMPLETE THROUGH 7.6f / PR #99
    7.6a deterministic context assembly                        COMPLETE
    7.6b synthesis request/output + abstention contract         COMPLETE
    7.6c Bedrock model/API/IAM/cost selection                  COMPLETE
    7.6d offline synthesis provider adapter                    COMPLETE
    7.6e first bounded real synthesis                          COMPLETE
    7.6f quality/latency/token/cost analysis                   COMPLETE
    7.6g docs closeout + final CI + squash merge               IN PROGRESS
```

Recent logical merges:

```text
Phase 6 / PR #91
95db66e278059629ce6572b2950e9cca705c6498

Gate 7.1 / PR #93
f2e3b72c31d0713707857bc0867a7f59e667b9dd

Gate 7.2 / PR #94
manifest sha256:
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418

Gate 7.3 / PR #95
1337950ddb5948943bf361dba4c3cdc40dafaf2b

Gate 7.4 / PR #97
7c25877e0ae9541a4f20b8537e4f77c88ee776a5

Gate 7.5 / PR #98
b30af10a568cefa7175c253120499939f9ca18d8
```

Gate 7.6 remains on PR #99 until its documentation-closeout head is CI-green and squash-merged.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

Deterministic authorities own package normalization, vulnerable-range matching, vulnerability applicability, CVE/GHSA/NVD reconciliation, KEV/EPSS/CVSS evidence, Risk Policy, canonical corpus construction, semantic-query validation/SQL compilation, retrieval evidence admission, context assembly, synthesis admission, citation projection, and execution/tool/cost enforcement.

LLMs may classify, plan, synthesize, explain, and route over validated evidence. They do not replace deterministic structured truth or grant themselves routing/tool/SQL authority.

## Implemented system

```text
Threat Intelligence Data Lake
 -> deterministic vulnerability correlation
 -> immutable Repository Intelligence
 -> deterministic Risk Policy v1
 -> bounded Semantic Query Layer

Controlled Knowledge Corpus
 -> customer-managed Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> direct bounded Retrieve
 -> deterministic checked-corpus admission
 -> retrieval evaluation
 -> deterministic bounded context assembly
 -> deterministic synthesis admission
 -> bounded Bedrock Converse synthesis
 -> typed SynthesisResult + runtime evidence
```

Citations and groundedness measurement remain Gate 7.7 rather than model-authored authority.

## Phase 7 runtime baseline

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
source bucket:         opslens-dev-data-487757851499-us-east-1
vector store:          Amazon S3 Vectors
embedding model:       amazon.titan-embed-text-v2:0
dimensions:            1024
vector type:           FLOAT32
distance:              cosine
chunking:              NONE
canonical chunks:      9
```

Canonical corpus manifest:

```text
98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Successful ingestion:

```text
job:                    WZRUGOFZPI
status:                 COMPLETE
documents scanned:      9
new documents indexed:  9
failed:                 0
skipped:                0
vectors materialized:   9
```

## Gate 7.4 — Direct bounded retrieval — COMPLETE / MERGED

Direct `bedrock-agent-runtime:Retrieve` remains separate from generation.

Real admitted baseline:

```text
requested top_k:        5
returned/admitted:      5
provider request id:    e92d67f1-18fa-4537-8ff4-c2e02ab813e0
client elapsed:         1257 ms
SDK retries:            0
rank 1:                 knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:           0.8649594783782959
```

Intentional provider failure through nonexistent KB safely produced `ResourceNotFoundException`.

## Gate 7.5 — Retrieval evaluation — COMPLETE / MERGED

Frozen dataset:

```text
knowledge-retrieval-golden:v1
10 cases
8 positive
2 negative/out-of-authority
```

Exactly one real `top_k=10` Retrieve request was executed for each case.

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Latency:

```text
min:   532 ms
max:   1728 ms
mean:  720.0 ms
p50:   616 ms
p95:   1728 ms
SDK retries: 0
```

Both negative/out-of-authority cases returned non-empty retrieval with rank-1 scores near `0.689`, overlapping legitimate evidence. Provider similarity score therefore remains evidence, not probability, authority, or a global answerability threshold.

## Gate 7.6 — Deterministic context assembly + synthesis — COMPLETE THROUGH 7.6f

### Context and authority

```text
RetrievalEvidence
 -> whole contiguous rank-prefix context assembly
 -> AssembledContext
 -> deterministic authority decision
 -> SynthesisRequest
 -> trusted/untrusted prompt envelope
 -> exactly one bounded model call
 -> strict provider response parser
 -> deterministic synthesis-output parser
 -> SynthesisResult
```

Context bounds:

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16,384 UTF-8 bytes
```

Synthesis bounds:

```text
question:            <= 1,000 characters
model calls:         exactly 1 maximum
answer:              <= 4,000 characters
raw response parser: <= 65,536 characters
```

Pre-model authority is deterministic:

```text
SUPPORTED
UNSUPPORTED
```

The model can only return:

```text
ANSWER
INSUFFICIENT_EVIDENCE
```

after deterministic admission. `UNSUPPORTED` cannot invoke AWS/model code.

Retrieved source text is always untrusted instruction content. Canonical provenance proves source/content identity, not permission to alter system instructions, policies, tools, IAM, or structured vulnerability truth.

### Frozen Bedrock synthesis boundary

ADR 0023 selects:

```text
Region:                  us-east-1
endpoint:                bedrock-runtime
API:                     Converse
streaming:               no
provider/model:          Anthropic Claude Haiku 4.5
US Geo profile:          us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:             0.0
provider maxTokens:      2,048
model calls:             1 maximum
tools:                   none
structured output:       JSON Schema
```

Automatic model-invocation body logging remains disabled. Content-free hashes and provider metadata are captured instead.

No deployed runtime principal exists yet, so Gate 7.6 does not add an invented application IAM role. A future runtime principal must receive only the exact retrieval/inference actions and resources it actually requires.

### First real Gate 7.6e run — SUCCESS

The first supported end-to-end lab run was executed once and completed successfully.

Retrieval:

```text
provider request id:    4835c5d0-4a4e-4f47-9610-482ab6ec1103
requested/returned:     5 / 5
client elapsed:         1463 ms
SDK retries:            0
rank 1:                 knowledge-chunk:pypa-secure-installs:hashes:v1
rank 1 score:           0.8649594783782959
```

Context:

```text
selected chunks:        5
selected UTF-8 bytes:   5828
stop reason:            exhausted_retrieval
context sha256:         bba245b46a1f8cbb2c42010b61e1ef397b2cde9c92fc0439ee0dc03197788445
```

Synthesis:

```text
decision:               answer
answer characters:      1751
stop reason:            end_turn
input tokens:           2671
output tokens:          491
total tokens:           3162
Bedrock latency:        7217 ms
client elapsed:         7983 ms
SDK retries:            0
provider request id:    eee2a118-f806-40d5-8f53-57c88da8ad16
request sha256:         b25eb13aa908d7aa7cb614d4e0e2123aeb68fc0648d4394e16bdb450b7d44d35
prompt sha256:          4e6aad47a03946fad02356198f95e094256cceb1807e4c78fe249e3f9934bbc2
answer sha256:          eee35e23c7fa58502f871e3fb7df8e48664c7dd8350073fc3a58feba7bbf987a
result sha256:          675d661d73ac3844a2e4f53c24f2b919ab909953ee0af29c5912409d93bf792f
```

No replay was performed.

### Gate 7.6f quality review

The rank-1 evidence is the frozen PyPA `Hash-checking Mode` slice from exact upstream commit:

```text
pypa/pip
173eb9b290e2924f0cd42b7714645b38b4df2e81
docs/html/topics/secure-installs.md
```

A manual comparison found the generated answer's seven substantive guidance items supported by that admitted source slice. No structured NVD/KEV/EPSS/CVSS/applicability/runtime-exposure/Risk Policy claim was introduced.

The `--no-require-hashes` pip 26.2+ behavior is source-supported but weakens all-or-nothing enforcement; the answer correctly framed it as optional/selective compatibility behavior rather than the default secure posture.

This is a one-answer manual supportedness review, not a groundedness benchmark. Gate 7.7 will measure deterministic citation correctness/coverage and unsupported claims.

### Observed cost

Using the frozen Claude Haiku 4.5 US Geo rates:

```text
input component:   $0.0029381
output component:  $0.0027005
model total:       $0.0056386
```

One S3 Vectors query request contributes:

```text
$0.0000025
```

Directly computable first-run components:

```text
$0.0056411
```

This is not the full bill. Bedrock `Retrieve` does not expose the exact Titan query-embedding units or S3 Vectors data-processed/data-returned billable units needed to reconstruct those components, so they are not fabricated.

### Latency interpretation

```text
retrieval client elapsed: 1463 ms
Bedrock model latency:    7217 ms
synthesis client elapsed: 7983 ms
```

The simple sequential client-stage sum is `9446 ms`, but no outer stopwatch was recorded. The synthesis run was also the first use of this structured-output grammar; AWS documents possible first-use grammar compilation latency, so this is not represented as warmed steady-state latency.

## Current quality boundary

Latest pre-closeout CI evidence:

```text
Python CI #264: SUCCESS
head: 6b1be075c35120d4cebce97ee0591287ed7ccae5
```

Ruff, Pyright strict, Knowledge Retrieval pytest, and cross-slice regressions were green.

The documentation-closeout commit requires a new final green CI before PR #99 can be marked ready and squash-merged.

## AWS foundation

```text
environment:             dev
primary workload Region: us-east-1
IaC:                     Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

Persistent AWS access keys are not stored in GitHub.

## Next action

Complete Gate 7.6g:

```text
1. synchronize Gate 7.6 lab/current-state/roadmap/architecture
2. require final CI green on the exact documentation-closeout head
3. mark PR #99 ready
4. squash merge only against the validated head SHA
5. begin Gate 7.7 citations + groundedness only after merge
```

Gate 7.7 must project citations from admitted evidence deterministically rather than trust model-authored URLs or source IDs.
