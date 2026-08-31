# Phase 2.5D-2 — Historical EPSS bounded bootstrap implementation closeout

## Status

**COMPLETE — implementation and validation only. No historical AWS mutation has been executed.**

Phase 2.5D-2 implements the bounded historical bootstrap runtime and the seven-snapshot canary plumbing frozen by Phase 2.5D-1.

The operating boundary remains:

```text
controlled operator coordinator
        -> dedicated historical transformer Lambda
        -> one explicit historical snapshot per synchronous invocation
```

No unrestricted historical fan-out is introduced.

## Implemented surface

D2 adds:

- deterministic historical bootstrap planning with a frozen `plan_id`;
- target-environment forward-boundary revalidation before mutation;
- pinned worklist generation from the approved EPSS archive commit;
- source byte SHA-256 and Git blob verification before Bronze acceptance;
- explicit seven-snapshot canary selection;
- confirmation guard `EPSS-HISTORY-CANARY-7` before any mutation path;
- sequential canary execution with effective concurrency `1`;
- dedicated historical transformer Lambda composition over the Phase 2.5C exact-evidence path;
- synchronous `RequestResponse` invocation semantics;
- dedicated coordinator and transformer IAM surfaces;
- content-addressed historical transformer Lambda deployment artifact publication;
- bounded CloudWatch/X-Ray observability;
- manual `EPSS History Canary` workflow plumbing;
- Terraform CI/build support for the historical transformer package.

## Historical transformer runtime envelope

Frozen D2 configuration:

```text
memory_size           1024 MB
timeout               120 s
canary concurrency    1
canary snapshot count 7
```

The transformer remains an explicit one-snapshot application composition. Historical Bronze and completion evidence retain the exact-version contracts frozen in Phase 2.5C.

## Lambda package evidence

Validated package:

```text
sha256              01a85fb532b4df4a7eed799ce0d575e91ad246f3eee5572af070bab3e96094ec
files               3451
compressed_bytes    67387627
uncompressed_bytes  184360025
```

Because the compressed artifact is larger than the direct Lambda upload envelope, deployment uses the existing versioned artifact bucket with a content-addressed key. The uncompressed artifact remains below the Lambda deployment-size ceiling.

## Validation evidence

Final D2 validation:

```text
workflow  Validate EPSS History 2.5D-2
run       33345440139
job       99348543835
commit    e3d601a827410be3d397fed3ad7d886cba37623f
result    SUCCESS
```

The final run passed:

```text
uv lock --check
uv sync --frozen
ruff
pyright
full pytest regression
all Lambda package builds required by Terraform
terraform fmt
terraform init -backend=false
terraform validate
TFLint
Checkov
frozen D2 control-surface assertions
```

The validated control-surface gates are:

```text
EPSS_HISTORY_D2_FORWARD_BOUNDARY_REVALIDATED_GATE=PASS
EPSS_HISTORY_D2_PLAN_ID_FROZEN_GATE=PASS
EPSS_HISTORY_D2_PINNED_WORKLIST_GATE=PASS
EPSS_HISTORY_D2_COORDINATOR_IAM_GATE=PASS
EPSS_HISTORY_D2_TRANSFORMER_IAM_GATE=PASS
EPSS_HISTORY_D2_SYNCHRONOUS_INVOCATION_GATE=PASS
EPSS_HISTORY_D2_CONCURRENCY_ONE_GATE=PASS
EPSS_HISTORY_D2_SEVEN_SNAPSHOT_LIMIT_GATE=PASS
EPSS_HISTORY_D2_OBSERVABILITY_GATE=PASS
EPSS_HISTORY_D2_COST_GUARDRAIL_GATE=PASS
EPSS_2_5D2_GATE=PASS
```

The temporary D2 validation workflow was removed after the successful proof.

## AWS execution boundary

At D2 closeout:

```text
historical Lambda deployed:      NO
Terraform applied:               NO
historical canary executed:      NO
historical Bronze writes:        0
historical Silver writes:        0
historical completion writes:    0
full historical backfill:        NO
Phase 3:                         BLOCKED
```

D2 therefore proves the implementation and static/runtime contracts without spending the mutation budget reserved for the canary gate.

## Next single gate

**Phase 2.5D-3 — deploy the bounded historical bootstrap surface and execute the seven-snapshot canary.**

D3 must remain limited to the seven representative snapshots and must validate exact Bronze, Silver, completion, replay, observability, IAM, forward-boundary, and measured cost/runtime evidence before any larger historical execution is authorized.

The full historical backfill remains unauthorized.
