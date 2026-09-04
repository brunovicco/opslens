# OpsLens — Current State

_Last updated: 2026-09-04_

## Status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2    Threat Intelligence Data Lake                       COMPLETE
Phase 3    Vulnerability Correlation Engine                    COMPLETE
Phase 4    Repository Intelligence                             COMPLETE
Phase 5    Risk Prioritization Engine                          COMPLETE
Phase 6    Semantic Query Layer                                COMPLETE
Phase 7    Knowledge Retrieval with Bedrock                    NEXT
```

Phase 6 was squash-merged through PR #91 into `main` at:

```text
95db66e278059629ce6572b2950e9cca705c6498
```

PR #90 was closed as superseded by #91. PR #89 remains draft and is reserved for later Phase 14 gateway/runtime integration; it is not part of Phase 7.

## Permanent boundaries

> **Agents reason. Code verifies evidence.**

> **Not every question is a RAG problem.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

Structured facts continue to use structured retrieval. Semantic retrieval is for knowledge/remediation/documentation questions and must not become a second authority for facts already owned by deterministic data sources.

Deterministic authorities remain responsible for package identity, version-range applicability, vulnerability correlation, KEV/EPSS/CVSS evidence, risk policy, semantic-query validation, SQL compilation, evidence validation, and execution/tool/cost limits.

## Implemented system

```text
Threat Intelligence Data Lake
 -> deterministic correlation
 -> repository intelligence
 -> deterministic Risk Policy v1
 -> bounded semantic query layer
 -> Bedrock planner proposal
 -> deterministic parser
 -> typed SemanticQuery
 -> deterministic SQL compiler
 -> bounded Athena
```

Phase 6 real E2E validation demonstrated:

```text
Natural-language question
 -> BedrockSemanticPlanner
 -> Claude Haiku 4.5 via US Geographic inference profile
 -> deterministic planner-output parser
 -> typed SemanticQuery
 -> deterministic compiler
 -> bounded Athena
```

Supported run evidence:

```text
question:              Which CVEs have EPSS of at least 0.7 on 2026-09-03?
decision:              semantic_query
model tokens:          942 input / 79 output / 1021 total
Bedrock latency:       1,632 ms
client elapsed:        2,894 ms
retries:               0
Athena rows:           20
Athena data scanned:   3,785,003 bytes (~3.61 MiB)
```

Fail-closed run evidence:

```text
question:              Which CVEs have EPSS of at least 0.7?
decision:              unsupported
reason:                missing_explicit_snapshot_date
athena_invoked:        false
```

Final deployed-runtime IAM least privilege remains deferred until an actual deployed runtime identity exists. The local IAM Identity Center bootstrap profile is a lab/admin identity, not the final runtime role.

## Next phase — Phase 7

Phase 7 adds a controlled knowledge-retrieval path for remediation/documentation questions while preserving the Phase 6 structured-query path.

Target conceptual split:

```text
STRUCTURED FACTS
question -> bounded planner -> SemanticQuery -> deterministic SQL -> Athena

KNOWLEDGE / REMEDIATION
question -> bounded retrieval -> retrieved chunks + metadata -> context assembly -> Bedrock synthesis -> citations
```

The first Phase 7 gate is offline only: freeze retrieval contracts and a golden evaluation dataset before creating Knowledge Base/vector infrastructure or making paid AWS calls.
