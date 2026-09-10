# Phase 17 — Gate 17.7: Architecture Documentation Synchronization

_Date: 2026-09-10_

## Status

**IMPLEMENTED — pending exact-head CI and protected merge.**

## Source checkpoint

```text
source protected main:  6dd37cc6646f5481abd48bae4202682241e680ff
Gate 17.6 closeout PR:   #274
Gate 17.7 issue:         #275
observed gap:            SEC17-DOC-001
```

## Problem

Gate 17.1 recorded a lower-priority documentation gap: the accumulated EN/PT-BR architecture documents still described Phase 9 as the current baseline and Phase 10 as the next phase even though the retained repository had advanced through Phase 16 and Gate 17.6 of Phase 17.

This was an operator/reviewer guidance problem, not a runtime control failure.

## Decision

Synchronize the accumulated architecture baseline with the actual retained platform state through Gate 17.6.

The synchronization updates:

```text
docs/architecture.md
docs/architecture.pt-br.md
```

The documents now represent the same architecture boundary in English and PT-BR and explicitly cover:

- deterministic business/evidence authority;
- structured, semantic and hybrid evidence paths;
- the public-analysis application boundary without claiming a public HTTP runtime;
- Bedrock Knowledge Base + S3 Vectors retrieval;
- the retained Phase 11 single-agent baseline and bounded Phase 12 multi-agent specialization;
- MCP, AgentCore and A2A retention/decommissioning boundaries;
- the Phase 16 read-only Inspector evidence boundary;
- Phase 17 CI/CD, dependency/code scanning, adversarial, telemetry and operational-recovery controls;
- standing versus historical authority;
- cost/amplification boundaries;
- the exact scope of the scheduled-ingestion pause.

## Important non-change

Gate 17.7 does not redesign the platform. No new runtime, protocol, service, IAM principal, model call, tool capability or business authority is introduced.

The architecture synchronization deliberately preserves the Gate 17.6 distinction:

```text
scheduled-ingestion pause != global kill switch
scheduler state != business/evidence authority
Terraform apply success != independent AWS state verification
```

It also preserves the Phase 17 interpretation boundaries established by prior gates rather than rewriting historical evidence.

## Before / after

Before:

```text
architecture.md baseline:        through Phase 9
architecture.md next phase:      Phase 10
architecture.pt-br.md baseline:  through Phase 9
architecture.pt-br.md next:      Phase 10
```

After this implementation:

```text
architecture baseline:           through Phase 17 Gate 17.6
Gate 17.7 purpose:               documentation synchronization only
next bounded step:               Phase 17 closeout
Phase 18:                        planned after closeout
```

## Authority impact

```text
AWS mutations:          0
new IAM permissions:    0
new IAM principals:     0
new AWS services:       0
new public runtimes:    0
model invocations:      0
capability executions:  0
business authority:     unchanged
PR #89 touched:         false
```

## Verification

Repository-level acceptance criteria for the exact PR head:

1. neither architecture document identifies Phase 9 as the current baseline;
2. neither architecture document identifies Phase 10 as the next phase;
3. EN and PT-BR describe the same current retained boundary;
4. Gate 17.6 is represented as a scheduled-ingestion pause, not a global kill switch;
5. historical/decommissioned surfaces remain separate from standing authority;
6. no non-documentation runtime/IAM change appears in the PR;
7. required protected-main CI passes before merge.

## Gate decision

After exact-head CI passes and the documentation-only PR is protected-merged, `SEC17-DOC-001` is considered closed and no further evidenced Phase 17 implementation gap remains from the Gate 17.1 inventory.

The next step is a dedicated **Phase 17 Security Hardening closeout** that freezes final retention, remaining deferrals, and Phase 18 entry conditions.

## AIP-C01 learning checkpoint

Architecture documentation is part of operational correctness. A technically correct control can still be unsafe to operate if the accumulated architecture tells reviewers that obsolete services or phases are current. Professional-level governance therefore keeps implementation evidence, standing authority, decommissioned experiments, and current architecture synchronized without turning documentation cleanup into an excuse for new cloud authority.
