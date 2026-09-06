# Phase 7 — Gate 7.7: Deterministic Citations + Groundedness Evaluation

_Date: 2026-09-06_

## Status

**IN PROGRESS — 7.7a AND 7.7b COMPLETE OFFLINE / 7.7c EVALUATION FIXTURE + METRICS NEXT.**

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

Gate 7.7 separates at least four questions that are often incorrectly collapsed into one RAG-quality score:

```text
retrieval relevance
citation target correctness
claim support / groundedness
citation coverage
```

A response can retrieve the right chunk and still make an unsupported claim. It can also make a supported claim while citing the wrong source. Those failure modes need separate evidence.

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

This means a future model may say `C1`, but it cannot decide that `C1` means a different URL or chunk.

## 7.7b — Structured claim-to-citation proposal contract — COMPLETE

A citation-aware request binds the existing Gate 7.6 synthesis request to the exact deterministic citation catalog:

```text
SynthesisRequest
 + CitationCatalog
 -> GroundedSynthesisRequest
```

The catalog must reference the exact same `context_sha256` as the synthesis request.

The frozen provider-independent output proposal is:

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

Important ownership rules:

- the model does **not** author claim IDs; deterministic code assigns claim indices `1..n`;
- the model does **not** author URLs, source IDs, document IDs, chunk IDs, or hashes;
- every answer claim requires at least one admitted citation ID;
- unknown citation IDs fail closed;
- duplicate citation IDs fail closed;
- model citation order is canonicalized to deterministic catalog order;
- extra provenance/source fields fail closed;
- `insufficient_evidence` requires zero claim text;
- the deterministic renderer joins admitted claims; uncited prose cannot exist outside the structured claims;
- the rendered answer remains under the original Gate 7.6 output entitlement.

Frozen v1 grounded bounds:

```text
max claims:              16
max characters/claim:   1,000
rendered answer:         <= Gate 7.6 request max_output_chars (hard <= 4,000)
raw provider response:   <= 65,536 characters
```

Content-addressed identities:

```text
CitationCatalog.catalog_sha256
GroundedSynthesisRequest.grounded_request_sha256
GroundedClaim.claim_sha256
GroundedSynthesisResult.result_sha256
```

## What this contract proves — and what it does not

The contract guarantees **syntactic citation coverage**: every admitted answer claim contains at least one citation reference and every reference resolves to a deterministic selected-context citation.

It does **not** prove that the cited source semantically supports the claim. A model can still attach `C1` to a statement that `C1` does not entail.

Therefore Gate 7.7 must not report `100% groundedness` merely because every claim has a valid citation ID.

The next evaluation layer must separately measure whether cited evidence actually supports each claim.

## 7.7c — Frozen evaluation fixture + metrics — NEXT

Before any citation-aware Bedrock call or prompt tuning, freeze evaluation semantics.

The design must distinguish:

```text
citation target precision/recall
 -> did model-selected citations align with frozen expected evidence targets?

claim supportedness
 -> does at least one cited source actually support the claim?

citation correctness
 -> what fraction of claim/citation pairs are judged supporting?

unsupported claim rate
 -> what fraction of answer claims have no supporting citation?

abstention behavior
 -> does insufficient evidence remain a clean zero-claim outcome?
```

Semantic support judgments must carry an explicit source (for example human-reviewed golden labels or a separately bounded evaluator signal). Metric computation remains deterministic; an evaluator model, if introduced later, cannot silently become truth authority.

The fixture must be frozen before prompt changes so Gate 7.7 does not tune itself against observed provider output.

## CI evidence

```text
Python CI #266: SUCCESS — deterministic citation catalog
Python CI #267: FAIL — Ruff export ordering only
Python CI #268: SUCCESS — grounded claim/citation contract
```

The #267 failure changed no behavior; `__all__` export order was corrected.

Latest CI-green head at this checkpoint:

```text
5b7540487a125e374e001524defd1e3df8a5887a
```

## AWS / IAM / cost effect

```text
new AWS calls:          0
new model calls:        0
new AWS resources:      0
new IAM permissions:    0
provider cost:          $0
```

No citation-aware prompt has been sent to Bedrock yet.

## Gate 7.7 plan

```text
[x] 7.7a deterministic citation catalog
[x] 7.7b structured claim-to-citation proposal contract
[ ] 7.7c frozen groundedness/citation fixture + deterministic metrics
[ ] 7.7d bounded Bedrock grounded-output request/adapter
[ ] 7.7e preserved real citation + groundedness evaluation
[ ] 7.7f docs/state closeout + final CI + squash merge
```

## Next authorized step

Continue **7.7c offline**. Freeze the evaluation fixture and metric semantics before changing the Bedrock prompt or structured-output schema. Do not make a real model call simply to discover what output is convenient to score.
