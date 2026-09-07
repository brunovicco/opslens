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
