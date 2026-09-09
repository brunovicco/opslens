# Phase 16 — Runtime Exposure with Amazon Inspector — Closeout

_Date: 2026-09-09_

## Status

**COMPLETE.**

Phase 16 introduced a bounded read-only Amazon Inspector evidence path without merging repository-risk truth, runtime evidence, model authority, or execution authority.

The phase closed only after the temporary discovery IAM was removed and the bootstrap control plane converged.

## Gate progression

```text
Gate 16.1  capability fit / authority
             -> COMPLETE / READ-ONLY ONLY

Gate 16.2  existing-role discovery
             -> COMPLETE / BLOCKED_BY_EXISTING_IAM

Gate 16.3  minimum read-only IAM decision
             -> COMPLETE / DEDICATED TEMP ROLE

Gate 16.4  temporary role + measured rerun
             -> COMPLETE / SUCCESS / ZERO RECORDS

Gate 16.5  mandatory temporary IAM teardown
             -> COMPLETE / ROLE ABSENT / TERRAFORM CONVERGED
```

## What was proven

### Independent read contract

OpsLens now retains a provider-specific adapter behind typed evidence objects for:

```text
ListCoverage
ListFindings
```

The adapter preserves page-level hashes, counts, SDK retry evidence, account/region context, and type-specific count summaries while avoiding unrestricted persistence of Inspector descriptions or code snippets.

### Authentication is not authorization

The first run successfully assumed the existing GitHub deployment role but measured:

```text
ListCoverage -> AccessDeniedException
```

This preserved:

```text
AWS authentication != Inspector read authorization
```

### Dedicated minimum principal

Rather than broaden `OpsLensGitHubDeployRole`, the experiment used a temporary principal limited to:

```text
inspector2:ListCoverage
inspector2:ListFindings
Resource = "*"
aws:RequestedRegion == us-east-1
main-only immutable GitHub OIDC subject
900-second requested workflow session
```

### Successful read with zero current evidence

Measured run:

```text
workflow:               Inspector Read-Only Discovery
run:                    34414116549 / #2
job:                    102675000098
source main SHA:        bc3c79b4168ffbaa1374b50e60bb8a6d416a14c2
result:                 SUCCESS
client elapsed:         465.877452 ms
ListCoverage:           SUCCESS / 1 page / 0 records / 0 retries
ListFindings:           SUCCESS / 1 page / 0 records / 0 retries
AWS mutations:          0
new IAM during read:    0
model invocations:      0
capability executions:  0
```

Artifact:

```text
id:      10128371987
sha256:  a6f917e62124b4c604891e1a83db9874e3ef34696110dfaead1af16d45a03365
```

The result means only that no coverage/findings were returned for the current dev account/region at measurement time. It does not establish global Inspector service state or value.

## Mandatory cleanup

After the measurement, the repository removed the temporary role/policy from desired state. Human bootstrap reviewed:

```text
Plan: 0 to add, 0 to change, 2 to destroy.
```

Only the experiment role and inline policy were destroyed.

Apply:

```text
0 added / 0 changed / 2 destroyed
```

Fresh plan:

```text
No changes. Your infrastructure matches the configuration.
```

Independent IAM verification:

```text
OpsLensInspectorDiscoveryRole:  ABSENT / NoSuchEntity
OpsLensGitHubDeployRole:         PRESENT
```

## Final retention

```text
Inspector read-only domain/adapter contract:   RETAIN
historical manual discovery workflow:          RETAIN / DISABLED BY DEFAULT
measured zero-record result:                    RETAIN
standing Inspector experiment IAM:              NONE
Inspector activation/configuration:             NOT CREATED
hybrid runtime_exposure routing:                NOT CREATED
repository/runtime automatic correlation:       NOT CREATED
runtime-risk composite scoring:                 NOT CREATED
model synthesis over Inspector evidence:        NOT CREATED
```

## Why no deeper integration

Phase 16 did not produce admitted runtime evidence records to correlate with repository findings. Creating scan configuration, runtime-risk scoring, model synthesis, or automatic correlation anyway would replace measured need with architecture-by-assumption.

The retained result is therefore intentionally smaller:

```text
proven read boundary + honest zero-data result + no standing IAM
```

## Permanent authority boundaries reinforced

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
Inspector finding status != business remediation state
Inspector evidence != model authority
runtime evidence correlation != capability authorization
```

## Canonical records

```text
docs/adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md
docs/adr/0061-dedicated-temporary-inspector-discovery-role.md
docs/adr/0062-retain-inspector-read-contract-without-standing-iam-or-scan-activation.md
docs/adr/0063-phase16-runtime-exposure-closeout.md
labs/evidence/phase-16-gate-16-1-inspector-runtime-evidence-fit-v1.json
labs/evidence/phase-16-gate-16-2-inspector-readonly-discovery-v1.json
labs/evidence/phase-16-gate-16-3-inspector-readonly-iam-decision-v1.json
labs/evidence/phase-16-gate-16-4-inspector-readonly-rerun-v1.json
labs/evidence/phase-16-gate-16-5-inspector-iam-cleanup-postapply-v1.json
labs/evidence/phase-16-closeout-v1.json
```

## Next phase

Phase 17 — Security Hardening is next. It should begin with a cross-cutting threat-model / control-gap inventory rather than introducing a new AWS service by default.

PR #89 remains untouched.
