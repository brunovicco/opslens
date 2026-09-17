# ADR 0089 — The correlation index answers which advisories apply, not what a CVE says

## Status

Accepted. Gate 20.2.

## Context

Gate 20.1 built the index and Gate 20.2 is the first
`PublicThreatEvidenceAuthority` implementation reading from it. Writing that
implementation required re-reading both types it must produce. One of them it cannot.

`GhsaPyPIVulnerabilityEvidence` rebuilds completely. `rebuild_ghsa_evidence` maps every
field from a stored row, and a test drives that mapping from `dataclasses.fields` so a
new field on the evidence type fails a test rather than producing an index that cannot
feed it.

`NvdCveCoreRecord` does not. It carries an `ObservedCveVersion`, whose validation
requires the complete canonical JSON of the source CVE, checks that its SHA-256 equals
the stored digest, re-canonicalizes it and checks the identity agrees. The index stores
the digest and seven scalars. It stores the fingerprint, not the body.

```text
the digest of the content != the content
```

The content is load-bearing rather than ceremonial.
`derive_repository_nvd_cvss_evidence` re-runs the Phase 2 CVSS transformer over that
canonical JSON on every request. CVSS is the entire point of NVD enrichment and it
cannot be derived from a hash.

This is the failure `evidence_rebuild` was written to prevent, appearing on the half
that was never given the same treatment. That module's own docstring says a claim about
field coverage rots silently, and proves the GHSA claim with an executable check. The
NVD claim was never written down, never checked, and rotted.

```text
a claim about coverage != a check of coverage
one half proved != both halves proved
```

## Where the content is

Nowhere, as a per-CVE artifact.

```text
NVD Silver   scalars plus pinned Bronze coordinates; no CVE body
NVD Bronze   bootstrap: one nvdcve-2.0-YYYY.json.gz per year, ~20,000 CVEs per object
             incremental: per-update objects from the API
```

`ExactNvdBronzeAuthorityReader` resolves one CVE through that lineage and is correct.
It was built for Gate 19, which read a single CVE for one curated repository. A public
request naming fifty CVEs would open fifty yearly feeds. That is not a tuning problem.

The corpus is mostly bootstrap: 48,293 of 60,259 distinct CVEs.

## Decision

**Gate 20.2 returns GHSA evidence and no NVD records.** The authority sets
`nvd_records` empty, and the Gate 20.4 envelope declares NVD as not covered rather than
omitting it.

The declaration is the load-bearing half. An envelope that returns GHSA evidence with no
NVD record and says nothing lets a caller read the silence as a finding.

```text
no NVD record stored != no NVD record exists
CVE absent from the corpus != CVE without a record
```

That declaration is required regardless of this decision. Only 1,642 of the 5,685 CVEs
the admitted GHSA rows name are present in NVD Silver at all — 28.9%, because the corpus
holds 60,259 of roughly 300,000 published CVEs and was never backfilled past its
yearly-feed bootstrap (ADR 0087, Correction). Absence was already the majority case
before this decision, and the envelope had to say so either way.

**The NVD index table stays and keeps being built.** It is not dead weight and should
not be read as an oversight by a later reader. It answers whether NVD knows a CVE at
all, and carries its status, publication and last-modified instants. That is real
information, short of a typed `NvdCveCoreRecord`, and Gate 20.4 may surface it as its
own weaker field. What it cannot do is satisfy the port's type, and nothing should
pretend otherwise by constructing a partial record.

## What was not decided

Three ways to give the request path the CVE body. None is chosen here, and each names
what it needs before it can be.

**The canonical JSON in the index item.** One read, no new store. DynamoDB caps an item
at 400 KB and CVEs with large CPE configurations exceed that. Needs the size
distribution of canonical CVE JSON — p50, p95, max — which cannot be measured with a
query, because the lake holds no per-CVE body to measure. It requires decompressing
Bronze feeds. After understating the stored item by 2.8x in ADR 0087, this ADR does not
estimate it.

**One S3 object of canonical JSON per CVE, keyed from the index item.** No 400 KB
ceiling, one point GET per CVE, roughly 1,642 objects per generation. It reintroduces
the small-file layout ADR 0086 measured as a problem — but that measurement was 35,584
objects scanned by a query, and this is 1,642 read by known key.

```text
evidence layout != query layout
```

The same distinction that condemned small files as a query surface permits them as a
lookup surface. That is an argument, not a measurement, and it should be checked
against read latency before being believed.

**Materialize per CVE during ingestion rather than during projection.** Cleanest
lineage: the body is written beside the observation that produced it, and the projection
stays a projection. It changes the NVD Silver pipeline, which currently runs on a
schedule without incident.

## Consequences

**Gates 20.2, 20.3, 20.4 and 21.4 are unblocked.** The first shippable slice — a real
verdict for one package — needs GHSA evidence, the Risk Policy score, KEV and EPSS. None
of those depends on the CVE body.

**`rebuild_nvd_evidence` deliberately does not exist.** A test asserts that the NVD index
row covers the scalar fields of `NvdCveCoreRecord` and does not cover
`observed_version.canonical_json`, so the gap is named by an executable check rather
than by this document alone. Someone adding a rebuild without also adding the body will
fail that test instead of shipping a record that cannot be validated.

**The NVD half of the projection is now speculative until one of the three options
lands.** It costs 9.85 MiB of scan and 1,642 items per build, which is cheap, and it
keeps the CVE spine current so that whichever option is chosen starts from a populated
table rather than a backfill. Naming the cost here so it is a choice rather than
inertia.

## Related

- ADR 0085 — partial Silver admission and passthrough emptiness
- ADR 0087 — correlation index store, and its 2026-09-17 correction
- ADR 0088 — index build and swap
- `docs/post-v1-online-analysis.md` — Gates 20.2 through 20.4
