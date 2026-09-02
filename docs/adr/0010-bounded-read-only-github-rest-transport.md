# ADR 0010 — Bound public GitHub REST acquisition before dependency reads

- Status: Accepted
- Date: 2026-09-02
- Phase: 4 — Repository Intelligence

## Context

Phase 4 now has an immutable public GitHub repository snapshot contract and a deterministic resolver boundary. The next step is to provide a concrete source implementation without weakening the permanent rule:

> **READ, NEVER EXECUTE third-party repository code.**

A public repository request is untrusted input. Even a read-only network client must therefore bound destination, method, redirects, request count, response bytes, timeout, authentication handling, and rate-limit behavior.

GitHub's REST API currently allows public-resource reads without authentication, but unauthenticated requests are limited to 60 requests per hour. Authenticated user requests normally receive a 5,000 requests-per-hour primary limit. GitHub recommends serial requests and requires clients to stop when rate limited rather than continuing to retry.

The REST API is versioned. The current documented version used by this integration is `2026-03-10`.

## Decision

Phase 4 v1 uses a small standard-library HTTPS transport with the following fixed boundary:

```text
scheme:             HTTPS only
host:               api.github.com only
HTTP method:        GET only
redirects:          not followed
API version:        2026-03-10
JSON media type:    application/vnd.github+json
snapshot requests:  serial
automatic retries:  none
```

No caller may provide an absolute URL or alternate host. Owner, repository name, and ref are validated before acquisition and are encoded only into fixed GitHub API path templates.

### Snapshot request shape

Resolving one snapshot uses exactly three REST reads:

```text
1. GET /repos/{owner}/{repo}
   -> repository id, canonical owner/name, public visibility, default branch

2. GET /repos/{owner}/{repo}/commits/{ref}
   Accept: application/vnd.github.sha
   -> exact commit SHA only

3. GET /repos/{owner}/{repo}/git/commits/{commit_sha}
   -> exact Git commit object and tree SHA
```

The regular JSON `Get a commit` representation is intentionally not used as snapshot authority because it can include file-change data and become much larger than the identity evidence required here.

The source adapter synthesizes only the minimal commit payload already accepted by the Gate 4.2 projection contract.

### Request bounds

Default v1 bounds:

```text
per-request timeout:       10 seconds
maximum JSON response:     1 MiB
maximum SHA response:      128 bytes
maximum snapshot requests: 3
worst configured network wait before caller handling: 30 seconds
```

These are explicit safety bounds, not promises about GitHub latency. A later public API gate may choose stricter end-to-end limits from measurement.

### Authentication

The transport accepts an optional bearer token supplied by its caller.

The transport does not discover credentials from repository content and does not persist or log the token. Token fields are excluded from object representation.

No authentication is required for supported public repositories, but unauthenticated capacity is intentionally understood to be low:

```text
60 requests/hour / 3 requests per uncached snapshot ~= 20 snapshot resolutions/hour
```

Authenticated capacity is higher, but caching and public-demo rate controls remain future Phase 4/9 concerns.

### Rate limits and failures

There are no automatic retries in this transport.

`403` or `429` responses that carry GitHub rate-limit evidence are surfaced as a typed rate-limit failure including only non-secret retry/reset metadata. The caller may later implement a bounded scheduling policy.

Other non-success statuses, oversized bodies, invalid content types, malformed JSON, malformed SHA responses, or source inconsistencies fail closed.

### Redirects

Redirects are not followed in v1. This keeps destination authority fixed at `api.github.com` and prevents server-provided locations from silently changing the acquisition target.

Repository rename/redirect support may be added later only with an explicit same-origin redirect contract and tests.

## Alternatives considered

### `requests` or `httpx`

Not selected for this gate. The required surface is three bounded GET operations, and adding another runtime dependency is not yet justified.

### Normal JSON `Get a commit`

Rejected for the identity-resolution path because it can include commit diff/file data that is not needed for snapshot authority.

### Automatic retry/backoff

Rejected inside the transport. Rate-limit and transient failure policy belongs to a bounded orchestration layer where total request count and delay can be observed and capped.

### GitHub GraphQL

Not selected. REST exposes the required repository, SHA, and Git commit object evidence with a smaller conceptual surface and supports public unauthenticated reads.

## Security and cost consequences

- repository input cannot choose a network host;
- no repository code is cloned or executed;
- no redirect is followed;
- response memory is bounded before JSON parsing;
- request count is deterministic;
- token values are not included in repr/error messages;
- no AWS resource or IAM permission is introduced;
- GitHub API budget, not AWS cost, is the main resource constraint in this gate.

## Validation gate

Before dependency evidence acquisition begins, tests must prove:

1. fixed HTTPS host and GET method;
2. validated/encoded owner, repository, and ref paths;
3. required GitHub Accept/API-version/User-Agent headers;
4. optional bearer token without secret representation;
5. exactly three successful reads per snapshot resolution;
6. SHA-only ref resolution followed by exact Git commit-object read;
7. response-byte limits;
8. timeout propagation;
9. redirect failure;
10. `404` and generic HTTP failure behavior;
11. `403/429` rate-limit behavior without retry;
12. malformed JSON/SHA/source mismatch fail closed;
13. existing Gate 4.1/4.2 and Phase 3 regressions remain green.

## References

- GitHub Docs — Rate limits for the REST API.
- GitHub Docs — Best practices for using the REST API.
- GitHub Docs — API versions.
- GitHub Docs — Get a commit and `application/vnd.github.sha`.
- GitHub Docs — Get a Git commit object.