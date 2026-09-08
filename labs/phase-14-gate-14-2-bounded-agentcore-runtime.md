# Phase 14 — Gate 14.2: First Bounded AgentCore HTTP/SigV4 Runtime Experiment

_Date: 2026-09-08_

## Status

**IN PROGRESS — OFFLINE CONTRACT/PACKAGE/NETWORK CHECKPOINT COMPLETE; AWS DEPLOYMENT PENDING PROTECTED MERGE.**

```text
source main: 144ae94c9b5b5b6e56188d5c881f2d0235a3af56
issue:       #198
branch:      feat/phase14-bounded-agentcore-runtime
PR:          #199
```

## Objective

Deploy exactly one removable AgentCore HTTP runtime around the retained Phase 11 bounded reasoning path, measure hosting/session/IAM/latency/cost behavior, and stop before capability execution.

This gate is not general AgentCore adoption.

## Frozen runtime contract

```text
raw JSON bytes
 -> exact-key admission
 -> 4,096-byte runtime envelope
 -> existing 2,048-byte SingleAgentTask text authority
 -> closed AgentCapability allowlist parsing
 -> content-addressed SingleAgentTask
 -> existing reason_about_task(...)
 -> exactly one bounded model proposal
 -> existing deterministic authorize_agent_action(...)
 -> content-addressed AgentCoreReasoningProjection
 -> bounded metadata-only protocol payload
 -> STOP before capability execution
```

Caller-controlled provider/model/region/URL/SQL/shell/args/kwargs/retry/fallback/execution results are not admitted.

Hard bounds:

```text
model invocations/request:      1
capability executions:          0
adaptive retries:               0
adaptive fallbacks:             0
MCP calls:                      0
A2A handoffs:                   0
Gateway/Memory/Browser/Code:    0
runtime-exposure authority:     0
```

Unit checkpoint:

```text
AgentCore runtime tests: 24 passed
Ruff:                   PASS
Pyright strict slice:   PASS
```

## Direct-code package checkpoint

The runtime package is built from the exact `uv.lock` closure rooted at `botocore` plus an explicit allowlist of reachable OpsLens source files.

First reproducibility CI exposed a useful deterministic-build failure: package validation imported staged Python modules after bytecode cleanup, recreating path-dependent `__pycache__/*.pyc` files. The validator was changed to run with `PYTHONDONTWRITEBYTECODE=1`, making validation non-mutating.

Successful exact package run:

```text
GitHub Actions run:      34288867537
job:                     102270665266
head:                    d8f971aaab6775949a3db5f252ef49db754e4b78
locked AWS provider:     6.60.0
provider resource probe: aws_bedrockagentcore_agent_runtime PASS
reproducible ZIP A/B:    PASS
```

Artifact evidence:

```text
runtime:            PYTHON_3_13
architecture:       arm64
platform:           aarch64-manylinux2014
entrypoint:         main.py
compressed:         16,058,438 bytes
uncompressed:       21,207,613 bytes
sha256:             a846034ad646c4f6383ac08e47d9ed065b4a9f3349c14104db49a2d510b3ec88
native files:       []
forbidden packages: []
```

Locked dependency closure:

```text
botocore==1.43.72
jmespath==1.1.0
python-dateutil==2.9.0.post0
six==1.17.0
urllib3==2.7.0
```

`mcp`, `boto3`, `s3transfer`, `pyarrow`, and `aws-lambda-powertools` are not admitted to the runtime artifact.

Conclusion:

```text
direct code: RETAIN
container:   NOT JUSTIFIED BY CURRENT PACKAGE EVIDENCE
```

## Exact outbound dependency review

The experiment terminates before business-capability execution. Application egress is only one fixed non-streaming Bedrock Converse invocation through:

```text
us.anthropic.claude-haiku-4-5-20251001-v1:0
```

There is no current runtime requirement for GitHub, Athena, data-lake S3, external URLs, MCP, A2A, Gateway, Memory, Browser, or Code Interpreter.

The repository has no application VPC foundation today.

## Network decision

ADR 0053 selects `PUBLIC` only for the first time-bounded dev experiment.

This is an explicit security exception, not a production recommendation. AWS Security Hub control `BedrockAgentCore.1` is High severity and fails PUBLIC runtime network mode.

The exception is constrained by:

```text
IAM SigV4 inbound invocation
closed request schema
no caller-provided network destinations
zero capability executions
zero business-data mutation
short lifecycle
mandatory runtime cleanup
```

If the Runtime is retained, VPC mode becomes the default next network candidate and must be evaluated with a Bedrock Runtime private access path and the direct-code service S3 requirements documented by AWS.

## Lifecycle decision

For the temporary replay:

```text
idle_runtime_session_timeout = 120
max_lifetime                 = 900
```

AWS currently documents 60 seconds as the microVM minimum and explicitly lists short demo/testing lifecycle patterns to reduce idle resource cost.

## IAM boundaries entering the next slice

Three identities remain separate:

```text
GitHub deployment principal
 -> publish/read exact artifact
 -> create/read/update/delete exact bounded Runtime
 -> PassRole only for exact runtime execution role

AgentCore runtime execution role
 -> exact non-streaming Bedrock model/profile invocation
 -> only service-required runtime logging permissions
 -> NO capability/data-lake/GitHub/MCP/A2A authority

runtime replay caller
 -> bedrock-agentcore:InvokeAgentRuntime only for admitted OpsLens runtime
```

The GitHub OIDC trust remains `refs/heads/main` only. Feature-branch deployment is forbidden.

## Current AWS impact

This checkpoint has made no paid AgentCore call and has created no AWS resource.

```text
new AgentCore runtimes:    0
new AgentCore invocations: 0
new IAM roles/policies:    0
new VPC resources:         0
new public app endpoints:  0
AgentCore cost:            USD 0.00
```

## Evidence

Machine-readable checkpoint:

```text
labs/evidence/phase-14-gate-14-2-offline-runtime-plan-v1.json
```

Architecture decision:

```text
docs/adr/0053-bounded-agentcore-direct-code-public-network-experiment.md
```

## Next authorized implementation slice

Still inside Gate 14.2, and still **offline on the feature branch**:

```text
1. add content-addressed AgentCore artifact publication contract
2. add Terraform runtime + least-privilege execution-role configuration
3. add bootstrap deployment permissions without changing main-only OIDC trust
4. validate exact provider configuration offline
5. keep PR draft until offline deployment prerequisites are green
```

Only after protected merge may the main-only deployment identity publish/deploy the runtime and perform the authenticated six-case replay.

## Exit checklist

```text
[x] exact HTTP request/projection contract frozen
[x] request refusal/fail-closed unit cases
[x] zero capability execution boundary tested
[x] exact direct-code dependency closure frozen
[x] byte-reproducible ZIP proven
[x] direct-code size/native evidence captured
[x] network dependency set reviewed
[x] network mode decision frozen with explicit Security Hub consequence
[x] lifecycle bounds frozen
[x] ADR 0053 recorded
[x] machine-readable offline checkpoint added
[ ] content-addressed artifact publisher implemented/tested
[ ] runtime execution-role Terraform implemented/tested
[ ] deployment principal permissions implemented/reviewed
[ ] exact offline Terraform validation green
[ ] protected merge before AWS deployment
[ ] authenticated Runtime deployment + READY evidence
[ ] unchanged six-case Phase 11 replay through AgentCore
[ ] meaningful real failure/authorization experiment
[ ] latency/session/token/retry evidence captured
[ ] AgentCore CPU/memory cost evidence captured
[ ] runtime cleanup proven
[ ] retain/reject AgentCore Runtime decision recorded
```
