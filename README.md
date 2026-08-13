# OpsLens

Agentic Cloud & Software Supply Chain Intelligence on AWS.

OpsLens is an open-source software supply chain intelligence platform designed to answer:

> Given the software I actually use, which vulnerabilities represent material risk, why, and what should I do about them?

## Status

**Phase 0 - AWS Foundation: complete.**
**Next:** Phase 1 - EPSS Vertical Slice.

Phase 0 established the AWS identity, infrastructure, CI/CD, cost-governance baseline, and initial observability foundation required before product functionality is introduced.

## Core principles

- Deterministic evidence and correlation first; generative reasoning second.
- Not every question is a RAG problem.
- Never execute third-party repository code.
- Repository risk and runtime exposure are separate concepts.
- IAM least privilege, cost controls, and observability are architectural requirements.
- AWS services are added only when they solve a concrete OpsLens problem.

## AWS foundation

The initial deployment uses one real environment:

- Environment: `dev`
- Primary workload Region: `us-east-1`
- Infrastructure as Code: Terraform
- Human bootstrap access: AWS IAM Identity Center
- CI/CD identity: GitHub Actions OIDC
- Remote Terraform state: Amazon S3
- Initial observability resource: CloudWatch Logs

GitHub Actions does not store persistent AWS access keys. The deployment role is assumed through OIDC and its trust policy is restricted to the repository's `main` branch subject.

The deployment role cannot modify its own trust relationship or the bootstrap IAM configuration.

## Infrastructure workflow

```text
Human bootstrap
AWS IAM Identity Center
        |
        v
infra/bootstrap/
        |
        +-- Terraform state S3 bucket
        +-- GitHub OIDC provider
        +-- GitHub deployment role
        +-- least-privilege deployment permissions

GitHub Actions
        |
       OIDC
        |
        v
OpsLensGitHubDeployRole
        |
        v
infra/environments/dev/
        |
        +-- /opslens/dev/platform CloudWatch Log Group
```

Terraform static/security checks run separately from AWS deployment authentication.

## Phase 0 evidence

Phase 0 demonstrated:

- remote Terraform state with locking and recovery controls;
- GitHub OIDC authentication without stored AWS access keys;
- branch-constrained IAM trust;
- successful and failed OIDC trust paths;
- least-privilege authorization troubleshooting;
- real Terraform deployment from GitHub Actions;
- CloudTrail correlation for STS federation events;
- Terraform formatting, validation, TFLint, and Checkov gates;
- resource discovery through AWS CLI;
- Terraform convergence after deployment.

See:

- [`docs/adr/0001-terraform-state-strategy.md`](docs/adr/0001-terraform-state-strategy.md)
- [`docs/adr/0002-github-actions-oidc.md`](docs/adr/0002-github-actions-oidc.md)
- [`docs/adr/0003-aws-region-strategy.md`](docs/adr/0003-aws-region-strategy.md)
- [`docs/labs/phase-0-iam-oidc-failure.md`](docs/labs/phase-0-iam-oidc-failure.md)
- [`docs/labs/phase-0-cloudwatch-authorization-failure.md`](docs/labs/phase-0-cloudwatch-authorization-failure.md)

## Next milestone

Phase 1 builds the first real end-to-end data path using FIRST EPSS:

```text
FIRST EPSS
 -> EventBridge Scheduler
 -> Lambda ingestion
 -> S3 Bronze
 -> transformation
 -> S3 Silver / Parquet
 -> Glue Data Catalog
 -> Athena
```

The first supported structured question will be:

> Which CVEs currently have EPSS above 0.7?
