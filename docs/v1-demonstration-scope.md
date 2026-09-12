# OpsLens V1 Demonstration Scope

OpsLens V1 is a demonstration and architecture lab. It is not presented as a production SaaS or an Internet-facing service.

## What V1 demonstrates

```text
public repository evidence
 -> inert dependency evidence
 -> structured threat evidence
 -> deterministic applicability/correlation
 -> deterministic risk prioritization
 -> bounded retrieval/reasoning where appropriate
 -> evidence-backed result
```

The project demonstrates that probabilistic reasoning can remain useful without becoming the authority for package identity, vulnerability applicability, source provenance, risk policy, SQL compilation, or execution limits.

## Canonical reviewer experience

The V1 target experience is:

```text
clone
 -> setup
 -> one deterministic demo command
 -> inspect evidence-backed result
```

The target is a reproducible demonstration in less than ten minutes on a clean developer environment after prerequisites are installed.

## Required V1 demo scenarios

1. A repository snapshot with at least one materially relevant vulnerability.
2. A controlled benign scenario where admitted evidence produces no material finding.
3. A fail-closed scenario where incomplete or ambiguous evidence cannot be interpreted as benign.

Each scenario must emit stable machine-readable evidence and a concise human-readable projection.

## What V1 does not claim

V1 does not claim:

- production availability or an SLA;
- multi-tenant security isolation;
- authentication/authorization for public users;
- commercial abuse controls or billing;
- high availability/disaster recovery;
- production monthly TCO;
- a permanently enabled public worker/API;
- complete provider-backed request-time threat acquisition for arbitrary repositories.

The retained Phase 19 async AWS runtime remains materialized but disabled. That architecture is evidence of deployment design, IAM separation, idempotency, retry, queue, and state authority; it is not a production-readiness claim.

## Completion gates

```text
19.9   V1 demonstration contract + current-state synchronization
19.10  deterministic end-to-end demo runner
19.11  curated scenarios + deterministic evaluation
19.12  minimal local visual demo
19.13  portfolio/readme/architecture polish
19.14  V1 closeout + release readiness
```

No gate above automatically grants AWS/Terraform/IAM mutation authority.

## Permanent invariants

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
Structured facts use structured retrieval.
missing evidence != benign evidence
materialized != enabled
demonstration readiness != production readiness
```
