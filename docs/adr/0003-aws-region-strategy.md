# ADR-0003: AWS Regional Strategy

- Status: Accepted
- Date: 2026-08-13

## Context

OpsLens needs one stable primary workload Region for the initial `dev` environment.

The AWS identity plane was established first through an AWS IAM Identity Center organization instance in `sa-east-1`.

The project also targets a later AWS/GenAI stack whose service and feature availability can differ by Region over time. The project instructions require current regional support to be revalidated before adopting each later service.

A multi-Region architecture would add cost and operational complexity before OpsLens has a requirement for high availability, disaster recovery, or geographic data placement.

## Decision

OpsLens separates the identity plane from the workload plane:

```text
Identity plane
AWS IAM Identity Center
Region: sa-east-1

Workload plane
OpsLens dev resources
Primary Region: us-east-1
```

`us-east-1` is the default primary Region for Terraform-managed OpsLens workload resources unless a later architectural requirement explicitly overrides it.

The Region is part of the infrastructure contract and appears in:

- Terraform providers;
- resource ARNs;
- GitHub Actions AWS configuration;
- Terraform state naming;
- operational commands and documentation.

Each new AWS service introduced in a later phase must still be checked against current AWS regional availability, pricing, compliance, and data-residency requirements before implementation.

## Why not move Identity Center

There is no current product requirement that justifies rebuilding the established Identity Center organization instance solely to align its Region with workloads.

Human authentication is a control-plane concern and does not require application data to be processed in the Identity Center Region.

## Alternatives considered

### Put all workloads in `sa-east-1`

Valid, but not selected as the initial default.

Keeping the workload plane in `us-east-1` reduces the likelihood that the project must change its primary Region merely to adopt a later AWS capability. Regional support is still verified service by service.

### Multi-Region from Phase 0

Rejected.

OpsLens currently has:

- one real `dev` environment;
- no public production SLA;
- no recovery-time or recovery-point requirement that justifies active/active or active/passive regional architecture.

Introducing multi-Region infrastructure now would violate the project's rule against adding architecture without a concrete requirement.

### Region chosen independently per service

Rejected as the default strategy.

Unnecessary cross-Region service placement increases latency, IAM complexity, data-transfer concerns, observability complexity, and troubleshooting surface.

Exceptions require an explicit reason.

## Consequences

### Positive

- one predictable workload Region;
- simpler Terraform and IAM ARN construction;
- simpler cost and observability analysis;
- reduced architectural complexity;
- Identity Center can remain where it is already established;
- later services still undergo explicit regional validation.

### Trade-offs

- identity and workload control planes use different Regions;
- any future data-residency requirement must be evaluated before product data is introduced;
- a service unavailable or unsuitable in `us-east-1` would require an explicit regional exception or architecture change;
- multi-Region resilience is intentionally not provided in the current phase.

## Operational rule

Unless an ADR changes this decision:

```text
human identity / SSO: sa-east-1
OpsLens workloads:    us-east-1
```

Do not infer that all future services are available or appropriate in `us-east-1`; verify them when the relevant phase begins.
