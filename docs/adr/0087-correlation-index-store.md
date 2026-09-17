# ADR 0087 — Store the correlation index in DynamoDB, one item per (package, advisory)

## Status

Accepted, with one measurement corrected after the index was built. Resolves the store
question left open in `docs/post-v1-online-analysis.md` for Gate 20.1.

The decision below is unchanged. Two numbers it cited are wrong and are corrected in
**Correction (2026-09-17)** at the end. Read that section before using any byte figure
from this ADR to size anything.

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

Both figures are projected source bytes, and both are wrong as index sizes. See
**Correction (2026-09-17)**.

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
against DynamoDB's 400 KB item limit. The real stored figure is 1.4 MB, so the conclusion
holds by a wider margin than the number that produced it — see
**Correction (2026-09-17)**. A per-package item would work for the median
package — which carries exactly one advisory — and fail for the one a Python developer
is most likely to have in their lock file.

```text
the median case != the case that breaks
```

NVD by CVE has no such skew and takes the same store for the same reason: point lookups
under a latency budget, at a size where nothing else argues.

## Consequences

**Phase 21 gains a bound it can compute rather than guess.** A lock file naming
`tensorflow` produces a query returning 1,323 items for **one** package. DynamoDB pages
queries at 1 MB, so a single package exhausts a page and spills into a second — not
"two or three packages", as first written here; see **Correction (2026-09-17)**. The
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

## Correction (2026-09-17)

The index was built and applied on 2026-09-17. Reading it back corrected two numbers
this ADR asserted. Evidence:
`labs/evidence/correlation-index-stored-item-size-v1.json`.

### The row size was understated by 2.8x

The probe reported 385 bytes per row on average and 426 for the largest. Those are the
bytes of the *projected source fields*. The request path does not read projected source
fields; it reads a stored DynamoDB item, which additionally carries every attribute
name, three full sha-256 digests, the sort key, the `github_identifiers` list as nested
maps, and an 89-byte `index_id` repeated on every one of the 11,081 items.

```text
projected bytes != stored bytes
```

Measured by issuing one unpaginated `Query` against the heaviest partition key and
dividing the page limit by the items that fit:

```text
1,048,576 / 973 items = 1,078 bytes per stored item
```

| | ADR as written | measured |
| --- | --- | --- |
| bytes per GHSA item | 385 | **1,078** |
| GHSA index at rest | 4.27 MB | **11.9 MB** |
| `tensorflow` (1,323 rows) | 564 KB, under one page | **1.43 MB, two pages** |
| `tensorflow` + `-gpu` + `-cpu` | 1.5 MB | **4.25 MB, six pages across three queries** |

Nothing about the store decision changes. 11.9 MB is as far below the point where
storage cost argues as 4.27 MB was, and the per-package item the ADR rejected would have
been 1.4 MB against a 400 KB limit rather than 564 KB — the rejection was right for a
larger reason than the one given.

What changes is the request bound. **973 rows fill a page.** Gate 21.1 must bound rows
against that measured figure, not against the projected one.

### The NVD side of the index is 1,642 rows, not 60,259

The size table above counts every CVE in NVD Silver. The projector does not store every
CVE: `nvd_projection_sql` scopes the NVD query to the CVEs the admitted GHSA rows name,
because `PublicRepositoryThreatEvidence` refuses NVD records unrelated to scoped GHSA
evidence. Of the 5,685 CVEs named by the 11,081 admitted rows, **1,642 were found** in
NVD Silver — 28.9%, because NVD Silver holds 60,259 of roughly 300,000 published CVEs
and was never backfilled past its yearly-feed bootstrap.

```text
CVE absent from the corpus != CVE without a record
```

That is a coverage fact the response envelope in Gate 20.4 has to declare. If the
endpoint returns GHSA evidence with no NVD record and says nothing, a caller reasonably
reads the absence as "no NVD severity exists" for seven CVEs in ten.

The NVD table takes one item per partition key by construction — the projection keeps
only the latest observed version of each CVE — so an NVD lookup returns exactly one item
and can never approach the page limit. Its item size is therefore not a request bound
and was not measured.

### What remains unmeasured

The size of a rebuilt evidence item in an API response. It is neither the projected row
nor the stored item, and this correction exists because those two were conflated once
already. Gate 21.1 measures it rather than deriving it from either.

**Measured 2026-09-17**, by `scripts/measure_response_item_size.py`, retained in
`labs/evidence/response-item-size-v1.json`:

```text
projected source row      385 B
stored index item       1,078 B     2.80x the projected row
final finding            3,267 B     3.03x the stored item, 8.49x the projected row
```

```text
projected bytes != stored bytes != response bytes
```

Three quantities, three multipliers, and a bound taken from the wrong one is wrong by up
to 8.5x. The consequence for Gate 21.1: **the response binds before the read does.** One
1 MB index page holds 973 rows, and one MiB of response holds 320 findings, so a request
that reads a single page can still produce a response no caller should receive.

```text
rows read != findings emitted != response bytes
```

The HTTP wire format is still unmeasured, because it does not exist. That script is what
re-measures when it lands.

## Related

- ADR 0084 — partial scope admission
- ADR 0086 — two scan budgets
- `docs/post-v1-online-analysis.md` — Gate 20.1
