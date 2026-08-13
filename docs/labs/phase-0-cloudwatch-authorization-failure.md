# Phase 0 CloudWatch Authorization Failure Lab

## Objective

Diagnose an AWS service authorization failure that occurs after GitHub OIDC federation has already succeeded.

This lab complements the IAM/OIDC trust failure lab by demonstrating the difference between:

- trust-policy failure before an AWS role session exists;
- authorization-policy failure after the AWS role session exists.

## Scenario

OpsLens attempted its first real Terraform workload deployment from GitHub Actions.

The intended resource was:

```text
CloudWatch Log Group: /opslens/dev/platform
Region: us-east-1
Retention: 14 days
```

GitHub Actions successfully authenticated through OIDC and assumed:

```text
arn:aws:iam::487757851499:role/OpsLensGitHubDeployRole
```

The Terraform plan succeeded with:

```text
Plan: 1 to add, 0 to change, 0 to destroy.
```

## Failed deployment

GitHub Actions run:

```text
Run ID: 31751886914
Branch: main
Result: failure
```

Successful steps included:

```text
Checkout repository
Configure AWS credentials
Setup Terraform
Terraform init
Terraform validate
Terraform plan
```

The failure occurred only during:

```text
Terraform apply
```

AWS returned:

```text
AccessDeniedException:
User with accountId: 487757851499 is not authorized to perform
CreateLogGroup with Tags.

An additional permission "logs:TagResource" is required.
```

## Diagnosis

This was not an OIDC trust failure.

The GitHub runner already had temporary AWS credentials and the Terraform provider was able to query AWS and create a valid plan.

The failure therefore belonged to the authorization layer:

```text
GitHub OIDC
    |
    v
IAM trust policy
    |
    v
STS role session             SUCCESS
    |
    v
IAM permissions
    |
    v
CreateLogGroup with tags     DENIED
```

The initial IAM policy allowed:

- `logs:CreateLogGroup` for the target log group ARN;
- resource-scoped `logs:TagResource` for the target log group.

During `CreateLogGroup` with tags, CloudWatch Logs evaluated `logs:TagResource` as a dependent permission before the target resource existed in the normal post-create form.

The resource-scoped tagging statement did not satisfy that create-time authorization check.

## Fix

A separate create-time tagging statement was added.

It permits only:

```text
logs:TagResource
```

with `Resource = "*"`, but constrains the request through exact tag conditions:

```text
Project     = opslens
Environment = dev
ManagedBy   = terraform
Repository  = brunovicco/opslens
Purpose     = platform-observability
```

and restricts `aws:TagKeys` to that exact set.

The existing resource-scoped tagging permission remains in place for post-create operations.

The fix does not grant:

```text
logs:*
logs:PutLogEvents
logs:CreateLogStream
iam:*
```

## Successful deployment

After the constrained tagging permission was applied through the human bootstrap identity, GitHub Actions run:

```text
Run ID: 31752492720
Branch: main
Result: success
```

successfully created:

```text
/opslens/dev/platform
```

Terraform reported:

```text
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.
```

AWS CLI verification showed:

```text
Name:        /opslens/dev/platform
Retention:   14
StoredBytes: 0
```

A subsequent Terraform plan reported no changes.

## Trust vs authorization comparison

### Failure class 1 - trust

From the earlier OIDC lab:

```text
OIDC token
 -> IAM trust policy
 -> AccessDenied
 -> no STS role session
```

Troubleshoot:

- OIDC provider;
- `aud`;
- `sub`;
- role trust conditions.

### Failure class 2 - authorization

From this lab:

```text
OIDC token
 -> trust accepted
 -> STS role session exists
 -> AWS service action
 -> AccessDenied
```

Troubleshoot:

- identity policy;
- resource policy when applicable;
- action/resource compatibility;
- dependent permissions;
- IAM conditions.

## Security lesson

Do not respond to every AWS `AccessDenied` by broadening permissions.

First identify which boundary rejected the request.

The final policy widened only the specific dependent permission that required create-time scope, then constrained that permission with exact request tags.

This preserves the OpsLens principle:

> IAM least privilege is a design and troubleshooting process, not simply a small list of actions.
