# Phase 2.4F — GHSA Cross-source Deterministic Evidence Closeout

_Date completed: 2026-08-30_

_Status: COMPLETE_

## Objective

Close the GHSA milestone with a real, read-only AWS proof that one CVE-centered deterministic evidence bundle can preserve independently attributable evidence from NVD, CISA KEV, FIRST EPSS, and GitHub Security Advisories without introducing an LLM, agent, unrestricted text-to-SQL path, package-version range evaluator, or new AWS runtime.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

## Existing analytical surfaces

The proof reused only the already deployed tables:

```text
opslens_dev.nvd_cve_versions
opslens_dev.kev_entries
opslens_dev.epss_scores
opslens_dev.ghsa_advisory_versions
```

No new Glue table, Lambda, queue, scheduler, crawler, database, S3 projection, IAM permission, or Athena workgroup change was required.

## Real proof coordinates

The read-only discovery helper established the actual available coordinates before selection:

```text
EPSS snapshot_date: 2026-08-30
KEV snapshot_date:  2026-08-29

NVD Bootstrap projection_date:
2026-08-22

NVD Incremental projection_date values:
2026-08-26
2026-08-27
2026-08-28
2026-08-29
2026-08-30

GHSA Silver content objects: 10

Athena workgroup: opslens-dev
Athena engine:    Athena engine version 3
cutoff/query:     10,485,760 bytes
result encryption: SSE_S3
```

The proof deliberately retains source-specific coordinates instead of fabricating one global analytical timestamp.

## Deterministic CVE selection

A GHSA-seeded Athena selection query ranked real candidates by:

```text
source_overlap_count DESC
GHSA package evidence present DESC
cve_id ASC
```

Selection query evidence:

```text
QueryExecutionId: 0033e4bf-e092-4b40-8510-1863af1bb6bc
State: SUCCEEDED
DataScannedInBytes: 2,691,294
EngineExecutionTimeInMillis: 1,825
TotalExecutionTimeInMillis: 2,014
```

No current GHSA CVE achieved four-source overlap. All nine returned GHSA CVEs had GHSA + NVD + EPSS evidence and no KEV row in the selected `2026-08-29` snapshot.

The deterministic proof CVE was:

```text
CVE-2026-42350
```

Selected cardinality:

```text
source_overlap_count=3
has_nvd=1
has_kev=0
has_epss=1
ghsa_advisory_version_count=1
ghsa_vulnerability_entry_count=4
nvd_observation_count=1
```

This is an empirical absence of KEV membership for the selected snapshot, not a claim that exploitation is impossible or absent in reality.

## CrossSourceCveEvidenceV1 — PASS

The permanent bundle builder executed five independent source-local Athena queries and composed the result in Python. It did not use a lossy four-way inner join.

Logical result:

```text
CrossSourceCveEvidenceV1
  cve_id=CVE-2026-42350

  NVD
    exists=true
    observation_count=1

  KEV
    snapshot_date=2026-08-29
    is_kev=false
    entry=null

  EPSS
    snapshot_date=2026-08-30
    evidence_present=true

  GHSA
    advisory_version_count=1
    vulnerability_entry_count=4
    range_evaluation_performed=false
```

The bundle retained explicit source coordinates, source-local cardinality checks, query IDs, scan bytes, and timing evidence.

## NVD evidence — PASS

NVD query:

```text
QueryExecutionId: 58059c0e-1603-4b99-ad3b-8648c65048c4
State: SUCCEEDED
DataScannedInBytes: 89,019
EngineExecutionTimeInMillis: 1,034
TotalExecutionTimeInMillis: 1,239
```

One authoritative projected observation was returned:

```text
cve_id=CVE-2026-42350
observed_cve_version_id=CVE-2026-42350@sha256:6896e43969f70c914dbad3cfec130779573a46cc2d990c4337951273746040e4
observation_id=70920613267f4444ac118ce56221837735a2f0579446ec1c90b119b5243f9f26
source_kind=bootstrap
projection_date=2026-08-22
vuln_status=Deferred
is_rejected=false
cwe_ids=[CWE-601]
```

The NVD evidence preserved the available CVSS observation rather than selecting a universal canonical score:

```text
family=V40
version=4.0
base_score=5.1
base_severity=MEDIUM
source=security-advisories@github.com
```

Formal semantic boundary:

```text
canonical_cvss_selected=false
```

## CISA KEV evidence — PASS

KEV query:

```text
QueryExecutionId: 827957c7-3d8d-4051-9466-1c59533b7064
State: SUCCEEDED
DataScannedInBytes: 11,416
EngineExecutionTimeInMillis: 489
TotalExecutionTimeInMillis: 652
```

Result:

```text
snapshot_date=2026-08-29
is_kev=false
entry=null
```

Absence semantics are intentionally limited to:

```text
not present in the selected KEV snapshot
```

No broader exploitation conclusion is inferred.

## FIRST EPSS evidence — PASS

EPSS query:

```text
QueryExecutionId: be524851-f721-4c30-b66f-8e0b9e1c568a
State: SUCCEEDED
DataScannedInBytes: 1,001,599
EngineExecutionTimeInMillis: 610
TotalExecutionTimeInMillis: 736
```

Evidence:

```text
snapshot_date=2026-08-30
cve=CVE-2026-42350
epss=0.00312
percentile=0.23543
model_version=v2026.06.15
score_timestamp=2026-08-30 12:03:42.000
source=first-epss
source_sha256=c6e1090d36708388fa10425d642db88f287b1efc820e7fbef290dce5377149d6
```

The score was read from the explicit latest-discovered snapshot. It was not derived from an implicit `latest` query and no missing score default was fabricated.

## GHSA advisory evidence — PASS

Advisory query:

```text
QueryExecutionId: 51565bb1-5d28-4fc1-8102-9544eb01374f
State: SUCCEEDED
DataScannedInBytes: 3,102
EngineExecutionTimeInMillis: 494
TotalExecutionTimeInMillis: 630
```

One exact historical advisory content version referenced the selected CVE:

```text
ghsa_id=GHSA-g7gw-m874-7rmf
observed_advisory_version_id=GHSA-g7gw-m874-7rmf@sha256:8bd86a78a479089883e824f3ab8477bc1be1d842621ecd7aa61d3d4a7dc97600
source_advisory_sha256=8bd86a78a479089883e824f3ab8477bc1be1d842621ecd7aa61d3d4a7dc97600
severity=low
advisory_type=reviewed
is_withdrawn=false
vulnerability_entry_count=4
```

Summary:

```text
Kargo has Open Redirect in UI OIDC Login Flow via redirectTo Query Parameter
```

The relation remains:

```text
historical exact-content versions; no implicit current
```

## GHSA package/range/fix evidence — PASS

Package query:

```text
QueryExecutionId: dd94f1df-e646-4ae2-bb2f-b504ae2479a2
State: SUCCEEDED
DataScannedInBytes: 3,088
EngineExecutionTimeInMillis: 956
TotalExecutionTimeInMillis: 1,184
```

Four independently identified vulnerability entries were preserved for:

```text
ecosystem=go
package_name=github.com/akuity/kargo
```

Published source evidence:

```text
< 1.7.10
  first_patched_version=1.7.10

>= 1.8.0, < 1.8.13
  first_patched_version=1.8.13

>= 1.9.0, < 1.9.8
  first_patched_version=1.9.8

>= 1.10.0, < 1.10.2
  first_patched_version=1.10.2
```

Every entry carries its own deterministic `vulnerability_entry_id` and `source_entry_sha256`.

The proof explicitly records:

```text
first_patched_version_present_count=4
range_evaluation_performed=false
```

Therefore Phase 2 can answer what GitHub published without deciding whether any concrete installed version is affected.

## Phase 3 boundary — PASS

The bundle proves:

```text
package_ranges_preserved=true
first_patched_versions_preserved=true
installed_version_evaluation_performed=false
repository_exploitability_decision_performed=false
```

No ecosystem range parser or installed-version applicability decision was added.

Those decisions remain deterministic Phase 3 Vulnerability Correlation Engine work.

## Source-local invariants — PASS

The bundle independently verified:

```text
nvd_observation_count=1
kev_row_count=0
epss_row_count=1
ghsa_advisory_version_count=1
ghsa_vulnerability_entry_count=4
ghsa_package_count_matches_advisory_counts=true
selection_expectations_match=true
source_overlap_count=3
```

Missing KEV evidence did not erase NVD, EPSS, or GHSA evidence, and GHSA one-to-many package rows did not multiply unrelated source fields.

## Cost boundary — PASS

The unchanged Athena cutoff remained:

```text
10,485,760 bytes per query
```

All five bundle queries remained independently below that boundary:

```text
NVD:             89,019 bytes
KEV:             11,416 bytes
EPSS:         1,001,599 bytes
GHSA advisory:    3,102 bytes
GHSA packages:    3,088 bytes
```

Aggregate informational scan across the five independent queries:

```text
1,108,224 bytes
```

The aggregate is recorded only for visibility. The enforced workgroup boundary applies independently to each query.

## Read-only / security proof — PASS

The complete 2.4F proof was analytical and read-only.

No proof step required:

```text
AWS infrastructure mutation
new runtime IAM
new deployment IAM
S3 write/delete
Glue mutation
Athena workgroup change
secrets
new scheduler/event source
```

Human execution used temporary AWS IAM Identity Center credentials through the existing `opslens-bootstrap` profile.

## Permanent reproducibility helpers

The following read-only helpers remain in the repository:

```text
scripts/discover_cross_source_coordinates.py
scripts/select_cross_source_proof_cve.py
scripts/build_cross_source_cve_evidence.py
```

They separate:

```text
coordinate discovery
candidate selection
evidence bundle construction
```

so the proof can be repeated without hard-coding stale dates or manually selecting a convenient CVE.

## Phase 2.4F gates

```text
GHSA_CROSS_SOURCE_EXPLICIT_TIME_COORDINATES_GATE=PASS
GHSA_CROSS_SOURCE_NO_IMPLICIT_LATEST_GATE=PASS
GHSA_CROSS_SOURCE_NO_LOSSY_JOIN_GATE=PASS
GHSA_CROSS_SOURCE_SOURCE_LOCAL_AUTHORITY_GATE=PASS
GHSA_CROSS_SOURCE_PHASE3_RANGE_BOUNDARY_GATE=PASS
GHSA_CROSS_SOURCE_NO_NEW_RUNTIME_GATE=PASS
GHSA_2_4F_1_GATE=PASS

GHSA_CROSS_SOURCE_REAL_COORDINATES_GATE=PASS
GHSA_CROSS_SOURCE_EPSS_COORDINATE_GATE=PASS
GHSA_CROSS_SOURCE_KEV_COORDINATE_GATE=PASS
GHSA_CROSS_SOURCE_NVD_SCOPE_GATE=PASS
GHSA_CROSS_SOURCE_GHSA_INVENTORY_GATE=PASS
GHSA_CROSS_SOURCE_WORKGROUP_GUARDRAIL_GATE=PASS
GHSA_2_4F_2_GATE=PASS

GHSA_CROSS_SOURCE_REAL_SELECTION_QUERY_GATE=PASS
GHSA_CROSS_SOURCE_NO_4_OF_4_OVERLAP_GATE=PASS
GHSA_CROSS_SOURCE_MAX_OVERLAP_SELECTION_GATE=PASS
GHSA_CROSS_SOURCE_DETERMINISTIC_TIE_BREAK_GATE=PASS
GHSA_CROSS_SOURCE_SELECTED_CVE_GATE=PASS
GHSA_2_4F_3_GATE=PASS

GHSA_CROSS_SOURCE_REAL_BUNDLE_GATE=PASS
GHSA_CROSS_SOURCE_SOURCE_LOCAL_QUERY_GATE=PASS
GHSA_CROSS_SOURCE_CARDINALITY_GATE=PASS
GHSA_CROSS_SOURCE_NVD_EVIDENCE_GATE=PASS
GHSA_CROSS_SOURCE_KEV_ABSENCE_SEMANTICS_GATE=PASS
GHSA_CROSS_SOURCE_EPSS_EVIDENCE_GATE=PASS
GHSA_2_4F_4_GATE=PASS

GHSA_CROSS_SOURCE_SOURCE_LOCAL_INVARIANTS_GATE=PASS
GHSA_CROSS_SOURCE_SELECTION_EQUIVALENCE_GATE=PASS
GHSA_CROSS_SOURCE_QUERY_COST_GATE=PASS
GHSA_2_4F_5_GATE=PASS

GHSA_CROSS_SOURCE_GHSA_PACKAGE_EVIDENCE_GATE=PASS
GHSA_CROSS_SOURCE_FIRST_PATCHED_VERSION_GATE=PASS
GHSA_CROSS_SOURCE_NO_RANGE_EVALUATION_GATE=PASS
GHSA_CROSS_SOURCE_PHASE3_BOUNDARY_PROOF_GATE=PASS
GHSA_2_4F_6_GATE=PASS

GHSA_2_4F_GATE=PASS
PHASE_2_4_GHSA_GATE=PASS
```

## Outcome

Phase 2.4 — GitHub Security Advisories — is complete.

OpsLens can now deterministically answer, for an explicit CVE and explicit source-time coordinates:

```text
Does NVD evidence exist?
What NVD CVSS/CWE/status evidence was preserved?
Was the CVE present in the selected CISA KEV snapshot?
What EPSS probability/percentile was present in the selected snapshot?
Which exact observed GHSA advisory versions reference the CVE?
Which package ecosystems/names/ranges did GitHub publish?
Which first patched versions did GitHub publish when available?
```

It still intentionally does not answer whether a concrete installed package version satisfies a vulnerable range. That deterministic correlation belongs to Phase 3.

The next roadmap milestone is Phase 2.5 — Historical EPSS expansion. Phase 3 must not begin until Phase 2.5 is completed or explicitly deferred according to the roadmap closeout rules.
