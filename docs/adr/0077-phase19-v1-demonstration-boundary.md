# ADR 0077 — Close OpsLens V1 as a demonstration architecture lab

Status: Accepted for review  
Date: 2026-09-12

## Context

OpsLens has completed Phases 0–18 and Phase 19 Gates 19.1–19.8. The repository now contains retained evidence for deterministic software-supply-chain analysis, Bedrock retrieval and reasoning, bounded agentic patterns, MCP/A2A experiments, security hardening, evaluation, observability, cost accounting, and a materialized-but-disabled async AWS runtime.

The next architectural question is not whether OpsLens can be expanded into a production SaaS. The project objective for V1 is demonstration: a technically credible, reproducible portfolio artifact that proves architecture and engineering judgment without creating operational scope that is unnecessary for the demonstration.

## Decision

OpsLens V1 is explicitly a **demonstration and architecture lab**, not a production service.

The V1 completion path prioritizes:

- deterministic reproducibility;
- evidence provenance;
- a short end-to-end demo path;
- failure-path demonstration;
- local visual presentation;
- architecture and portfolio clarity;
- retained CI/security/evaluation evidence.

The canonical V1 demo target is:

```text
clone
 -> setup
 -> one deterministic demo command
 -> evidence-backed repository analysis
 -> human-readable explanation/provenance
```

The canonical authority chain remains:

```text
public repository evidence
 -> inert dependency evidence
 -> structured threat evidence
 -> deterministic applicability/correlation
 -> deterministic risk prioritization
 -> bounded retrieval/reasoning where appropriate
 -> evidence-backed result
```

No production runtime enablement is required for V1 completion. Existing async AWS resources remain architecture evidence and stay disabled unless a separately reviewed future requirement changes that boundary.

## Consequences

### Positive

- V1 completion remains bounded and can finish around demonstrable value rather than operational completeness.
- The project preserves its strongest differentiator: deterministic authority around AI reasoning.
- Recruiters and reviewers get a reproducible path instead of needing AWS credentials or a live public service.
- The project avoids unsupported production claims.
- Historical infrastructure work remains useful evidence without becoming a maintenance obligation.

### Trade-offs

- V1 does not prove multi-tenant production operation.
- V1 does not expose a stable Internet-facing API or production SLO.
- The materialized async runtime remains intentionally disabled.
- Request-time structured-threat provider adaptation may remain a post-V1 experiment unless required by the local demo path.

## V1 non-goals

```text
Internet-facing production runtime
authentication / OIDC / Cognito
multi-tenancy
commercial billing or quotas
custom public domain
WAF or production abuse controls
24x7 on-call operations
production SLO/SLA
HA/DR program
production TCO claim
public worker/event-source enablement
```

## Completion sequence

```text
Gate 19.9   V1 demonstration contract + current-state synchronization
Gate 19.10  deterministic end-to-end demo runner
Gate 19.11  curated demo scenarios + deterministic evaluation
Gate 19.12  minimal local visual demo surface
Gate 19.13  portfolio/readme/architecture polish
Gate 19.14  V1 closeout + release readiness
```

These gates do not grant standing authority for AWS or Terraform mutation.

## Rejected alternatives

### Require a production-public async runtime before V1

Rejected. It would add auth, abuse protection, multi-tenancy, operational SLO, cost controls, public-domain, and support concerns that are not required to demonstrate the core architecture.

### Stop immediately after Gate 19.8

Rejected. The repository has deep technical evidence but still lacks one concise deterministic end-to-end demo path and a polished local presentation surface.

### Add more AWS services before closing V1

Rejected. A service is not a portfolio feature by itself. New AWS services are admitted only if they solve a concrete demonstration gap.

## Controlling rules

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
missing evidence != benign evidence
materialized != enabled
demonstration readiness != production readiness
AIP-C01 topic != product requirement
```
