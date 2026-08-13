# Infrastructure

OpsLens infrastructure is managed with Terraform.

## Layout

```text
infra/
├── bootstrap/
├── modules/
└── environments/
    └── dev/
```

- `bootstrap/`: state, CI federation, and permissions that must exist before workload Terraform can operate.
- `modules/`: reusable modules introduced only when a concrete requirement appears.
- `environments/dev/`: the single real OpsLens deployment environment.

OpsLens does not maintain fictional staging or production environments.

## Deployment model

### Human bootstrap plane

Bootstrap resources are managed with temporary credentials from AWS IAM Identity Center.

Human bootstrap is responsible for trust and authorization boundaries that CI must not be able to grant to itself, including:

- Terraform state infrastructure;
- GitHub Actions OIDC provider;
- GitHub deployment role trust policy;
- deployment-role IAM permissions.

The human bootstrap profile is:

```text
opslens-bootstrap
```

It is not configured as the default AWS CLI identity.

### GitHub deployment plane

GitHub Actions assumes:

```text
arn:aws:iam::487757851499:role/OpsLensGitHubDeployRole
```

through GitHub OIDC.

The trust relationship is restricted to the immutable `main` branch subject and audience `sts.amazonaws.com`.

The role receives only the permissions needed by the current `dev` infrastructure. It does not have IAM permissions to modify its own trust policy or bootstrap configuration.

## Regions

- Identity Center Region: `sa-east-1`
- Primary workload Region: `us-east-1`

See [ADR-0003](../docs/adr/0003-aws-region-strategy.md).

## Conventions

### Deployment

- Project: `opslens`
- Environment: `dev`
- Primary workload Region: `us-east-1`
- Infrastructure as Code: Terraform

### Resource naming

When the AWS service permits predictable names, use:

```text
opslens-dev-<purpose>
```

Services with global namespaces, such as Amazon S3, may require an additional deterministic uniqueness suffix.

### Resource tags

Terraform-managed resources should use these baseline tags when supported:

```text
Project     = opslens
Environment = dev
ManagedBy   = terraform
Repository  = brunovicco/opslens
```

Additional tags are introduced only when they serve an operational, security, governance, or cost-management purpose.

## Terraform state

Terraform state is stored remotely in:

```text
s3://opslens-dev-tfstate-487757851499-us-east-1
```

State keys:

```text
bootstrap/terraform.tfstate
environments/dev/terraform.tfstate
```

The backend provides:

- S3 Versioning;
- SSE-S3 encryption;
- S3 Block Public Access;
- native S3 state locking through `.tflock`;
- `prevent_destroy` on the state bucket;
- expiration of noncurrent state-object versions after 90 days;
- cleanup of incomplete multipart uploads after 7 days;
- no persistent AWS credentials in Terraform configuration.

The GitHub deployment role can access only the `dev` state key and its lock object. It cannot access the bootstrap state key.

See [ADR-0001](../docs/adr/0001-terraform-state-strategy.md).

## CI and deployment workflows

### Static/security CI

`.github/workflows/terraform-ci.yml`

Runs without AWS credentials and performs:

- `terraform fmt`;
- `terraform validate`;
- TFLint;
- Checkov.

Static source validation is intentionally separated from AWS trust.

### Dev plan

`.github/workflows/terraform-dev-plan.yml`

Uses GitHub OIDC to:

- assume `OpsLensGitHubDeployRole`;
- initialize the remote `dev` backend;
- validate Terraform;
- produce an AWS-backed Terraform plan.

### Dev apply

`.github/workflows/terraform-dev-apply.yml`

Uses the same OIDC trust boundary and performs a saved-plan apply from `main`.

The first successful real deployment through this path created:

```text
/opslens/dev/platform
```

as a CloudWatch Log Group with 14-day retention.

See [ADR-0002](../docs/adr/0002-github-actions-oidc.md).

## IAM design rule

Separate:

```text
trust
  -> who may obtain the role session

authorization
  -> what an obtained role session may do
```

The Phase 0 labs deliberately exercised both failure classes:

- OIDC trust-policy denial before an STS session existed;
- service authorization denial after an STS session existed.

See the Phase 0 labs under `docs/labs/`.
