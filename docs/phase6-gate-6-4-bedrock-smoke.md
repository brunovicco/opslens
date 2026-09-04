# Phase 6 Gate 6.4 — real Bedrock planner smoke

Date: 2026-09-04

## Purpose

Gate 6.4 performs the first real model invocation after ADR 0021 froze the bounded semantic-query planner contract offline.

The model remains a proposal generator only. Deterministic OpsLens code remains authoritative for planner-output parsing, `SemanticQuery` construction, SQL compilation, and Athena execution.

## Frozen runtime boundary

- provider: Anthropic through Amazon Bedrock;
- model: Claude Haiku 4.5;
- model ID: `anthropic.claude-haiku-4-5-20251001-v1:0`;
- region: `us-east-1`;
- endpoint: `bedrock-runtime`;
- API: non-streaming `Converse`;
- temperature: `0.0`;
- max output tokens: `256`;
- structured output: existing planner JSON Schema;
- tools: none;
- retries in the smoke harness: none;
- smoke question: `Show the 5 CVEs with the highest EPSS score on 2026-09-01.`

AWS documentation was revalidated on 2026-09-04: Claude Haiku 4.5 remains active, supports `bedrock-runtime`, Converse, structured outputs, and In-Region execution in `us-east-1`.

## Identity boundary

The existing `OpsLensGitHubDeployRole` deliberately trusts only `main` and is not reused for model inference.

Gate 6.4 introduces `OpsLensBedrockSmokeRole` with:

- OIDC trust restricted to `feat/phase6-gate-6-4-bedrock-smoke`;
- audience restricted to `sts.amazonaws.com`;
- only `bedrock:InvokeModel`;
- resource restricted to `arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0`.

No streaming, agents, tools, knowledge bases, prompt management, IAM mutation, or general Bedrock permissions are granted to this role.

## Evidence contract

A successful smoke must return and validate:

- exactly one non-empty Bedrock text content block;
- `inputTokens`;
- `outputTokens`;
- `totalTokens` equal to input plus output;
- `latencyMs`;
- a planner proposal accepted by the existing deterministic `parse_planner_json`;
- a semantic query matching the fixed smoke question.

Missing usage or latency fails closed. The harness does not manufacture zero values or substitute local wall-clock timing for Bedrock evidence.

Raw prompts, credentials, and raw provider responses are not persisted as evidence.

## Cost snapshot

For this one validation, observed cost is calculated from measured Bedrock tokens using a pricing snapshot dated 2026-09-04:

- input: USD 1.10 per million tokens;
- output: USD 5.50 per million tokens.

Source: AWS material describing Amazon Bedrock with Claude Haiku 4.5 current pricing. The values are a dated smoke-test snapshot, not a durable application pricing authority. Production cost accounting must use a maintained pricing source rather than these validation constants.

## Execution sequence

1. static Python/Terraform CI validates the branch;
2. the dedicated IAM smoke role is provisioned through the bootstrap stack;
3. the manual `Phase 6 Gate 6.4 Bedrock Smoke` workflow is dispatched from this exact branch;
4. one Converse request is issued;
5. bounded runtime evidence and the deterministically parsed proposal are recorded from the workflow output;
6. Gate 6.4 is marked complete only if all of the above pass.

The workflow must not be executed before the dedicated role exists.
