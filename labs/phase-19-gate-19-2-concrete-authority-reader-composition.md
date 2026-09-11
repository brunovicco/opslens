# Phase 19 — Gate 19.2 Concrete Threat-Authority Reader Composition

Status: **implementation only; no live measurement**.

This increment provides the provider-composition seam needed by a later human-run preparation driver. It accepts an already-created exact-version read-only S3 capability, one explicit bucket, and five independent byte ceilings for GHSA Silver, NVD Silver, NVD Bronze, KEV Bronze, and EPSS Bronze.

Construction performs zero provider I/O. The resulting readers remain inert until `materialize_pre_measurement_threat_evidence` resolves already-admitted immutable `object_key + VersionId` coordinates.

The separation is intentional: S3 authority reads are pre-measurement preparation for Gate 19.2. They are not inserted into `RepresentativeWorkloadExecution`, because S3 request count and latency are outside the frozen request-time provider-accounting contract. `UNMEASURED != zero` remains enforced structurally rather than inferred.

No default byte ceilings are introduced by this increment. A human-run driver must supply explicit positive limits, making the operational bound visible at composition time rather than hidden in adapter defaults.

This is not a production topology decision and does not imply `SYNC` or `ASYNC` public execution. Gate 19.2 remains `DEFERRED_PENDING_MEASUREMENT` until a real admitted live measurement exists.

No AWS call, Bedrock call, IAM mutation, public endpoint, mutable discovery, retry, fallback, or third-party repository code execution is introduced here. PR #89 remains out of scope.
