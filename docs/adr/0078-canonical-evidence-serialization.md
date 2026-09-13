# ADR 0078 — One canonical serialization for evidence identity

- Status: Accepted
- Date: 2026-09-12
- Supersedes: none
- Related: ADR 0008 (PyPI correlation semantics), ADR 0011 (immutable uv.lock evidence)

## Context

Evidence identity in OpsLens is a SHA-256 over serialized JSON. Identity only
holds if every module that produces or compares one serializes the same logical
payload to the same bytes.

An audit of `src/` found **34 independent canonicalizations** in three semantic
variants:

```text
23 sites   sort_keys=True  ensure_ascii=True   allow_nan=False
 3 sites   sort_keys=True  ensure_ascii=False  allow_nan=False
 6 sites   sort_keys=True  ensure_ascii=False  allow_nan=OMITTED
```

Two defects follow.

**`ensure_ascii` divergence breaks identity.** The flag decides whether a
non-ASCII character is escaped or emitted as UTF-8, and the two encodings hash
differently:

```text
{"cve":"CVE-2026-1","vendor":"Ação Segurança"}

ensure_ascii=True   -> 8b2c43f70c25474fad955c63e6a77e38a07aa0dae71e6b55c3cbcf8e47b7db73
ensure_ascii=False  -> 9a40de2d23d2e5ba109c067cae17255fdb9719ed9652c0d270dafc88cb4d551b
```

Non-ASCII text is not hypothetical in this corpus. CISA KEV vendor and product
names, GitHub Advisory summaries and NVD CVE descriptions all carry it. The
`risk_policy` module hashed with `ensure_ascii=False` while `public_analysis`
and `demo` hashed with `ensure_ascii=True`, and nothing — not a type, not a
test, not a review checklist — held the two to one answer.

**Omitted `allow_nan` converts missing evidence into emitted evidence.** Five
`knowledge_retrieval` sites omitted it, so a `NaN` EPSS or CVSS score would
serialize to the non-standard token `NaN` instead of being rejected. That is the
inverse of the repository's stated fail-closed posture.

No retained identity was observed to be wrong today: every checked-in fixture is
pure ASCII, and the only non-ASCII byte anywhere in `labs/evidence` is an em
dash inside prose fields that are not hashed. The defect was latent, not active.
That is the reason to fix it now rather than after a Portuguese vendor name
enters a fixture.

## Decision

One module, `opslens.shared.evidence.canonical`, owns JSON canonicalization.

Two serializations exist, and the distinction is deliberate:

| Function | Encoding | Purpose |
| --- | --- | --- |
| `canonical_json` | `ensure_ascii=True`, bytes | Evidence identity |
| `canonical_json_text` | `ensure_ascii=True`, str | Identity bytes, decoded |
| `model_visible_json` | `ensure_ascii=False`, str | Prompt text a model reads |

All three sort keys, use `(",", ":")` separators, and reject non-finite floats.
`canonical_sha256`, `sha256_hex` and `evidence_id` build on them.

Identity is ASCII-escaped so the bytes survive any transport, terminal, editor or
filesystem encoding that later handles them without changing the digest.

Prompt payloads keep `ensure_ascii=False`, because a model should read `Ação`,
not `A\u00e7\u00e3o`. **Prompt identity hashes the model-visible bytes**, so the
digest binds what was actually sent rather than a re-encoding of it. This is the
one place where the two serializations legitimately coexist, and the rule is
that the digest always covers the bytes that left the process.

Human-readable report writers under `*/cli/` that pass `indent=2` are not
canonicalizations and are out of scope.

Two architecture tests enforce the decision:

- no `json.dumps` outside the canonical module may pass `sort_keys`,
  `separators`, `ensure_ascii` or `allow_nan` unless it also passes `indent`;
- no `sha256` call anywhere may take a local `json.dumps` as its argument.

## Consequences

Positive:

- One place decides what an evidence identity is, and a property test pins the
  behaviour under key reordering, non-ASCII text, `NaN`, `Infinity` and
  unserializable payloads.
- `allow_nan=False` now holds everywhere, so a non-finite score fails closed
  instead of emitting `NaN`.
- A `TypeError` from an unserializable payload surfaces as
  `CanonicalSerializationError`, so callers catch one contract error.
- 43 wrapper definitions collapsed to delegating one-liners: −235 lines.

Negative:

- The four identity sites that used `ensure_ascii=False` now produce different
  bytes for any payload containing non-ASCII characters. Measured: the full
  suite, all three demo scenarios, the suite evaluation and all 22 runnable gate
  verifiers are byte-identical before and after, because every fixture is ASCII.
  Any identity retained from a non-ASCII payload outside this repository would
  have to be recomputed.
- Two serializations mean a contributor has to choose. The names carry the
  choice, and the architecture tests catch a third one being invented.

## Verification

```text
uv run ruff check .                          All checks passed
uv run pyright                               0 errors / 906 files
uv run pytest                                0 failures / 2.427 tests
scripts/verify_module_imports.py             557 modules
scripts/demo_opslens.py (3 scenarios)        byte-identical JSON
scripts/evaluate_opslens_demo.py             sha256:ed99f385…cee146d3 unchanged
22 runnable verify_* gate scripts            unchanged
```

```text
identidade determinística != identidade única
missing evidence != benign evidence
MEASURED != DERIVED
```
