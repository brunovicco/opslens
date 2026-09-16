# ADR 0087 — Store the correlation index in DynamoDB, one item per (package, advisory)

## Status

Accepted. Resolves the store question left open in `docs/post-v1-online-analysis.md`
for Gate 20.1.

## Context

The request path needs two lookups per analysis: GHSA advisories by normalized package
name, and NVD records by CVE. The open question was whether to keep that projection in
DynamoDB or as Parquet on S3 read through S3 Select. The plan deferred it pending
measurement, and the measurement was blocked twice — first because the GHSA corpus held
ten advisories, then because three of the six queries hit the request path's 10 MiB scan
cutoff (ADR 0086).

Both are resolved. Evidence:
`labs/evidence/correlation-index-probe-v2.json`, probe
`opslens-correlation-index-probe:v1@sha256:4c6024d4…d4a1`, measured 2026-09-16.

## What the measurement says

**Size decides nothing.**

```text
GHSA PyPI index   11,081 rows over 1,491 packages    4,271,187 bytes
NVD by CVE        60,259 CVEs                        6,658,712 bytes
                                                     ─────────────
                                                     10.4 MiB
```

Ten megabytes is below the point where storage cost is an argument. Parquet on S3 is
cheaper at rest and the difference is cents per year. So the choice falls entirely to
access shape, which is what it should have turned on all along.

**The distribution decides the schema.**

```text
max_advisories_per_package  1,323
p95                            18
p50                             1
```

The heaviest key is real, not a normalization artifact. Named:

```text
tensorflow      1,323    shortest source name 10
tensorflow-gpu  1,311    shortest source name 14
tensorflow-cpu  1,307    shortest source name 14
django            416
salt              213
plone             195
```

`shortest_source_name` is 10 for `tensorflow`, so no empty or absent `package_name`
collapsed into that key — the measurement was written to detect exactly that and it
found none.

## Decision

**DynamoDB**, keyed with the normalized package name as partition key and the advisory
identity as sort key: **one item per (package, advisory) pair**, not one item per
package.

The pair shape is forced, not preferred. At the measured 426 bytes for the largest
projected row, an item holding all of `tensorflow`'s advisories would be roughly 564 KB,
against DynamoDB's 400 KB item limit. A per-package item would work for the median
package — which carries exactly one advisory — and fail for the one a Python developer
is most likely to have in their lock file.

```text
the median case != the case that breaks
```

NVD by CVE has no such skew and takes the same store for the same reason: point lookups
under a latency budget, at a size where nothing else argues.

## Consequences

**Phase 21 gains a bound it can compute rather than guess.** A lock file naming
`tensorflow` produces a query returning 1,323 items, about 564 KB, for **one** package.
DynamoDB pages queries at 1 MB, so two or three such packages exhaust a page. The
request bound therefore cannot be expressed in packages alone; it must also bound rows
returned, and — per the project's central invariant — a bound that is reached must
produce an explicit rejection rather than a short answer.

```text
missing evidence != benign evidence
truncated page != complete answer
```

**One project is 36% of the index.** `tensorflow`, `tensorflow-gpu` and `tensorflow-cpu`
carry 3,941 of 11,081 rows between them, because GitHub publishes most TensorFlow
advisories against all three distributions. That is worth knowing before the result
cache in Gate 21.3 is sized, and it means a response naming affected packages will often
repeat near-identical advisory sets three times.

**Widening beyond PyPI stays open.** PyPI is 11,284 of 66,000 vulnerability entries,
17%. All ecosystems together project to roughly 28 MB, still small enough that this
decision would not change. The PyPI-first scope is a choice about applicability-matching
effort, not a limit this store imposes.

## Alternatives

**Parquet on S3 with S3 Select.** Cheaper at rest by an amount too small to matter, and
worse per request: an object read and a scan where DynamoDB does a point lookup. It
would also need either one object per package — 1,491 small objects, reproducing in the
projection the small-file problem ADR 0086 measured in Silver — or a scan whose cost
grows with corpus rather than with request.

**Athena per request.** Rejected earlier and confirmed here. The measurements that
answer these questions scanned 71–82 MiB each. An anonymous caller must not be able to
trigger that, which is why the request path keeps the 10 MiB workgroup and the
projection has its own.

## Related

- ADR 0084 — partial scope admission
- ADR 0086 — two scan budgets
- `docs/post-v1-online-analysis.md` — Gate 20.1
