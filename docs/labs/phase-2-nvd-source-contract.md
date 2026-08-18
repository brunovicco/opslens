# Phase 2 Lab — NVD Source Contract and Workload Spike

## Purpose

Validate the source contract, temporal semantics, workload characteristics, and
minimum deterministic analytical model required before implementing NVD/CVE
ingestion in OpsLens.

This is Phase 2.3A.

It intentionally creates no AWS resources.

The lab proves the invariant:

> Agents reason. Code verifies evidence.

No model participates in source interpretation, CVE existence, CVSS selection,
CWE normalization, version identity, temporal state, or runtime selection.

## Scope

This lab validates:

```text
NVD yearly JSON 2.0 feed
        ↓
real source META and payload
        ↓
integrity measurement
        ↓
workload measurement
        ↓
representative record inspection

NVD CVE API 2.0
        ↓
real closed lastModified window
        ↓
incremental response measurement
        ↓
pagination contract

evidence
        ↓
Bronze contract
        ↓
minimum Silver contract
        ↓
Lambda-first runtime decision
```

Out of scope:

- AWS resource creation;
- Terraform changes;
- EventBridge scheduling;
- production Lambda code;
- Glue tables;
- Athena tables;
- GitHub Security Advisories;
- multi-source correlation;
- RAG;
- embeddings;
- Bedrock;
- agents;
- unrestricted text-to-SQL.

## Repository baseline

The spike started from:

```text
branch:
phase-2-nvd-source-contract

base commit:
74f0c6d3bf24ef163b4d9fc1dc20959a98155855

base commit message:
feat(phase-2): complete CISA KEV Glue and Athena analytics (#19)
```

The branch was created from a clean and current `main`.

## Temporary workspace

Large source artifacts were intentionally kept outside the repository.

```text
/tmp/opslens-nvd-spike
```

The yearly NVD feed was not copied into Git.

## Yearly feed inspected

Source artifact:

```text
nvdcve-2.0-2026.json.gz
```

Associated META values observed on 2026-08-18:

```text
lastModifiedDate:
2026-08-18T03:00:12-04:00

size:
282112001

zipSize:
23938309

gzSize:
23938173

sha256:
10FB32C20BD6187FE43FA047D74772256F5B37C18029B17C5379A1F4E18F5D4F
```

Measured exact gzip size:

```text
23938173 bytes
```

Measured SHA-256 of the stored gzip bytes:

```text
e3b48ac725eda895208fda77165d611e9a8d118304442e5b988c9108ded59739
```

Measured SHA-256 of the uncompressed JSON:

```text
10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f
```

Measured uncompressed size:

```text
282112001 bytes
```

The independently calculated uncompressed SHA-256 matched the NVD META value.

Result:

```text
NVD_FEED_INTEGRITY_GATE=PASS
```

## Integrity model

The lab established two different integrity values.

```text
source_sha256
    NVD-provided SHA-256 of the uncompressed JSON

bronze_object_sha256
    OpsLens-computed SHA-256 of the exact gzip bytes stored in Bronze
```

Both must be preserved because they prove different properties.

The first verifies the payload according to the source manifest.

The second verifies the exact object persisted by OpsLens.

## Feed structure and workload

Observed NVD envelope:

```text
FORMAT=NVD_CVE
VERSION=2.0
TIMESTAMP=2026-08-18T03:00:01.3993321
RESULTS_PER_PAGE=45447
START_INDEX=0
TOTAL_RESULTS=45447
ACTUAL_RECORDS=45447
```

Local Python `json.load()` measurement:

```text
PARSE_DURATION_SECONDS=2.867
MAX_RSS_BYTES=1224441856
MAX_RSS_MIB=1167.72
```

The external timing command additionally reported:

```text
real:
3.87 seconds

maximum resident set size:
1224441856 bytes

peak memory footprint:
2131068992 bytes
```

The representative-record inspection later observed:

```text
maximum resident set size:
1422262272 bytes

peak memory footprint:
2104805344 bytes
```

The feed therefore cannot be evaluated by compressed size alone.

Approximately 23.9 MB of gzip source material expanded into a workload with
more than 1 GiB of Python resident memory before adding the complete production
normalization and Parquet pipeline.

## Record coverage

Observed 2026 records:

```text
WITH_METRICS=43864
WITHOUT_METRICS=1583

WITH_WEAKNESSES=42643
WITHOUT_WEAKNESSES=2804

WITH_CONFIGURATIONS=24413
WITHOUT_CONFIGURATIONS=21034
```

Observed vulnerability statuses:

```text
Analyzed:               21260
Modified:                3000
Deferred:               13440
Rejected:                 688
Undergoing Analysis:      445
Awaiting Analysis:       1999
Received:                4615
```

Missing metrics, weaknesses, or configurations are therefore legitimate source
conditions and cannot automatically be interpreted as malformed records.

## Metric families

Observed metric assessment counts:

```text
cvssMetricV40: 13801
cvssMetricV31: 47489
cvssMetricV2:   4053
ssvcV203:      40286
cvssMetricV30:   471
```

This proved that the NVD `metrics` container is not a CVSS-only container.

A parser must distinguish known CVSS metric families from other metric
families.

An additive unsupported metric family is preserved in Bronze and must not be
silently reinterpreted as CVSS.

Malformed data inside a metric family that OpsLens explicitly supports fails
closed.

## Representative CVEs

The structural probe selected:

```text
CVE-2026-0544
    CVSS v4.0
    multiple CVSS assessments

CVE-2026-21452
    NVD CWE placeholder

CVE-2026-21644
    Rejected record without metrics

CVE-2026-0581
    Boolean AND configuration
```

All four target CVEs were found.

```text
FOUND=[
  'CVE-2026-0544',
  'CVE-2026-0581',
  'CVE-2026-21452',
  'CVE-2026-21644'
]
```

## Multiple CVSS assessments

`CVE-2026-0544` demonstrated materially different assessments for one CVE.

Observed examples:

```text
CVSS 4.0
source=cna@vuldb.com
type=Secondary
baseScore=5.5
baseSeverity=MEDIUM

CVSS 3.1
source=cna@vuldb.com
type=Secondary
baseScore=7.3
baseSeverity=HIGH

CVSS 3.1
source=nvd@nist.gov
type=Primary
baseScore=9.8
baseSeverity=CRITICAL

CVSS 2.0
source=cna@vuldb.com
type=Secondary
baseScore=7.5
baseSeverity=null
```

A single ingest-time field such as:

```text
cvss_score=9.8
```

would discard valid source evidence and introduce an unstated selection policy.

Result:

```text
NVD_CVSS_MULTI_ASSESSMENT_GATE=PASS
```

## Non-CVSS metrics

The same CVE contained:

```text
METRIC_FAMILY=ssvcV203
```

with `ssvcData` instead of `cvssData`.

This proves that iterating every `metrics` member as CVSS is invalid.

Result:

```text
NVD_CVSS_NON_CVSS_METRIC_GATE=PASS
```

## CWE provenance

`CVE-2026-0544` contained CNA Secondary weakness assertions:

```text
CWE-74
CWE-89
```

and an NVD Primary assertion:

```text
CWE-89
```

The same weakness identifier therefore may have multiple assertions with
different provenance.

`CVE-2026-21452` contained:

```text
CNA Secondary:
CWE-400
CWE-789

NVD Primary:
NVD-CWE-Other
```

`NVD-CWE-Other` is legitimate NVD evidence and must not be rejected merely
because it does not match `CWE-<number>`.

Result:

```text
NVD_CWE_PROVENANCE_GATE=PASS
NVD_CWE_PLACEHOLDER_GATE=PASS
```

## Rejected CVE semantics

Observed record:

```text
CVE:
CVE-2026-21644

status:
Rejected

description:
Rejected reason: Not used

metrics:
[]

weaknesses:
[]

configurations:
[]
```

The deterministic interpretation is:

```text
CVE exists in persisted NVD evidence:
true

vulnerability_status:
Rejected

CVSS:
unavailable in this observation

CWE:
unavailable in this observation
```

The following interpretations are invalid:

```text
CVE does not exist
CVSS = 0
```

Result:

```text
NVD_REJECTED_CVE_GATE=PASS
```

## Boolean CPE configuration semantics

`CVE-2026-0581` contained one configuration with top-level:

```text
operator=AND
```

and two OR nodes.

One match represented vulnerable firmware:

```text
vulnerable=true
criteria=cpe:2.3:o:tenda:ac1206_firmware:15.03.06.23:*:*:*:*:*:*:*
```

Another represented associated hardware:

```text
vulnerable=false
criteria=cpe:2.3:h:tenda:ac1206:-:*:*:*:*:*:*:*
```

The `vulnerable=false` entry participates in the Boolean applicability
expression.

Flattening only vulnerable CPE entries would destroy that semantics.

Result:

```text
NVD_CONFIGURATION_BOOLEAN_SEMANTICS_GATE=PASS
```

CPE configurations remain in Bronze in the minimum Phase 2.3 slice.

## Free-text fixed version

One inspected CVE description contained an explicit sentence identifying a
fixed software version.

The Phase 2.3 source contract does not convert such prose into an authoritative
`fixed_version`.

The text remains preserved as source evidence.

Structured fixed-version evidence should come from an appropriate structured
source or a separately verified deterministic policy.

## Real incremental API window

A real closed `lastModified` interval was retrieved:

```text
lastModStartDate:
2026-08-18T18:00:00.000

lastModEndDate:
2026-08-18T20:00:00.000
```

Observed response:

```text
BYTES=636122
FORMAT=NVD_CVE
VERSION=2.0
TIMESTAMP=2026-08-18T21:47:02.824
RESULTS_PER_PAGE=227
START_INDEX=0
TOTAL_RESULTS=227
RECORDS_IN_RESPONSE=227
```

First record in the response:

```text
CVE-2026-20068
published=2026-03-04T18:16:22.330
lastModified=2026-08-18T18:32:42.913
```

Last record in the response:

```text
CVE-2026-70667
published=2026-08-18T19:17:03.293
lastModified=2026-08-18T19:17:03.293
```

The measured normal incremental workload was small but the production contract
must remain paginated.

Result:

```text
NVD_INCREMENTAL_REAL_WINDOW_GATE=PASS
```

## Temporal model

A `snapshot_date`-only model is not sufficient for NVD.

NVD CVEs can change repeatedly, and OpsLens must preserve each observed record
version.

The selected temporal model is:

```text
source run
    ↓
immutable Bronze evidence
    ↓
canonical record SHA-256
    ↓
observed CVE version
```

Incremental runs use explicit closed `lastModified` windows.

A run watermark advances only after complete Bronze and Silver success.

Result:

```text
NVD_TEMPORAL_MODEL_GATE=PASS
```

## Bootstrap strategy

The selected bootstrap strategy is:

```text
T0
 ↓
NVD JSON 2.0 yearly feeds
 ↓
feed integrity validation
 ↓
bootstrap transform
 ↓
bootstrap COMPLETE
 ↓
NVD CVE API catch-up T0 → T1
 ↓
ongoing incremental API windows
```

Overlap between feed data and API catch-up is acceptable because processing is
idempotent.

A source-evidence gap is not acceptable.

Result:

```text
NVD_BOOTSTRAP_STRATEGY_GATE=PASS
```

## Minimum Silver contract

The Phase 2.3 minimum analytical model is separated into:

```text
nvd_vulnerability_versions
nvd_cvss_metrics
nvd_cwe_mappings
```

This preserves:

- CVE version history;
- CVSS version;
- CVSS source;
- CVSS assessment type;
- CVSS score and vector;
- nullable severity;
- CWE source;
- CWE assessment type;
- NVD CWE placeholders;
- ingestion provenance.

No implicit preferred CVSS score is created.

CPE configuration expressions remain in Bronze.

Result:

```text
NVD_MINIMUM_SILVER_CONTRACT_GATE=PASS
```

## Lambda versus Glue ETL

The local measurements rule out treating the feed as a small-memory workload.

They do not yet justify Spark.

The first production transformation benchmark therefore uses Lambda.

Initial benchmark candidate:

```text
memory:
4096 MB

timeout:
300 seconds
```

The benchmark must measure the full transformation path rather than JSON parsing
alone.

The required path includes:

```text
source retrieval
decompression
JSON parsing
validation
normalization
Arrow construction
Parquet serialization
```

Glue ETL remains the fallback only if that measured Lambda path cannot remain
comfortably bounded.

Result:

```text
NVD_LAMBDA_VS_GLUE_EVIDENCE_GATE=PASS
```

## API-key decision

No NVD API key is introduced by the first implementation.

The bootstrap uses yearly feeds and the measured two-hour incremental request
returned only 227 records.

Adding secret management before a demonstrated throughput requirement would add
architecture without evidence.

The decision can be revisited if operational measurements require authenticated
higher-rate API access.

## Failure scenario selected for Phase 2.3

The main deliberate failure will be pagination inconsistency.

Example invalid evidence:

```text
page 0:
startIndex=0
totalResults=3500

page 1:
startIndex=2001
```

Expected behavior:

```text
PAGINATION_GATE=FAIL
COMPLETE_MANIFEST_CREATED=false
SILVER_CREATED=false
WATERMARK_ADVANCED=false
```

The failure is simulated through the source adapter/test boundary.

OpsLens will not deliberately cause public NVD throttling by sending excessive
requests.

## Final Phase 2.3A gates

```text
NVD_SOURCE_INTERFACE_GATE=PASS
NVD_FEED_INTEGRITY_GATE=PASS
NVD_BOOTSTRAP_STRATEGY_GATE=PASS
NVD_INCREMENTAL_STRATEGY_GATE=PASS
NVD_INCREMENTAL_REAL_WINDOW_GATE=PASS
NVD_TEMPORAL_MODEL_GATE=PASS
NVD_BRONZE_CONTRACT_GATE=PASS
NVD_CVSS_MULTI_ASSESSMENT_GATE=PASS
NVD_CVSS_NON_CVSS_METRIC_GATE=PASS
NVD_CWE_PROVENANCE_GATE=PASS
NVD_CWE_PLACEHOLDER_GATE=PASS
NVD_REJECTED_CVE_GATE=PASS
NVD_CONFIGURATION_BOOLEAN_SEMANTICS_GATE=PASS
NVD_MINIMUM_SILVER_CONTRACT_GATE=PASS
NVD_LAMBDA_VS_GLUE_EVIDENCE_GATE=PASS
NVD_2_3A_GATE=PASS
```

## Result

Phase 2.3A is complete.

No AWS resource was introduced by this lab.

The next implementation increment is:

```text
Phase 2.3B — NVD Bootstrap Bronze
```

The next increment must implement only the first deterministic bootstrap
ingestion path before adding the incremental API runtime or analytical Silver
datasets.
