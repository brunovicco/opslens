# ADR 0088 — Build the index into a fresh generation and swap, never in place

## Status

Accepted, with the generation derivation corrected on 2026-09-17. Gate 20.1.

The build-and-swap design is unchanged. The claim about what the generation is derived
from was false in both directions and is corrected in **Correction (2026-09-17)** at the
end. The index contract version moved to `v2` with the fix.

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
re-run is idempotent rather than a new generation of the same thing. That was the
intent; under `v1` the derivation did not deliver it. See
**Correction (2026-09-17)**.

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

## Correction (2026-09-17)

The sentence above — the generation is content-addressed, so a re-run of identical
content is idempotent — was wrong in both directions under `v1`. Writing the offline
index fixture surfaced the second half; the first had been noted and left.

### The identity did not distinguish content

`v1` took the manifest identity over `built_at`, the counts and the watermarks. The rows
were not in it. Two indexes holding entirely different rows in the same quantity, with
the same watermarks and the same clock, derived the same identity — and therefore the
same generation, and the same key space:

```text
index A   one row:  requests    GHSA-fq2j-3j99-rx65
index B   one row:  tensorflow  GHSA-pmpr-55fj-r229, different digest

both      opslens-correlation-index:v1@sha256:08902acd55fd8af3…
```

Nothing about those two indexes is the same except their shape.

```text
identity of the description != identity of the content
```

In practice `built_at` hid this, because it moves every second and the projection takes
about a minute. But what protected the key space was an accident of the clock, not the
rule this ADR says is in force — and the same `built_at` was breaking the other half.

### The identity distinguished time, which is not content

Because `built_at` was inside the identity, a nightly rebuild of an unchanged corpus
produced a new generation every night: the same rows written to a fresh key space, the
previous generation still resident until its TTL, the stored rows doubled for nothing.
That is exactly the counter-like behaviour the paragraph above says the design avoids.

### The fix

`v2` takes the identity over `(contract_version, content_digest, counts, watermarks)`.

- `content_digest` is a sha-256 over every field of every row, sorted by store key so a
  differently ordered query over the same corpus produces the same digest. Coverage is
  asserted from `dataclasses.fields`, so a new row field fails a test until the digest
  carries it.
- `built_at` leaves the identity and stays in the stored manifest. It is provenance: a
  response still reports when the index was built, and two builds of identical content
  from identically fresh sources are the same index whenever they ran.

```text
what is stored != what is digested
when it was built != what was built
```

Watermarks remain in the identity. Two builds over the same rows from sources at
different freshness are different answers, because a response cites that freshness as
its own.

The contract version moves to `v2` so a `v1` digest can never silently match a `v2`
manifest — the same reasoning that moved `public-threat-evidence-scope` to `v2` in Gate
20.0. The next projection run writes a `v2` generation; the `v1` generation expires under
its existing TTL.

## Related

- ADR 0086 — two scan budgets
- ADR 0087 — the store and its schema
