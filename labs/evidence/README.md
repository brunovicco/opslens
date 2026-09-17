# OpsLens Lab Evidence

This directory contains content-addressed, reviewable evidence produced by bounded laboratory gates.

## Gate 7.7 groundedness baseline

`phase-7-gate-7-7-first-run-review-v1.json` preserves the human-reviewed, metadata-only semantic support evidence for the first real `knowledge-grounding-golden:v1` execution.

The artifact intentionally stores claim hashes, citation IDs, canonical chunk mappings, request/result/catalog hashes, and content-addressed human judgments rather than copied model claim text or source bodies.

The raw real-run JSON was inspected from the operator's preserved local output and was not replayed after observation. The review artifact is tied to pre-run validated head `507fe04f963c7eeb49748eb950101ea2fc55e14f`.

## Gate 11.4 first real reasoning baseline

`phase-11-gate-11-4-first-real-baseline-v1.json` preserves the first successful real Bedrock replay of the frozen six-case `single-agent-reasoning-evaluation:v1` corpus.

The artifact is tied to source head `626139690d61c20583e8cc51c1dfecf80b8789d3` and preserves only admitted proposal/authorization outcomes, content-addressed reasoning identities, Bedrock request metadata, token/latency/retry observations, aggregate measurements, and the pricing inputs used for the experiment-time cost derivation. Raw model output and credentials are intentionally absent.

The six-case run completed with `6/6` decision, capability, authorization, and bounds matches, zero SDK retries, zero capability executions, 3,291 input tokens, 104 output tokens, and a derived USD 0.0041921 inference cost using the contemporaneously verified US geographic cross-Region Claude Haiku 4.5 rates.

## Correlation index stored item size

`correlation-index-stored-item-size-v1.json` records what the built correlation index
actually costs to read, measured against the live tables after the first apply
(generation `ee5826ced8931fb4`, built 2026-09-17T03:40:55Z).

It exists because the ADR 0087 sizing was taken from projected source bytes and
understated the stored item by 2.8x. The measurement method is recorded alongside the
result: the AWS CLI paginates `Query` and `Scan` and reports `ConsumedCapacity` for a
single page, so a per-item size is derived from the item count of one unpaginated full
page rather than from reported capacity. The artifact also records what was deliberately
not measured, including the size of a rebuilt evidence item in an API response.

All observations are read-only; no write was performed against the index.

## Correlation index version-selection ties

`correlation-index-version-selection-ties-v1.json` records why two projection runs over
an unchanged corpus produced different indexes, and how large the exposure was.

Both projection statements selected the latest observed version of each source record
with `ROW_NUMBER` ordered on a non-unique key. Seven GHSA advisories carry two observed
versions at the same `updated_at`; the NVD corpus carries none today, which is a property
of the data rather than of the query. The artifact keeps the two diverging index
identities, the counting method, and what it deliberately leaves unresolved — including
whether ties were the only source of non-determinism.

Read-only; no write was performed.

