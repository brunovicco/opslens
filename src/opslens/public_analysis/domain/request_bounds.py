"""What one public request is allowed to cost, and the refusal when it costs more.

Phase 21's rule is one sentence: reject, never truncate. A bound that silently trims its
input produces a benign-looking answer from partial evidence, which on this endpoint is
the same as lying. So every bound here raises with a reason code, and none of them
shortens anything.

```text
truncated input != smaller input
a bound reached != a smaller answer
```

The numbers come from three places, and which place matters more than the number.

**Measured.** `labs/evidence/response-item-size-v1.json`: a final finding projection is
3,267 bytes, a stored index item is 1,078, and a projected source row is 385. The
response bound is derived from the first, the read bound from the second, and neither
from the third — which was the figure ADR 0087 originally sized from, and is wrong for
both by up to 8.5x.

```text
projected bytes != stored bytes != response bytes
rows read != findings emitted != response bytes
```

**Assumed about the platform, and deliberately not asserted.** A synchronous Lambda
response and an API Gateway integration timeout both have ceilings, and this module does
not know them: it states the headroom it intends and names the assumption. ADR 0086
already paid for the other version of this mistake, where the probe carried the scan
cutoff as a constant and would have reported a bound that was not the one in force.

```text
declared constant != configuration in force
```

Gate 21.2 configures the gateway and the reserved concurrency. It has to verify these
assumptions against what is actually deployed rather than trusting this file, and the
assumption fields exist so that verification has something to compare against.

That verification found the first one wrong. The timeout shipped here as 29 seconds, the
classic REST API Gateway ceiling; the deployed HTTP API integration is configured at 10.
`tests/unit/public_analysis/test_platform_assumptions.py` now reads it out of the
Terraform, so the number cannot drift back into being guessed.

```text
a named assumption != a checked assumption
```

The response ceiling stays unverified, because it is AWS's number and nothing in this
repository can read it. What protects that one is margin rather than a check: the budget
projects about a megabyte, so the assumption would have to be wrong by more than six
times before it binds.

**Policy.** The package and lock bounds are choices about what this endpoint is for, not
derivations. A lock with more than a thousand identified packages is a monorepo, and an
endpoint that answers for strangers can decline to be a monorepo scanner without
apologising for it.
"""

from dataclasses import dataclass
from typing import Final

from opslens.public_analysis.domain.errors import PublicAnalysisValidationError

# Measured, 2026-09-17. See labs/evidence/response-item-size-v1.json.
FINDING_RESPONSE_BYTES: Final = 3267
STORED_INDEX_ITEM_BYTES: Final = 1078

# The response budget this endpoint holds itself to. Not a platform limit: a choice made
# so the platform limit is never the thing that stops a request.
RESPONSE_BUDGET_BYTES: Final = 1024 * 1024


class PublicRequestBoundError(PublicAnalysisValidationError):
    """Raised when one request would cost more than the endpoint allows.

    Attributes:
        reason_code: Stable machine-readable cause.
        limit: The bound that was reached.
        observed: What the request would have cost.
    """

    def __init__(self, message: str, *, reason_code: str, limit: int, observed: int) -> None:
        """Record what was exceeded, by how much, and why.

        Args:
            message: Human-readable explanation.
            reason_code: Stable machine-readable cause.
            limit: The bound that was reached.
            observed: What the request would have cost.
        """
        super().__init__(message)
        self.reason_code = reason_code
        self.limit = limit
        self.observed = observed


@dataclass(frozen=True, slots=True)
class PublicRequestBounds:
    """Every ceiling one public request is held to.

    Attributes:
        max_lock_bytes: Largest `uv.lock` this endpoint will read.
        max_lock_package_records: Most records that lock may declare.
        max_scoped_packages: Most distinct packages one request may query the index for.
        max_index_rows_read: Most stored rows one request may read across all packages.
        max_findings_emitted: Most findings one response may carry.
        assumed_platform_response_bytes: The response ceiling this budget assumes the
            platform has. Gate 21.2 verifies it; this module does not know it.
        assumed_platform_timeout_seconds: The integration timeout this budget assumes.
            Same caveat, same gate.
    """

    max_lock_bytes: int
    max_lock_package_records: int
    max_scoped_packages: int
    max_index_rows_read: int
    max_findings_emitted: int
    assumed_platform_response_bytes: int
    assumed_platform_timeout_seconds: int

    def __post_init__(self) -> None:
        """Reject a bound set that cannot hold.

        Raises:
            PublicAnalysisValidationError: If a bound is not positive, or if the response
                budget does not fit inside the platform ceiling it assumes.
        """
        for field, value in (
            ("max_lock_bytes", self.max_lock_bytes),
            ("max_lock_package_records", self.max_lock_package_records),
            ("max_scoped_packages", self.max_scoped_packages),
            ("max_index_rows_read", self.max_index_rows_read),
            ("max_findings_emitted", self.max_findings_emitted),
            ("assumed_platform_response_bytes", self.assumed_platform_response_bytes),
            ("assumed_platform_timeout_seconds", self.assumed_platform_timeout_seconds),
        ):
            if type(value) is not int or value <= 0:
                raise PublicAnalysisValidationError(
                    f"public request bound {field} must be a positive integer"
                )

        if self.max_findings_emitted > self.max_index_rows_read:
            raise PublicAnalysisValidationError(
                "a request cannot emit more findings than the rows it is allowed to read"
            )
        if self.projected_response_bytes > self.assumed_platform_response_bytes:
            raise PublicAnalysisValidationError(
                "the finding bound projects a response larger than the platform ceiling "
                "this bound set assumes"
            )

    @property
    def projected_response_bytes(self) -> int:
        """Return what a response at the finding bound would weigh, at measured size."""
        return self.max_findings_emitted * FINDING_RESPONSE_BYTES

    @property
    def platform_headroom(self) -> float:
        """Return how many times over the assumed ceiling the budget leaves."""
        return self.assumed_platform_response_bytes / self.projected_response_bytes

    def admit_lock_bytes(self, observed: int) -> None:
        """Refuse a lock larger than this endpoint reads.

        Args:
            observed: Size of the lock file.

        Raises:
            PublicRequestBoundError: If the lock is too large.
        """
        if observed > self.max_lock_bytes:
            raise PublicRequestBoundError(
                f"lock file is {observed} bytes, above the {self.max_lock_bytes} allowed",
                reason_code="lock_too_large",
                limit=self.max_lock_bytes,
                observed=observed,
            )

    def admit_lock_records(self, observed: int) -> None:
        """Refuse a lock declaring more records than this endpoint parses.

        Args:
            observed: Records the lock declares.

        Raises:
            PublicRequestBoundError: If there are too many.
        """
        if observed > self.max_lock_package_records:
            raise PublicRequestBoundError(
                f"lock declares {observed} records, above the "
                f"{self.max_lock_package_records} allowed",
                reason_code="lock_records_exceeded",
                limit=self.max_lock_package_records,
                observed=observed,
            )

    def admit_scoped_packages(self, observed: int) -> None:
        """Refuse a scope with more packages than this endpoint queries for.

        Args:
            observed: Distinct packages the scope names.

        Raises:
            PublicRequestBoundError: If there are too many.
        """
        if observed > self.max_scoped_packages:
            raise PublicRequestBoundError(
                f"request scopes {observed} packages, above the "
                f"{self.max_scoped_packages} allowed",
                reason_code="scoped_packages_exceeded",
                limit=self.max_scoped_packages,
                observed=observed,
            )

    def admit_rows_read(self, observed: int) -> None:
        """Refuse a request that would read more index rows than allowed.

        This is the capacity bound. It is separate from the finding bound because a row
        that is read and found not to apply costs capacity and no response bytes.

        Args:
            observed: Stored rows read so far.

        Raises:
            PublicRequestBoundError: If too many rows would be read.
        """
        if observed > self.max_index_rows_read:
            raise PublicRequestBoundError(
                f"request would read {observed} index rows, above the "
                f"{self.max_index_rows_read} allowed",
                reason_code="index_rows_exceeded",
                limit=self.max_index_rows_read,
                observed=observed,
            )

    def admit_findings(self, observed: int) -> None:
        """Refuse a response carrying more findings than the budget holds.

        Args:
            observed: Findings the response would carry.

        Raises:
            PublicRequestBoundError: If the response would be too large.
        """
        if observed > self.max_findings_emitted:
            raise PublicRequestBoundError(
                f"analysis produced {observed} findings, above the "
                f"{self.max_findings_emitted} one response may carry",
                reason_code="findings_exceeded",
                limit=self.max_findings_emitted,
                observed=observed,
            )


# The bound set this endpoint runs under.
#
# max_findings_emitted   RESPONSE_BUDGET_BYTES / FINDING_RESPONSE_BYTES, measured.
# max_index_rows_read    Enough for the three heaviest packages in the live index —
#                        tensorflow, tensorflow-gpu and tensorflow-cpu carry 3,941 rows
#                        between them (ADR 0087) — with room above. At the measured
#                        stored item that is about 5.1 MB read, roughly five index
#                        pages.
# max_scoped_packages    Policy. This repository's own lock declares 55. A thousand is
#                        generous for a project and a refusal for a monorepo, which this
#                        endpoint is not for.
# max_lock_*             The existing repository-evidence ceilings, restated here so the
#                        public bound set is readable in one place rather than inferred
#                        from four modules.
PUBLIC_REQUEST_BOUNDS: Final = PublicRequestBounds(
    max_lock_bytes=1_048_576,
    max_lock_package_records=5_000,
    max_scoped_packages=1_000,
    max_index_rows_read=5_000,
    max_findings_emitted=RESPONSE_BUDGET_BYTES // FINDING_RESPONSE_BYTES,
    assumed_platform_response_bytes=6 * 1024 * 1024,
    # Read out of infra/environments/dev/public_async_runtime.tf, not assumed from the
    # service's documented maximum. The bound set first shipped with 29 — the classic
    # REST API Gateway ceiling — and the deployed HTTP API integration is configured at
    # 10 seconds. A standing test compares the two so this cannot drift back.
    assumed_platform_timeout_seconds=10,
)


__all__ = [
    "FINDING_RESPONSE_BYTES",
    "PUBLIC_REQUEST_BOUNDS",
    "RESPONSE_BUDGET_BYTES",
    "STORED_INDEX_ITEM_BYTES",
    "PublicRequestBoundError",
    "PublicRequestBounds",
]
