"""Bounded read-only Amazon Inspector discovery with content-minimized evidence."""

import json
from collections import Counter
from collections.abc import Mapping
from datetime import date, datetime
from hashlib import sha256
from time import perf_counter_ns
from typing import Protocol, cast

from botocore.exceptions import ClientError

from opslens.runtime_exposure.domain.discovery import (
    DiscoveryApiEvidence,
    InspectorDiscoveryEvidence,
)

_MAX_RESULTS = 100
_ACCESS_DENIED_CODES = frozenset(
    {
        "AccessDenied",
        "AccessDeniedException",
        "UnauthorizedOperation",
    }
)


class InspectorReadClient(Protocol):
    """Smallest Inspector2 client surface authorized by Gate 16.2."""

    def list_coverage(self, **kwargs: object) -> dict[str, object]:
        """List Inspector coverage records."""
        ...

    def list_findings(self, **kwargs: object) -> dict[str, object]:
        """List Inspector finding records."""
        ...


def _json_default(value: object) -> str:
    """Normalize AWS timestamp-like values for deterministic hashing."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"unsupported value in Inspector evidence page: {type(value).__name__}")


def _page_hash(records: list[object]) -> str:
    """Hash only business records, excluding request IDs and pagination tokens."""
    raw = json.dumps(
        records,
        allow_nan=False,
        default=_json_default,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _mapping(value: object, *, label: str) -> dict[str, object]:
    """Require one mapping with string keys."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    raw = cast(Mapping[object, object], value)
    if any(not isinstance(key, str) for key in raw):
        raise ValueError(f"{label} keys must be strings")
    return {cast(str, key): item for key, item in raw.items()}


def _list(value: object, *, label: str) -> list[object]:
    """Require one list."""
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return cast(list[object], value)


def _string(value: object, *, label: str) -> str:
    """Require one non-empty string."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _retry_count(response: dict[str, object]) -> int:
    """Extract SDK retry evidence without persisting response metadata."""
    metadata_value = response.get("ResponseMetadata")
    if metadata_value is None:
        return 0
    metadata = _mapping(metadata_value, label="ResponseMetadata")
    retries = metadata.get("RetryAttempts", 0)
    if not isinstance(retries, int) or retries < 0:
        raise ValueError("ResponseMetadata.RetryAttempts must be a non-negative integer")
    return retries


def _next_token(response: dict[str, object]) -> str | None:
    """Read an opaque pagination token without persisting it."""
    value = response.get("nextToken")
    if value is None:
        return None
    return _string(value, label="nextToken")


def _error_code(error: ClientError) -> str:
    """Extract one AWS error code from a ClientError."""
    response = _mapping(error.response, label="ClientError.response")
    error_value = _mapping(response.get("Error"), label="ClientError.Error")
    return _string(error_value.get("Code"), label="ClientError.Error.Code")


def _failed_api_evidence(*, code: str) -> DiscoveryApiEvidence:
    """Create content-minimized evidence for a failed attempted API."""
    outcome = "ACCESS_DENIED" if code in _ACCESS_DENIED_CODES else "API_ERROR"
    return DiscoveryApiEvidence(
        attempted=True,
        outcome=outcome,
        page_count=0,
        record_count=0,
        page_content_sha256=(),
        sdk_retry_count=0,
        error_code=code,
    )


def _not_attempted_api_evidence() -> DiscoveryApiEvidence:
    """Create evidence for an API intentionally skipped after fail-closed stop."""
    return DiscoveryApiEvidence(
        attempted=False,
        outcome="NOT_ATTEMPTED",
        page_count=0,
        record_count=0,
        page_content_sha256=(),
        sdk_retry_count=0,
    )


def _collect_pages(
    *,
    client: InspectorReadClient,
    operation: str,
) -> tuple[DiscoveryApiEvidence, list[object]]:
    """Read all pages for one of the two authorized Inspector APIs."""
    if operation not in {"coverage", "findings"}:
        raise ValueError("unsupported Inspector discovery operation")

    token: str | None = None
    page_hashes: list[str] = []
    records: list[object] = []
    retry_count = 0

    while True:
        kwargs: dict[str, object] = {"maxResults": _MAX_RESULTS}
        if token is not None:
            kwargs["nextToken"] = token
        try:
            response = (
                client.list_coverage(**kwargs)
                if operation == "coverage"
                else client.list_findings(**kwargs)
            )
        except ClientError as error:
            if page_hashes:
                raise RuntimeError(
                    f"Inspector {operation} failed after partial pagination"
                ) from error
            return _failed_api_evidence(code=_error_code(error)), []

        response_object = _mapping(response, label=f"List{operation.title()} response")
        field = "coveredResources" if operation == "coverage" else "findings"
        page_records = _list(response_object.get(field, []), label=field)
        page_hashes.append(_page_hash(page_records))
        records.extend(page_records)
        retry_count += _retry_count(response_object)
        token = _next_token(response_object)
        if token is None:
            break

    return (
        DiscoveryApiEvidence(
            attempted=True,
            outcome="SUCCESS",
            page_count=len(page_hashes),
            record_count=len(records),
            page_content_sha256=tuple(page_hashes),
            sdk_retry_count=retry_count,
        ),
        records,
    )


def _coverage_counts(
    records: list[object],
    *,
    expected_account_id: str | None,
) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]]:
    """Count coverage resource and scan-status dimensions without retaining raw records."""
    resource_types: Counter[str] = Counter()
    scan_statuses: Counter[str] = Counter()
    for index, raw in enumerate(records):
        record = _mapping(raw, label=f"coveredResources[{index}]")
        account_id = _string(record.get("accountId"), label="coverage accountId")
        if expected_account_id is not None and account_id != expected_account_id:
            raise ValueError("Inspector coverage account does not match the expected account")
        resource_types[_string(record.get("resourceType"), label="coverage resourceType")] += 1
        scan_status = _mapping(record.get("scanStatus"), label="coverage scanStatus")
        scan_statuses[
            _string(scan_status.get("statusCode"), label="coverage scanStatus.statusCode")
        ] += 1
    return tuple(sorted(resource_types.items())), tuple(sorted(scan_statuses.items()))


def _finding_counts(
    records: list[object],
    *,
    expected_account_id: str | None,
) -> tuple[tuple[tuple[str, int], ...], tuple[tuple[str, int], ...]]:
    """Count finding/resource types and enforce EC2-only reachability semantics."""
    finding_types: Counter[str] = Counter()
    resource_types: Counter[str] = Counter()
    for index, raw in enumerate(records):
        finding = _mapping(raw, label=f"findings[{index}]")
        account_id = _string(finding.get("awsAccountId"), label="finding awsAccountId")
        if expected_account_id is not None and account_id != expected_account_id:
            raise ValueError("Inspector finding account does not match the expected account")
        finding_type = _string(finding.get("type"), label="finding type")
        finding_types[finding_type] += 1
        resources = _list(finding.get("resources"), label="finding resources")
        if not resources:
            raise ValueError("Inspector finding must contain at least one resource")
        for resource_index, raw_resource in enumerate(resources):
            resource = _mapping(
                raw_resource,
                label=f"findings[{index}].resources[{resource_index}]",
            )
            resource_type = _string(resource.get("type"), label="finding resource type")
            resource_types[resource_type] += 1
            if finding_type == "NETWORK_REACHABILITY" and resource_type != "AWS_EC2_INSTANCE":
                raise ValueError("NETWORK_REACHABILITY evidence must remain EC2-only")
    return tuple(sorted(finding_types.items())), tuple(sorted(resource_types.items()))


def run_readonly_inspector_discovery(
    *,
    client: InspectorReadClient,
    region: str,
    expected_account_id: str | None = None,
) -> InspectorDiscoveryEvidence:
    """Run the Gate 16.2 read-only discovery and stop closed on access denial."""
    if not region:
        raise ValueError("region must not be empty")
    started_ns = perf_counter_ns()

    coverage, coverage_records = _collect_pages(client=client, operation="coverage")
    if coverage.outcome != "SUCCESS":
        result = (
            "BLOCKED_BY_EXISTING_IAM"
            if coverage.outcome == "ACCESS_DENIED"
            else "COVERAGE_API_ERROR"
        )
        return InspectorDiscoveryEvidence(
            contract_version="inspector-readonly-discovery:v1",
            region=region,
            expected_account_id=expected_account_id,
            result=result,
            coverage=coverage,
            findings=_not_attempted_api_evidence(),
            coverage_resource_type_counts=(),
            finding_resource_type_counts=(),
            finding_type_counts=(),
            scan_status_counts=(),
            client_elapsed_ms=(perf_counter_ns() - started_ns) / 1_000_000,
        )

    coverage_resource_types, scan_statuses = _coverage_counts(
        coverage_records,
        expected_account_id=expected_account_id,
    )
    findings, finding_records = _collect_pages(client=client, operation="findings")
    if findings.outcome != "SUCCESS":
        result = (
            "BLOCKED_BY_EXISTING_IAM"
            if findings.outcome == "ACCESS_DENIED"
            else "FINDINGS_API_ERROR"
        )
        return InspectorDiscoveryEvidence(
            contract_version="inspector-readonly-discovery:v1",
            region=region,
            expected_account_id=expected_account_id,
            result=result,
            coverage=coverage,
            findings=findings,
            coverage_resource_type_counts=coverage_resource_types,
            finding_resource_type_counts=(),
            finding_type_counts=(),
            scan_status_counts=scan_statuses,
            client_elapsed_ms=(perf_counter_ns() - started_ns) / 1_000_000,
        )

    finding_types, finding_resource_types = _finding_counts(
        finding_records,
        expected_account_id=expected_account_id,
    )
    return InspectorDiscoveryEvidence(
        contract_version="inspector-readonly-discovery:v1",
        region=region,
        expected_account_id=expected_account_id,
        result="SUCCESS",
        coverage=coverage,
        findings=findings,
        coverage_resource_type_counts=coverage_resource_types,
        finding_resource_type_counts=finding_resource_types,
        finding_type_counts=finding_types,
        scan_status_counts=scan_statuses,
        client_elapsed_ms=(perf_counter_ns() - started_ns) / 1_000_000,
    )


__all__ = ["InspectorReadClient", "run_readonly_inspector_discovery"]
