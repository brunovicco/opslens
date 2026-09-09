# Phase 14 — Gate 14.4: Standing AgentCore Experiment IAM Cleanup

_Date: 2026-09-09_

## Status

**COMPLETE — STANDING EXPERIMENT-SPECIFIC GITHUB IAM REMOVED AND VERIFIED.**

```text
issue:                  #224
implementation PR:      #225
implementation merge:   9913c3cbf5f2239d6445042a139a9cca890590c8
exact-head AgentCore CI: 34396085154 / run #63 / PASS
exact-head Terraform CI: 34396085123 / run #267 / PASS
```

Gate 14.3 retained AgentCore only as an optional disabled-by-default lab target. Gate 14.4 removes the ambient GitHub IAM that existed solely to deploy and invoke the completed Gate 14.2 experiment.

## Cleanup boundary

The Runtime itself was already absent from Gate 14.2 cleanup evidence:

```text
Terraform runtime cleanup: 0 add / 0 change / 3 destroy
independent verifier:      RESOURCE_NOT_FOUND
```

Gate 14.4 therefore targeted only standing experiment bootstrap authority:

```text
OpsLensGitHubDeployRole
 -> REMOVE attachment: OpsLensAgentCoreDeployDevAccess

OpsLensAgentCoreReplayRole
 -> REMOVE invocation-only inline policy
 -> REMOVE role
```

The shared deployment role itself remains. The GitHub OIDC provider remains. The account-level Runtime Identity service-linked role remains intentionally protected.

## Repository implementation

Removed Terraform configuration:

```text
infra/bootstrap/github_agentcore_deploy_permissions.tf
infra/bootstrap/github_agentcore_replay_role.tf
```

Removed output:

```text
infra/bootstrap/outputs.tf
 -> github_actions_agentcore_replay_role_arn
```

Retained:

```text
infra/bootstrap/agentcore_runtime_identity_service_linked_role.tf
 -> aws_iam_service_linked_role.bedrock_agentcore_runtime_identity
 -> prevent_destroy = true
```

The service-linked role is AWS-service/account scoped rather than GitHub ambient experiment authority. Safe deletion has not been proven, so Gate 14.4 does not weaken `prevent_destroy` merely to produce an empty-looking footprint.

## Human bootstrap plan and apply

The reviewed saved plan from merged `main` was exactly:

```text
Plan: 0 to add, 0 to change, 4 to destroy.
```

Destroyed exactly:

```text
aws_iam_policy.github_actions_agentcore_deploy
aws_iam_role.github_actions_agentcore_replay
aws_iam_role_policy.github_actions_agentcore_replay
aws_iam_role_policy_attachment.github_actions_agentcore_deploy
```

No creates, updates, replacements, unrelated destroys, or service-linked-role destruction appeared.

Apply result:

```text
Apply complete! Resources: 0 added, 0 changed, 4 destroyed.
```

## Terraform convergence

A fresh post-apply bootstrap plan returned:

```text
No changes. Your infrastructure matches the configuration.
```

This proves the Terraform control plane converged after the cleanup rather than merely accepting a successful destroy command.

## Independent IAM verification

Post-apply AWS IAM checks produced:

```text
OpsLensAgentCoreReplayRole:
  ABSENT / NoSuchEntity

OpsLensAgentCoreDeployDevAccess:
  ABSENT / NoSuchEntity

OpsLensAgentCoreDeployDevAccess attached to OpsLensGitHubDeployRole:
  []

OpsLensGitHubDeployRole:
  PRESENT

AWSServiceRoleForBedrockAgentCoreRuntimeIdentity:
  PRESENT / intentionally retained
```

This separates the intended outcome clearly:

```text
experiment-only AgentCore authority removed
!=
shared GitHub deployment identity removed
```

## Workflow disposition

`.github/workflows/agentcore-runtime-experiment.yml` remains as historical/reproducible lab automation together with runtime/module/package code and evidence.

After Gate 14.4, that workflow is intentionally non-operational until a future AgentCore experiment explicitly re-bootstraps minimum authority:

```text
historical reproducible automation
!=
standing permission to execute it
```

A future AgentCore re-entry must start from a new evidence-backed issue and make a new network decision. The Gate 14.2 `PUBLIC` exception is not inherited.

## Authority outcome

Gate 14.4 closes the standing-IAM gap without moving any business authority:

```text
agent proposal != authorization
runtime authentication != capability authorization
runtime execution role != model/tool authority
runtime deployment != runtime-exposure truth
AgentCore hosting != business authorization
```

No new Runtime, invocation, capability execution, feature-branch AWS credential path, or OIDC widening was introduced.

## Phase 14 closeout consequence

With Gate 14.4 complete, the final Phase 14 retained state is:

```text
Phase 11 direct Bedrock reasoning reference:  RETAIN / DEFAULT
AgentCore implementation/evidence:           RETAIN
AgentCore managed Runtime as default:         DO NOT RETAIN
AgentCore standing Runtime resources:         DO NOT RETAIN / NONE
AgentCore standing experiment GitHub IAM:     REMOVED
PUBLIC network exception:                     DO NOT RETAIN
Runtime Identity service-linked role:         RETAIN pending separate safety proof
```

Phase 15 A2A may begin without assuming AgentCore as its hosting substrate.

## Evidence

Predeploy evidence:

```text
labs/evidence/phase-14-gate-14-4-agentcore-iam-cleanup-predeploy-v1.json
```

Post-apply evidence:

```text
labs/evidence/phase-14-gate-14-4-agentcore-iam-cleanup-postapply-v1.json
```

Architecture decision:

```text
docs/adr/0055-remove-standing-agentcore-experiment-iam.md
```

Durable human-bootstrap checkpoint:

```text
issue #224 comment 5607892995
```

## Exit checklist

```text
[x] exact standing GitHub AgentCore IAM scope identified
[x] deploy policy/attachment removed from Terraform desired state
[x] replay role/policy removed from Terraform desired state
[x] replay role output removed
[x] Runtime Identity service-linked role preserved with prevent_destroy
[x] AgentCore runtime/module/workflow/evidence preserved
[x] no feature-branch AWS mutation
[x] exact-head CI green
[x] protected merge
[x] human bootstrap plan contains only intended cleanup
[x] human bootstrap apply succeeds
[x] bootstrap plan converges after apply
[x] replay role absence independently verified
[x] deploy policy absence independently verified
[x] shared deploy role presence verified
[x] service-linked role intentional retention verified
[x] immutable post-apply evidence recorded
[x] Phase 14 closeout ready for repository state synchronization
```
