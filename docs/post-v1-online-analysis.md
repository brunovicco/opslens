# Post-V1 — Online real-time analysis (Phases 20–22)

Taking a package name or a repository URL and returning a real vulnerability verdict, in
real time, from a public endpoint — without the endpoint ever claiming more than the
evidence behind it supports.

Decisions taken:

| Question | Answer |
| --- | --- |
| Scope of the claim | Identity **plus real correlation** against ingested NVD / GHSA / KEV / EPSS |
| Runtime | **Enable the async stack Gate 19.7 already materialized** |
| Access | **Public**, with hard request bounds and a budget kill switch |
| Scope admission | **Admit partial coverage** — ADR 0084 |

## The work is narrower than it sounds

Two of the three halves already exist and are real.

**Already built, already real**

- *The input half.* Read-only GitHub transport, immutable snapshot bound to commit, tree
  and blob sha, `uv.lock` parser, PyPI normalization to purls. Proven against this
  repository's own lock: 55 packages, 54 normalized.
- *The delivery half.* HTTP API → API Lambda → DynamoDB job and idempotency authority →
  SQS → worker → DynamoDB result, plus DLQ. Gate 19.7 materialized 21 resources and
  proved Terraform convergence, with the endpoint, submit path, worker and event-source
  mapping all disabled.
- *The advisory data.* NVD, GHSA, KEV and EPSS ingested Bronze → Silver as Parquet,
  Glue-catalogued. Real upstream data, not fixtures.
- *Applicability matching, complete.* `evaluate_pypi_correlation` does PEP 440 evaluation
  against a frozen operator grammar and returns `UNSUPPORTED` for a range it cannot
  parse. The fail-closed behaviour a live endpoint needs is written and tested.
- *Scoring and identity.* Risk Policy v1, and one canonical serialization owner so every
  response can be content-addressed.

**Missing, and on the critical path**

- *Any implementation of the authority port.* Gate 19.8 froze
  `PublicThreatEvidenceAuthority` completely — scoped request, content-addressed
  binding, provenance projection. It has **zero implementations**, in source or in
  fixtures; the type is only ever constructed inside its own unit test. This is the gap,
  and it is the whole gap.
- *A package-keyed GHSA and NVD read path.* Nothing projects Silver into a shape that
  answers "advisories for this package" without a table scan.
- *Public exposure controls.* No throttling, no request bounds, no cost ceiling. V1
  deferred all of it deliberately, which is why the endpoint is disabled rather than
  unfinished.

## The contract already decided half of this

The Gate 19.8 request type does not treat its four sources alike.

**KEV and EPSS are whole snapshots, by contract.** Both carry `raw_bytes` — the original
CISA JSON and the original FIRST gzip — because a snapshot's identity *is* its bytes.
There is no content-addressed snapshot without the content, so no projection can
substitute. That sounds expensive per request and is not: with a daily cadence a worker
loads the current pair once, verifies each digest, and serves every warm invocation from
memory. An S3 GET per cold start, not per request.

**GHSA and NVD are scoped to the request.** The validator refuses GHSA evidence outside
the admitted package scope, and refuses NVD records unrelated to the scoped GHSA CVEs.
These two are the only sources that need to answer "what applies to *these* packages" —
and answering that from Athena per request is the wrong tool: cold queries run in
seconds, cost scales with bytes scanned, and an unbounded scan is an unbounded bill
triggered by an anonymous caller. The semantic-query compiler also knows exactly one
relation today, and that narrowness is a security property rather than an omission.

So the projection is narrower than "an advisory index": **GHSA keyed by normalized
package name, NVD keyed by CVE.** Two lookups, bounded by the request's own package
count, with Athena confined to the scheduled projector.

The projection is a derived artifact, so it carries a contract version, a `built_at` and
the source watermarks it was built from, and every response names the index that
answered it.

```text
projected index != source of truth
MEASURED != DERIVED
historical evidence != standing authority
```

"No known vulnerabilities" stops being a timeless claim and becomes a dated one, which
is the only kind that is true.

## Phase 20 — Make correlation real

The only phase that adds a capability. Nothing is exposed publicly until it is finished.

| Gate | State | What it is |
| --- | --- | --- |
| 20.0 | **Done** — ADR 0084 | Admit partial coverage, with coverage inside the scope identity |
| 20.1 | **Done** — ADRs 0086–0088 | GHSA-by-package and NVD-by-CVE projection, with a content-addressed manifest carrying `built_at`, per-source watermarks and record counts, preserving enough of each source record to rebuild the typed evidence the port demands — including the exact source hashes its validator cross-checks |
| 20.2 | **Done** — GHSA only, ADR 0089 | The first `PublicThreatEvidenceAuthority` implementation: scoped GHSA from the projection, complete KEV and EPSS snapshots loaded once per worker and digest-verified. A fixture implementation lands alongside it so the offline demo keeps working with no network and no AWS. NVD records are returned empty: the index stores the CVE digest, and `NvdCveCoreRecord` requires the canonical CVE body that nothing in the lake holds per CVE |
| 20.3 | **Done** | No new logic. Wires the existing scan to loaded evidence and counts the five distinct ways a dependency ends up without an answer separately — unidentified record, unkeyable advisory, undecidable range, no advisory in the index, NVD not covered — because four of them look identical from outside |
| 20.4 | **Done** | The request-time response envelope: verdict, Risk Policy score, index manifest identity, snapshot provenance, and explicit accounting of what could not be evaluated — including NVD, declared as not covered rather than omitted (ADR 0089). Content-addressed over the index that answered rather than when it was built, so an idempotent rebuild leaves the answer byte-identical. While NVD is uncovered every scored finding is a partial evaluation requiring review, and the envelope counts them |

## Phase 21 — Make it safe to point at strangers

Everything V1 deliberately deferred. Reject, never truncate: a bound that silently trims
input produces a benign-looking answer from partial evidence.

| Gate | State | What it is |
| --- | --- | --- |
| 21.1 | **Partly done** | Request bounds — lock size, lock records, scoped packages, index rows read and findings emitted, each an explicit rejection with a reason code, sized from `labs/evidence/response-item-size-v1.json`. The hard timeout is not here: it is enforced by the platform, and Gate 21.2 both sets it and verifies the platform assumptions this bound set declares rather than asserts |
| 21.2 | **Written, not applied** | Abuse and cost ceiling. Throttling (burst 10, rate 5) and reserved concurrency zero already exist from Gate 19.4. What this gate adds is the monthly ceiling: an AWS Budgets action that attaches an explicit deny to the two public-analysis roles at 100% of a configured USD limit, with a warning at 60%. It disables invocation and destroys no evidence. Applying it is a human decision. This gate also verified the platform assumptions Gate 21.1 declared, and the timeout one was wrong |
| 21.3 | **Partly done** | Content-addressed result cache. The key is **four** inputs, not the two originally written here: the subject, the index identity, and the KEV and EPSS snapshot digests — KEV refreshes nightly and decides `kev_state`, so a key omitting it serves yesterday's verdict. Key, port and in-memory retention are in; the retained payload stays opaque until Phase 22 defines the wire format, and a shared store waits on 21.2 |
| 21.4 | **Done** | Two input shapes. A single dependency (`name==version`) is a direct lookup needing none of the repository machinery, and answers with its own envelope because its warrant is the caller's assertion rather than evidence OpsLens observed. A repository (`owner/repo[@ref]`) runs snapshot → lock → inventory → correlation |

## Phase 22 — Enable, deliberately

| Gate | What it is |
| --- | --- |
| 22.1 | The ADR that crosses the line — what changed, and what is still **not** claimed: no SLO or SLA, no multi-tenancy, no HA/DR, no production TCO |
| 22.2 | An admitted plan, not a blind apply. The Gate 19.6 and 19.7 evidence admission tools take a plan JSON and a plan binary and admit or reject against an expected source head. They were built for exactly this |
| 22.3 | The page people see. A hosted Claude artifact **cannot** call this API — its sandbox blocks network requests to any host that is not an allowlisted script CDN. So the front end is served by the runtime itself: the API Lambda returning one self-contained HTML page, rendered by the existing visual projection module. One renderer serves both the offline demo and the live endpoint, and `projection != identity` holds in both |

```text
materialized != enabled
enabled != production-ready
demonstration readiness != production readiness
```

## The one place this can accidentally lie

The project's credibility rests on a single sentence: missing evidence is not benign
evidence. A public endpoint returning "no vulnerabilities found" for an arbitrary
repository is the easiest place in the entire system to break it — if the index is
stale, if an affected range failed to parse, if packages came from a source the
normalizer does not support, or if the lock was larger than the bound.

So the response contract carries freshness, unevaluated-package counts and source
coverage at the **same prominence** as the verdict, and an incomplete analysis returns a
distinct outcome that is not a clean bill of health. ADR 0084 already put coverage inside
the scope identity for exactly this reason.

```text
missing evidence != benign evidence
incomplete evidence != no material finding
stale index != current answer
```

## Order of work

The sequence is load-bearing: exposing the endpoint before correlation is real would
ship a public surface whose answers come from fixtures.

| Step | Gate | Why here |
| ---: | --- | --- |
| 1 | 20.0 scope admission | **Done.** Decides what 20.2 is allowed to return |
| 2 | 20.1 GHSA and NVD projection | Nothing downstream can be real without it |
| 3 | 20.2 + 20.3 authority and wiring | Correlation becomes real, still entirely offline and private |
| 4 | 20.4 + 21.4 single-dependency path | **First shippable slice.** Real verdict for one package, no repository surface, no GitHub reads |
| 5 | 21.1 + 21.2 bounds and ceiling | Must precede any public exposure, not follow it |
| 6 | 21.3 result cache | Turns repeat traffic into retained evidence rather than cost |
| 7 | 22.1 → 22.3 ADR, admitted plan, enable | The endpoint opens last, and on the record |

## Open before Gate 20.1

**Index store.** DynamoDB point lookups suit a request path with a hard latency budget
and a small key space. Parquet on S3 read via S3 Select is cheaper at rest and worse per
request. Worth measuring the GHSA-by-package and NVD-by-CVE projection size against the
existing Silver tables before committing, since it is now the only projection being
built.

**Projection cadence.** Daily matches the existing ingestion schedules and keeps the
freshness claim easy to state. Anything faster buys little and complicates the watermark
story.

**Ecosystem scope.** PyPI only, at first. The normalizer already handles it, the
advisory sources cover it well, and widening to npm or Maven multiplies the
applicability-matching work without strengthening the argument.
