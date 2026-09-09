"""Content-minimized evidence produced by read-only Amazon Inspector discovery."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiscoveryApiEvidence:
    """Measured outcome for one bounded Inspector read API."""

    attempted: bool
    outcome: str
    page_count: int
    record_count: int
    page_content_sha256: tuple[str, ...]
    sdk_retry_count: int
    error_code: str | None = None

    def __post_init__(self) -> None:
        """Reject malformed measurement evidence."""
        if not self.outcome:
            raise ValueError("outcome must not be empty")
        for name, value in (
            ("page_count", self.page_count),
            ("record_count", self.record_count),
            ("sdk_retry_count", self.sdk_retry_count),
        ):
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if len(self.page_content_sha256) != self.page_count:
            raise ValueError("one page hash is required for each successful page")
        if any(len(value) != 64 for value in self.page_content_sha256):
            raise ValueError("page hashes must be SHA-256 hex digests")
        if self.attempted is False and self.page_count != 0:
            raise ValueError("an unattempted API cannot have pages")


@dataclass(frozen=True, slots=True)
class InspectorDiscoveryEvidence:
    """Independent summary of one read-only Amazon Inspector discovery run."""

    contract_version: str
    region: str
    expected_account_id: str | None
    result: str
    coverage: DiscoveryApiEvidence
    findings: DiscoveryApiEvidence
    coverage_resource_type_counts: tuple[tuple[str, int], ...]
    finding_resource_type_counts: tuple[tuple[str, int], ...]
    finding_type_counts: tuple[tuple[str, int], ...]
    scan_status_counts: tuple[tuple[str, int], ...]
    client_elapsed_ms: float
    aws_mutation_count: int = 0
    new_iam_count: int = 0
    model_invocations: int = 0
    capability_executions: int = 0

    def __post_init__(self) -> None:
        """Protect the zero-mutation discovery boundary."""
        if self.contract_version != "inspector-readonly-discovery:v1":
            raise ValueError("unsupported Inspector discovery contract")
        if not self.region:
            raise ValueError("region must not be empty")
        if not self.result:
            raise ValueError("result must not be empty")
        if self.client_elapsed_ms < 0:
            raise ValueError("client_elapsed_ms must be non-negative")
        for name, value in (
            ("aws_mutation_count", self.aws_mutation_count),
            ("new_iam_count", self.new_iam_count),
            ("model_invocations", self.model_invocations),
            ("capability_executions", self.capability_executions),
        ):
            if value != 0:
                raise ValueError(f"{name} must remain zero in Gate 16.2")
        for label, counts in (
            ("coverage_resource_type_counts", self.coverage_resource_type_counts),
            ("finding_resource_type_counts", self.finding_resource_type_counts),
            ("finding_type_counts", self.finding_type_counts),
            ("scan_status_counts", self.scan_status_counts),
        ):
            if any(not key or count < 1 for key, count in counts):
                raise ValueError(f"{label} contains invalid counts")
            if tuple(sorted(counts)) != counts:
                raise ValueError(f"{label} must be sorted for deterministic evidence")


__all__ = ["DiscoveryApiEvidence", "InspectorDiscoveryEvidence"]
