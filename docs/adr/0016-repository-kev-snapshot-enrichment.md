# ADR 0016 — Enrich Repository Findings from a Complete CISA KEV Snapshot

- Status: Accepted
- Date: 2026-09-03
- Phase: 4 — Repository Intelligence
- Gate: 4.9 — CISA KEV enrichment

## Context

Gate 4.8 preserves deterministic repository applicability plus exact GHSA/CVE/NVD/CVSS evidence. Phase 4 must also surface CISA Known Exploited Vulnerabilities (KEV) evidence.

KEV has an important negative-evidence boundary: a missing `SilverKevRecord` supplied to one function call does not prove that a CVE is absent from the CISA catalog. An explicit `not_in_kev` conclusion requires a validated complete catalog snapshot.

Phase 2 already provides the required authority:

- `KevCatalogSnapshot` preserves the original CISA JSON bytes, catalog version, source release time, retrieval time, SHA-256, and declared record count;
- `KevSilverTransformer` validates catalog metadata and declared counts against those immutable bytes, rejects duplicate CVEs, and emits one normalized `SilverKevRecord` per source vulnerability.

Gate 4.9 must reuse that complete-snapshot contract rather than accepting detached KEV rows.

## Decision

### 1. Gate 4.9 accepts one complete immutable KEV Bronze snapshot

The enrichment input is a validated `KevCatalogSnapshot`, not an arbitrary list of KEV rows.

The repository layer reruns the existing `KevSilverTransformer` against the snapshot's immutable `raw_bytes` and verifies complete record accounting before evaluating repository findings.

### 2. KEV state is a three-state evidence result

For each already affected repository finding, Gate 4.9 emits exactly one of:

- `present`: the finding has a GitHub-asserted CVE and that CVE exists in the complete supplied KEV snapshot;
- `absent`: the finding has a GitHub-asserted CVE and that CVE does not exist in the complete supplied KEV snapshot;
- `cve_unavailable`: the GHSA occurrence did not assert a CVE, so KEV membership cannot be evaluated by CVE identity.

`cve_unavailable` must never collapse to `absent`.

### 3. CVE identity comes from the already preserved GHSA alias evidence

The lookup key is `RepositoryNvdEnrichedFinding.alias.github_cve_id`.

NVD presence is not required for KEV evaluation. A GitHub CVE assertion may be checked against a complete KEV snapshot even when no NVD record was supplied to Gate 4.8.

Gate 4.9 does not invent aliases or discover alternate vulnerability identifiers.

### 4. Positive and negative KEV evidence share the same exact snapshot provenance

Every Gate 4.9 record preserves:

- CISA catalog version;
- CISA catalog release timestamp;
- OpsLens retrieval timestamp;
- snapshot UTC date;
- immutable Bronze SHA-256;
- declared/validated record count.

A `present` state additionally preserves the complete normalized `SilverKevRecord` fields for that CVE.

An `absent` state is meaningful only because the complete supplied snapshot was deterministically transformed and indexed.

### 5. The KEV snapshot is bounded before transformation

Gate 4.9 accepts at most 50,000 KEV vulnerability records and at most 32 MiB of KEV source bytes.

Bounds fail closed before an expensive transformation where possible. Input is never truncated.

### 6. Gate 4.9 does not change applicability or priority

The base Gate 4.7 finding id and the Gate 4.8 NVD enrichment id remain unchanged.

KEV membership is evidence only. Gate 4.9 does not assign a risk score, severity, SLA, or priority. Risk weighting belongs to Phase 5 Risk Policy v1.

### 7. KEV enrichment is independently content-addressed

Each enrichment record commits to:

- the prior NVD enrichment id and SHA-256;
- evaluated CVE identity when available;
- KEV state;
- complete KEV snapshot provenance;
- normalized KEV record when present.

This produces a reproducible `repository-kev-enrichment:v1` identity without mutating previous evidence identities.

## Alternatives considered

### Accept `Iterable[SilverKevRecord]`

Rejected. Missing rows would be ambiguous between catalog absence and incomplete caller input.

### Treat missing NVD evidence as inability to check KEV

Rejected. KEV is keyed by CVE and the GHSA source may already assert a CVE independently of NVD.

### Emit only positive KEV matches

Rejected. The Phase 4 finding must distinguish a known complete-snapshot absence from unknown/unavailable CVE identity.

### Query CISA live for every repository finding

Rejected. It would introduce network-time state, duplicate Phase 2 ingestion, impair reproducibility, and increase cost/failure modes.

## Security and operational impact

- No repository or third-party package code is executed.
- Existing immutable CISA source bytes are parsed as data only.
- No LLM is involved.
- No new AWS service or IAM permission is required.
- Incremental AWS cost for this pure deterministic gate is $0.
- Existing Phase 2 ingestion remains the source authority.

## AIP-C01 learning relevance

This gate demonstrates:

- explicit source provenance;
- deterministic grounding before any AI reasoning;
- fail-closed handling of incomplete evidence;
- distinction between negative evidence and missing evidence;
- bounded processing and reproducibility.

## Next gate

Gate 4.10 will attach EPSS evidence with an explicit score snapshot/date contract. EPSS absence or historical selection must remain source- and time-aware rather than being inferred from an incomplete row list.
