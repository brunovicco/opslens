# Phase 2.3E.1 — NVD Silver Runtime Workload Proof

## Status

COMPLETE

## Purpose

Measure the frozen NVD Silver v1 transformation contract against real immutable
NVD Bootstrap Bronze evidence before selecting an AWS runtime primitive.

This experiment answers whether the current NVD Silver transformation can run
with comfortable AWS Lambda headroom or whether chunking / AWS Glue is justified.

No NVD Silver AWS runtime infrastructure was created during this proof.

## Exact Bronze evidence

Source:

```text
NVD JSON 2.0 yearly feed
feed year: 2026
feed revision:
20260818T070012Z-10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f
```

Manifest:

```text
VersionId:
O9t9lPdkxd0GnvqZBBGU87mqRa5MrIRl

SHA-256:
c05376f10867dbda5b0fd49fbf9c9dabbb2c43f92d01877fdbfdaccbf188efc8

size:
1107 bytes
```

Feed object:

```text
VersionId:
To7DT_5iOOGPGXn8ZcYjGUpL54lW65i8

gzip SHA-256:
e3b48ac725eda895208fda77165d611e9a8d118304442e5b988c9108ded59739

gzip bytes:
23938173

uncompressed source SHA-256:
10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f

uncompressed bytes:
282112001
```

META object:

```text
VersionId:
B3.YI53rpiBEnHe8POj7cxsJs3gq4qHB

SHA-256:
fed969adf0692e84aaea70a2cd32c001b87841fddc7e1984396c437be3d38ae4

size:
168 bytes
```

Source CVE count:

```text
45447
```

All benchmark inputs were downloaded using explicit S3 object VersionIds and
verified locally by SHA-256 before transformation.

## Contract correction discovered by the workload proof

The first execution failed closed on:

```text
Unsupported NVD vulnStatus: 'Undergoing Analysis'
```

The real 2026 feed contained:

```text
21260  Analyzed
 1999  Awaiting Analysis
13440  Deferred
 3000  Modified
 4615  Received
  688  Rejected
  445  Undergoing Analysis
```

There were no missing `vulnStatus` or `sourceIdentifier` values in the measured
feed.

The Silver contract previously used:

```text
UndergoingAnalysis
AwaitingAnalysis
```

instead of the values observed in NVD source payloads:

```text
Undergoing Analysis
Awaiting Analysis
```

The bounded enum was corrected without widening the contract or changing the
fail-closed behavior for unknown future values.

Corrective commit:

```text
9bec380
fix(phase-2): align NVD vulnerability status values
```

Validation after the correction:

```text
NVD transformation tests: 145 passed
Ruff: PASS
Pyright: PASS
git diff --check: PASS
```

## Benchmark environment

```text
OS:
macOS 26.5.2 arm64

Python:
3.13.12 CPython

PyArrow:
25.0.1

Git commit:
9bec3809fb9251feeee72c26834a050df9b26daf
```

This is a local workload proof, not an AWS Lambda runtime benchmark.

S3 retrieval latency was intentionally excluded.

## Measured execution

Two independent Python processes executed the same exact immutable Bronze
evidence.

### Run 1

```text
workload wall time:
35.307 s

normalization:
19.062 s

logical record-set hash:
6.466 s

Parquet serialization:
2.277 s

completion binding reserialization:
2.105 s

maximum RSS:
1714651136 bytes

Silver rows:
45447

Parquet bytes:
34678854
```

### Run 2

```text
workload wall time:
33.347 s

normalization:
18.729 s

logical record-set hash:
6.287 s

Parquet serialization:
2.198 s

completion binding reserialization:
2.040 s

maximum RSS:
1829617664 bytes

Silver rows:
45447

Parquet bytes:
34678854
```

Largest observed local maximum RSS was approximately 1.70 GiB.

macOS also reported a higher peak memory footprint of approximately 2.45 GiB,
which is retained as a conservative operational signal.

## Determinism evidence

Logical record-set SHA-256:

```text
54e0982038c148f98aa9bae0c8a450c33e60acefd81ab40cf17be31ce48415ac
```

Physical Parquet SHA-256:

```text
ff9491867fc1fb45918eb6e0950a5a17066be370ce18bc92296308f58dc49216
```

Both independent processes produced byte-identical Parquet artifacts.

Validated gates:

```text
NVD_SILVER_BYTE_REPLAY_GATE=PASS
NVD_SILVER_ROW_COUNT_REPLAY_GATE=PASS
NVD_SILVER_LOGICAL_HASH_REPLAY_GATE=PASS
NVD_SILVER_PARQUET_HASH_REPLAY_GATE=PASS
NVD_SILVER_WARNING_REPLAY_GATE=PASS
```

Unsupported CVSS families:

```text
none
```

Warning count:

```text
0
```

## Memory observation

The current serializer is not streaming.

The workload can hold multiple representations during execution:

```text
source JSON object graph
    +
normalized Silver records
    +
sorted record collection
    +
mapped Python rows
    +
Arrow table
    +
Parquet output buffer
```

`row_group_size=5000` controls Parquet row groups but does not bound the
application working set to 5000 CVEs.

This behavior was intentionally measured before changing the implementation.

## Runtime decision

### Selected direction

```text
AWS Lambda first
```

Initial AWS validation candidate:

```text
memory:
4096 MB

timeout:
180 seconds

runtime:
Python 3.13
```

These values are validation candidates, not final optimized production settings.

### Why Lambda

The measured workload:

```text
45447 CVEs
~34 seconds local wall time
< 2.5 GiB conservative local memory signal
```

does not demonstrate a need for distributed execution.

A 4096 MB Lambda gives meaningful initial memory headroom while preserving a
simple, bounded, observable serverless runtime.

### Why not AWS Glue yet

The measured transformation:

- completes in tens of seconds;
- processes 45447 CVEs;
- fits within a few GiB of local process memory;
- does not require distributed joins, shuffle, or aggregation.

There is no measured requirement for a distributed Spark runtime in this
increment.

### Why not chunking yet

Chunking would complicate:

- deterministic artifact identity;
- global row ordering;
- logical record-set proof;
- Silver COMPLETE evidence;
- replay semantics;
- failure recovery.

The current complete-batch workload fits the initial Lambda validation envelope,
so that complexity is not justified yet.

## AWS runtime proof still required

The local benchmark does not prove:

- Linux vs macOS physical Parquet identity;
- Lambda cold-start overhead;
- Lambda-native peak memory usage;
- S3 exact-version read latency;
- Lambda CPU scaling characteristics at 4096 MB;
- deployed PyArrow package behavior;
- actual Lambda duration and cost.

The deployed AWS environment will become the canonical production environment
for physical Parquet reproduction.

## IAM impact

None in Phase 2.3E.1.

A future Silver runtime is expected to require narrowly scoped permissions such
as:

```text
s3:GetObjectVersion
    exact NVD Bronze scope

s3:PutObject
    exact NVD Silver scope
```

Final IAM is deferred until the runtime adapter is implemented.

No `s3:ListBucket` requirement has been demonstrated.

## Cost impact

Phase 2.3E.1 introduced no deployed AWS compute resources.

Only bounded reads of existing immutable Bronze evidence were required.

Future Lambda cost will be measured from the deployed runtime rather than
claimed from the local benchmark.

## Observability

This proof recorded:

- phase-level wall time;
- process peak RSS;
- row count;
- physical output size;
- logical hash;
- physical hash;
- warning count;
- replay equality.

The AWS runtime will later add CloudWatch and tracing evidence.

## Failure evidence

The workload proof surfaced a real source-contract incompatibility before
deployment:

```text
real Bronze source
    -> deterministic Silver normalization
    -> unsupported real vulnStatus
    -> fail closed
```

The contract was corrected and the exact same immutable Bronze evidence was
replayed successfully.

This demonstrates why real workload proofs are required before infrastructure
deployment.

## AIP-C01 relevance

This increment exercises Professional-level reasoning around:

- proof-of-concept validation before full deployment;
- data processing and validation;
- serverless compute selection;
- resource-efficiency measurement;
- performance benchmarking;
- deterministic testing;
- troubleshooting;
- failure diagnosis;
- cost-aware architecture.

## Exit criteria

Phase 2.3E.1 is complete because:

```text
exact Bronze evidence: PASS
record count: PASS
Silver normalization: PASS
logical proof: PASS
Parquet serialization: PASS
same-process deterministic replay: PASS
cross-process byte replay: PASS
peak memory measured: PASS
wall time measured: PASS
warnings measured: PASS
runtime primitive decision: PASS
```

Decision:

```text
continue with Lambda-first NVD Silver runtime
```

The next increment is Phase 2.3E.2 — application orchestration.

No Terraform or Lambda runtime should be added until the application boundary is
composed and tested independently from AWS.
