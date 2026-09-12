# Phase 19 Gate 19.9 — V1 demonstration closeout contract

Issue: pending  
Source protected main: `e538fa3e96c29cf76dd3aa83a9967e090587b6fb`  
Gate 19.8 protected merge: PR #375  
Gate 19.8 post-merge CodeQL: run `34713360403` / run #393 / `success`

## Status

**IN PROGRESS — V1 scope freeze and current-state synchronization only.**

## Why this gate exists

OpsLens V1 is a demonstration and architecture lab, not a production SaaS. The project already proves substantial AWS, software-supply-chain, deterministic authority, retrieval, agentic, security, evaluation, observability, and cost-engineering concepts. V1 completion therefore must optimize for reproducibility, architectural clarity, evidence quality, and a short demonstrable path rather than production operations.

Gate 19.9 freezes that product boundary before any additional implementation work.

## V1 product intent

The V1 demo must make this end-to-end authority chain understandable and reproducible:

```text
public repository evidence
 -> inert dependency evidence
 -> structured threat evidence
 -> deterministic applicability/correlation
 -> deterministic risk prioritization
 -> bounded retrieval/reasoning where appropriate
 -> evidence-backed result
```

The public async AWS runtime remains useful architecture evidence, but V1 does not require it to become an Internet-facing production service.

## V1 definition of done

A reviewer should be able to clone the repository, follow one documented setup path, run one deterministic demo command, and inspect an evidence-backed result in less than ten minutes, without executing third-party repository code.

V1 requires:

1. one deterministic offline demo runner as the canonical demonstration path;
2. three curated scenarios: material vulnerability, controlled benign result, and fail-closed incomplete/ambiguous evidence;
3. stable machine-readable output plus a concise human-readable projection;
4. a minimal local visual demo surface over the same admitted application contract;
5. current English/Portuguese README and architecture documentation;
6. final portfolio evidence, architecture diagram, security/authority explanation, and demo walkthrough;
7. CI/security/CodeQL green on the final protected checkpoint;
8. Phase 19 closeout plus `v1.0.0` release/tag after HUMAN review.

## Explicit V1 non-goals

The following are not required to call OpsLens V1 complete:

```text
Internet-facing production runtime
authentication or OIDC/Cognito
multi-tenancy
commercial quotas or billing
custom public domain
WAF or production abuse controls
24x7 operations or on-call
production SLOs/SLA
HA/DR program
production TCO claim
provider-backed arbitrary request-time threat adapter
public worker enablement
event-source enablement
new Terraform/AWS/IAM mutation solely for V1 demo
```

Historical AWS materialization evidence remains valid. `materialized != enabled` continues to describe the retained async runtime.

## Remaining V1 sequence

```text
Gate 19.9   V1 demonstration contract + current-state synchronization
Gate 19.10  deterministic end-to-end demo runner
Gate 19.11  curated demo scenarios + deterministic evaluation
Gate 19.12  minimal local visual demo surface
Gate 19.13  portfolio/readme/architecture polish
Gate 19.14  V1 closeout + release readiness
```

The gate names above are completion slices, not standing authority for later implementation. Each gate must still preserve the project authority model and stop at any new HUMAN mutation or protected-merge boundary.

## Authority impact

```text
Terraform/provider operations:          0
AWS mutations:                          0
IAM mutations:                          0
Lambda artifact publications:           0
runtime enablements:                    0
provider live executions:               0
third-party repository code executions: 0
PR #89 modifications:                   0
```

## Exit criteria

Gate 19.9 is complete when current-facing documentation records Gate 19.8 as complete, the demonstration-only V1 scope is explicit, the remaining completion sequence is frozen, stale production-runtime expectations are removed from active docs, and exact-head CI/security/CodeQL are green.

Controlling invariants:

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
Structured facts use structured retrieval.
missing evidence != benign evidence
materialized != enabled
demonstration readiness != production readiness
AIP-C01 topic != product requirement
```
