# Phase 19 — Gate 19.2 pre-measurement authority composition

Status: **implementation only; no live measurement has been executed**.

Gate 19.2 now has one application-level composition seam for materializing the representative threat authority before the measured request begins.

The boundary is intentionally ordered:

```text
CrossSourceCveEvidenceV1
  -> parse exact logical coordinates
  -> admit separately supplied immutable locator manifest
  -> locator-bound GHSA/NVD/KEV/EPSS sources
  -> bundle-bound authority loaders
  -> exact typed source readers
  -> final RepresentativeRepositoryThreatEvidence admission
  -> preloaded service-state input for measured workload
```

The locator manifest is admitted before any source loader can execute. Object keys and S3 VersionIds are never inferred from analytical rows, dates, naming conventions, list order, or mutable discovery.

## Measurement boundary

Exact GHSA/NVD/KEV/EPSS source reads remain **pre-measurement preparation** for the frozen Gate 19.2 experiment. They are not inserted into `RepresentativeWorkloadExecution` because the frozen provider-accounting contract does not classify S3 request count or S3 request latency. Treating hidden request-time S3 I/O as zero would violate `UNMEASURED != zero`.

After materialization, the measured workload consumes an already-admitted `RepresentativeRepositoryThreatEvidence` through the existing preloaded loader, whose provider usage is structurally zero.

This is an experiment composition decision, not a claim about the eventual production runtime topology.

## Human execution boundary

This increment constructs no boto3 client and performs no AWS call. A later human-run preparation driver may provide the admitted analytical bundle, the separately captured immutable locator manifest, and concrete exact typed readers using existing operator credentials. That future read-only execution remains a human boundary.

No AWS/IAM resources, public endpoints, or Bedrock calls are created by this increment. PR #89 remains out of scope.

Gate 19.2 remains `DEFERRED_PENDING_MEASUREMENT` until an actual admitted live measurement artifact exists.
