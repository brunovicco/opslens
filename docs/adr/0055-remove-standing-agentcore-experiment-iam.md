# ADR 0055 — Remove Standing AgentCore Experiment IAM After the Retention Decision

- Status: Accepted
- Date: 2026-09-09
- Phase: 14 — Amazon Bedrock AgentCore
- Gate: 14.4 — Standing AgentCore Experiment IAM Cleanup and Phase Closeout

## Context

Gate 14.3 retained Amazon Bedrock AgentCore Runtime only as a disabled-by-default optional lab/deployment target. It explicitly did not retain AgentCore as the default OpsLens reasoning runtime, did not retain the Gate 14.2 `PUBLIC` network posture, and concluded that standing experiment-specific GitHub deployment/replay IAM is no longer justified without an active experiment.

The Gate 14.2 runtime itself has already been deleted and independently verified as `RESOURCE_NOT_FOUND`. The remaining standing authority is human-bootstrap IAM created solely to let the main-only GitHub deployment plane deploy the bounded Runtime and let a separate replay identity invoke it.

Current bootstrap resources are isolated as follows:

```text
infra/bootstrap/github_agentcore_deploy_permissions.tf
 -> aws_iam_policy.github_actions_agentcore_deploy
 -> aws_iam_role_policy_attachment.github_actions_agentcore_deploy
 -> OpsLensAgentCoreDeployDevAccess

infra/bootstrap/github_agentcore_replay_role.tf
 -> aws_iam_role.github_actions_agentcore_replay
 -> aws_iam_role_policy.github_actions_agentcore_replay
 -> OpsLensAgentCoreReplayRole

infra/bootstrap/outputs.tf
 -> github_actions_agentcore_replay_role_arn
```

The account-level Runtime Identity service-linked role is separate:

```text
aws_iam_service_linked_role.bedrock_agentcore_runtime_identity
service: runtime-identity.bedrock-agentcore.amazonaws.com
lifecycle: prevent_destroy = true
```

That service-linked role is an AWS service-owned account prerequisite, not a GitHub invocation/deployment principal. Its safe deletion has not been proven and the current Terraform configuration deliberately protects it from destruction.

## Decision

Remove the standing GitHub experiment authority from Terraform and AWS, while preserving the AgentCore implementation and historical evidence as an optional lab target.

Repository cleanup:

```text
DELETE configuration:
  infra/bootstrap/github_agentcore_deploy_permissions.tf
  infra/bootstrap/github_agentcore_replay_role.tf

REMOVE output:
  github_actions_agentcore_replay_role_arn

KEEP:
  infra/bootstrap/agentcore_runtime_identity_service_linked_role.tf
  AgentCore runtime/module/application code
  agentcore-runtime-experiment workflow
  direct-code packaging path
  Gate 14.1–14.3 ADRs/labs/evidence
```

Expected human-bootstrap Terraform destroy set after protected merge:

```text
aws_iam_role_policy_attachment.github_actions_agentcore_deploy
aws_iam_policy.github_actions_agentcore_deploy
aws_iam_role_policy.github_actions_agentcore_replay
aws_iam_role.github_actions_agentcore_replay
```

The exact saved Terraform plan is authoritative. Human apply must stop if any unrelated destroy/change appears.

## Why keep the Runtime Identity service-linked role

Gate 14.4 does not have evidence that deleting `AWSServiceRoleForBedrockAgentCoreRuntimeIdentity` is safe at the account level. In addition, the resource is explicitly protected with `prevent_destroy = true`.

Keeping it does not preserve the experiment's ambient GitHub authority:

```text
GitHub deploy permission for AgentCore: removed
GitHub replay invocation role:          removed
service-linked role:                    retained / AWS-service scoped
```

A later independent cleanup may reconsider the service-linked role only after proving that no current or future account dependency requires it. Gate 14.4 will not weaken `prevent_destroy` merely to obtain a cosmetically empty AgentCore footprint.

## Workflow consequence

`.github/workflows/agentcore-runtime-experiment.yml` remains in the repository as reproducible historical lab automation, but after the human IAM cleanup it is intentionally non-operational because its deploy/replay authority is absent.

This is fail-closed by design.

A future AgentCore re-entry must first create a new evidence-backed issue and explicitly re-bootstrap the minimum required authority. It must also make a new network decision; the Gate 14.2 `PUBLIC` exception must not be inherited.

The retained workflow therefore means:

```text
reproducible experiment recipe != ambient permission to run experiment
```

## Human bootstrap boundary

The feature branch and PR perform no AWS mutation.

After protected merge, the human bootstrap plane using `opslens-bootstrap` must:

1. verify no bounded AgentCore Runtime remains;
2. initialize/refresh `infra/bootstrap` from merged `main`;
3. produce and save an exact Terraform plan;
4. verify the plan contains only the intended AgentCore experiment IAM destroys plus output disappearance;
5. apply the reviewed plan;
6. rerun Terraform plan and require convergence;
7. independently verify the replay role and deploy policy are absent;
8. verify `OpsLensGitHubDeployRole` itself and unrelated policies remain intact;
9. verify the service-linked role remains intentionally present.

CI cannot and must not remove its own authority.

## Preserved authority boundaries

After cleanup:

```text
GitHub Actions OIDC:                         RETAIN, unchanged
OpsLensGitHubDeployRole:                     RETAIN, unrelated deployment authority intact
AgentCore deploy managed policy attachment: REMOVE
OpsLensAgentCoreReplayRole:                  REMOVE
AgentCore Runtime Identity SLR:              RETAIN, service-owned account prerequisite
feature-branch OIDC widening:                NONE
AgentCore Runtime resource:                  NONE
capability execution:                        NONE
runtime-exposure authority:                  NONE
```

Permanent boundaries remain:

```text
Agents reason. Code verifies evidence.
AgentCore hosting != business authorization
runtime authentication != capability authorization
runtime session != identity authority
runtime execution role != model/tool authority
runtime telemetry != business truth
runtime deployment != runtime-exposure truth
Repository Risk != Runtime Exposure
```

## Alternatives considered

### Keep the GitHub IAM for convenience

Rejected. Gate 14.3 did not retain AgentCore as an active/default runtime. Ambient deployment and invocation authority without an active workload violates the project's least-privilege discipline.

### Delete all AgentCore code and evidence

Rejected. The implementation, failed-attempt history, final measured run, lifecycle lessons, and reproducible package path remain valuable architecture and certification evidence. The correct cleanup target is ambient authority, not historical knowledge.

### Delete the Runtime Identity service-linked role now

Rejected for this gate. Safe account-level deletion is unproven and Terraform deliberately sets `prevent_destroy = true`. Removing that guard without evidence would weaken safety to make the cleanup appear more complete.

### Disable or delete the historical workflow

Not required. With the deploy policy and replay role removed, the workflow cannot complete an AgentCore experiment. Retaining it preserves the exact lab recipe while fail-closing on missing bootstrap authority. Any future reactivation still requires a new architecture/network/IAM decision.

## Consequences

Positive:

- restores least privilege after the bounded experiment;
- removes standing GitHub AgentCore deployment and invocation authority;
- preserves all measured implementation/evidence for future learning or a justified re-entry;
- keeps the optional lab disabled by default at both Terraform and IAM layers;
- lets Phase 15 A2A start without inheriting AgentCore as a hosting assumption.

Trade-offs:

- rerunning AgentCore later requires deliberate human re-bootstrap;
- the Runtime Identity service-linked role remains as an account-level AWS-managed prerequisite;
- the historical workflow remains visible but is intentionally non-operational without re-bootstrap.

## Validation and closeout

The code-side cleanup is complete only when exact-head CI validates the branch and the PR is protected-merged.

Phase 14 itself is complete only after the human bootstrap apply proves the intended IAM resources are actually absent and the repository records immutable Gate 14.4 cleanup evidence.

Until that post-merge AWS checkpoint exists:

```text
Gate 14.4 implementation: PREDEPLOY READY
AWS IAM cleanup:           PENDING HUMAN BOOTSTRAP
Phase 14:                  IN PROGRESS
```

## AIP-C01 learning connection

Least privilege includes removing temporary authority after an experiment, not merely constraining it while the experiment is active. A managed runtime evaluation should have a complete identity lifecycle:

```text
justify -> grant -> measure -> decide -> revoke when no longer needed
```

The service-linked-role exception also illustrates an important boundary: application deployment authority and AWS service-owned account prerequisites are different IAM surfaces and should not be deleted under the same evidence standard.
