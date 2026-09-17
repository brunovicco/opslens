# ADR 0088 — Build the index into a fresh generation and swap, never in place

## Status

Accepted. Gate 20.1.

## Context

The projection is rebuilt on a schedule from the whole corpus. Between the first write
and the last, the index holds a mixture of two builds. The request path cannot tell the
difference, so during that window it can answer from a package's new rows and another
package's old ones — or, worse, from a package whose new rows have not been written yet.

The second case is the one that matters. A package whose rows are mid-rewrite looks
exactly like a package with no advisories, and the endpoint answers "no known
vulnerabilities". That is the single failure this project cannot afford, produced by a
maintenance window rather than by a defect.

```text
partially built index != index
missing rows != no advisories
```

## Options considered

**Overwrite in place.** Rejected outright. It is the mixture described above.

**Tag every row with the build that wrote it, filter at read time.** Correct, and
expensive exactly where it hurts. ADR 0087 measured `tensorflow` at 1,323 rows; with two
generations resident, a query for that one package reads 2,646 items to return 1,323.
The cost of the safety lands on the hottest key in the corpus, and the request path pays
it on every request.

**Alternate between two tables, with a pointer naming the live one.** Correct and
avoids the filtering, at the cost of doubling the tables and making the table name itself
dynamic.

## Decision

One table per source, with the **build generation in the partition key**:

```text
ghsa    pk = "<generation>#<canonical package name>"    sk = "<occurrence key>"
nvd     pk = "<generation>#<cve id>"
```

A build writes into a key space nothing is reading. When it finishes, it writes the
manifest and flips a single pointer item naming the live generation. Until that write,
the new rows are unreachable; after it, the old ones are.

The generation is the manifest's own content-addressed digest, truncated. It is not a
counter, so two builds of identical content land in the same key space and a
re-run is idempotent rather than a new generation of the same thing.

```text
written != readable
readable != current
```

Old generations expire by TTL rather than being deleted by the build, so a build that
fails halfway leaves no orphan cleanup to run and no partial delete to reason about.

## Consequences

**A reader takes one small read before its first query.** The pointer item names the
live generation; a worker reads it once per cold start and caches it. That read is a
single item, not a scan.

**A response can name what answered it, and prove it.** The generation in the key is
derived from the manifest digest, so a row's own key ties it to the manifest the response
cites. A response citing a manifest whose generation does not match its rows is
detectable rather than plausible.

**Storage doubles during a build, briefly.** ADR 0087 measured the whole index at
10.4 MiB. Two generations resident is 21 MiB. This is not a consideration at this size,
and saying so is more useful than pretending it was weighed.

**The TTL sets a floor on rebuild cadence.** A generation must outlive any request that
started under it. The cadence is daily and requests are bounded in seconds, so the floor
is far below the cadence — but a future move to continuous rebuilds would have to
revisit it, and that is named here rather than discovered then.

## Related

- ADR 0086 — two scan budgets
- ADR 0087 — the store and its schema
