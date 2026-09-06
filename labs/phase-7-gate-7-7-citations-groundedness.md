# Phase 7 — Gate 7.7: Deterministic Citations + Groundedness Evaluation

_Date: 2026-09-06_

## Status

**IN PROGRESS — 7.7a–7.7d COMPLETE / 7.7e REAL-EVALUATION HARNESS CI-GREEN / FIRST REAL RUN PENDING.**

Gate 7.6 was squash-merged through PR #99 at:

```text
cc8097b3e2e9b048ca069e961736788de0a79f0d
```

Gate 7.7 is active on draft PR #100 from that exact main commit.

## Permanent boundary

> **Models may select among already-admitted citation IDs. They may not create citation authority.**

This extends:

> **Agents reason. Code verifies evidence.**

and preserves:

> **Structured facts use structured retrieval.**

Canonical URI, source ID, document ID, chunk ID, and content hashes originate from the deterministic retrieval/context authority chain, never from model-authored provenance fields.

## Why Gate 7.7 is separate from Gate 7.6

Gate 7.6 intentionally proved synthesis without citations so generation could be measured independently. Its first real answer was manually found supported by admitted evidence, but one successful answer is not a groundedness benchmark.

Gate 7.7 separates four questions that are often incorrectly collapsed into one RAG-quality score:

```text
retrieval relevance
citation target correctness
claim support / groundedness
citation coverage
```

A response can retrieve the right chunk and still make an unsupported claim. It can also make a supported claim while citing the wrong source. Those failure modes require separate evidence.

## 7.7a — Deterministic citation catalog — COMPLETE

Provider-independent flow:

```text
AssembledContext
 -> exact selected ContextEvidenceBlock[]
 -> deterministic C1..Cn projection
 -> ProjectedCitation[]
 -> CitationCatalog
```

Rules:

- only blocks already selected into `AssembledContext` may become citation authority;
- a retrieval suffix excluded by context limits cannot be cited;
- citation IDs are deterministic `C1..Cn` in selected retrieval-rank order;
- canonical URI/document/source identity is projected from admitted context evidence;
- document and chunk content hashes remain bound to every projected citation;
- provider relevance score is intentionally absent;
- source text is not duplicated into citation operational identity;
- each projected citation has `citation_sha256`;
- the catalog has `catalog_sha256` bound to `context_sha256` and exact canonical citation evidence.

A model may reference `C1`, but it cannot redefine what `C1` means.

## 7.7b — Structured claim-to-citation proposal contract — COMPLETE

A citation-aware request binds the existing Gate 7.6 synthesis request to the exact deterministic citation catalog:

```text
SynthesisRequest
 + CitationCatalog
 -> GroundedSynthesisRequest
```

The catalog must reference the exact same `context_sha256` as the synthesis request.

Frozen provider-independent output proposal:

```json
{
  "decision": "answer",
  "claims": [
    {
      "text": "...",
      "citation_ids": ["C1", "C2"]
    }
  ]
}
```

or:

```json
{
  "decision": "insufficient_evidence",
  "claims": []
}
```

Ownership rules:

- the model does not author claim IDs; deterministic code assigns claim indices `1..n`;
- the model does not author URLs, source IDs, document IDs, chunk IDs, or hashes;
- every answer claim requires at least one admitted citation ID;
- unknown citation IDs fail closed;
- duplicate citation IDs fail closed;
- model citation order is canonicalized to deterministic catalog order;
- extra provenance/source fields fail closed;
- `insufficient_evidence` requires zero claims;
- the deterministic renderer joins admitted claims; uncited prose cannot exist outside structured claims;
- the rendered answer remains under the original Gate 7.6 output entitlement.

Frozen v1 grounded bounds:

```text
max claims:             16
max characters/claim:  1,000
rendered answer:        <= Gate 7.6 request max_output_chars (hard <= 4,000)
raw provider response:  <= 65,536 characters
```

Syntactic citation coverage does not prove semantic support.

## 7.7c — Frozen groundedness fixture + metrics — COMPLETE

The evaluation contract was frozen before citation-aware provider execution or prompt tuning.

Dataset:

```text
knowledge-grounding-golden:v1
4 cases
3 expected answer cases
1 expected insufficient-evidence case
judgment authority: human_reviewed_claim_citation_pairs_v1
```

Frozen cases cover:

```text
artifact/hash verification
transitive dependency review
isolated remediation validation
exact pip TLS cipher request outside corpus evidence
```

The deterministic evaluator keeps separate:

```text
citation target precision/recall
claim supportedness
claim/citation pair correctness
unsupported claim rate
abstention behavior
```

Semantic support judgments are explicit, content-addressed evidence. Metric code cannot silently declare semantic support from citation syntax, source identity, provider score, or string overlap.

## 7.7d — Bounded Bedrock grounded-output integration — COMPLETE OFFLINE

The provider boundary reuses the already-proven Gate 7.6 Bedrock profile:

```text
Region:                 us-east-1
endpoint/API:           bedrock-runtime / Converse
model/profile:          us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:              no
temperature:            0.0
provider maxTokens:     2,048
tools:                  none
structured output:      JSON Schema
```

Provider flow:

```text
GroundedSynthesisRequest
 -> deterministic grounded prompt envelope
 -> exact C1..Cn evidence serialized as untrusted user-role data
 -> one bounded Converse call
 -> exactly one assistant text block
 -> stopReason=end_turn
 -> deterministic grounded-output parser
 -> GroundedSynthesisResult
 -> content-free provider/runtime evidence
```

The structured-output schema constrains answer/abstention + claims + non-empty citation arrays. Application code remains authoritative for hard claim-count, claim-length, output-size, citation allowlist, and provenance invariants.

Retrieved prompt-injection text remains untrusted data and cannot enter system instructions.

## 7.7e — Preserved real citation + groundedness evaluation — HARNESS READY

The first-run runtime harness is implemented and CI-green, but no real Gate 7.7 call has been executed yet.

Per frozen case:

```text
frozen question
 -> exactly one bounded direct Retrieve attempt (top_k=5)
 -> deterministic context assembly
 -> deterministic C1..Cn citation catalog
 -> exactly one grounded Converse attempt
 -> admitted claims/citations + provider telemetry
```

Execution policy:

- one application attempt maximum per frozen case;
- stop after the first failed application attempt;
- preserve the successfully completed prefix and partial failed-case evidence;
- do not replay provider/model cases merely to improve results;
- raw retrieved source bodies are not persisted in the runtime artifact;
- claim text is persisted because human semantic support review must inspect the exact generated claims;
- semantic judgments are deliberately absent from the first runtime artifact and are added only after explicit review.

The CLI records retrieval IDs/request IDs, result counts, relevance scores, context/catalog hashes, citation identities, grounded request/result hashes, model request ID, latency, token counts, SDK retry counts, stop reason, model decision, claims, and selected citation IDs.

## CI evidence

Relevant Gate 7.7 checkpoints:

```text
#266 SUCCESS — deterministic citation catalog
#267 FAIL    — Ruff export ordering only
#268 SUCCESS — grounded claim/citation contract
#273 FAIL    — Ruff forward-reference style only
#274 SUCCESS — frozen grounding evaluation
#275 FAIL    — unused import in grounded Bedrock request
#276 FAIL    — strict typing in negative request test
#277 SUCCESS — grounded Bedrock request/adapter
#278 FAIL    — strict typing in runtime-runner test only
#279 SUCCESS — real grounding evaluation harness
```

Current CI-green head before the first real Gate 7.7 run:

```text
714ae6b66a6dc5fcbc3b087160132b16a14869a4
```

## AWS / IAM / cost effect so far

```text
Gate 7.7 real Retrieve calls:  0
Gate 7.7 real Converse calls:  0
new AWS resources:             0
new IAM permissions:           0
Gate 7.7 provider cost:        $0
```

Gate 7.7 reuses the existing Bedrock Knowledge Base, S3 Vectors store, retrieval admission path, and Bedrock Runtime synthesis profile. No new service or IAM entitlement is justified for this gate.

## Gate 7.7 plan

```text
[x] 7.7a deterministic citation catalog
[x] 7.7b structured claim-to-citation proposal contract
[x] 7.7c frozen groundedness/citation fixture + deterministic metrics
[x] 7.7d bounded Bedrock grounded-output request/adapter
[ ] 7.7e execute and preserve first real citation + groundedness evaluation
[ ] 7.7f semantic review, docs/state closeout, final CI, ready, squash merge
```

## Next authorized step

Execute the frozen four-case Gate 7.7 runtime exactly once from CI-green head `714ae6b66a6dc5fcbc3b087160132b16a14869a4` using the existing dev Knowledge Base. If the provider/application run fails, preserve that first evidence and do not replay automatically.

After the runtime artifact exists, human-review the exact generated claim/citation pairs, add content-addressed support judgments, compute the frozen deterministic metrics, then close Gate 7.7 without post-hoc prompt tuning or replay.
