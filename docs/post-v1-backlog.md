# OpsLens Post-V1 / Experiments Backlog

This backlog contains work intentionally excluded from the demonstration-focused V1 closeout. Inclusion here is not standing implementation or mutation authority.

## Production runtime experiments

- Internet-facing async API enablement.
- Authentication and identity boundary.
- Multi-tenant isolation.
- WAF, abuse controls, per-tenant quotas, and denial-of-wallet defenses.
- Custom public domain and TLS lifecycle.
- Production SLO/error-budget definition from measured load.
- HA/DR and operational ownership.

## Threat evidence runtime experiments

- Provider-backed request-time `PublicThreatEvidenceAuthority` adapter for arbitrary admitted repositories.
- S3 object-read vs Glue/Athena bounded adapter comparison.
- Request-time structured-threat latency and scan-cost measurement.
- Least-privilege worker IAM for any selected physical adapter.

## Interoperability/runtime experiments

- Public MCP transport if a concrete consumer appears.
- Real A2A peer runtime if interoperability value can be measured.
- AgentCore Runtime revisit only if it solves a concrete hosting or operational requirement.

## Product experiments

- Repository history/change tracking.
- Multi-repository portfolio view.
- Organization-level policy overlays.
- Notification or ticketing integrations.

## Rule

A backlog item does not become part of V1 merely because it is technically interesting or relevant to AIP-C01.

```text
AIP-C01 topic != product requirement
historical experiment != standing authority
```
