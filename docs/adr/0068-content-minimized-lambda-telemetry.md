# ADR 0068 — Content-Minimized Lambda Telemetry

- Status: Accepted
- Date: 2026-09-09
- Phase: 17 — Security Hardening
- Gate: 17.5

## Context

OpsLens already suppresses AWS Lambda input-event logging with `log_event=False` and retains bounded operational fields, EMF metrics, and X-Ray spans. Gate 17.5 found two separate content-bearing telemetry surfaces that were not covered by that control.

First, retained Powertools Lambda handlers used bare `@tracer.capture_lambda_handler`. Logger event capture and tracer response/error capture are independent mechanisms; disabling one does not disable the other. Lambda responses can contain repository, object, version, hash, and processing metadata, while exceptions can contain provider/source or attacker-controlled text.

Second, `PowertoolsTelemetry.exception(...)` delegated to `logger.exception(...)`. That logging API implicitly serializes the active exception and traceback. A caller could therefore correctly supply only bounded structured fields while uncontrolled exception text still crossed the shared logging adapter.

The relevant interpretation boundaries are:

```text
log event suppression != trace response/error suppression
exception text != safe telemetry by default
trace metadata != business/evidence truth
loggable identifier != authorization
telemetry correlation != capability authorization
content-minimized failure log != execution result
redaction success != proof source content is non-sensitive
```

## Decision

Retain AWS Lambda Powertools telemetry with explicit content minimization at the shared and Lambda boundaries.

Every retained Powertools Lambda handler must explicitly use:

```python
@logger.inject_lambda_context(..., log_event=False)
@tracer.capture_lambda_handler(
    capture_response=False,
    capture_error=False,
)
```

The shared `PowertoolsTelemetry.exception(...)` API remains available to preserve the existing application-facing telemetry port, but its implementation emits a bounded `logger.error(...)` record using only the code-owned message and explicitly supplied structured fields. It must not implicitly serialize the active exception, traceback, `exc_info`, or stack information.

A repository-wide AST verifier owns regression enforcement:

```text
scripts/verify_telemetry_safety.py
```

It discovers retained Powertools Lambda entrypoints and requires event, response, and error auto-capture to remain explicitly disabled. It also verifies that the shared exception adapter cannot silently regress to `logger.exception(...)` or enable implicit stack capture.

A dedicated unit regression proves that attacker-controlled active exception text is not forwarded through the shared logger adapter.

## Why not preserve automatic exception tracebacks?

Automatic tracebacks are convenient for debugging, but the shared adapter cannot prove that arbitrary exception messages, chained exceptions, provider errors, source data, protocol payloads, paths, or stack-local values are safe to export. The default platform boundary therefore favors content minimization.

Detailed diagnosis should use stable failure categories, bounded operational coordinates, deterministic evidence, local reproduction, and explicitly reviewed diagnostics rather than automatically exporting uncontrolled exception content.

This does not claim that every explicitly supplied telemetry field is inherently non-sensitive. Existing field allowlists and low-cardinality contracts remain independently authoritative.

## Consequences

Positive consequences:

- Lambda invocation events are not automatically logged;
- Lambda handler responses are not automatically attached to traces;
- Lambda handler errors are not automatically attached to traces;
- active exception text and tracebacks do not cross the shared exception adapter implicitly;
- content-minimization intent is executable and repository-wide rather than convention-only;
- business behavior, result admission, and application authority remain unchanged.

Trade-offs:

- automatic production traceback detail is reduced;
- some incidents may require bounded reproduction or separately authorized diagnostic instrumentation;
- developers must consciously choose any future content-bearing diagnostic surface and justify it separately.

## Authority impact

```text
AWS IAM mutation:                    NONE
new AWS service:                     NONE
new observability vendor:            NONE
new public runtime:                  NONE
new model/provider:                  NONE
new tool/capability authority:        NONE
business/evidence authority change:   NONE
PR #89 modification:                 NONE
```

Telemetry remains operational evidence only. A successful trace or log emission does not authorize a capability, prove a business result, or change evidence truth.

## Verification

Canonical implementation evidence is recorded in:

```text
labs/phase-17-gate-17-5-telemetry-safety.md
labs/evidence/phase-17-gate-17-5-telemetry-safety-v1.json
```

The retained regression surfaces are:

```text
scripts/verify_telemetry_safety.py
tests/unit/shared/observability/test_powertools_telemetry_safety.py
.github/workflows/security-hardening-ci.yml
```

## Rejected alternatives

### Rely only on `log_event=False`

Rejected because Lambda logger event capture and tracer response/error capture are separate mechanisms.

### Keep `logger.exception(...)` and redact known strings

Rejected because the exception/traceback surface is open-ended. A denylist cannot establish complete content safety.

### Remove tracing or operational logging entirely

Rejected because bounded metrics, spans, stable messages, and explicit fields remain operationally useful and do not require uncontrolled payload capture.

### Add a new observability service or runtime

Rejected. Gate 17.5 is a hardening slice over retained telemetry, not an observability-platform expansion.
