# ADR 0063 — Close Phase 16 at the Proven Read-Only Runtime-Evidence Boundary

- Status: Accepted
- Date: 2026-09-09
- Phase: 16 — Runtime Exposure with Amazon Inspector
- Gate: 16.5 — Closeout after mandatory temporary-IAM teardown

## Context

Phase 16 tested whether Amazon Inspector should become an independent runtime-evidence source for OpsLens while preserving:

> **Repository Risk != Runtime Exposure.**

The phase deliberately refused to infer runtime truth from repository findings or to grant Inspector evidence any authority over Risk Policy v1, capability authorization, or model/tool selection.

The first read-only experiment used the existing `OpsLensGitHubDeployRole` and measured `AccessDeniedException` on `ListCoverage`. Instead of widening that shared role, Gate 16.3 accepted a separate temporary `OpsLensInspectorDiscoveryRole` limited to:

```text
inspector2:ListCoverage
inspector2:ListFindings
Resource = "*"
aws:RequestedRegion == us-east-1
immutable GitHub OIDC main subject
900-second requested workflow session
```

Human bootstrap created exactly that temporary boundary. One and only one rerun then succeeded:

```text
run:               34414116549 / #2
ListCoverage:      SUCCESS / 1 page / 0 records
ListFindings:      SUCCESS / 1 page / 0 records
SDK retries:       0
AWS mutations:     0
model invocations: 0
capability execs:  0
```

The read contract therefore works, but the current dev account exposes no Inspector coverage or finding records through those APIs.

ADR 0061 required teardown after the bounded experiment. Gate 16.5 removed the temporary role/policy with an exact `0 add / 0 change / 2 destroy` plan, applied it, obtained a fresh `No changes` Terraform plan, and independently verified the role is absent with `NoSuchEntity` while `OpsLensGitHubDeployRole` remains present.

## Decision

Close Phase 16 with the following retained state:

```text
Inspector read-only domain/adapter contract:   RETAIN
ListCoverage/ListFindings discovery harness:   RETAIN AS DISABLED LAB TOOL
Gate 16.4 zero-record measured evidence:       RETAIN
standing Inspector discovery IAM:              DO NOT RETAIN / REMOVED
Inspector authority on shared deploy role:     NONE IN RETAINED OPSLENS TERRAFORM
Inspector activation/configuration changes:    DO NOT CREATE IN PHASE 16
hybrid runtime_exposure routing integration:   DO NOT CREATE IN PHASE 16
repository/runtime automatic correlation:      DO NOT CREATE
runtime-risk composite scoring:                DO NOT CREATE
model synthesis over Inspector evidence:       DO NOT CREATE
```

The historical manual workflow remains reproducible but disabled by default. A future re-entry must explicitly recreate a separately authorized temporary role and must not silently inherit standing authority.

## Why stop here

The experiment answered the architectural question that Phase 16 was designed to answer:

1. Inspector read evidence can be acquired through a narrow independent adapter.
2. AWS authentication and Inspector authorization are distinct boundaries.
3. A dedicated temporary principal is preferable to broadening the shared deployment role.
4. API success does not imply evidence presence.
5. The current dev account has zero observed coverage and findings under the selected read surface.
6. Activating or reconfiguring scanning solely to manufacture portfolio data would violate the project's evidence-first and least-privilege approach.

A zero-record result is evidence about this account/region/time, not a product-wide statement about Inspector.

## Consequences

### Positive

- runtime evidence has a typed, source-preserving entry point without becoming repository-risk truth;
- `ListCoverage` and `ListFindings` semantics remain testable independently;
- the project preserved least privilege through principal separation and teardown;
- no standing experiment IAM remains;
- no cloud scanning configuration was changed merely to produce a demo;
- later phases may reference the measured negative/zero-data result rather than repeating the experiment without a new hypothesis.

### Constraints

- `runtime_exposure` remains unsupported by the retained Phase 8 hybrid route authority;
- no automatic repository/runtime linkage exists;
- no current runtime exposure can be claimed from the zero-record Inspector result;
- any future Inspector activation or correlation work requires a new issue, explicit authority decision, and new evidence.

## Permanent boundaries reinforced

```text
Repository Risk != Runtime Exposure
AWS authentication != Inspector read authorization
Inspector API success != runtime evidence presence
Inspector coverage != vulnerability finding
Inspector finding != repository finding
Inspector package match != deployed application ownership
Inspector resource presence != network exposure
Inspector PACKAGE_VULNERABILITY != NETWORK_REACHABILITY
Inspector score != Risk Policy v1
Inspector EPSS != OpsLens source-authority replacement
Inspector evidence != model authority
runtime evidence correlation != capability authorization
```

## Alternatives rejected

### Keep the temporary role standing

Rejected. The experiment is complete and no retained runtime consumer needs the authority.

### Add Inspector permissions to `OpsLensGitHubDeployRole`

Rejected. This would permanently broaden a shared deployment identity for a bounded experiment.

### Enable/configure Inspector to manufacture evidence

Rejected for Phase 16. No concrete product requirement justified changing EC2/ECR/Lambda scanning merely to populate a lab result.

### Wire runtime evidence into hybrid routing now

Rejected. The measured account returned zero runtime evidence and no deterministic repository/runtime identity bridge has been proven.

## Evidence

```text
labs/evidence/phase-16-gate-16-1-inspector-runtime-evidence-fit-v1.json
labs/evidence/phase-16-gate-16-2-inspector-readonly-discovery-v1.json
labs/evidence/phase-16-gate-16-3-inspector-readonly-iam-decision-v1.json
labs/evidence/phase-16-gate-16-4-inspector-readonly-rerun-v1.json
labs/evidence/phase-16-gate-16-5-inspector-iam-cleanup-postapply-v1.json
labs/evidence/phase-16-closeout-v1.json
```

## Next phase

Phase 17 — Security Hardening may begin from this retained state. It must treat the Inspector experiment as closed and must not recreate the temporary discovery IAM without a new evidence-backed hypothesis.
