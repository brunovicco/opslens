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

- `bootstrap/`: resources required before the main Terraform backend can be used.
- `modules/`: reusable infrastructure modules introduced only when required.
- `environments/dev/`: the single real OpsLens deployment environment.

OpsLens does not maintain fictional staging or production environments.

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

Additional tags should be introduced only when they serve an operational, security, governance, or cost-management purpose.

## Terraform state

Terraform state is stored remotely in Amazon S3.

The state backend provides:

- S3 Versioning for recovery;
- SSE-S3 encryption;
- S3 Block Public Access;
- native S3 state locking;
- no persistent AWS credentials in Terraform configuration.

The bootstrap configuration is located in `infra/bootstrap/`.

See [ADR-0001](../docs/adr/0001-terraform-state-strategy.md) for the architectural decision and trade-offs.
