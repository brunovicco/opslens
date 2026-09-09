# ADR 0060 — Bound Amazon Inspector as an independent runtime-evidence authority before activation or correlation

- Status: Accepted
- Date: 2026-09-09
- Phase: 16 — Runtime Exposure with Amazon Inspector
- Gate: 16.1 — Amazon Inspector Runtime-Evidence Capability Fit

## Context

OpsLens has intentionally preserved the invariant:

```text
Repository Risk != Runtime Exposure
```

Repository analysis can prove that a dependency in an immutable repository snapshot is vulnerable. It cannot prove that the same package is deployed in an AWS resource, that Amazon Inspector is actively scanning that resource, that Inspector currently observes the vulnerability there, or that the resource is network reachable.

Phase 8 therefore kept `runtime_exposure` unavailable. Phase 16 introduces an independent runtime evidence source rather than deriving runtime truth from repository risk, model reasoning, protocol metadata, or hosting state.

Amazon Inspector currently exposes read APIs that can independently answer different runtime questions:

```text
ListCoverage -> which resources Inspector reports as covered/scannable and with what scan state
ListFindings -> which findings Inspector reports for concrete resources
```

Inspector finding types include:

```text
NETWORK_REACHABILITY
PACKAGE_VULNERABILITY
CODE_VULNERABILITY
```

AWS resource types represented by Inspector include EC2 instances, ECR container images/repositories, Lambda functions, and code repositories.

A critical semantic constraint is that `NETWORK_REACHABILITY` findings are currently produced only for EC2 instances. Package-vulnerability findings can apply to EC2, ECR images, and Lambda functions. These dimensions must not be collapsed into one generic exposure boolean.

## Decision

Treat Amazon Inspector as a new independent **runtime evidence authority**, but authorize only one read-only discovery experiment before any activation, IAM expansion, routing integration, or repository/runtime correlation.

Decision:

```text
Amazon Inspector capability fit:       YES
runtime evidence source:               INDEPENDENT AUTHORITY
first experiment:                      READ-ONLY DISCOVERY ONLY
allowed first APIs:                    ListCoverage + ListFindings
Inspector activation/change:           NOT AUTHORIZED
new IAM:                               NOT AUTHORIZED
hybrid routing integration:            NOT AUTHORIZED
repository/runtime auto-correlation:    NOT AUTHORIZED
```

## Evidence taxonomy

Phase 16 must preserve independent evidence dimensions.

### Runtime coverage

```text
Inspector reports a concrete resource
+ scan type
+ scan status
+ last-scanned metadata when available
```

Coverage proves Inspector coverage state only.

```text
coverage != vulnerability finding
coverage != network reachability
```

### Runtime package vulnerability

```text
active Inspector PACKAGE_VULNERABILITY finding
+ exact Inspector resource identity
+ vulnerability id
+ Inspector-reported vulnerable package details
```

This is runtime-resource vulnerability evidence from Inspector. It does not automatically prove ownership by a particular GitHub repository or application.

### Network reachability

```text
Inspector NETWORK_REACHABILITY finding
+ EC2 resource identity
+ protocol
+ open port range
+ network path identities
```

Network reachability is its own evidence class and remains EC2-only unless the upstream Inspector contract changes and is explicitly re-evaluated.

### Code vulnerability

Inspector `CODE_VULNERABILITY` evidence remains separate from package vulnerability, repository package applicability, and network reachability.

## Authority boundary

The target Phase 16 boundary is:

```text
Amazon Inspector read response
 -> source-preserving raw snapshot
 -> exact account / region / pagination context
 -> deterministic resource/finding parser
 -> type-specific evidence record
 -> RuntimeEvidenceEnvelope
 -> optional deterministic correlation only when identity is provable
 -> fail closed / remain independent when correlation is ambiguous
```

The following are permanent Phase 16 separations:

```text
Inspector coverage != vulnerability finding
Inspector finding != repository finding
Inspector package match != deployed application ownership
Inspector resource presence != network exposure
Inspector PACKAGE_VULNERABILITY != NETWORK_REACHABILITY
Inspector score != OpsLens Risk Policy v1
Inspector EPSS != OpsLens source-authority replacement
Inspector finding status != business remediation state
Inspector evidence != model authority
runtime evidence correlation != capability authorization
```

## Stable identity direction

Gate 16.1 does not freeze the final implementation contract, but the first implementation must preserve enough source identity to make evidence replayable and auditable.

Candidate resource identity:

```text
provider
account_id
region
resource_type
resource_id
scan_type
scan_status
last_scanned_at
```

Candidate finding identity:

```text
finding_arn
finding_type
finding_status
resource identity
first_observed_at
last_observed_at
updated_at
```

Type-specific details may be admitted only from the corresponding Inspector finding type.

For package vulnerabilities, bounded details may include Inspector-reported `vulnerabilityId`, vulnerable package name/version/package manager, fixed version when present, exploit availability, fix availability, and Inspector-provided EPSS as Inspector evidence.

For network reachability, bounded details may include only the reported protocol, open port range, and network path component identities.

## Correlation rule

Phase 16 must not correlate Inspector findings to repository findings merely because a package name or CVE string looks similar.

A later correlation gate must prove a deterministic mapping across at least the required package ecosystem/version semantics and runtime resource identity. Until then:

```text
repository evidence: independent
Inspector runtime evidence: independent
```

## First experiment

Authorize Gate 16.2 to run one bounded read-only discovery against the existing dev account using only:

```text
inspector2:ListCoverage
inspector2:ListFindings
```

The experiment must first test whether existing human/bootstrap credentials already have these read permissions. Access denial is acceptable evidence and must not trigger automatic IAM widening.

The experiment must record independently:

```text
API call attempted
HTTP/SDK outcome
pagination count
covered-resource count
finding count
finding-type counts
resource-type counts
scan-status counts
elapsed time
SDK retry count when observable
AWS mutations = 0
new IAM = 0
model invocations = 0
capability executions = 0
```

If existing credentials cannot read Inspector, Gate 16.2 must stop and record the exact denial. A separate IAM decision is required before adding permissions.

## Not authorized by this ADR

```text
Enable / Disable Inspector
ECR scanning configuration changes
EC2 scan-mode changes
Lambda scanning activation
EventBridge rules
suppression filters
new IAM roles/policies
runtime-risk composite scoring
hybrid route support for runtime_exposure
model synthesis over Inspector evidence
agent capability execution
repository/runtime automatic correlation
```

## Consequences

Phase 16 can now progress without weakening the central architecture. Amazon Inspector becomes a candidate independent source of deployed-resource evidence, while repository risk remains an independent authority.

The first experiment is deliberately useful even if it returns zero resources/findings or AccessDenied: each outcome answers whether current Inspector state can support the next gate without silently changing the account.

## Next gate

Gate 16.2 — bounded read-only Amazon Inspector discovery.

It must execute no mutation and must not create IAM automatically.

## Evidence

```text
labs/phase-16-gate-16-1-inspector-runtime-evidence-fit.md
labs/evidence/phase-16-gate-16-1-inspector-runtime-evidence-fit-v1.json
```

## PR #89

The unrelated Governed LLM Gateway work remains untouched:

```text
PR:     #89
branch: feat/governed-gateway-semantic-planner
```
