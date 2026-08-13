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
