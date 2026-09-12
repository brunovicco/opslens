# Demo Authority Boundary

The OpsLens V1 demo is a projection of retained application authority, not a second implementation of business truth.

## Deterministic authority

The demo may only present facts admitted by retained deterministic code for:

- repository/source identity;
- dependency/package identity;
- vulnerability applicability;
- GHSA/NVD/KEV/EPSS provenance;
- risk policy;
- structured-query admission/compilation where used;
- evidence and result admission;
- execution/resource limits.

## Model authority

A model may explain, summarize, classify, or synthesize admitted evidence. It may not create package identity, decide vulnerability applicability, invent source provenance, override risk policy, authorize tools, or turn missing evidence into a benign result.

## Offline-first rule

The canonical V1 demo must not require AWS credentials and must not require live third-party/provider access. Optional live demonstrations must remain separately bounded and are not the canonical reviewer path.

## Safety rule

```text
READ, NEVER EXECUTE third-party repository code.
```

Fixtures and repository artifacts are treated as inert data only.
