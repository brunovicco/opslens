# OpsLens — Phase 2 Closeout Roadmap

_Last updated: 2026-09-02_

This checkpoint advances the roadmap only through the formally completed Phase 2 exit boundary. It does not start Phase 3.

## Roadmap status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2.1  CISA KEV Bronze ingestion                          COMPLETE
Phase 2.2  CISA KEV Silver + Glue + Athena                    COMPLETE
Phase 2.3  NVD / CVE Bronze + Silver + Watermark + Analytics  COMPLETE
Phase 2.4  GitHub Security Advisories                         COMPLETE
Phase 2.5  Historical EPSS expansion                          COMPLETE
Phase 2    Threat Intelligence Data Lake                      COMPLETE
Phase 3    Vulnerability Correlation Engine                   NEXT / NOT STARTED
Phase 4    Repository Intelligence                            NOT STARTED
Phase 5    Risk Prioritization Engine                         NOT STARTED
Phase 6    Semantic Query Layer                               NOT STARTED
Phase 7    Knowledge Retrieval with Bedrock                   NOT STARTED
```

## Phase 2 exit criteria — closed

The completed deterministic data lake can now support the evidence required to answer:

- whether a CVE exists in the NVD evidence plane;
- whether it is present in CISA KEV for an explicit snapshot;
- its current or historical EPSS evidence for an explicit snapshot;
- EPSS temporal change across the complete historical interval available from the pinned archive;
- CVSS/severity evidence preserved from NVD and GHSA source observations;
- which reviewed GitHub advisories reference a vulnerability;
- published affected package/range/fixed-version evidence where GHSA provides it.

Phase 2 intentionally stops before determining whether a concrete installed package version falls inside a vulnerable range. That applicability decision belongs to Phase 3.

## Phase 3 — Vulnerability Correlation Engine

### Goal

Implement deterministic package/version-to-vulnerability matching over the evidence collected in Phase 2.

### Input

```text
ecosystem
package
version
purl
```

### Output

```text
affected status
matched vulnerable range
fixed version when known
vulnerability identifiers / aliases
exact match evidence
```

### Permanent rule

> No LLM decides vulnerability applicability.

Package identity normalization, version parsing, version-range evaluation, alias handling, fixed-version evaluation, and match evidence remain deterministic.

### Phase 3 decisions to make

The Phase 3 implementation should be divided into small reviewed gates. Before code, explicitly decide:

1. the first supported ecosystem and version semantics;
2. canonical package identity and purl normalization;
3. typed internal representation for vulnerable ranges;
4. exact handling of inclusive/exclusive bounds and open-ended ranges;
5. fixed-version semantics;
6. CVE/GHSA alias reconciliation without collapsing source-local evidence;
7. unsupported or malformed range fail-closed behavior;
8. deterministic evidence emitted for every match or non-match;
9. benchmark/test corpus structure;
10. cost and observability boundaries for any later service integration.

### Phase 3 exit criteria

Phase 3 is complete only when:

- supported ecosystems have typed normalization;
- vulnerable and fixed versions are correctly differentiated;
- CVE/GHSA aliases are handled deterministically;
- edge cases are covered by tests;
- every applicability result emits reproducible evidence;
- a benchmark/test corpus exists and can be expanded;
- unsupported semantics fail closed rather than being guessed;
- no model is required to establish affected/not-affected truth.

## Phase 4 — Repository Intelligence

Phase 4 remains blocked until Phase 3 is complete because repository findings require deterministic package/version applicability.

The planned security rule remains:

> READ, NEVER EXECUTE third-party repository code.

A future repository snapshot should be inspected through metadata and inert dependency/SBOM evidence, then passed into the Phase 3 correlation engine.

## Later phases

Phase 5 will add explicit deterministic risk policy over validated findings. Phase 6 may add natural-language planning that compiles only to validated typed queries and bounded SQL. Phase 7 may add controlled retrieval/synthesis for remediation and documentation questions.

None of those later phases should bypass deterministic evidence or authority established by Phases 0–3.

## Next authorized action

The next project action, in a separate explicit Phase 3 start, should be planning only:

```text
read the Phase 2 closeout state
confirm Phase 3 dependencies are complete
show the Phase 3 package/version applicability architecture
choose the first ecosystem
freeze typed version/range semantics
recommend only the first implementation step
```

No Phase 3 implementation is part of this documentation checkpoint.
