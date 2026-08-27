# Phase 2.4B — GHSA Advisory / Silver Contract

_Date started: 2026-08-27_

_Status: IN PROGRESS_

## Purpose

Freeze the deterministic GitHub Security Advisory normalization contract before GHSA Bronze/runtime AWS resources are introduced.

Phase 2.4A already accepted the source and synchronization boundary:

```text
runtime source: GitHub Global Security Advisories REST API
API version:    2026-03-10
scope:          reviewed only
identity:       GHSA-first
pagination:     exact Link continuation
bootstrap:      bounded published-time windows
incremental:    bounded modified-time windows
```

Phase 2.4B now defines how one exact source advisory observation becomes versioned structured evidence.

The invariant remains:

> **Agents reason. Code verifies evidence.**

No LLM participates in advisory identity, CVE alias validation, package/range normalization, patched-version evidence, CVSS/CWE normalization, Parquet serialization, or completion decisions.

## Current increment — observed advisory identity and core fields

The first 2.4B increment implements:

```text
complete source advisory object
        ↓
Canonical JSON v1
        ↓
SHA-256
        ↓
ObservedGhsaAdvisoryVersion
        ↓
reviewed-only core normalization
```

The source advisory identity and observed content-version identity remain separate:

```text
ghsa_id
    logical GitHub advisory identity

source_advisory_sha256
    exact canonical source-content identity

observed_advisory_version_id
    GHSA ID + source content SHA-256
```

`updated_at` remains source metadata and is not trusted as the sole content identity.

Unknown additive fields participate in canonical source identity even before they receive dedicated normalized Silver columns.

## Canonical GHSA identifier

The observed-version contract uses GitHub's documented GHSA identifier alphabet and shape:

```text
GHSA-xxxx-xxxx-xxxx
```

The suffix uses the canonical GitHub advisory character set:

```text
23456789cfghjmpqrvwx
```

Malformed primary advisory identity fails closed.

## Core Silver fields

The first normalized record preserves the documented scalar source fields:

```text
ghsa_id
cve_id                         nullable
url
html_url
repository_advisory_url        nullable
summary
description
type
severity
source_code_location           nullable
published_at
updated_at
github_reviewed_at             nullable
nvd_published_at               nullable
withdrawn_at                   nullable
```

Phase 2.4 scope is `type=reviewed`; `unreviewed` and `malware` fail the Silver scope boundary instead of being silently mixed into the curated dataset.

The documented severity vocabulary is bounded to:

```text
unknown
low
medium
high
critical
```

Unknown values in known core semantics fail closed.

## CVE semantics

`cve_id` is optional.

The live Phase 2.4A probes observed reviewed advisories without CVE identifiers, so the Silver contract must not require one CVE per GHSA.

When present, a CVE identifier must use canonical CVE syntax.

The richer `identifiers` collection remains a later 2.4B increment. It will be preserved as source evidence and validated against the primary GHSA/CVE fields without replacing GHSA as the advisory key.

## Temporal semantics

GitHub REST timestamps are parsed as timezone-aware ISO-8601 values and normalized to UTC.

Unlike the NVD contract, the GHSA transformer does not silently assume UTC for a timestamp that omits its offset. A naive timestamp fails closed because the GitHub source contract provides explicit timezone-bearing timestamps.

`withdrawn_at` remains a nullable historical state:

```text
withdrawn_at = null
    -> active observation

withdrawn_at != null
    -> withdrawn historical observation
```

Withdrawal never means that the persisted advisory did not exist.

## Current code boundary

Implemented in this increment:

```text
src/opslens/transformation/ghsa/domain/canonicalization.py
src/opslens/transformation/ghsa/domain/errors.py
src/opslens/transformation/ghsa/domain/models.py
src/opslens/transformation/ghsa/domain/transformer.py
```

Unit coverage includes:

```text
object-key order independence
same-content replay identity
additive-field identity changes
updated_at not used as sole identity
withdrawal creates changed source version
source-array order participates in identity
invalid GHSA rejection
non-finite JSON rejection
noncanonical direct construction rejection
reviewed core normalization
nullable CVE
withdrawal preservation
reviewed-only source scope
bounded severity vocabulary
canonical CVE validation
timezone requirement
missing required-field rejection
```

## Silver shape still to freeze

The Phase 2.4A live evidence showed that one advisory can contain many vulnerability/package entries — up to 36 in the measured recent modified window.

Therefore Phase 2.4B must not flatten package evidence into one arbitrary scalar set.

The next contract increments must decide and prove the deterministic representation of:

```text
identifiers
references
CWEs
CVSS v3 / v4 evidence
GitHub EPSS fields, if retained as source evidence
credits, if retained
vulnerabilities[]
    package.ecosystem
    package.name
    vulnerable_version_range
    first_patched_version
    vulnerable_functions
```

The package/range/fix representation must preserve one-to-many advisory semantics and remain queryable without evaluating package-version applicability.

## Explicit Phase boundary

Phase 2.4 may preserve:

```text
package ecosystem
package name
vulnerable version range expression
first patched version when present
```

It must not decide:

```text
installed_version ∈ vulnerable_version_range
```

That decision remains deterministic Phase 3 — Vulnerability Correlation Engine work.

## AWS / IAM / cost boundary

This increment creates no AWS resources and introduces no AWS runtime cost.

Not implemented here:

```text
GHSA Bronze S3 objects
Lambda
Terraform
EventBridge Scheduler
IAM
secret storage
Silver persistence
Glue
Athena
watermark / authority mutation
```

Credential design remains deferred to the GHSA runtime/security gate accepted by ADR-0005.

## Current gates

```text
GHSA_OBSERVED_ADVISORY_IDENTITY_GATE=PASS
GHSA_CORE_FIELDS_GATE=PASS
GHSA_REVIEWED_SCOPE_SILVER_GATE=PASS
GHSA_CVE_NULLABILITY_GATE=PASS
GHSA_WITHDRAWAL_CORE_GATE=PASS
GHSA_COLLECTIONS_CONTRACT_GATE=PENDING
GHSA_VULNERABILITY_ENTRIES_GATE=PENDING
GHSA_ARROW_SCHEMA_GATE=PENDING
GHSA_PARQUET_DETERMINISM_GATE=PENDING
GHSA_2_4B_GATE=IN_PROGRESS
```

## Next step

Define and test the source collections and one-to-many vulnerability/package evidence before selecting the final Arrow/Parquet physical shape.

Do not introduce GHSA AWS runtime resources until the Phase 2.4B Silver contract is frozen.

## Official reference

- GitHub REST API — Global security advisories: https://docs.github.com/en/rest/security-advisories/global-advisories
- ADR-0005 — GHSA source and synchronization strategy: `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
