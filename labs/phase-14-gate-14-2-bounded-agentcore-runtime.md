# Phase 14 — Gate 14.2: First Bounded AgentCore HTTP/SigV4 Runtime Experiment

_Date: 2026-09-08_

## Status

**READY FOR PROTECTED MERGE — OFFLINE PREDEPLOY IMPLEMENTATION COMPLETE; NO AGENTCORE RUNTIME HAS BEEN CREATED YET.**

```text
source main: 144ae94c9b5b5b6e56188d5c881f2d0235a3af56
issue:       #198
branch:      feat/phase14-bounded-agentcore-runtime
PR:          #199
```

The AWS experiment remains intentionally impossible from the feature branch. The only deployment workflow is manual, requires explicit confirmation, and requires `refs/heads/main`.

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

## Latest offline predeploy validation

Implementation head validated before this documentation synchronization:

```text
head:                 e208ab1be4e5192e6deec724fae933d450388cf5
AgentCore CI run:     34294710346
Terraform CI run:     34294710387
AgentCore unit tests: 33 passed
Ruff:                 PASS
Pyright strict slice: PASS
workflow guardrails:  PASS
provider schema:      aws_bedrockagentcore_agent_runtime PASS
Terraform fmt:        PASS
Terraform validate:   PASS
TFLint:               PASS
Checkov:              PASS
```

The final PR head must still be green after this documentation-only synchronization before merge.

## Direct-code package checkpoint

The runtime package is built from the exact `uv.lock` closure rooted at `botocore` plus an explicit allowlist of reachable OpsLens source files.

The first reproducibility CI exposed a deterministic-build defect: package validation imported staged Python modules after bytecode cleanup, recreating path-dependent `__pycache__/*.pyc` files. Validation now runs with `PYTHONDONTWRITEBYTECODE=1`, so the validation step is non-mutating.

Latest validated package evidence:

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
idle runtime session timeout = 120 seconds
maximum runtime lifetime     = 900 seconds
mandatory runtime cleanup
```

If Runtime is retained, VPC mode becomes the default next network candidate and must be evaluated with a Bedrock Runtime private access path and the direct-code service S3 requirements documented by AWS.

## IAM boundaries

The experiment preserves three separate authorities:

```text
GitHub deployment principal
 -> publish/read only the AgentCore artifact prefix
 -> create/read/update/delete only the bounded Runtime family
 -> create/manage only the exact runtime execution role
 -> PassRole only for that exact role to bedrock-agentcore.amazonaws.com
 -> MUST NOT invoke AgentCore Runtime

AgentCore runtime execution role
 -> exact non-streaming Bedrock model/profile invocation
 -> service-required logging/tracing/metric emission only
 -> NO capability/data-lake/GitHub/MCP/A2A authority

runtime replay caller
 -> bedrock-agentcore:InvokeAgentRuntime only for the bounded OpsLens Runtime family
 -> NO deployment/control-plane authority
```

The replay role is `OpsLensAgentCoreReplayRole`. Its GitHub OIDC trust is restricted to the immutable OpsLens `main` subject and audience `sts.amazonaws.com`.

Feature-branch OIDC trust was not widened.

## Authenticated replay implementation

The retained Phase 11 corpus is replayed unchanged through the AgentCore data-plane API:

```text
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
cases:         6
```

The replay contract records per-case runtime session identity, transport elapsed time, deterministic decision/capability/authorization scoring, and the existing reasoning invocation evidence including token counts and SDK retry attempts.

The replay fails closed on:

```text
wrong runtime session identity
non-200 Runtime status
non-JSON Runtime response
missing invocation evidence
Phase 11 corpus identity drift
case-count drift
SDK retry evidence above the frozen bound
```

Capability execution remains exactly zero.

## Main-only experiment workflow

`.github/workflows/agentcore-runtime-experiment.yml` is a dedicated `workflow_dispatch` path. It requires:

```text
github.ref == refs/heads/main
confirm_public_experiment == true
```

Its bounded sequence is:

```text
build deterministic direct-code ZIP
 -> publish create-only content-addressed S3 artifact
 -> validate exact SHA-256 + S3 VersionId
 -> targeted Terraform plan/apply for experiment-only resources
 -> wait for Runtime READY
 -> assume invocation-only replay role
 -> replay unchanged Phase 11 six-case corpus
 -> restore deployment role
 -> prove deployment role is denied InvokeAgentRuntime
 -> always plan/apply experiment cleanup
 -> verify Runtime returns ResourceNotFound after cleanup
 -> always preserve experiment JSON evidence as a GitHub Actions artifact
```

The evidence artifact uses pinned `actions/upload-artifact` v7.0.1 commit `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` and retains the immediate experiment evidence for 30 days so the first real result can be reviewed and promoted into immutable repository evidence without relying only on console output.

Expected transient evidence files include:

```text
opslens-agentcore-lifecycle.json
opslens-agentcore-publication.json
opslens-agentcore-runtime.json
opslens-agentcore-replay.json
opslens-agentcore-deploy-role-denial.json
```

## Required human bootstrap after protected merge

The experiment workflow cannot and must not grant its own IAM authority.

After protected merge, the human bootstrap plane using the existing `opslens-bootstrap` Identity Center profile must apply the `infra/bootstrap` changes before the experiment workflow runs. That apply creates the invocation-only replay role and attaches the bounded AgentCore deployment policy to `OpsLensGitHubDeployRole`.

This is intentional separation of duties:

```text
human bootstrap plane
 -> grants CI trust/authorization

GitHub deployment plane
 -> consumes only previously granted authority
 -> cannot modify its own bootstrap state or OIDC trust
```

No feature-branch AWS deployment is authorized as a workaround.

## Cost evidence plan

AgentCore Runtime resource telemetry is not inferred from wall-clock time. The post-experiment cost checkpoint must use the service-provided resource metrics:

```text
namespace: AWS/Bedrock-AgentCore
service:   AgentCore.Runtime
resource:  exact runtime ARN
metrics:   CPUUsed-vCPUHours
           MemoryUsed-GBHours
```

AWS documents these resource-usage metrics at one-minute resolution and warns that resource telemetry may be delayed by up to 60 minutes. Therefore the immediate workflow preserves the runtime ARN and timestamps first; CPU/memory cost evidence is collected after the metrics become available.

Runtime cost will be derived from observed CPU/memory usage plus contemporaneous AgentCore pricing. The AWS billing statement remains authoritative if telemetry and billed usage differ.

No monthly extrapolation is part of Gate 14.2.

## Current AWS impact

This feature-branch checkpoint has made no paid AgentCore call and has created no AgentCore or experiment IAM resource.

```text
new AgentCore runtimes:    0
new AgentCore invocations: 0
new experiment IAM roles:  0
new VPC resources:         0
new public app endpoints:  0
AgentCore cost:            USD 0.00
```

Terraform code describing future resources is present, but all workload experiment resources are disabled by default and bootstrap changes have not been applied from the feature branch.

## Evidence

Machine-readable offline checkpoint:

```text
labs/evidence/phase-14-gate-14-2-offline-runtime-plan-v1.json
```

Architecture decision:

```text
docs/adr/0053-bounded-agentcore-direct-code-public-network-experiment.md
```

## Next authorized sequence

```text
1. final exact-head PR CI green
2. mark PR #199 ready and protected squash merge
3. human bootstrap apply from merged main using opslens-bootstrap
4. manually run AgentCore Runtime Experiment on main with explicit PUBLIC confirmation
5. preserve the first real six-case replay and denial/cleanup evidence
6. wait for delayed AgentCore CPU/memory telemetry when necessary
7. derive actual gate cost from observed usage
8. record Gate 14.2 measured outcome
9. defer retain/reject optimization decision to the next gate
```

## Exit checklist

```text
[x] exact HTTP request/projection contract frozen
[x] request refusal/fail-closed unit cases
[x] zero capability execution boundary tested
[x] exact direct-code dependency closure frozen
[x] byte-reproducible ZIP proven
[x] direct-code size/native evidence captured
[x] content-addressed artifact publisher implemented/tested
[x] network dependency set reviewed
[x] network mode decision frozen with explicit Security Hub consequence
[x] lifecycle bounds frozen
[x] ADR 0053 recorded
[x] runtime execution-role Terraform implemented/tested
[x] deployment principal permissions implemented/reviewed offline
[x] invocation-only replay role implemented/reviewed offline
[x] unchanged Phase 11 replay client implemented/tested
[x] main-only deploy/replay/denial/cleanup workflow implemented
[x] evidence preservation + cleanup verification implemented
[x] exact offline Terraform validation green
[x] machine-readable offline checkpoint added
[ ] final exact-head PR CI green after documentation synchronization
[ ] protected merge before AWS deployment
[ ] human bootstrap IAM apply from merged main
[ ] authenticated Runtime deployment + READY evidence
[ ] unchanged six-case Phase 11 replay through AgentCore
[ ] meaningful real deployment-principal invocation denial evidence
[ ] latency/session/token/retry evidence captured
[ ] AgentCore CPU/memory cost evidence captured
[ ] runtime cleanup proven in AWS
[ ] Gate 14.2 measured outcome recorded
```
