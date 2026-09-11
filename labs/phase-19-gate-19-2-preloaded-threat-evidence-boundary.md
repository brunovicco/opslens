# Phase 19 Gate 19.2 — Preloaded Threat Evidence Boundary

_Date: 2026-09-10_

## Decision

For the frozen Gate 19.2 representative measurement, GHSA/NVD/KEV/EPSS source-authority materialization is a **pre-measurement human preparation boundary**.

The measured workload receives one already-admitted `RepresentativeRepositoryThreatEvidence` through `PreloadedRepresentativeThreatEvidenceLoader`.

```text
exact source-authority reads
        -> typed GHSA/NVD/KEV/EPSS
        -> threat-evidence admission
        -> preloaded service state
        |  measurement boundary
        v
repository acquisition
        -> deterministic correlation/risk
        -> Bedrock Retrieve
        -> model reasoning
        -> admitted result
```

## Accounting rationale

Gate 19.2 currently has explicit request-time measurement coverage for GitHub, Athena, Bedrock Retrieve, Bedrock model invocation, retries, result size, and stage/end-to-end latency. It does not define request-time S3 request metrics.

Performing S3 authority reads inside the measured `RepresentativeThreatEvidenceLoader` would therefore create real provider activity that is absent from the frozen accounting contract. That is forbidden by the project invariant:

```text
UNMEASURED != zero
```

The preloaded loader itself performs no provider I/O. It returns the default zero-valued `ProviderResourceUsage` because there are structurally no provider calls in that handoff, not because unobserved S3 use is being treated as zero.

The earlier read-only Athena/source-authority materialization remains preparation evidence outside the request-time workload. Existing Gate 19.2 Athena classifications remain `NOT_APPLICABLE` for the measured workload.

## Frozen binding

The preload is released only to the exact representative anchor:

```text
repository: https://github.com/openedx/mockprock
commit:     18c954d8604df4740c829ba17fa2f3640b92b900
file:       uv.lock
dependency: webob==1.8.10
CVE:        CVE-2026-54770
GHSA:       GHSA-6hx8-3wjj-gr8g
```

Repository URL or immutable commit drift fails closed before the preloaded threat authority is released.

## Non-implications

This experiment boundary does **not** select a production topology. It does not establish that production threat state should be preloaded, request-local, synchronous, or asynchronous.

It creates no public endpoint, AWS resource, IAM role/policy, retry/fallback behavior, or provider call. Bedrock execution remains a human live-execution boundary.

Runtime decision remains:

```text
DEFERRED_PENDING_MEASUREMENT
```
