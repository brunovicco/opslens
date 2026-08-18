# ADR-0004: NVD Ingestion and Vulnerability Versioning Strategy

- Status: Accepted
- Date: 2026-08-18

## Context

OpsLens Phase 2.3 introduces NVD/CVE data as the next deterministic
vulnerability-intelligence source after FIRST EPSS and CISA KEV.

The NVD source differs materially from the previous OpsLens sources.

NVD provides:

- yearly JSON 2.0 vulnerability feeds suitable for bulk population;
- a CVE API 2.0 suitable for incremental retrieval by `lastModified`;
- multiple CVSS versions and multiple assessments for the same CVE;
- vulnerability states including `Analyzed`, `Modified`, `Deferred`,
  `Rejected`, `Undergoing Analysis`, `Awaiting Analysis`, and `Received`;
- CWE assessments from different sources;
- NVD-specific CWE placeholders;
- hierarchical CPE configuration expressions;
- metric families that are not CVSS, including SSVC;
- additive schema evolution over time.

A CVE may also be modified repeatedly. OpsLens must preserve the evidence
actually observed at ingestion time instead of overwriting prior observations.

The project invariant remains:

> Agents reason. Code verifies evidence.

No model may determine whether a CVE exists, choose an authoritative CVSS
assessment, infer a CWE, reconstruct a prior NVD state, or advance ingestion
state.

## Evidence from Phase 2.3A

A real NVD 2026 JSON 2.0 yearly feed was inspected on 2026-08-18.

Observed feed characteristics:

```text
compressed bytes:          23,938,173
uncompressed bytes:       282,112,001
records:                    45,447
JSON parse duration:         2.867 s
maximum resident set:        1.17 GiB
peak memory footprint:       ~2.0 GiB
```

The NVD META SHA-256 matched the independently computed SHA-256 of the
uncompressed JSON payload.

A real two-hour CVE API `lastModified` window was also inspected:

```text
window:
2026-08-18T18:00:00
through
2026-08-18T20:00:00

records:                    227
response bytes:             636,122
pages:                      1
```

Representative records proved that:

- one CVE can contain CVSS 4.0, 3.1, and 2.0 simultaneously;
- one CVSS version can contain multiple assessments from different sources;
- NVD Primary and CNA Secondary assessments can materially disagree;
- `metrics` contains non-CVSS families such as `ssvcV203`;
- CWEs preserve source and assessment type;
- `NVD-CWE-Other` is legitimate source evidence;
- rejected CVEs may contain no metrics, weaknesses, or configurations;
- CPE applicability can contain Boolean `AND` expressions where both
  `vulnerable=true` and `vulnerable=false` entries are semantically relevant.

## Decision

OpsLens uses a hybrid NVD ingestion strategy.

```text
Initial population
NVD JSON 2.0 yearly feeds
        ↓
immutable Bronze
        ↓
deterministic Silver

Catch-up and ongoing updates
NVD CVE API 2.0
lastModified windows
        ↓
immutable Bronze run
        ↓
COMPLETE manifest
        ↓
deterministic Silver
        ↓
watermark advancement
```

Yearly feeds are used for bootstrap.

The CVE API is used for incremental synchronization.

This avoids forcing a full API population through one long-running paginated
runtime while still using the API for precise ongoing changes.

## Bootstrap boundary

Bootstrap establishes a deterministic start instant `T0` before bulk feed
retrieval begins.

After all selected yearly feeds have been validated and transformed, OpsLens
performs an API catch-up covering changes from `T0` to a later closed instant
`T1`.

```text
T0
 ↓
download and validate yearly feeds
 ↓
transform bootstrap
 ↓
bootstrap COMPLETE
 ↓
API catch-up T0 → T1
 ↓
incremental operation
```

Overlap is acceptable because writes are idempotent.

A temporal gap is not acceptable.

The design therefore intentionally prefers duplicate source observations over
missing source evidence.

## Bronze contract

Bronze stores immutable source evidence.

### Yearly feed

Candidate path:

```text
bronze/nvd/cve/bootstrap/
  feed_year=YYYY/
    feed_revision=<source-revision>/
      nvdcve-2.0-YYYY.json.gz
      nvdcve-2.0-YYYY.meta
      manifest.json
```

The feed evidence preserves both integrity domains:

```text
source_sha256
    SHA-256 supplied by NVD for the uncompressed JSON

bronze_object_sha256
    SHA-256 computed by OpsLens over the exact stored gzip bytes
```

The manifest also records, at minimum:

- feed year;
- source interface and format;
- source revision;
- NVD META `lastModifiedDate`;
- compressed and uncompressed sizes;
- source SHA-256;
- Bronze object SHA-256;
- retrieval timestamp;
- S3 keys;
- exact S3 VersionIds.

### Incremental API run

Candidate path:

```text
bronze/nvd/cve/updates/
  update_id=<deterministic-run-identity>/
    page_start=000000/response.json
    page_start=002000/response.json
    ...
    manifest.json
```

Each run records:

- normalized requested `lastModStartDate`;
- normalized requested `lastModEndDate`;
- source API format and version;
- source response timestamps;
- `totalResults`;
- page inventory;
- page `startIndex`;
- page byte sizes;
- page SHA-256 values;
- retrieval timestamps;
- exact S3 VersionIds.

A run becomes eligible for deterministic transformation only after all expected
pages pass consistency validation and the run COMPLETE manifest is created.

Individual pages are not authoritative completion evidence.

## Incremental watermark

OpsLens maintains the last successfully completed incremental boundary.

The watermark advances only after:

1. all expected API pages are persisted;
2. page consistency checks pass;
3. the Bronze COMPLETE manifest exists;
4. deterministic Silver transformation succeeds.

A partial download, failed transformation, retry, or invocation success without
complete evidence must not advance the watermark.

A small versioned S3 control object is the initial preferred mechanism.

Introducing DynamoDB solely for this watermark is not justified by the current
requirements.

## Vulnerability version identity

OpsLens does not overwrite a previously observed CVE version.

The logical CVE identifier remains:

```text
CVE-YYYY-NNNN...
```

The observed record-version identity is based on a deterministic canonical
record SHA-256.

`lastModified` is preserved as source metadata but is not trusted as the sole
content identity.

This distinguishes:

```text
same CVE
same source timestamp
same content
```

from:

```text
same CVE
changed observed content
```

and preserves what OpsLens actually received.

## Minimum Silver model

Phase 2.3 initially produces three source-specific analytical datasets.

### Vulnerability versions

One row represents one observed version of a CVE record.

Minimum fields:

```text
cve
source_identifier
published_at
last_modified_at
vulnerability_status
description_en

record_sha256
ingestion_run_id
source_interface
source_version
source_payload_sha256
retrieved_at
```

Initial partition:

```text
cve_year
```

`cve_year` is derived deterministically from the CVE identifier.

### CVSS assessments

One row represents one observed CVSS assessment.

Minimum fields:

```text
cve
cve_record_sha256

metric_family
cvss_version
metric_source
metric_type

base_score
base_severity
vector_string

ingestion_run_id
source_payload_sha256
retrieved_at
```

Initial partition:

```text
cve_year
```

Recognized initial CVSS families are:

```text
cvssMetricV40
cvssMetricV31
cvssMetricV30
cvssMetricV2
```

OpsLens does not collapse these records into one implicit `cvss_score`.

Selecting one preferred score would create a policy that is separate from
source normalization and therefore requires an explicit future deterministic
selection rule.

`base_severity` is nullable because not every supported CVSS representation
provides it in the same way.

### CWE mappings

One row represents one weakness assertion from one source.

Minimum fields:

```text
cve
cve_record_sha256

weakness_source
weakness_type
weakness_id
weakness_kind

ingestion_run_id
source_payload_sha256
retrieved_at
```

Initial partition:

```text
cve_year
```

The initial deterministic classification is:

```text
CWE-<number>
    → CWE

NVD-CWE-Other
NVD-CWE-noinfo
    → NVD_PLACEHOLDER
```

Source and assessment type are retained rather than flattening CWEs into one
source-free list.

## Rejected CVE semantics

A record with:

```text
vulnerability_status = Rejected
```

still proves that the CVE identifier exists in the persisted NVD evidence.

Missing metrics or weaknesses do not imply:

```text
CVSS = 0
CWE = none by authoritative assessment
CVE does not exist
```

They mean that the corresponding structured evidence is unavailable in that
observed record.

## Unsupported metric families

The NVD `metrics` container is not synonymous with CVSS.

Recognized CVSS families are normalized to the CVSS Silver dataset.

Unknown or intentionally unsupported metric families:

- remain preserved in Bronze;
- are not reinterpreted as CVSS;
- may be counted or observed through telemetry;
- do not fail merely because an additive metric family appears.

Malformed content inside a metric family that OpsLens explicitly supports is a
different condition and fails closed.

This distinction allows source schema evolution without silently accepting
invalid known semantics.

## CPE configuration semantics

NVD CPE configurations are not flattened in the minimum Phase 2.3 Silver
contract.

Configuration trees can encode:

- `AND`;
- `OR`;
- `negate`;
- vulnerable and non-vulnerable CPE matches;
- match criteria identifiers;
- version boundaries.

Flattening only `vulnerable=true` entries would destroy the applicability
semantics of legitimate NVD records.

Raw configuration evidence therefore remains in Bronze until OpsLens
introduces a dedicated deterministic configuration model.

## Fixed-version extraction

OpsLens does not derive an authoritative `fixed_version` from free-text NVD
descriptions.

A description may mention a fixed version, but converting that prose into an
authoritative structured fact would require an extraction policy and additional
verification.

Structured advisory sources may provide stronger fixed-version evidence in a
later Phase 2 source increment.

## Runtime choice

Lambda is the first transformation runtime for NVD.

The Phase 2.3A workload spike showed that one current yearly feed is large
enough to rule out small-memory Lambda configurations but remains bounded
enough that Glue ETL is not yet justified.

Initial AWS benchmark candidate:

```text
memory:  4096 MB
timeout: 300 seconds
```

These values are measurement starting points, not final configuration.

The real transformation benchmark must include:

```text
download
decompression
JSON parsing
validation
normalization
Arrow construction
Parquet serialization
```

Glue ETL remains a fallback only if measured Lambda execution cannot remain
comfortably within the runtime and memory envelope.

Glue Data Catalog usage is independent from the choice of Glue ETL as a
transformation engine.

## Idempotency

Idempotency is defined at separate layers.

Bootstrap source identity:

```text
feed year
+
NVD source revision / source SHA-256
```

Incremental run identity:

```text
normalized closed lastModified window
```

Observed CVE version identity:

```text
CVE identifier
+
canonical record SHA-256
```

Reprocessing identical source evidence must not create duplicate logical
evidence.

A genuinely changed CVE record creates a new observed version instead of
overwriting the prior version.

## Failure semantics

Transient failures may be retried, including:

- network timeouts;
- temporary NVD server failures;
- throttling;
- temporary S3 failures.

Deterministic evidence failures fail closed, including:

- source hash mismatch;
- page sequence inconsistency;
- inconsistent `totalResults`;
- malformed required CVE identity;
- malformed known CVSS structures;
- manifest inconsistency.

A deterministic failure must not:

- create a COMPLETE run manifest;
- publish that run as valid Silver evidence;
- advance the incremental watermark.

The Phase 2.3 deliberate-failure scenario will use pagination inconsistency to
prove this behavior without intentionally hammering the public NVD API.

## API key

OpsLens does not introduce an NVD API key in the initial design.

The bootstrap uses yearly feeds and the measured normal incremental workload is
small enough to begin within the public API limits.

This avoids adding secret management before a measured throughput requirement
exists.

An API key may be introduced later if operational evidence demonstrates a real
need.

## Alternatives considered

### API-only bootstrap

Rejected for the initial architecture.

Bulk population would require many paginated API calls, rate-limit pacing, and
a longer orchestration path despite NVD already publishing bounded yearly
artifacts designed for bulk consumption.

### Feed-only ongoing synchronization

Rejected.

Repeatedly downloading modified/recent feed windows is less precise than using
the CVE API `lastModified` contract for ongoing incremental synchronization.

### One flattened vulnerability table

Rejected.

It would either lose multiple CVSS assessments and CWE provenance or produce a
large nested analytical schema with unclear semantics.

### One canonical CVSS score during ingestion

Rejected.

The source can contain multiple valid assessments that materially disagree.
Choosing one is policy, not normalization.

### Flatten CPE matches into affected products

Rejected.

It destroys the Boolean applicability semantics represented by NVD
configuration trees.

### Glue ETL from the first implementation

Not selected.

The measured current feed does not yet justify introducing Spark. Glue ETL
remains a runtime fallback based on evidence.

### DynamoDB for the initial watermark

Not selected.

One versioned control object is sufficient for the current single-source
incremental state requirement.

## Consequences

### Positive

- preserves historical observations instead of overwriting CVEs;
- keeps source evidence immutable and reproducible;
- separates bootstrap efficiency from incremental precision;
- retains CVSS provenance and disagreement;
- retains CWE provenance;
- handles rejected CVEs correctly;
- tolerates additive NVD metric families without weakening known validation;
- avoids incorrect CPE flattening;
- supports deterministic recovery after partial ingestion;
- avoids unnecessary AWS services.

### Trade-offs

- Silver contains multiple rows for one CVE and may require explicit temporal
  selection in queries;
- consumers cannot assume one canonical CVSS score;
- historical versioning increases storage compared with latest-state-only
  normalization;
- CPE applicability remains unavailable as a normalized Silver capability in
  the minimum slice;
- Lambda memory must be benchmarked with the complete transformation pipeline;
- bootstrap requires an explicit feed-to-API catch-up boundary.

## Operational rule

Until superseded by another ADR:

```text
bootstrap:
NVD yearly JSON 2.0 feeds

incremental:
NVD CVE API 2.0 lastModified windows

history:
preserve observed CVE versions

Bronze:
immutable source evidence

Silver:
vulnerability versions
CVSS assessments
CWE mappings

CPE configurations:
Bronze only in the minimum slice

preferred CVSS:
no implicit selection policy

runtime:
Lambda first
Glue ETL only if measurement requires it

watermark:
advance only after complete Bronze and Silver success
```
