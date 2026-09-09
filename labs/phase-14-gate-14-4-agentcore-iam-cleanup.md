# Phase 14 — Gate 14.4: Standing AgentCore Experiment IAM Cleanup

_Date: 2026-09-09_

## Status

**PREDEPLOY READY — REPOSITORY CLEANUP IMPLEMENTED; HUMAN BOOTSTRAP AWS REMOVAL PENDING.**

```text
issue:       #224
source main: 9f044a47d4605d1624aec6784e1994e54e6e75e3
```

Gate 14.3 retained AgentCore only as an optional disabled-by-default lab target. Gate 14.4 removes the ambient GitHub IAM that existed solely to deploy and invoke the completed Gate 14.2 experiment.

## Cleanup boundary

The Runtime itself is already absent from Gate 14.2 cleanup evidence:

```text
Terraform runtime cleanup: 0 add / 0 change / 3 destroy
independent verifier:      RESOURCE_NOT_FOUND
```

This gate targets only standing experiment bootstrap authority:

```text
OpsLensGitHubDeployRole
 -> REMOVE attachment: OpsLensAgentCoreDeployDevAccess

OpsLensAgentCoreReplayRole
 -> REMOVE invocation-only inline policy
 -> REMOVE role
```

The shared deployment role itself is retained. The GitHub OIDC provider is retained. No unrelated deployment authority is changed.

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

Retained unchanged:

```text
infra/bootstrap/agentcore_runtime_identity_service_linked_role.tf
 -> aws_iam_service_linked_role.bedrock_agentcore_runtime_identity
 -> prevent_destroy = true
```

The service-linked role is not a GitHub deployment/replay principal and is not deleted without independent proof that account-level removal is safe.

## Expected human Terraform plan

After protected merge, the expected bootstrap plan is limited to destruction of:

```text
aws_iam_role_policy_attachment.github_actions_agentcore_deploy
aws_iam_policy.github_actions_agentcore_deploy
aws_iam_role_policy.github_actions_agentcore_replay
aws_iam_role.github_actions_agentcore_replay
```

The replay-role output disappears from Terraform output state as a consequence of the configuration removal.

The expected plan is a hypothesis until produced by the human bootstrap plane. The actual saved Terraform plan is authoritative.

Do not apply if the plan includes:

```text
OpsLensGitHubDeployRole destruction
GitHub OIDC provider destruction
Runtime Identity service-linked role destruction
unrelated IAM/resource changes
unexpected creates or replacements
```

## Why the workflow remains

The historical `.github/workflows/agentcore-runtime-experiment.yml` is retained together with the runtime/module/package code and evidence.

After IAM cleanup, the workflow cannot complete because the exact deployment policy and replay role no longer exist. That is intentional:

```text
historical reproducible automation
!=
standing permission to execute it
```

A future AgentCore experiment must first justify a new workload, network posture, and re-bootstrap of minimum authority. It cannot inherit the Gate 14.2 `PUBLIC` network exception automatically.

## No AWS action from feature branch

This branch performs only repository/Terraform desired-state changes.

```text
new AgentCore Runtime:          0
new AgentCore invocation:       0
capability executions:         0
feature-branch AWS deployment:  0
feature-branch OIDC widening:   0
AWS IAM deletions so far:       0
```

AWS deletion is intentionally deferred until protected merge and human `opslens-bootstrap` review/apply.

## Human post-merge procedure

From merged `main`:

```bash
git switch main
git pull --ff-only
aws sso login --profile opslens-bootstrap

AWS_PROFILE=opslens-bootstrap terraform -chdir=infra/bootstrap init -input=false
AWS_PROFILE=opslens-bootstrap terraform -chdir=infra/bootstrap plan \
  -input=false \
  -lock-timeout=30s \
  -out=/tmp/opslens-agentcore-iam-cleanup.tfplan

AWS_PROFILE=opslens-bootstrap terraform -chdir=infra/bootstrap show \
  -no-color /tmp/opslens-agentcore-iam-cleanup.tfplan
```

Only after exact review:

```bash
AWS_PROFILE=opslens-bootstrap terraform -chdir=infra/bootstrap apply \
  -input=false /tmp/opslens-agentcore-iam-cleanup.tfplan
```

Then require convergence:

```bash
AWS_PROFILE=opslens-bootstrap terraform -chdir=infra/bootstrap plan \
  -input=false \
  -lock-timeout=30s \
  -detailed-exitcode
```

Expected convergence exit code:

```text
0
```

## Independent IAM verification

After apply, verify at minimum:

```bash
aws iam get-role \
  --role-name OpsLensAgentCoreReplayRole \
  --profile opslens-bootstrap

aws iam get-policy \
  --policy-arn arn:aws:iam::487757851499:policy/OpsLensAgentCoreDeployDevAccess \
  --profile opslens-bootstrap

aws iam get-role \
  --role-name OpsLensGitHubDeployRole \
  --profile opslens-bootstrap

aws iam get-role \
  --role-name AWSServiceRoleForBedrockAgentCoreRuntimeIdentity \
  --profile opslens-bootstrap
```

Expected semantic result:

```text
OpsLensAgentCoreReplayRole:                 NoSuchEntity
OpsLensAgentCoreDeployDevAccess:            NoSuchEntity
OpsLensGitHubDeployRole:                    PRESENT
AWSServiceRoleForBedrockAgentCoreRuntimeIdentity: PRESENT / intentionally retained
```

The exact AWS CLI error payload may vary; capture exit codes and stable semantic outcomes rather than treating human-readable wording as the authority.

## Closeout evidence still required

Gate 14.4 is not complete merely because Terraform code deletes the resources.

Required post-merge evidence:

```text
protected merge SHA
human bootstrap plan summary
human bootstrap apply summary
post-apply convergence
independent IAM absence/presence checks
no unrelated resource impact
final repository state sync
```

Only then may Phase 14 move to `COMPLETE` and Phase 15 become the next authorized phase.

## Evidence

Offline/predeploy artifact:

```text
labs/evidence/phase-14-gate-14-4-agentcore-iam-cleanup-predeploy-v1.json
```

Architecture decision:

```text
docs/adr/0055-remove-standing-agentcore-experiment-iam.md
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
[ ] exact-head CI green
[ ] protected merge
[ ] human bootstrap plan contains only intended cleanup
[ ] human bootstrap apply succeeds
[ ] bootstrap plan converges after apply
[ ] replay role absence independently verified
[ ] deploy policy absence independently verified
[ ] shared deploy role presence verified
[ ] service-linked role intentional retention verified
[ ] immutable post-apply evidence recorded
[ ] Phase 14 closeout synchronized
```
