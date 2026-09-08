"""Deterministic business-result projection for the first bounded MCP transport slice."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from opslens.agent_baseline.domain import (
    AgentCapability,
    StructuredSecurityQueryInvocation,
    StructuredSecurityQueryResultBinding,
)
from opslens.mcp_boundary.domain.errors import McpBoundaryValidationError
from opslens.mcp_boundary.domain.execution import McpCapabilityExecutionBridge
from opslens.mcp_boundary.domain.exposure import McpToolName

MCP_RESULT_PROJECTION_CONTRACT_VERSION = "mcp-result-projection:v1"
MAX_MCP_RESULT_ROWS = 100
MAX_MCP_EPSS_TEXT_CHARS = 32

_CVE_PATTERN = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,19}$", re.ASCII)
_EPSS_PATTERN = re.compile(r"^(?:0(?:\.[0-9]+)?|1(?:\.0+)?)$", re.ASCII)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_PROJECTION_ID_PATTERN = re.compile(
    rf"^{re.escape(MCP_RESULT_PROJECTION_CONTRACT_VERSION)}:projection:[0-9a-f]{{64}}$",
    re.ASCII,
)
_EXPECTED_ATHENA_COLUMNS = ("cve", "epss")
_PROTOCOL_COLUMNS = ("cve", "epss_score")


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic MCP result-projection identity payload."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    """Hash one canonical MCP result-projection payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _validate_sha256(value: object, *, label: str, expected: str | None = None) -> str:
    """Validate one lowercase SHA-256 field and optional canonical expectation."""
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        raise McpBoundaryValidationError(f"{label} must be lowercase SHA-256")
    if expected is not None and value != expected:
        raise McpBoundaryValidationError(f"{label} must match canonical MCP result semantics")
    return value


def _normalize_epss_score(value: object) -> str:
    """Validate one bounded EPSS text value and return stable decimal text."""
    if type(value) is not str or not value or len(value) > MAX_MCP_EPSS_TEXT_CHARS:
        raise McpBoundaryValidationError("projected EPSS score is outside the bounded text shape")
    if _EPSS_PATTERN.fullmatch(value) is None:
        raise McpBoundaryValidationError("projected EPSS score must be decimal text from 0 to 1")
    if value.startswith("1"):
        return "1"
    if "." not in value:
        return "0"
    normalized = value.rstrip("0").rstrip(".")
    return normalized or "0"


@dataclass(frozen=True, slots=True)
class McpStructuredEpssRow:
    """Allowlisted structured-security business row exposed through MCP."""

    cve: str
    epss_score: str

    def __post_init__(self) -> None:
        """Reject null, malformed, or oversized row content before transport."""
        if type(self.cve) is not str or _CVE_PATTERN.fullmatch(self.cve) is None:
            raise McpBoundaryValidationError("projected CVE identity is invalid")
        normalized_score = _normalize_epss_score(self.epss_score)
        object.__setattr__(self, "epss_score", normalized_score)

    def canonical_payload(self) -> dict[str, str]:
        """Return the exact protocol-safe business row shape."""
        return {"cve": self.cve, "epss_score": self.epss_score}


@dataclass(frozen=True, slots=True)
class McpStructuredSecurityResultProjection:
    """Content-addressed structured-query result projection bound to Gate 13.3 evidence."""

    contract_version: str
    tool_name: McpToolName
    capability: AgentCapability
    invocation_id: str
    execution_id: str
    bridge_id: str
    result_sha256: str
    columns: tuple[str, str]
    rows: tuple[McpStructuredEpssRow, ...]
    projection_sha256: str
    projection_id: str

    def __post_init__(self) -> None:
        """Reject forged projection identity or capability/result broadening."""
        if self.contract_version != MCP_RESULT_PROJECTION_CONTRACT_VERSION:
            raise McpBoundaryValidationError("MCP result projection contract version is invalid")
        if self.tool_name is not McpToolName.STRUCTURED_SECURITY_QUERY:
            raise McpBoundaryValidationError("MCP result projection tool is unsupported")
        if self.capability is not AgentCapability.STRUCTURED_SECURITY_QUERY:
            raise McpBoundaryValidationError("MCP result projection capability is unsupported")
        if self.columns != _PROTOCOL_COLUMNS:
            raise McpBoundaryValidationError("MCP result projection columns are not code-owned")
        if type(self.rows) is not tuple or any(
            type(row) is not McpStructuredEpssRow for row in self.rows
        ):
            raise McpBoundaryValidationError("MCP result projection rows are invalid")
        if len(self.rows) > MAX_MCP_RESULT_ROWS:
            raise McpBoundaryValidationError("MCP result projection exceeds the row bound")
        _validate_sha256(self.result_sha256, label="result_sha256")
        expected = _canonical_sha256(self.identity_payload())
        _validate_sha256(
            self.projection_sha256,
            label="projection_sha256",
            expected=expected,
        )
        expected_id = f"{MCP_RESULT_PROJECTION_CONTRACT_VERSION}:projection:{expected}"
        if self.projection_id != expected_id:
            raise McpBoundaryValidationError(
                "projection_id must match content-addressed MCP result semantics"
            )
        if _PROJECTION_ID_PATTERN.fullmatch(self.projection_id) is None:
            raise McpBoundaryValidationError("projection_id violates the MCP result contract")

    def identity_payload(self) -> dict[str, object]:
        """Return canonical projection semantics, including only allowlisted business content."""
        return {
            "bridge_id": self.bridge_id,
            "capability": self.capability.value,
            "columns": list(self.columns),
            "contract_version": self.contract_version,
            "execution_id": self.execution_id,
            "invocation_id": self.invocation_id,
            "result_sha256": self.result_sha256,
            "rows": [row.canonical_payload() for row in self.rows],
            "tool_name": self.tool_name.value,
        }

    @classmethod
    def create(
        cls,
        *,
        invocation: StructuredSecurityQueryInvocation,
        bridge: McpCapabilityExecutionBridge,
        result: StructuredSecurityQueryResultBinding,
    ) -> McpStructuredSecurityResultProjection:
        """Project one already-admitted structured result through an explicit code-owned policy."""
        if type(invocation) is not StructuredSecurityQueryInvocation:
            raise McpBoundaryValidationError(
                "structured MCP result projection requires the structured invocation"
            )
        if type(bridge) is not McpCapabilityExecutionBridge:
            raise McpBoundaryValidationError("structured MCP result projection requires one bridge")
        if type(result) is not StructuredSecurityQueryResultBinding:
            raise McpBoundaryValidationError(
                "structured MCP result projection requires one admitted structured result"
            )
        if bridge.tool_name is not McpToolName.STRUCTURED_SECURITY_QUERY:
            raise McpBoundaryValidationError("MCP execution bridge tool is not structured security")
        if bridge.capability is not AgentCapability.STRUCTURED_SECURITY_QUERY:
            raise McpBoundaryValidationError(
                "MCP execution bridge capability is not structured security"
            )
        if bridge.invocation_id != invocation.invocation_id:
            raise McpBoundaryValidationError("MCP result projection invocation identity drifted")
        if bridge.invocation_sha256 != invocation.invocation_sha256:
            raise McpBoundaryValidationError("MCP result projection invocation digest drifted")
        if result.invocation_sha256 != invocation.invocation_sha256:
            raise McpBoundaryValidationError("structured result is bound to another invocation")
        if bridge.downstream_result_sha256 != result.result_sha256:
            raise McpBoundaryValidationError("MCP execution bridge result digest drifted")

        athena_result = result.result
        if athena_result.columns != _EXPECTED_ATHENA_COLUMNS:
            raise McpBoundaryValidationError(
                "Athena projection columns are outside the frozen slice"
            )
        if len(athena_result.rows) > invocation.query.limit:
            raise McpBoundaryValidationError("Athena result exceeds the semantic-query row limit")
        if len(athena_result.rows) > MAX_MCP_RESULT_ROWS:
            raise McpBoundaryValidationError("Athena result exceeds the MCP result row bound")

        projected_rows: list[McpStructuredEpssRow] = []
        for row in athena_result.rows:
            if len(row) != 2 or row[0] is None or row[1] is None:
                raise McpBoundaryValidationError("Athena result row is not projectable")
            projected_rows.append(McpStructuredEpssRow(cve=row[0], epss_score=row[1]))

        rows = tuple(projected_rows)
        provisional = cls.__new__(cls)
        object.__setattr__(provisional, "contract_version", MCP_RESULT_PROJECTION_CONTRACT_VERSION)
        object.__setattr__(provisional, "tool_name", McpToolName.STRUCTURED_SECURITY_QUERY)
        object.__setattr__(provisional, "capability", AgentCapability.STRUCTURED_SECURITY_QUERY)
        object.__setattr__(provisional, "invocation_id", invocation.invocation_id)
        object.__setattr__(provisional, "execution_id", bridge.execution_id)
        object.__setattr__(provisional, "bridge_id", bridge.bridge_id)
        object.__setattr__(provisional, "result_sha256", result.result_sha256)
        object.__setattr__(provisional, "columns", _PROTOCOL_COLUMNS)
        object.__setattr__(provisional, "rows", rows)
        digest = _canonical_sha256(provisional.identity_payload())
        return cls(
            contract_version=MCP_RESULT_PROJECTION_CONTRACT_VERSION,
            tool_name=McpToolName.STRUCTURED_SECURITY_QUERY,
            capability=AgentCapability.STRUCTURED_SECURITY_QUERY,
            invocation_id=invocation.invocation_id,
            execution_id=bridge.execution_id,
            bridge_id=bridge.bridge_id,
            result_sha256=result.result_sha256,
            columns=_PROTOCOL_COLUMNS,
            rows=rows,
            projection_sha256=digest,
            projection_id=f"{MCP_RESULT_PROJECTION_CONTRACT_VERSION}:projection:{digest}",
        )


__all__ = [
    "MAX_MCP_EPSS_TEXT_CHARS",
    "MAX_MCP_RESULT_ROWS",
    "MCP_RESULT_PROJECTION_CONTRACT_VERSION",
    "McpStructuredEpssRow",
    "McpStructuredSecurityResultProjection",
]
