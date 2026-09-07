# ADR 0033 — Instrument Governed Public-Analysis Orchestration Without Moving Authority

- Status: Accepted
- Date: 2026-09-07
- Phase: 10 — Observability & Operational Excellence
- Gate: 10.2 — Governed Orchestration Instrumentation

## Context

Phase 9 froze a governed public-analysis application boundary ending at `PublicAnalysisAdmissionHandoff`. Phase 10 Gate 10.1 then froze `operational-telemetry:v1` as provider-neutral, content-minimized operational evidence.

The next step is to make the already-governed application path diagnosable without inventing a deployed public runtime and without letting telemetry become repository, vulnerability, risk, route, SQL, model, or execution authority.

The existing Phase 9 semantic composite performed planning, deterministic route admission, and final handoff construction in one application call. That behavior is valid, but it hides the distinction between planner-output rejection, route-policy rejection, and handoff-binding rejection.

## Decision

Instrument the existing Phase 9 path at exactly five ordered stages:

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

Gate 10.2 reuses the existing business functions and performs only the smallest behavior-preserving semantic-planning refactor needed to expose:

```text
parsed planner proposal
 -> deterministic public-v1 route admission
 -> exact handoff binding
```

Phase 8 remains the hybrid route authority. `PublicAnalysisAdmissionHandoff` remains the final deterministic binding authority.

### Mandatory in-process evidence

Every completed stage must first construct a valid `OperationalEvent`. If event construction or the injected monotonic-clock contract fails, orchestration fails closed before later business work.

```text
valid event construction failure -> stop
clock contract failure            -> stop
```

### Best-effort external delivery

External delivery is a separate injected `OperationalEventSink` port.

```text
sink delivery failure != business failure
sink delivery failure != route authority
sink delivery failure != permission to bypass deterministic checks
```

A sink failure records only the already-admitted event identity in bounded execution/failure evidence. Provider/sink exception text is never copied into operational events.

This is deliberately not a production delivery guarantee. A future deployed runtime may adopt stronger telemetry-delivery requirements only through a separate versioned policy decision.

### Failure taxonomy

The instrumented application boundary maps failures deterministically:

```text
request contract rejection        -> rejected / request_contract
source transport failure          -> failed   / source_resolution
repository evidence rejection     -> rejected / evidence_contract
planner invocation failure        -> failed   / planner_invocation
planner output rejection          -> rejected / planner_output_contract
route/policy rejection            -> rejected / route_authority
handoff binding rejection         -> rejected / handoff_contract
unexpected stage failure          -> failed   / unexpected_internal
```

A terminal stage emits no later-stage business work or telemetry event.

### Content minimization

Operational events may carry only the Gate 10.1 bounded semantics plus Phase 9 content-addressed identities when those identities already exist:

```text
public_request_id
source_execution_id
handoff_id
```

They never carry raw repository URLs, repository content, dependency names/versions, lockfile bytes, prompt/model text, SQL, credentials, secrets, or provider error messages.

## Authority boundary

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry delivery != execution authority
```

The injected clock and sink are operational ports only. Neither may create, broaden, retry, or override Phase 9/Phase 8 business authority.

## Consequences

### Positive

- success/failure location becomes explicit without a deployed runtime;
- planner invocation, proposal admission, route admission, and handoff binding remain independently diagnosable;
- event ordering and provenance progression are regression-testable;
- sink outages cannot silently change application decisions;
- future CloudWatch/OpenTelemetry adapters can consume a frozen provider-neutral contract.

### Costs / constraints

- orchestration contains explicit stage boundaries rather than one compact composite call;
- external telemetry delivery is not durable or guaranteed in this gate;
- latency measurements are laboratory/injected-clock semantics until a real runtime executes the path;
- no production SLO, p95/p99, error rate, or cost/request can be claimed yet.

## Non-goals

Gate 10.2 does not deploy HTTP compute, Lambda, API Gateway, ECS, IAM, CloudWatch dashboards/alarms, OpenTelemetry exporters, agents, MCP, AgentCore, A2A, runtime exposure, or the Governed LLM Gateway integration.

## AIP-C01 learning note

Operational telemetry should make model/retrieval/runtime behavior diagnosable while preserving the separation between observability and authorization. A trace or log can prove that a stage ran or failed; it must not become permission to skip deterministic validation or redefine business truth.
