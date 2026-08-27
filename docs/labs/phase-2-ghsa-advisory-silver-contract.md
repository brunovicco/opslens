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

Phase 2.4B defines how one exact source advisory observation becomes versioned structured evidence.

The invariant remains:

> **Agents reason. Code verifies evidence.**

No LLM participates in advisory identity, CVE alias validation, package/range normalization, patched-version evidence, CVSS/CWE normalization, Parquet serialization, or completion decisions.

## Increment 1 — observed advisory identity and core fields

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

The first increment was locally validated with:

```text
19 passed
Ruff: all checks passed
Pyright strict: 0 errors / 0 warnings / 0 informations
```

## Core Silver fields

The normalized core record preserves:

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

## Increment 2 — identifiers, references, CWE, CVSS, and package evidence

The second logical increment adds deterministic structured normalization before any Arrow/Parquet decision.

### Identifiers

The source `identifiers[]` array is preserved in source order.

Known identifier types receive structural validation:

```text
GHSA -> canonical GHSA syntax
CVE  -> canonical CVE syntax
```

Unknown future identifier types remain structured evidence rather than being rejected merely because a new type was introduced.

Collection consistency requires the primary `ghsa_id` to appear in the identifier evidence. When scalar `cve_id` is present, that CVE must also appear in `identifiers[]`. Additional CVE identifiers are not collapsed because advisory-to-CVE aliasing must not be forced into a one-to-one model.

### References

`references[]` is preserved as an ordered collection of non-empty source strings.

OpsLens does not dereference those URLs during normalization.

### CWE

Each source CWE is preserved as:

```text
cwe_id
name
```

Known CWE identifiers must use canonical `CWE-<number>` syntax.

### CVSS

GitHub API version `2026-03-10` deprecates the older top-level `cvss` property in favor of `cvss_severities` for advisory APIs.

GHSA Silver therefore normalizes the current structured source contract:

```text
cvss_severities.cvss_v3
cvss_severities.cvss_v4
```

Known families preserve:

```text
vector_string
score
```

Scores must be finite and between 0 and 10. The vector prefix must match the declared family.

The complete `cvss_severities` source object is also retained as Canonical JSON v1. This means future additive CVSS-family fields remain exact structured evidence even before OpsLens explicitly understands them.

The deprecated top-level `cvss` field still participates in the complete observed-advisory content identity when returned by the source, but no new authoritative Silver field is based on that deprecated property.

### GitHub EPSS

GitHub currently returns an `epss` structure for some global advisories. Phase 2.4B does not select that mirror as the authoritative OpsLens EPSS dataset because FIRST EPSS already has its own source path and provenance model.

The GitHub field remains preserved in the complete source advisory content identity. A dedicated duplicate EPSS Silver authority is not introduced here.

### Credits

GitHub `credits` remains preserved in the complete source advisory object and therefore in observed content identity. Credits are not required for the Phase 2 vulnerability/advisory query exit criteria and do not receive dedicated Silver columns in this increment.

## One-to-many vulnerability/package evidence

The Phase 2.4A live probe observed as many as 36 vulnerability entries in one advisory. Package evidence is therefore modeled as a source-ordered one-to-many collection.

Each `vulnerabilities[]` occurrence preserves:

```text
source_index
package.ecosystem
package.name
vulnerable_version_range
first_patched_version          nullable
vulnerable_functions[]
canonical source-entry JSON
source-entry SHA-256
```

The documented current ecosystem vocabulary is:

```text
rubygems
npm
pip
maven
nuget
composer
go
rust
erlang
actions
pub
other
swift
```

A source value outside that versioned contract fails closed. GitHub's explicit `other` value remains supported.

### Vulnerability occurrence identity

The exact source-array occurrence is identified as:

```text
<observed_advisory_version_id>
/vulnerability:<source_index>
@sha256:<canonical-entry-sha256>
```

Including `source_index` prevents two identical source entries from silently collapsing into one observation.

The complete entry JSON also participates in identity, so an additive source field changes the exact entry version even before receiving a dedicated normalized field.

A reviewed advisory with an empty `vulnerabilities[]` array remains valid evidence; advisory existence is not made conditional on package evidence.

## Explicit Phase boundary

Phase 2.4 preserves source package facts:

```text
package ecosystem
package name
vulnerable version range expression
first patched version when present
vulnerable functions when present
```

The exact `vulnerable_version_range` string is preserved without parsing or simplification.

Phase 2.4 does not decide:

```text
installed_version ∈ vulnerable_version_range
```

That decision remains deterministic **Phase 3 — Vulnerability Correlation Engine** work and will require ecosystem-specific version semantics.

## Current code boundary

Implemented so far:

```text
src/opslens/transformation/ghsa/domain/canonicalization.py
src/opslens/transformation/ghsa/domain/errors.py
src/opslens/transformation/ghsa/domain/models.py
src/opslens/transformation/ghsa/domain/transformer.py
src/opslens/transformation/ghsa/domain/collections_models.py
src/opslens/transformation/ghsa/domain/collections_transformer.py
src/opslens/transformation/ghsa/domain/vulnerability_models.py
src/opslens/transformation/ghsa/domain/vulnerabilities_transformer.py
```

The second increment adds unit coverage for:

```text
identifier/CVE consistency
future identifier preservation
ordered references
canonical CWE validation
CVSS v3/v4 normalization
future CVSS-family source preservation
deprecated cvss independence
one-to-many package entries
nullable first_patched_version
exact range preservation
duplicate source occurrence identity
additive entry evidence
changed entry identity
empty vulnerability arrays
documented ecosystem vocabulary
malformed package/function failure semantics
```

## Silver physical shape still to freeze

Logical advisory and package evidence is now separated cleanly enough to select the physical Silver representation without flattening away source cardinality.

The remaining 2.4B work must freeze and prove:

```text
final composed Silver record
explicit Arrow schema v1
nested/list physical representation
row cardinality rule
deterministic row ordering
deterministic Parquet serialization
logical record-set SHA-256
source-to-Silver provenance fields
Silver completion proof
```

Whether the physical dataset uses one advisory-version row with nested vulnerability entries or multiple related physical datasets must be decided from queryability, provenance, Athena cost, and replay semantics rather than convenience.

## AWS / IAM / cost boundary

This gate still creates no AWS resources and introduces no AWS runtime cost.

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
GHSA_COLLECTIONS_CONTRACT_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_VULNERABILITY_ENTRIES_GATE=PASS_PENDING_LOCAL_VALIDATION
GHSA_ARROW_SCHEMA_GATE=PENDING
GHSA_PARQUET_DETERMINISM_GATE=PENDING
GHSA_2_4B_GATE=IN_PROGRESS
```

## Next step

Run the focused unit/Ruff/Pyright validation for the second logical increment. If green, freeze the composed logical Silver record and Arrow/Parquet v1 physical contract.

Do not introduce GHSA AWS runtime resources until the Phase 2.4B Silver contract is frozen.

## Official references

- GitHub REST API — Global security advisories: https://docs.github.com/en/rest/security-advisories/global-advisories
- GitHub REST API breaking changes — `cvss` deprecation in favor of `cvss_severities`: https://docs.github.com/en/enterprise-cloud@latest/rest/about-the-rest-api/breaking-changes?apiVersion=2026-03-10
- ADR-0005 — GHSA source and synchronization strategy: `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
