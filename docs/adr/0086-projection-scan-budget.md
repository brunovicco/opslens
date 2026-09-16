# ADR 0086 — Two scan budgets, because a request and a projection are not the same query

## Status

Accepted.

## Context

`opslens-dev` is the only Athena workgroup, and it enforces
`bytes_scanned_cutoff_per_query = 10485760` with `enforce_workgroup_configuration = true`.
Its own Terraform comment records where that number came from: *"Athena/Terraform
minimum: 10 MiB"*. It was not chosen against a workload. It was set to the floor, at a
time when the only thing queried was a single EPSS Silver Parquet object.

Loading the real GHSA corpus made the consequence measurable. On 2026-09-16 the
correlation index sizing probe reported:

```text
ghsa_advisory_versions   35584 objects   738.5 MiB   35584 partition prefixes
nvd_cve_versions           253 objects    62.6 MiB      23 partition prefixes

ghsa_census        SUCCEEDED   scanned  7.43 MiB
ghsa_ecosystems    CANCELLED   scanned 10.00 MiB   Bytes scanned limit was exceeded
ghsa_shape         CANCELLED   scanned 10.00 MiB   Bytes scanned limit was exceeded
ghsa_hot_key       CANCELLED   scanned 10.00 MiB   Bytes scanned limit was exceeded
```

The census survives because it reads scalar columns. The other three read the nested
`vulnerabilities` array — 66,000 entries carrying package name, vulnerable range,
first patched version, entry id and source hash. The table is partitioned by `ghsa_id`,
so there are 35,584 partitions and no partition prunes an ecosystem filter. Any
aggregate over that column reads the corpus.

This is not a probe problem. The same queries are what Gate 20.1 has to run to build
the GHSA-by-package and NVD-by-CVE projection, and a projection keyed by package
cannot be built from a subset of the corpus.

## Decision

Add a second bounded workgroup, `opslens-dev-projection`, with
`bytes_scanned_cutoff_per_query = 2147483648` and configuration still enforced. The
scheduled projector and operator measurements run there. Everything reachable from the
public request path continues to run in `opslens-dev` at its 10 MiB floor.

```text
request budget != projection budget
```

The 10 MiB cutoff is not a limitation to be worked around. It is the control that stops
an anonymous caller from triggering an unbounded scan, and it is exactly right for that
job. Raising it to accommodate the projector would have disarmed the request path to
feed a scheduled batch job — the two workloads would have shared a number that suits
neither.

2 GiB is sized from the measurement, not picked: a full column scan across both Silver
tables stays under 800 MiB today, so the ceiling carries about 2.5x of corpus growth and
still stops a runaway query. At Athena's per-terabyte rate a full scan costs under a
cent, so a daily projection build is not a cost argument in either direction.

The probe also stops asserting the cutoff and reads it from the workgroup. It previously
carried `_WORKGROUP_SCAN_CUTOFF_BYTES = 10_485_760` as a constant and published it as
evidence. Pointed at a different workgroup, that constant would have reported a bound
that was not the one in force.

```text
declared constant != configuration in force
```

## Consequences

Gate 20.1 can take its shape measurement and the store decision it was blocked on.

Two workgroups now exist, and which one a query runs in becomes a security-relevant
choice rather than a detail. A future change that lets a request-path component address
the projection workgroup would quietly remove the ceiling that makes the endpoint safe
to expose. That coupling deserves its own standing verifier when the request path is
built; it is named here rather than left implicit.

A second measurement is recorded without being acted on yet. 35,584 Parquet objects
averaging roughly 21 KiB is a small-file layout: right for immutable per-advisory
evidence, where each advisory carries its own identity, and wrong as a query surface.
It is the strongest available argument that the projection has to exist rather than the
request path querying Silver directly — and it is now measured rather than assumed.

```text
evidence layout != query layout
```

## Related

- ADR 0082 — semantic query catalog configuration
- `docs/post-v1-online-analysis.md` — Gate 20.1
