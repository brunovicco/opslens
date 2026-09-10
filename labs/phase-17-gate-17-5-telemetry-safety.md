# Phase 17 — Gate 17.5: Sensitive-Data, Logging, and Telemetry Hardening

_Date: 2026-09-09_

## Status

**IN PROGRESS — measured implementation validation is green; final PR-head validation and protected merge pending.**

## Objective

Harden already-retained AWS Lambda observability so operational telemetry cannot silently serialize uncontrolled invocation events, handler responses, active exceptions, or tracebacks.

This gate changes telemetry transport behavior only. It does not alter business logic, evidence admission, capability authorization, AWS IAM, runtime topology, or model/tool authority.

## Source baseline

```text
main:  cf5afe1d5d352cf301295b72031cb67a8d510fbb
issue: #266
PR:    #268
ADR:   0068-content-minimized-lambda-telemetry.md
```

## Observed gaps

### TRACE17-001 — tracer response/error capture remained implicit

Retained Powertools Lambda handlers already used:

```python
@logger.inject_lambda_context(..., log_event=False)
```

but used bare:

```python
@tracer.capture_lambda_handler
```

These are independent capture surfaces. Suppressing event logging does not prove response/error payloads are absent from X-Ray trace metadata.

### LOG17-001 — shared exception logging serialized active exceptions implicitly

`PowertoolsTelemetry.exception(...)` delegated to `logger.exception(...)`. The caller could supply only bounded fields while the current exception and traceback were still emitted implicitly.

A concrete adversarial path exists where invalid invocation text may include attacker-controlled field names. The shared adapter therefore cannot treat arbitrary active exception text as safe telemetry.

## Implemented controls

### Explicit Lambda trace minimization

All 12 retained Powertools Lambda handlers discovered at the source baseline now require:

```python
@tracer.capture_lambda_handler(
    capture_response=False,
    capture_error=False,
)
```

The handlers remain distributed across ingestion and transformation boundaries for KEV, EPSS, NVD, GHSA, historical EPSS, NVD promotion, and analytics projection.

Input event logging remains explicitly disabled with `log_event=False`.

### Content-minimized shared exception adapter

The application-facing `OperationalTelemetry.exception(...)` contract is preserved, but the Powertools implementation now emits exactly one bounded `logger.error(...)` record containing only:

```text
code-owned message
explicit caller-supplied structured fields
```

It does not implicitly serialize:

```text
active exception text
traceback
exc_info
stack_info
```

### Repository-wide static verifier

`scripts/verify_telemetry_safety.py` AST-parses retained Powertools Lambda modules and the shared telemetry adapter. It fails closed if any discovered handler loses an explicit content-minimization setting or if shared failure logging regains implicit exception/stack capture.

The universal `Security Hardening CI` executes the verifier on every pull request.

### Adversarial unit regression

`tests/unit/shared/observability/test_powertools_telemetry_safety.py` raises an exception containing an attacker-controlled marker and proves that marker is absent from logger-adapter calls while the bounded failure message and request identifier remain available.

## Measured implementation validation

Implementation head:

```text
f40aae0650199a1931f21f8b9f4abbfd8dc0c31a
```

Measured pull-request runs:

```text
Security Hardening CI         34428925731 / #28 / SUCCESS
  Repository security job     102720032719
  telemetry verifier          PASS / handlers=12

Operational Observability CI  34428925787 / #21 / SUCCESS
  job                          102720032658
  Ruff                         PASS
  Pyright                      0 errors / 0 warnings
  pytest                       28 passed

Dependency Review             34428925717 / #13 / SUCCESS
CodeQL / Python               34428925715 / #17 / SUCCESS
```

This evidence measures the implementation plus architecture/evidence files before the measured-evidence recording commits. A final exact-head CI pass is still required before merge so recording evidence cannot mask a subsequent regression.

## Permanent interpretation boundaries

```text
log event suppression != trace response/error suppression
exception text != safe telemetry by default
trace metadata != business/evidence truth
loggable identifier != authorization
telemetry correlation != capability authorization
content-minimized failure log != execution result
redaction success != proof source content is non-sensitive
```

## Preserved controls

Gate 17.5 does not replace earlier observability contracts. The following remain separately authoritative:

```text
OperationalEvent exact-field admission
content-minimized operational failure categories
CloudWatch EMF fixed low-cardinality dimensions
request/source/handoff identifiers forbidden as metric dimensions
telemetry evidence forbidden from becoming business authority
```

## Authority impact

```text
AWS mutations:             0
new IAM permissions:       0
new AWS services:          0
model invocations:         0
capability executions:     0
new tool authority:        0
new public runtime:        0
PR #89 changes:            0
```

## Final validation requirement

Before retention, the exact final PR head must prove:

```text
scripts/verify_telemetry_safety.py                    PASS / handlers=12
Repository security invariants                        PASS
Operational Observability CI                          PASS
Dependency Review                                     PASS where triggered
CodeQL / Python                                       PASS where triggered
```

## Decision

Retain content-minimized Lambda telemetry rather than automatic response/error/traceback export.

Automatic diagnostic convenience is subordinate to the requirement that uncontrolled input, provider errors, source content, and protocol data do not become telemetry merely because an exception occurred.
