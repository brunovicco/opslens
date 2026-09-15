# ADR 0085 — Admit a GHSA Silver page partially, and read an empty passthrough link as absent

- Status: Accepted
- Date: 2026-09-15
- Supersedes: part of the Gate 2.4 GHSA Silver transformation contract
- Related: ADR 0084 (partial scope admission), ADR 0079 (retained artifact reproducibility)

## Context

The first real GHSA corpus load reached Silver and stopped on one advisory:

```text
opslens-dev-ghsa-silver returned an error:
Invalid GitHub advisory core record 'GHSA-fq2j-3j99-rx65':
GitHub advisory field 'source_code_location' cannot be empty when present.
```

Two separate defects, both invisible until the pipeline met real upstream data instead
of the single curated advisory the GHSA milestone closed on.

**`_optional_text` treats an empty string as corruption.** GitHub returns `""` for
`source_code_location` and `repository_advisory_url` when it has none, so empty and
absent mean the same thing upstream. The V1 rule encoded an assumption real data
violates.

**One refused record aborted the whole manifest.** `process_page` composed with a tuple
comprehension, so a single unanticipated advisory discarded every advisory promoted
alongside it — and the service then rejected the attempt outright, so nothing was
promoted at all.

The second is the serious one. A discarded advisory becomes a silent absence in Silver,
then in the projected index, then in a correlation answer, where it reads as "no known
vulnerability". Excessive strictness arrives at the same wrong answer as laxity, from
the opposite direction, and this repository's whole argument is that the wrong answer
is what matters.

```text
excessive strictness != safety
rejected advisory != absent advisory
```

## Decision

**An empty string means absent for pure passthrough links, and only for those.**
`_optional_text` gains an explicit `empty_means_absent` flag, passed for
`source_code_location` and `repository_advisory_url`. Neither carries identity,
applicability or severity: the Parquet schema declares both nullable, and only the row
mapper reads them. Rejecting an advisory over one discards the package name and version
range correlation actually needs, in exchange for a link.

`cve_id` keeps the strict rule. It is the correlation link to NVD — the threat-evidence
validator admits NVD records only when they relate to a scoped GHSA CVE — so reading an
empty value there as "no CVE assigned" would silently drop a real correlation edge.
Same field shape, different authority, different answer.

**A page is composed with partial admission and exact accounting.** `process_page`
returns `GhsaSilverPageCompositionV1`, carrying admitted bindings and
`GhsaSilverRejectedAdvisoryV1` entries that preserve the transformer's own message
rather than rewording it. A rejection without both an identity and a stated reason is
itself refused, because a rejection with neither is indistinguishable from a dropped
record.

Only `ValueError` — the base of every transformer and domain refusal here — is
accounted for and continued past. Any other exception still propagates, because only a
stated domain refusal is safe to treat as data.

**The count invariant is strengthened, not relaxed.** The service asserted that bound
records equal the Bronze manifest's `total_items`. It now asserts that admitted plus
rejected equals it. The property that mattered was never "everything succeeded" — it
was "every source record is accounted for exactly once", which is what
`RepositoryPyPINormalizationInventory` already does for lock records and what ADR 0084
did for dependency scope.

```text
admitted + rejected == total_items
```

## Consequences

Positive:

- The corpus load can complete. One advisory the V1 validators did not anticipate no
  longer discards a whole leaf manifest.
- Coverage is visible instead of assumed. A rejected advisory is a recorded fact with a
  reason, so the gap between what upstream published and what Silver holds is
  measurable rather than inferred from a count that came out low.
- The strict-versus-absent distinction is now a decision per field rather than one rule
  applied to three fields of different authority.

Negative:

- The Silver runtime response and completion evidence gain a rejected count, so a
  consumer that assumed "completed means everything promoted" is wrong until updated.
  The count is the point: silence was the previous behaviour and it was worse.
- Partial admission means a reviewer must read coverage alongside any conclusion drawn
  from Silver, exactly as ADR 0084 requires for scope. That cost is paid twice now,
  deliberately.
- Rejection reasons are transformer messages, so they are stable only as long as those
  messages are. They are evidence for an operator, not a machine-readable taxonomy; a
  reason-code vocabulary would be the next step if anything needs to branch on them.

## Verification

```text
ruff check . / pyright                                clean / 0 errors
pytest                                                2540 passed
run_repository_invariants.py                          23/23 standing verifiers
empty source_code_location / repository_advisory_url   admitted, normalized to None
empty cve_id                                           still refused
one broken advisory among three                        2 admitted, 1 rejected, 3 accounted
rejection without identity or reason                   refused
demo suite evaluation identity                         sha256:deac5a84...1346d3a9  (unchanged)
```

```text
excessive strictness != safety
admitted + rejected == total_items
```
