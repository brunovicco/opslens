# ADR 0053 — Use a Reproducible Direct-Code Artifact and a Time-Bounded PUBLIC Network Exception for the First AgentCore Runtime Experiment

- Status: Accepted
- Date: 2026-09-08
- Phase: 14 — Amazon Bedrock AgentCore
- Gate: 14.2 — First Bounded AgentCore HTTP/SigV4 Runtime Experiment

## Context

Gate 14.1 authorized exactly one removable AgentCore Runtime experiment around the retained Phase 11 reasoning path. PR #199 has now frozen the HTTP request/projection contract and proved an exact direct-code dependency slice without adding capability execution authority.

The remaining pre-deployment choices are packaging, network mode, lifecycle bounds, and the minimum IAM surfaces needed to deploy and invoke the experiment.

Current official AWS documentation was rechecked on 2026-09-08. The exact locked HashiCorp AWS provider is `6.60.0`; its documentation and the PR CI schema probe both expose direct-code `aws_bedrockagentcore_agent_runtime` configuration with `PYTHON_3_13`, S3 code artifacts, `PUBLIC | VPC` network modes, and explicit HTTP protocol configuration.

## Package evidence

AgentCore CI run `34288867537` proved two independently built ZIPs are byte-identical after package validation was made non-mutating.

```text
artifact_version:               agentcore-runtime-package:v1
runtime:                        PYTHON_3_13
architecture:                   arm64
python_platform:                aarch64-manylinux2014
entry_point:                    main.py
compressed_bytes:               16,058,438
uncompressed_bytes:             21,207,613
sha256:                         a846034ad646c4f6383ac08e47d9ed065b4a9f3349c14104db49a2d510b3ec88
native_files:                   0
forbidden_distributions:        0
MCP runtime dependency:         absent
```

Exact locked runtime dependency closure:

```text
botocore==1.43.72
jmespath==1.1.0
python-dateutil==2.9.0.post0
six==1.17.0
urllib3==2.7.0
```

The artifact is far below the currently documented direct-code limits of 250 MB compressed and 750 MB uncompressed. A container/ECR deployment would therefore add machinery without solving a demonstrated packaging problem.

## Outbound dependency review

The first experiment stops before capability execution. Runtime application code requires only:

```text
one non-streaming Amazon Bedrock Converse call
 -> fixed US Geographic inference profile
 -> us.anthropic.claude-haiku-4-5-20251001-v1:0
```

It does not require:

```text
GitHub
Athena
OpsLens data lake reads/writes
MCP
A2A
AgentCore Gateway
Memory
Browser
Code Interpreter
arbitrary caller-supplied URLs
arbitrary provider/model endpoints
```

The repository currently has no application VPC foundation. Introducing VPC mode only for this experiment would require new subnets/security groups and a private Bedrock Runtime access path, or NAT-based egress. AWS documents that AgentCore Runtime ENIs in VPC mode do not gain internet access merely by using public subnets; private subnets plus NAT are required for internet egress, while AWS service access should use VPC endpoints where practical.

## Security fact: PUBLIC is not the production-preferred posture

AWS Security Hub control `BedrockAgentCore.1` is High severity and fails AgentCore runtimes configured with `PUBLIC` network mode. AWS recommends VPC mode to reduce network attack surface.

That fact is not hidden or reinterpreted.

For Gate 14.2, however, VPC infrastructure would materially change the experiment from:

```text
Does AgentCore Runtime add useful managed hosting value?
```

into:

```text
Can OpsLens build and operate a new VPC/private-endpoint topology for one temporary runtime?
```

The latter is a separate infrastructure decision and would also introduce persistent networking cost before the managed runtime itself has demonstrated retention value.

## Decision

### 1. Retain direct code

Use the reproducible Python 3.13/arm64 ZIP for the first deployment.

The deployment artifact must be published to the existing private OpsLens dev deployment-artifacts bucket under a content-addressed AgentCore prefix. Publication is create-only/idempotent: an existing object is admissible only when its content identity matches the expected SHA-256.

The Terraform runtime must pin the exact S3 object version when available rather than silently following an overwritten mutable key.

### 2. Use PUBLIC network mode only as a bounded dev experiment exception

Select:

```text
network_mode = PUBLIC
```

for the first authenticated runtime replay only.

This does **not** mean unauthenticated public application access. Inbound invocation remains IAM SigV4 and requires `bedrock-agentcore:InvokeAgentRuntime`. The runtime request contract remains closed and cannot supply endpoints, URLs, provider/model selection, SQL, shell commands, tool kwargs, or capability execution authority.

The exception is acceptable only because all of the following are true:

```text
environment:                    dev experiment
caller authentication:         IAM SigV4
capability executions:          0
caller-controlled egress:       0
business-data mutation:         0
MCP/A2A/Gateway/tool execution: 0
runtime retention decision:     pending measurement
cleanup after replay:           mandatory
```

If AgentCore Runtime is retained beyond this experiment, network posture must be re-evaluated and VPC mode becomes the default candidate. A later public demo must not inherit this exception implicitly.

### 3. Bound runtime lifecycle aggressively

Use the documented demo/testing-style lifecycle:

```text
idle_runtime_session_timeout = 120 seconds
max_lifetime                 = 900 seconds
```

AWS currently permits these values and explicitly recommends shorter development/test timeouts to reduce idle memory cost. The six-case replay should use controlled session IDs and record cold/warm behavior rather than extending lifecycle merely for convenience.

### 4. Keep runtime execution IAM narrower than AWS examples

The Runtime execution role may receive only permissions required by the exact retained path and service operation.

For model inference, reuse the already reviewed Phase 7/11 cross-Region authorization shape:

```text
bedrock:InvokeModel
 -> exact US Geographic inference-profile ARN
 -> exact Claude Haiku 4.5 foundation-model ARNs in documented candidate US Regions
 -> foundation-model access conditioned on the exact bedrock:InferenceProfileArn
```

Do not grant streaming model invocation because the retained adapter is non-streaming.

Any logging permissions required by AgentCore must be scoped to the AgentCore runtime log-group family for this named runtime where the AWS API permits it. Do not bundle unrelated CloudWatch administration into the Bedrock inference statement.

Explicitly excluded from the runtime role:

```text
Athena
GitHub access
S3 data-lake mutation
OpsLens business-capability execution
bedrock-agentcore Gateway/Memory/Browser/Code Interpreter actions
MCP/A2A authority
runtime-exposure authority
bedrock:InvokeModelWithResponseStream
```

The trust policy must use service principal `bedrock-agentcore.amazonaws.com` plus `aws:SourceAccount` and the narrowest practical AgentCore `aws:SourceArn` pattern available before the runtime ID exists.

### 5. Keep deployment identity and runtime identity separate

The GitHub Actions deployment role remains main-branch-only. Gate 14.2 does not widen OIDC trust to the feature branch.

After protected merge, the deployment principal may receive only the control-plane/S3/IAM pass-role permissions required to publish the exact artifact and create/read/update/delete the bounded runtime. Direct-code troubleshooting guidance requires the principal calling Create/UpdateAgentRuntime to have `s3:GetObject` for the referenced artifact.

Invocation permission remains separate from control-plane mutation. The replay caller should be narrowed to `bedrock-agentcore:InvokeAgentRuntime` for the OpsLens runtime resource, using resource tags or an exact ARN once it exists.

## Observability and cost

The deployment/replay must record at minimum:

```text
runtime ARN / ID / version
network mode
artifact S3 version + SHA-256
session ID
request/task/reasoning/projection IDs
Bedrock request ID
stop reason
tokens/cache tokens
provider/client latency
SDK retries
authorization outcome
capability executions (= 0)
create/ready/invoke/delete timestamps
failure reason when present
```

AgentCore Runtime pricing remains measured from observed CPU/memory consumption, not inferred from list-price examples alone. The short lifecycle is specifically intended to reduce idle memory billing after the experiment.

## Failure and rollback

Expected meaningful failure paths include malformed runtime requests, model authorization denial, artifact/deployment authorization denial, runtime create failure, health failure, and invoke denial.

Rollback for the experiment is deletion of the AgentCore Runtime and any experiment-only IAM policy/role resources after evidence capture. The content-addressed artifact may remain in the existing private deployment bucket as provenance unless a concrete retention/cost reason requires removal.

## Alternatives considered

### VPC mode immediately

Not selected for the first experiment. It is the stronger retained-network candidate, but OpsLens currently has no VPC foundation and the experiment has only one AWS service egress dependency. Building VPC/endpoints before Runtime retention is measured would confound scope and add persistent cost.

### Container/ECR deployment

Rejected for the first experiment. The direct-code artifact is deterministic, dependency-minimized, native-file-free, and comfortably within service limits.

### Default 15-minute idle timeout / 8-hour max lifetime

Rejected for this bounded test. AWS provides shorter lifecycle controls and documents short demo/testing patterns; keeping a temporary microVM warm longer would add cost without experimental value.

### OAuth/JWT inbound authorization

Deferred. The first caller is an AWS principal, so IAM SigV4 remains sufficient.

## Consequences

Positive:

- isolates AgentCore Runtime value from unrelated VPC/container platform work;
- preserves a reproducible content-addressed artifact;
- keeps capability execution at zero;
- makes the PUBLIC-network security exception explicit and temporary;
- provides aggressive lifecycle cost bounds;
- preserves least-privilege separation between deployment, runtime execution, and invocation.

Trade-offs:

- the experiment intentionally triggers a Security Hub High-severity posture if that control is enabled;
- PUBLIC mode is not a production-ready network conclusion;
- a retained Runtime will require a separate VPC/private-connectivity decision;
- cross-Region model authorization remains operationally sensitive to inference-profile destination changes and must be revalidated immediately before deployment.

## Validation requirement

Before first AWS deployment:

```text
1. Terraform configuration validates with exact locked AWS provider 6.60.0
2. artifact build remains byte-reproducible
3. artifact publisher is content-addressed and create-only
4. execution-role policy excludes capability/data-plane authority
5. deployment role remains main-only OIDC
6. no feature-branch AWS deployment occurs
7. exact current model/profile destination Regions are rechecked
8. offline request/failure tests remain green
```

After protected merge, perform one authenticated six-case replay, one meaningful authorization/failure experiment, capture cost/latency/session evidence, and delete the runtime before deciding whether AgentCore Runtime should be retained.

## References checked on 2026-09-08

- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-vpc.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-security-best-practices.html
- https://docs.aws.amazon.com/securityhub/latest/userguide/bedrockagentcore-controls.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-lifecycle-settings.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-invoke-agent.html
- https://docs.aws.amazon.com/service-authorization/latest/reference/list_bedrock-agentcore.html
- https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/v6.60.0/website/docs/r/bedrockagentcore_agent_runtime.html.markdown
- `docs/adr/0024-phase7-runtime-iam-boundary.md`
