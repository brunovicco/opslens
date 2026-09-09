# Phase 16 — Gate 16.1: Amazon Inspector Runtime-Evidence Capability Fit

_Date: 2026-09-09_

## Status

**COMPLETE — GO TO ONE READ-ONLY DISCOVERY EXPERIMENT; NO INSPECTOR ACTIVATION OR IAM EXPANSION AUTHORIZED.**

```text
issue:        #238
source main:  ba60a17fa9be2b3507661ba33014fde51c26ff88
phase:        Phase 16 — Runtime Exposure with Amazon Inspector
decision:     GO READ-ONLY ONLY
```

## Why this gate exists

OpsLens already proves repository vulnerability applicability from immutable repository evidence. That does not prove deployment, Inspector scan coverage, an active runtime finding, or network reachability.

The permanent separation remains:

```text
Repository Risk != Runtime Exposure
```

Phase 16 therefore starts by defining Amazon Inspector as a separate evidence source rather than attaching runtime meaning to existing repository risk.

## Current Inspector capability surface

Current Amazon Inspector documentation establishes two useful read surfaces for the first experiment:

```text
ListCoverage
ListFindings
```

Inspector finding types include:

```text
NETWORK_REACHABILITY
PACKAGE_VULNERABILITY
CODE_VULNERABILITY
```

Relevant AWS resource identities include:

```text
AWS_EC2_INSTANCE
AWS_ECR_CONTAINER_IMAGE
AWS_ECR_REPOSITORY
AWS_LAMBDA_FUNCTION
CODE_REPOSITORY
```

The most important constraint for OpsLens semantics is:

```text
NETWORK_REACHABILITY is currently EC2-only.
```

Package vulnerability findings on Lambda/ECR must not be mislabeled as network exposure.

## Evidence taxonomy

The first implementation must keep these dimensions independent:

```text
runtime_coverage
runtime_vulnerability
network_reachability
code_vulnerability
```

### runtime_coverage

Inspector says a concrete resource is represented in scan coverage, together with scan type/status metadata.

### runtime_vulnerability

Inspector reports a `PACKAGE_VULNERABILITY` against a concrete runtime resource.

This is stronger than repository-only risk because the finding is associated with an AWS resource. It is still not proof that the finding belongs to a specific GitHub repository/application unless deterministic correlation is proven separately.

### network_reachability

Only an Inspector `NETWORK_REACHABILITY` finding may create this evidence class. The current upstream scope is EC2 only.

### code_vulnerability

Inspector code findings are independent evidence and are not automatically equivalent to package vulnerability or repository dependency applicability.

## Authority boundary

```text
Amazon Inspector read response
 -> preserve raw source evidence
 -> exact account / region / pagination identity
 -> deterministic resource/finding type validation
 -> type-specific bounded evidence
 -> RuntimeEvidenceEnvelope
 -> optional future correlation only after deterministic proof
```

Do not flatten the evidence into one `exposed=true` field.

## Permanent Phase 16 separations

```text
Inspector coverage != vulnerability finding
Inspector finding != repository finding
Inspector package match != deployed application ownership
Inspector resource presence != network exposure
Inspector PACKAGE_VULNERABILITY != NETWORK_REACHABILITY
Inspector score != Risk Policy v1
Inspector EPSS != OpsLens source-authority replacement
Inspector finding status != business remediation state
Inspector evidence != model authority
runtime evidence correlation != capability authorization
```

## Candidate contract direction

Resource evidence:

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

Finding evidence:

```text
finding_arn
finding_type
finding_status
resource identity
first_observed_at
last_observed_at
updated_at
type-specific bounded details
```

Package-vulnerability details may later admit:

```text
vulnerability_id
package name
package version
package manager
fixed version when present
exploit availability
fix availability
Inspector EPSS as Inspector-scoped evidence
```

Network-reachability details may later admit only:

```text
protocol
open port range
network path component identities
```

## Gate 16.2 authorization

One read-only discovery experiment is authorized using only:

```text
inspector2:ListCoverage
inspector2:ListFindings
```

The experiment should use existing human/bootstrap credentials first.

Expected outcomes are all valid evidence:

```text
PASS with coverage/findings
PASS with zero coverage/findings
AccessDenied
```

An `AccessDenied` result must stop the experiment. It must not cause automatic permission creation.

## Required measured dimensions

```text
ListCoverage attempted
ListFindings attempted
API outcome per call
pages read
covered resources
findings
finding type counts
resource type counts
scan status counts
elapsed time
SDK retry count when observable
AWS mutations = 0
new IAM = 0
model invocations = 0
capability executions = 0
```

## Not authorized

```text
Enable Inspector
Disable Inspector
change scan mode
change ECR scanning
activate Lambda scanning
create EventBridge integration
create suppression filters
new IAM roles/policies
hybrid route integration
runtime-risk scoring
model synthesis
agent capability execution
automatic repository/runtime correlation
```

## Decision

```text
Amazon Inspector fits as an independent runtime-evidence authority.

GO TO ONE BOUNDED READ-ONLY DISCOVERY EXPERIMENT.
```

## Evidence

```text
docs/adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md
labs/evidence/phase-16-gate-16-1-inspector-runtime-evidence-fit-v1.json
```

PR #89 / `feat/governed-gateway-semantic-planner` remains untouched.
