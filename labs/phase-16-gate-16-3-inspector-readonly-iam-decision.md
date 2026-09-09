# Phase 16 Gate 16.3 — Minimum Amazon Inspector Read-Only IAM Boundary Decision

## Status

```text
COMPLETE / ACCEPT DEDICATED TEMPORARY DISCOVERY ROLE
```

## Measured trigger

Gate 16.2 proved that the existing GitHub deployment role cannot read the first required Inspector discovery surface:

```text
run:                      34411934819 / #1
job:                      102668116801
workflow conclusion:      SUCCESS
experiment result:        BLOCKED_BY_EXISTING_IAM
ListCoverage:             ACCESS_DENIED / AccessDeniedException
ListFindings:             NOT_ATTEMPTED
AWS mutations:            0
new IAM:                  0
```

Authentication succeeded while Inspector authorization failed.

## Decision question

What is the smallest independently reviewable authority that can support one second bounded read-only Inspector experiment?

Options:

```text
A. widen OpsLensGitHubDeployRole
B. create a dedicated temporary Inspector discovery role
C. stop Phase 16
```

## Option comparison

### A — widen the deploy role

Rejected.

`OpsLensGitHubDeployRole` already exists to perform general deployment/bootstrap work. Adding Inspector reads would make every eligible use of that shared principal carry runtime-evidence authority as well.

This would reduce resource count but increase blast radius and standing permission coupling.

### B — dedicated temporary discovery role

Accepted.

The experiment gets a separate principal with exactly two Inspector list actions and no deployment permissions:

```text
OpsLensInspectorDiscoveryRole
 -> inspector2:ListCoverage
 -> inspector2:ListFindings
```

The AWS Service Authorization Reference exposes no resource type for these actions, so resource-level ARN restriction is unavailable. The resulting `Resource = "*"` is compensated by:

```text
exact two-action allowlist
aws:RequestedRegion == us-east-1
main-only immutable GitHub OIDC subject
900-second requested STS session
no other service permissions
mandatory teardown after one measured experiment
```

### C — stop Phase 16

Rejected for now.

The measured denial did not answer whether the account contains useful Inspector coverage/finding evidence. Because the required permission surface is only two isolated read actions, one reversible experiment remains justified.

## Frozen Gate 16.4 IAM contract

```text
role:                       OpsLensInspectorDiscoveryRole
purpose:                    experiment-only Inspector discovery
OIDC provider:              existing GitHub Actions provider
audience:                   sts.amazonaws.com
subject:                    repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/main
allowed action 1:           inspector2:ListCoverage
allowed action 2:           inspector2:ListFindings
resource:                   *
region condition:           aws:RequestedRegion == us-east-1
requested session:          900 seconds
inspector write actions:    0
IAM actions:                0
other AWS actions:          0
model invocations:          0
capability executions:      0
```

## Why no workflow-specific OIDC claim

GitHub documents that AWS does not support custom GitHub OIDC claims. OpsLens therefore keeps the already-established immutable repository/main `sub` boundary rather than depending on a claim AWS cannot evaluate.

A GitHub Environment could change the standard `sub` shape, but adding an out-of-band environment control is not necessary for this one experiment and would create a new configuration dependency that has not been measured or provisioned by the project.

## Teardown contract

The accepted role is temporary.

After one Gate 16.4 discovery run:

```text
1. preserve the content-minimized measured evidence;
2. remove the experiment role/policy from Terraform;
3. human-apply the cleanup;
4. independently verify the role is absent;
5. only then decide whether any retained runtime Inspector identity is justified.
```

The experiment role must not become a production/runtime identity by default.

## Authority boundaries retained

```text
AWS authentication != Inspector read authorization
Inspector read authorization != business authority
Inspector coverage != vulnerability finding
Inspector finding != repository finding
Inspector package match != deployed application ownership
Inspector resource presence != network exposure
Inspector PACKAGE_VULNERABILITY != NETWORK_REACHABILITY
Inspector evidence != model authority
Repository Risk != Runtime Exposure
```

## Gate 16.4 authorization

Gate 16.4 is authorized to implement the frozen Terraform/workflow slice **offline in the repository**.

A real AWS IAM apply remains a human execution boundary.

Allowed repository changes:

```text
infra/bootstrap temporary Inspector discovery role/policy
workflow role-to-assume switch to the dedicated role
role-duration-seconds = 900
Terraform / CI guardrails
negative-permission tests where feasible
```

Not authorized:

```text
apply IAM automatically from this decision gate
modify OpsLensGitHubDeployRole permissions
enable/disable Inspector
change scan configuration
add EventBridge
perform repository/runtime correlation
create runtime-risk score
invoke a model
execute an agent capability
```

## Sources

- AWS Service Authorization Reference — Amazon Inspector2: https://docs.aws.amazon.com/service-authorization/latest/reference/list_inspector2.html
- AWS global condition context keys: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html
- GitHub Actions OIDC in AWS: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
- OpsLens current OIDC trust: `infra/bootstrap/github_role.tf`
- Gate 16.2 evidence: `labs/evidence/phase-16-gate-16-2-inspector-readonly-discovery-v1.json`

Canonical architecture decision: `docs/adr/0061-dedicated-temporary-inspector-discovery-role.md`.

PR #89 remains untouched.
