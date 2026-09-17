# Continuation brief

Written 2026-09-17, at `0c1d8ee`, for whoever picks this work up next.

This is not a summary of the project — `docs/post-v1-online-analysis.md` is the plan and
`docs/adr/` is the reasoning. This is the handover: what is true right now, what is left,
what was learned the expensive way, and the conventions that make a change here look like
the rest of the repository.

---

## 1. Rules that are not negotiable

**Nothing published names a tool, a model or a vendor as an author.** No
`Co-Authored-By` trailer, no attribution line, no generated-with footer — not in a commit
message, a PR body, an ADR, a docstring or a code comment. Every ship script in `.tmp/`
greps the outgoing commits and refuses to push when it finds one. Do not remove that guard.

**Publication is human and create-only.** No `terraform apply`, no artifact publish, no
`--apply` on any script without the operator asking for that specific action in that
specific moment. Writing the Terraform and running it are separate acts, and only the second needs a
person deciding.

**Never disable TLS verification and never unset a proxy** to make a request succeed.

**Reject, never truncate.** This is the whole posture of the public surface. A bound that
silently trims input produces a benign-looking answer from partial evidence, and on a
vulnerability endpoint a benign-looking wrong answer is the worst possible output.

---

## 2. Where things actually stand

### Live in `opslens-dev` (account 487757851499, us-east-1)

```text
GHSA corpus          35,584 advisory versions / 35,577 advisories, frozen at
                     2026-09-16T18:56:22Z — no schedule yet, see §4
NVD Silver           86,475 records / 60,259 distinct CVEs, incremental every 2h
KEV                  nightly 23:30 UTC
EPSS                 daily
correlation index    generation 4969e3b7879d704e, v2 contract, 11,081 GHSA rows over
                     1,491 packages, 1,642 NVD spine rows
public runtime       materialized but disabled: reserved concurrency 0,
                     execute-api endpoint disabled, SQS→worker mapping off
```

The index is certified, deterministic, reproducible, and readable. That was verified
against the live corpus, not only in tests: three consecutive runs over an unchanged
corpus produced one identity, and a full-table read returned 11,081 rows.

### Phase status

Phase 20 is complete. Phase 21 is partly done and Phase 22 has not started. The table in
`docs/post-v1-online-analysis.md` carries the per-gate state and is kept current — trust
it over this section if the two disagree.

---

## 3. Numbers that took work to get, and must not be re-guessed

Three byte counts were conflated at least once each, and each conflation was wrong by a
large factor. They are all measured now and retained as evidence.

```text
projected source row      385 B    labs/evidence/correlation-index-probe-v2.json
stored index item       1,078 B    labs/evidence/correlation-index-stored-item-size-v1.json
final finding           3,267 B    labs/evidence/response-item-size-v1.json
```

```text
projected bytes != stored bytes != response bytes
rows read != findings emitted != response bytes
```

Derived facts that bounds depend on:

- **973 stored items fill one 1 MB DynamoDB page.** `tensorflow` carries 1,323 rows, so a
  single package spans two pages.
- **320 findings fill the 1 MiB response budget.** The response binds before the read
  does.
- The heaviest packages are `tensorflow` (1,323), `tensorflow-gpu` (1,311) and
  `tensorflow-cpu` (1,307) — 3,941 rows between them, 36% of the index.
- Only **1,642 of 5,685** CVEs named by admitted advisories exist in NVD Silver (28.9%).

`scripts/measure_response_item_size.py` regenerates the third number offline. If a
serialization changes, re-run it rather than adjusting a constant.

---

## 4. What is left, in the order it should be done

### 4.1 Finish the GHSA schedule — highest value, lowest risk

GHSA is the only source without a schedule. The corpus has been frozen since the backfill
and ages one day per day. Nothing breaks — every response states the watermark — but a
freshness field that only moves backwards is a system reporting honestly that it stopped.

Four PRs have landed: the window planner, the watermark contract and scheduled-invocation
contract, the S3 store with conditional writes, and the run orchestration. What remains:

1. **A Lambda entry point.** `src/opslens/ingestion/ghsa/incremental_lambda_handler.py`,
   mirroring `src/opslens/ingestion/nvd/incremental_lambda_handler.py`. It parses the
   fired instant, composes the store and the existing Bronze runtime, and calls
   `run_incremental_sync`. The Bronze execution path already exists and is reusable:
   `execute_bronze_request` in `src/opslens/ingestion/ghsa/lambda_handler.py`.
2. **A seed script**, mirroring `scripts/seed_nvd_authoritative_watermark.py`. It
   establishes the first boundary at `2026-09-16T18:56:22Z` with a note saying the corpus
   backfill produced it. `initialize` is create-only, so this is safe to have and
   dangerous to skip.
3. **Terraform**: a second Lambda function on the existing GHSA Bronze artifact, an
   EventBridge schedule, and IAM. Copy `infra/environments/dev/nvd_incremental_scheduler.tf`
   — including its `<aws.scheduler.scheduled-time>` input template, which needs the
   `replace(replace(jsonencode(...)))` dance because `jsonencode` escapes the angle
   brackets. The GHSA parser expects `{"schema_version": "1", "target_end_at": "..."}`
   and refuses unknown fields.
4. **Then run it once manually** and confirm the watermark advances and the index's GHSA
   watermark moves on the next projection.

Cadence: daily is enough. GHSA does not publish at NVD's rate, and the `modified` window
picks up revisions regardless of when they happen.

### 4.2 Phase 22 — enable, deliberately

- **22.1** is the ADR that crosses the line. It must be explicit about what is *not*
  claimed: no SLO or SLA, no multi-tenancy, no HA/DR, no production TCO. It should also
  carry, plainly, the two honest limitations the system currently has: NVD content is not
  covered (ADR 0089), so **every scored finding is a partial evaluation requiring review**;
  and the advisory corpus refresh depends on §4.1 landing.
- **22.2** uses the existing Gate 19.6/19.7 evidence admission tooling to admit a plan
  JSON and plan binary against an expected source head. Do not invent a new mechanism.
- **22.3** is the page, served by the API Lambda itself. The plan explains why it cannot be
  a hosted page elsewhere: that sandbox blocks network requests to any host that is not an
  allowlisted script CDN. So the front end is one self-contained HTML document returned by
  the runtime, rendered by the existing visual projection module — one renderer serving
  both the offline demo and the live endpoint.

### 4.3 Close the partly-done Phase 21 gates

- **21.2** the cost ceiling is written (`infra/environments/dev/public_analysis_cost_ceiling.tf`)
  and not applied. It defaults to creating nothing. It has never been `terraform validate`d
  — it has only ever been checked with `terraform fmt`, because the provider cached in this
  repository is `darwin_arm64` and validation was attempted from a Linux shell. **See the plan before applying.** The monthly ceiling defaults to USD 25,
  which is a placeholder, not a derivation.
- **21.3** the cache key, port and in-memory implementation exist. The retained payload is
  opaque because the wire format does not exist until 22.3. A shared store needs 21.2.
- **21.1** the bounds are enforced; the hard timeout is the platform's and is verified
  rather than implemented. `assumed_platform_response_bytes` is still unverified and
  protected only by a 6× margin — if the deployed Lambda's response ceiling is ever
  readable, check it.

### 4.4 Presentation, for the three audiences the repository is for

Recruiters and leadership, engineers who read code, and the open-source community. None
of this exists yet:

- A README that opens with what the system does and what it deliberately does not claim.
  Bilingual was requested.
- An architecture diagram.
- A clean-clone quickstart. There is already a CI job called "README quickstart on a clean
  clone" — make sure what the README promises is what that job runs.
- LICENSE and CONTRIBUTING.

### 4.5 Deferred debt, none of it urgent

- **F-05**: duplication across four ingestion S3 adapters.
- **`ruff format`** has never been adopted; 418 of 972 files would change. Best done as
  one mechanical commit at a quiet moment, never mixed with behaviour.
- **PR #89** is still open.
- Roughly eleven stale local branches.
- A CI gate that builds Lambda artifacts and compares digests against what is pinned.
- Schema-aware coverage for the two projection SQL statements.
- The `.tmp/ship_*.sh` scripts are disposable scaffolding that became load-bearing. They
  emit raw `git` fatals when a branch was already merged and deleted.

---

## 5. Mistakes made here, and what they cost

Each of these is in the repository's history with its correction. They are listed because
the same shapes will recur.

**Measuring on the wrong machine.** A build digest was verified in a Linux container and
reported as a pin for a macOS build. `deterministic on one machine != reproducible across
machines`.

**Reading a number without checking what it counts.** `ConsumedCapacity` from the AWS CLI
is per page, not per query. A per-item byte size was derived from it and was wrong. The
tell was available and ignored: a full-table scan and a single-partition query reported the
identical figure.

**Filtering for something the format cannot contain.** `grep -E "START|REPORT"` against
Lambda logs in JSON format found nothing, and the absence was reported as "the function
never ran". It had run for 630 seconds. `no log line != no execution`.

**Trusting a declared constant as configuration.** The bound set declared a 29-second
platform timeout; the deployed integration is configured at 10. The assumption was named
but not checked, and naming an assumption without checking it is a constant with a longer
name. `declared constant != configuration in force`.

**Assuming a schedule's cadence instead of reading it.** The NVD incremental runs every
two hours, not hourly. A prediction built on the guess was wrong within one turn.

**Fixtures tidier than the source.** The NVD result fixture used ISO-8601 instants; Athena
renders `2026-07-22 15:17:17.527`. The mapping was never asked to do the conversion it was
missing, and the defect reached the live index. `a fixture's rendering != the source's rendering`.

**An identity over a description rather than over content.** The index identity was taken
over counts and watermarks, so two indexes holding entirely different rows in the same
quantity collided. It was invisible because `built_at` was also in the identity, making
every build differ anyway. Fixing the second exposed the first.

**Non-determinism hidden by a moving part.** `ROW_NUMBER` ordered on a non-unique key, and
seven advisories carry two observed versions at the same `updated_at`. Two runs over an
unchanged corpus produced two different indexes. Invisible until `built_at` left the
identity. The census had reported the signal — 35,584 rows against 35,577 advisories — and
nobody read it as one.

**Committing to `main` instead of a branch.** Twice, because a `git checkout -b` failed
silently behind a stale lock file and the next command did not verify. The working tree is shared
between two shells that both run git against it; the ship scripts now clear `.git/*.lock`
before touching refs.

---

## 6. Conventions, so a change looks like the rest

**Every module docstring explains the failure it prevents**, not what the module contains.
If a file cannot name something that would go wrong without it, it probably should not
exist. Invariants are written as fenced pairs:

```text
the thing you might assume != the thing that is true
```

They are not decoration. Each one in the codebase corresponds to a real defect, a real
measurement, or a real refusal.

**A claim about coverage must be executable.** The projection was contracted without
`github_identifiers` and nothing caught it, so field coverage is now asserted from
`dataclasses.fields`. Do the same for any new mapping: a hand-maintained list of fields
drifts silently.

**Prefer a test that reads configuration over a test that restates it.** The watermark
tests read declared column types out of the Glue Terraform; the platform-assumption test
reads the integration timeout out of the runtime Terraform. That is how a constant stops
being a guess.

**Measure rather than derive, and say which one a number is.** When something cannot be
measured, say so in the artifact and state the margin that protects being wrong.

**Fixtures exercise the real path.** Tests compose the real store adapter and the real
authority over canned bytes rather than mocking them, so the certification and the round
trip actually run. `a fixture that bypasses the logic != a fixture of the logic`.

**PRs are one change with a body that explains the defect, not the diff.** Commit messages
carry the reasoning; the shape is visible in `git log`.

---

## 7. Environment

```text
repository        /Users/brunovicco/Projects/opslens
AWS               profile opslens-bootstrap, us-east-1, account 487757851499
data bucket       opslens-dev-data-487757851499-us-east-1
index tables      opslens-dev-correlation-index-ghsa / -nvd
Athena workgroups opslens-dev (10 MiB, request path) and
                  opslens-dev-projection (2 GiB, projector only)
python            uv; pyright strict; ruff with TID251 banning
                  `from __future__ import annotations`
terraform         1.15.8; HCL has no implicit string concatenation, and
                  `terraform fmt -check` before every .tf PR
shell             the operator's default shell is macOS bash 3.2 — no `declare -A`
```

`gh pr checks` exits non-zero both when checks fail and when none have registered yet, so
anything polling it has to distinguish the two. Merges are squash-only, which means a
stacked branch needs `git rebase --onto origin/main <old parent>` rather than a plain
rebase — patch-id matching does not work after a squash.

---

## 8. The one question that decides whether any of this is honest

Before shipping anything that answers a caller, ask what happens when the answer is empty.

An empty result from this system can mean: the package is clean; the index was never
built; the pointer names a generation whose rows expired; the advisory could not be keyed;
the range could not be decided; the lock record had no PyPI identity; or NVD has no record
because the corpus holds 29% of published CVEs. Six of those seven are gaps and one is
good news, and they are indistinguishable unless something counts them apart.

```text
no finding != nothing to find
```

That is what the coverage accounting, the manifest certification and the freshness
watermarks exist for. Anything added downstream has to preserve it.
