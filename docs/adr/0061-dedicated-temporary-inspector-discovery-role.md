# ADR 0061 — Use a Dedicated Temporary IAM Role for Inspector Discovery

- Status: Accepted
- Date: 2026-09-09
- Phase: 16 — Runtime Exposure with Amazon Inspector
- Gate: 16.3 — Minimum Inspector Read-Only IAM Boundary Decision

## Context

Gate 16.2 attempted the bounded Inspector read surface with the already-existing `OpsLensGitHubDeployRole` and produced measured terminal evidence:

```text
workflow:                 Inspector Read-Only Discovery
run:                      34411934819 / #1
job:                      102668116801
workflow conclusion:      SUCCESS
experiment result:        BLOCKED_BY_EXISTING_IAM
ListCoverage:             ACCESS_DENIED / AccessDeniedException
ListFindings:             NOT_ATTEMPTED after fail-closed stop
AWS mutations:            0
new IAM:                  0
```

OIDC authentication and role assumption succeeded. Inspector read authorization did not.

The next experiment therefore needs an explicit IAM decision if Phase 16 is to continue. That decision must not silently turn a general deployment role into a broader cross-domain read principal.

## Current repository facts

`OpsLensGitHubDeployRole` is the general GitHub Actions deployment identity. It already carries multiple unrelated bootstrap and deployment permissions.

Its current OIDC trust is restricted to:

```text
aud = sts.amazonaws.com
sub = repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/main
```

The immutable owner/repository identifiers are already part of the subject claim.

## Current upstream IAM facts

The AWS Service Authorization Reference classifies both selected Inspector2 actions as `List` actions:

```text
inspector2:ListCoverage
inspector2:ListFindings
```

The authorization table does not expose a resource type for either action. Therefore the identity policy cannot be narrowed to an Inspector resource ARN for these calls and must use:

```json
"Resource": "*"
```

The action set can still be narrowed exactly, and the global `aws:RequestedRegion` condition can constrain the invoked service endpoint to `us-east-1`.

GitHub's AWS OIDC guidance states that AWS does not support custom GitHub OIDC claims. The existing immutable `sub` claim therefore remains the reproducible trust boundary for this experiment rather than inventing a workflow-specific claim that AWS cannot evaluate.

References:

- AWS Service Authorization Reference — Amazon Inspector2: https://docs.aws.amazon.com/service-authorization/latest/reference/list_inspector2.html
- AWS global condition context keys: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html
- GitHub Actions OIDC in AWS: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws

## Options considered

### Option A — widen `OpsLensGitHubDeployRole`

Advantages:

```text
fewest Terraform resources
no workflow trust change
fastest path to another experiment
```

Disadvantages:

```text
adds Inspector read authority to every eligible use of the general deploy role
mixes deployment and runtime-evidence discovery responsibilities
increases standing blast radius
makes later removal less obvious because authority is embedded in a shared principal
```

Decision: **Rejected**.

### Option B — dedicated temporary Inspector discovery role

Advantages:

```text
isolates runtime-evidence discovery from deployment authority
permits an exact two-action identity policy
supports explicit region restriction
supports explicit short STS session request
can be independently verified and removed after the experiment
creates a clean negative-permission surface
```

Disadvantages:

```text
adds temporary IAM resources
reuses the repository/main OIDC trust rather than a workflow-specific AWS claim
requires explicit teardown after the measured experiment
```

Decision: **Accepted**.

### Option C — stop Phase 16 without additional IAM

Advantages:

```text
zero new IAM
zero additional cloud authority
```

Disadvantages:

```text
leaves the Inspector capability-fit hypothesis unmeasured beyond authorization denial
cannot determine whether useful coverage/finding evidence exists in the account
```

Decision: **Rejected for now** because the candidate authority surface is only two read actions and can be isolated and removed after one bounded experiment.

## Decision

Gate 16.4 may implement a **temporary dedicated role** with the following frozen contract:

```text
role name:                  OpsLensInspectorDiscoveryRole
purpose:                    one bounded Inspector read-only experiment
trust provider:             existing GitHub Actions OIDC provider
audience:                   sts.amazonaws.com
subject:                    repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/main
allowed actions:            inspector2:ListCoverage
                            inspector2:ListFindings
resource:                   *
region condition:           aws:RequestedRegion == us-east-1
requested STS session:      900 seconds
Inspector write actions:    NONE
IAM mutation actions:       NONE
other AWS service actions:  NONE
model/capability authority: NONE
```

The role's permission policy must be independently reviewable and must not include wildcard Inspector actions such as `inspector2:*`.

The workflow must explicitly assume this role instead of `OpsLensGitHubDeployRole` for the experiment.

## Teardown requirement

The role is **experiment-specific**, not a retained production/runtime identity.

After one measured Gate 16.4 discovery attempt:

```text
remove OpsLensInspectorDiscoveryRole
remove its inline/attached Inspector read policy
verify both are absent
```

A later gate may separately decide whether any runtime Inspector identity is worth retaining. The experiment role must not become that identity by inertia.

## Fail-closed requirements

Gate 16.4 must preserve all Gate 16.2 behavior:

```text
AccessDenied -> measured terminal evidence
partial pagination failure -> reject partial result
cross-account response -> reject
NETWORK_REACHABILITY on non-EC2 -> reject
no automatic IAM widening
no Inspector activation/configuration change
```

The experiment must still stop before repository/runtime correlation, runtime-risk scoring, model synthesis, or agent capability execution.

## Consequences

Positive:

- deployment and discovery authority remain separated;
- the smallest possible action set is explicit;
- unavoidable `Resource = "*"` scope is compensated by exact actions and a region condition;
- the role is reversible and independently testable;
- the project gains a concrete least-privilege IAM laboratory relevant to AIP-C01.

Negative:

- one extra temporary IAM role/policy must be created and later removed;
- the role trust remains repository/main scoped because AWS cannot evaluate arbitrary GitHub custom OIDC claims;
- a second human AWS apply/cleanup boundary is required.

## Not authorized by this ADR

```text
IAM apply in AWS:                       NO — requires Gate 16.4 implementation + human apply boundary
modify OpsLensGitHubDeployRole:         NO
enable/disable Inspector:               NO
change ECR/Lambda/EC2 scan settings:    NO
EventBridge integration:                NO
suppression filters:                    NO
repository/runtime correlation:         NO
runtime-risk scoring:                   NO
model synthesis:                        NO
agent capability execution:             NO
```

PR #89 / `feat/governed-gateway-semantic-planner` remains out of scope and untouched.
