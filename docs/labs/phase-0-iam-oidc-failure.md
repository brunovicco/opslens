# Phase 0 IAM/OIDC Failure Lab

## Objective

Validate and diagnose the GitHub Actions to AWS OIDC trust boundary used by OpsLens.

The experiment verifies that:

- the trusted `main` branch can assume the deployment role;
- an untrusted branch cannot assume the same role;
- the failure happens at the STS trust boundary, before AWS resource permissions are evaluated;
- the result can be correlated between GitHub Actions and AWS CloudTrail.

## Architecture under test

GitHub Actions authenticates to AWS using OpenID Connect and temporary STS credentials.

No persistent AWS access keys are stored in GitHub.

The target role is:

```text
arn:aws:iam::487757851499:role/OpsLensGitHubDeployRole
```

The trust policy requires:

```text
aud = sts.amazonaws.com

sub =
repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/main
```

Therefore, only the `main` branch subject is accepted by the current trust relationship.

## Positive test

GitHub Actions run:

```text
Run ID: 31739269032
Branch: main
Result: success
```

The OIDC authentication succeeded and AWS STS returned the assumed-role identity:

```text
arn:aws:sts::487757851499:assumed-role/OpsLensGitHubDeployRole/GitHubActions
```

CloudTrail recorded a successful event at:

```text
2026-08-13T20:07:26Z
```

with:

```text
eventName: AssumeRoleWithWebIdentity
awsRegion: us-east-1
errorCode: null
roleArn: arn:aws:iam::487757851499:role/OpsLensGitHubDeployRole
roleSessionName: GitHubActions
```

## Negative test

A temporary branch named:

```text
oidc-failure-test
```

executed the same workflow against the same AWS role.

GitHub Actions run:

```text
Run ID: 31739453390
Branch: oidc-failure-test
Result: failure
```

The workflow failed during AWS credential configuration.

The subsequent caller identity step was never executed because no AWS role session was created.

The observed error was:

```text
Not authorized to perform sts:AssumeRoleWithWebIdentity
```

## CloudTrail evidence

CloudTrail Event History was queried for:

```text
EventName = AssumeRoleWithWebIdentity
Region    = us-east-1
Window    = 2026-08-13T20:00:00Z to 2026-08-13T20:15:00Z
```

Thirteen events were returned:

```text
1 successful AssumeRoleWithWebIdentity call
12 denied AssumeRoleWithWebIdentity calls
```

The twelve denied calls correspond to the retry behavior observed in the failed GitHub Actions job.

The rejected events contained:

```text
errorCode: AccessDenied
errorMessage: Not authorized to perform sts:AssumeRoleWithWebIdentity
```

In the inspected CloudTrail projection, `roleArn` and `roleSessionName` were not populated for the denied events.

## Root cause

The failure was intentional.

The IAM role trust policy only accepts the immutable GitHub OIDC subject associated with:

```text
refs/heads/main
```

The temporary branch produces a different subject and therefore does not satisfy the `sub` condition.

The request is rejected by AWS STS before a role session is created.

This is a trust-policy failure, not an authorization-policy failure.

The role's S3 permissions are therefore irrelevant to this specific failure.

## Diagnosis model

When diagnosing GitHub Actions to AWS failures, separate authentication/trust from authorization:

```text
GitHub OIDC token
        |
        v
IAM role trust policy
        |
        +--- rejected ---> AssumeRoleWithWebIdentity AccessDenied
        |
        v
STS role session
        |
        v
IAM permissions policy
        |
        +--- rejected ---> AWS service action AccessDenied
        |
        v
AWS resource
```

A failure at `AssumeRoleWithWebIdentity` indicates that troubleshooting should begin with:

- OIDC provider configuration;
- token audience;
- token subject;
- IAM role trust conditions.

Broadening the role's resource permissions would not fix this class of failure.

## Recovery procedure

For an unexpected OIDC trust failure:

1. Confirm the GitHub workflow ref and triggering branch.
2. Inspect the IAM role trust policy.
3. Compare the expected `aud` and `sub` claims with the configured conditions.
4. Inspect the GitHub Actions authentication step.
5. Correlate `AssumeRoleWithWebIdentity` events in CloudTrail.
6. Change the trust policy only if the new identity path is intentionally authorized.
7. Re-test both an allowed and a denied path.

Do not solve a trust-policy failure by granting broader AWS resource permissions.

## Security conclusion

The experiment validates a fail-closed trust boundary:

```text
authorized main branch     -> temporary AWS session
unauthorized test branch   -> no AWS session
```

The GitHub deployment role remains branch-constrained and no persistent AWS access keys are required.

## Phase 0 learning outcome

This lab demonstrates the distinction between:

- identity federation;
- IAM trust policies;
- STS role assumption;
- temporary credentials;
- resource authorization;
- CloudTrail audit evidence.

It also provides a repeatable troubleshooting model for federated CI/CD authentication failures.
