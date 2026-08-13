# ADR-0002: GitHub Actions OIDC Deployment Identity

- Status: Accepted
- Date: 2026-08-13

## Context

OpsLens needs GitHub Actions to plan and deploy Terraform without storing long-lived AWS access keys in GitHub.

The deployment mechanism must also preserve a clear separation between:

- human bootstrap authority;
- CI federation trust;
- CI workload permissions;
- runtime application identities introduced later.

Allowing CI to administer the IAM trust relationship that grants CI its own AWS identity would weaken that separation.

## Decision

OpsLens uses GitHub Actions OpenID Connect federation with AWS STS.

The AWS OIDC provider is:

```text
https://token.actions.githubusercontent.com
```

with audience:

```text
sts.amazonaws.com
```

GitHub Actions assumes:

```text
arn:aws:iam::487757851499:role/OpsLensGitHubDeployRole
```

The role trust policy allows `sts:AssumeRoleWithWebIdentity` only for the immutable GitHub OIDC subject corresponding to the `main` branch:

```text
repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/main
```

The role session duration is bounded to one hour.

No persistent AWS access keys are stored in GitHub.

## Authority split

### Human bootstrap

AWS IAM Identity Center is used for temporary human bootstrap access.

Human bootstrap owns:

- the GitHub OIDC provider;
- the deployment-role trust relationship;
- deployment-role permission policies;
- Terraform bootstrap/state infrastructure.

CI is not granted IAM permissions to alter these controls.

### GitHub deployment role

`OpsLensGitHubDeployRole` receives only permissions required by the current `dev` deployment.

During Phase 0 these include:

- exact access to the `environments/dev/terraform.tfstate` state object;
- exact access to its `.tflock` object;
- CloudWatch Logs infrastructure permissions for `/opslens/dev/platform`;
- `logs:DescribeLogGroups`;
- create-time tagging permission constrained by the exact required OpsLens tags.

The role is not granted:

- `iam:*`;
- access to the bootstrap Terraform state;
- unrestricted `s3:*`;
- unrestricted `logs:*`;
- application log-writing permissions such as `logs:PutLogEvents`.

Future phases extend the role only when a concrete Terraform-managed resource requires additional deployment authority.

## CI separation

Static Terraform checks do not require AWS credentials.

The static/security workflow runs:

- Terraform formatting checks;
- Terraform validation;
- TFLint;
- Checkov.

AWS OIDC is used only by trusted workflows that need AWS-backed planning or deployment.

## Validation

The trust boundary was validated through both positive and negative paths.

### Positive path

GitHub Actions run:

```text
31739269032
```

on `main` successfully assumed the deployment role and returned:

```text
arn:aws:sts::487757851499:assumed-role/OpsLensGitHubDeployRole/GitHubActions
```

### Negative path

GitHub Actions run:

```text
31739453390
```

from `oidc-failure-test` failed with:

```text
Not authorized to perform sts:AssumeRoleWithWebIdentity
```

The caller-identity step was never reached because no AWS role session was created.

CloudTrail showed one successful and twelve denied `AssumeRoleWithWebIdentity` calls in the inspected test window.

See:

```text
docs/labs/phase-0-iam-oidc-failure.md
```

## Real deployment proof

GitHub Actions run:

```text
31752492720
```

successfully:

1. authenticated to AWS through OIDC;
2. initialized the remote Terraform backend;
3. validated Terraform;
4. created a saved plan;
5. applied the plan;
6. created `/opslens/dev/platform` in CloudWatch Logs.

Terraform subsequently converged with no changes.

## Alternatives considered

### Static AWS access keys in GitHub Secrets

Rejected.

Long-lived access keys create rotation, leakage, revocation, and secret-management obligations that are unnecessary when workload identity federation is available.

### Broad administrator role for GitHub Actions

Rejected.

The CI role should grow incrementally from explicit resource requirements rather than begin with administrative access.

### Let CI manage its own IAM trust and permissions

Rejected.

A principal should not normally be able to widen the trust or authorization boundary that controls its own authority.

### Human-only Terraform deployment

Rejected as the steady-state deployment path.

Human bootstrap remains necessary for trust-boundary changes, but repeatable workload deployment should be automated through short-lived CI credentials.

## Consequences

### Positive

- no persistent AWS credentials in GitHub;
- short-lived STS credentials;
- repository/branch-constrained trust;
- auditable federation through CloudTrail;
- explicit separation between trust and authorization;
- CI cannot grant itself broader AWS authority;
- workload deployment is repeatable.

### Trade-offs

- IAM permissions must evolve as Terraform begins managing new AWS resource types;
- some AWS APIs have dependent permissions that require careful least-privilege modeling;
- trust-policy changes require human bootstrap access;
- a main-only trust relationship means branch deployments are intentionally denied unless a future ADR changes the model.

## Security lesson

An `AccessDenied` must be diagnosed at the correct layer.

```text
AssumeRoleWithWebIdentity denied
 -> federation / trust-policy problem

AWS service API denied after role assumption
 -> authorization-policy or resource-policy problem
```

Broadening resource permissions cannot fix an OIDC trust failure, and changing OIDC trust cannot fix a missing service permission.
