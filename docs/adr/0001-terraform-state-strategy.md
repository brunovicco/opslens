# ADR-0001: Terraform State Strategy

- Status: Accepted
- Date: 2026-08-13

## Context

OpsLens requires a Terraform state strategy that is secure, recoverable, inexpensive, and suitable for both local development and future GitHub Actions deployments.

Keeping the main Terraform state only on a developer workstation would make recovery and automated deployment unnecessarily fragile.

The state storage mechanism must also avoid persistent AWS credentials and unnecessary infrastructure.

## Decision

OpsLens stores Terraform state in an Amazon S3 bucket in `us-east-1`.

The state bucket is created by a small bootstrap Terraform configuration that initially uses local state.

After the bucket is created, the bootstrap state itself is migrated to the S3 backend.

The backend uses:

- Amazon S3 for remote state storage;
- S3 Versioning for state recovery;
- SSE-S3 (`AES256`) for encryption at rest;
- S3 Block Public Access;
- native S3 state locking with `use_lockfile = true`;
- `prevent_destroy` on the state bucket;
- temporary AWS credentials supplied externally to Terraform.

The bootstrap state key is:

```text
bootstrap/terraform.tfstate
```

Terraform configuration does not contain a local AWS profile or static credentials.

Human execution currently uses IAM Identity Center through:

```text
AWS_PROFILE=opslens-bootstrap
```

Future CI execution will use GitHub Actions OIDC and a dedicated AWS role.

## Alternatives considered

### Local state only

Rejected for the main project because it is workstation-dependent and unsuitable for automated CI/CD.

### S3 state with DynamoDB locking

Not selected because Terraform supports native S3 lock files and DynamoDB-based locking is deprecated.

### Terraform Cloud / HCP Terraform

A valid alternative, but it would introduce an additional control plane that does not solve a concrete OpsLens requirement at this stage.

### Customer-managed AWS KMS key

Not selected initially. SSE-S3 provides encryption at rest without introducing additional key-management complexity or cost.

A customer-managed KMS key can be reconsidered if a concrete key-ownership, separation-of-duties, or compliance requirement appears.

## Consequences

### Positive

- state is not tied to a single workstation;
- state history can be recovered through S3 Versioning;
- concurrent Terraform operations can use native S3 locking;
- no DynamoDB table is required for locking;
- no persistent AWS access keys are stored in the repository;
- the solution has negligible cost at OpsLens scale.

### Trade-offs

The S3 bucket stores the Terraform state that also manages the bucket itself.

If the bucket is deleted outside Terraform, recovery requires using the bootstrap configuration and available state backups or reconstruction procedures.

This risk is reduced by:

- `prevent_destroy`;
- S3 Versioning;
- Block Public Access;
- explicit IAM boundaries;
- reproducible Terraform configuration.

## Validation

The strategy was validated by:

1. creating the state bucket through Terraform;
2. verifying S3 Versioning;
3. verifying SSE-S3 encryption;
4. verifying S3 Block Public Access;
5. verifying resource tags;
6. migrating existing local state to S3;
7. running `terraform plan` after migration;
8. confirming that Terraform reported no infrastructure changes.

A credentials failure test also confirmed that Terraform cannot access AWS without an explicitly available AWS identity.
