"""Deterministic evidence binding MCP admission to one typed capability execution."""

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from opslens.agent_baseline.domain import (
    AgentCapability,
    AgentCapabilityExecution,
    AgentCapabilityInvocation,
    action_for_invocation,
    capability_for_invocation,
)
from opslens.mcp_boundary.domain.errors import McpBoundaryValidationError
from opslens.mcp_boundary.domain.exposure import (
    McpToolCallAdmission,
    McpToolName,
    capability_for_mcp_tool,
)

MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION = "mcp-capability-execution:v1"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_ACTION_ID_PATTERN = re.compile(r"^single-agent-authority:v1:action:[0-9a-f]{64}$", re.ASCII)
_INVOCATION_ID_PATTERN = re.compile(
    r"^single-agent-execution:v1:invocation:[0-9a-f]{64}$",
    re.ASCII,
)
_ADMISSION_ID_PATTERN = re.compile(
    r"^mcp-capability-exposure:v1:admission:[0-9a-f]{64}$",
    re.ASCII,
)
_EXECUTION_ID_PATTERN = re.compile(
    r"^single-agent-execution:v1:execution:[0-9a-f]{64}$",
    re.ASCII,
)
_BRIDGE_ID_PATTERN = re.compile(
    rf"^{re.escape(MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION)}:bridge:[0-9a-f]{{64}}$",
    re.ASCII,
)


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic MCP execution-bridge identity payload."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    """Hash one canonical MCP execution-bridge identity payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _validate_sha256(value: object, *, label: str, expected: str | None = None) -> str:
    """Validate one lowercase SHA-256 field and optional canonical expectation."""
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        raise McpBoundaryValidationError(f"{label} must be lowercase SHA-256")
    if expected is not None and value != expected:
        raise McpBoundaryValidationError(f"{label} must match canonical MCP execution semantics")
    return value


def _validate_identifier(
    value: object,
    *,
    label: str,
    pattern: re.Pattern[str],
) -> str:
    """Validate one exact upstream or MCP execution identifier."""
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise McpBoundaryValidationError(f"{label} violates the MCP execution identity contract")
    return value


def _validate_content_addressed_pair(
    *,
    identifier: str,
    digest: str,
    label: str,
) -> None:
    """Require an identifier suffix to carry its paired content digest."""
    if not identifier.endswith(digest):
        raise McpBoundaryValidationError(f"{label} id and digest must identify the same value")


def _bridge_payload(
    *,
    tool_name: McpToolName,
    capability: AgentCapability,
    action_id: str,
    invocation_id: str,
    invocation_sha256: str,
    admission_id: str,
    admission_sha256: str,
    execution_id: str,
    execution_sha256: str,
    downstream_result_sha256: str,
) -> dict[str, object]:
    """Return canonical semantics for one MCP-admitted capability execution."""
    return {
        "action_id": action_id,
        "admission_id": admission_id,
        "admission_sha256": admission_sha256,
        "capability": capability.value,
        "contract_version": MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION,
        "downstream_result_sha256": downstream_result_sha256,
        "execution_id": execution_id,
        "execution_sha256": execution_sha256,
        "invocation_id": invocation_id,
        "invocation_sha256": invocation_sha256,
        "tool_name": tool_name.value,
    }


@dataclass(frozen=True, slots=True)
class McpCapabilityExecutionBridge:
    """Content-addressed evidence that MCP admission preceded one typed execution."""

    tool_name: McpToolName
    capability: AgentCapability
    action_id: str
    invocation_id: str
    invocation_sha256: str
    admission_id: str
    admission_sha256: str
    execution_id: str
    execution_sha256: str
    downstream_result_sha256: str
    bridge_sha256: str
    bridge_id: str

    def __post_init__(self) -> None:
        """Reject forged or authority-drifting MCP execution evidence."""
        if type(self.tool_name) is not McpToolName:
            raise McpBoundaryValidationError("tool_name must be McpToolName")
        if type(self.capability) is not AgentCapability:
            raise McpBoundaryValidationError("capability must be AgentCapability")
        if capability_for_mcp_tool(self.tool_name) is not self.capability:
            raise McpBoundaryValidationError("MCP execution tool/capability binding is invalid")

        action_id = _validate_identifier(
            self.action_id,
            label="action_id",
            pattern=_ACTION_ID_PATTERN,
        )
        invocation_id = _validate_identifier(
            self.invocation_id,
            label="invocation_id",
            pattern=_INVOCATION_ID_PATTERN,
        )
        invocation_sha256 = _validate_sha256(
            self.invocation_sha256,
            label="invocation_sha256",
        )
        _validate_content_addressed_pair(
            identifier=invocation_id,
            digest=invocation_sha256,
            label="invocation",
        )
        admission_id = _validate_identifier(
            self.admission_id,
            label="admission_id",
            pattern=_ADMISSION_ID_PATTERN,
        )
        admission_sha256 = _validate_sha256(
            self.admission_sha256,
            label="admission_sha256",
        )
        _validate_content_addressed_pair(
            identifier=admission_id,
            digest=admission_sha256,
            label="admission",
        )
        execution_id = _validate_identifier(
            self.execution_id,
            label="execution_id",
            pattern=_EXECUTION_ID_PATTERN,
        )
        execution_sha256 = _validate_sha256(
            self.execution_sha256,
            label="execution_sha256",
        )
        _validate_content_addressed_pair(
            identifier=execution_id,
            digest=execution_sha256,
            label="execution",
        )
        downstream_result_sha256 = _validate_sha256(
            self.downstream_result_sha256,
            label="downstream_result_sha256",
        )

        expected_sha256 = _canonical_sha256(
            _bridge_payload(
                tool_name=self.tool_name,
                capability=self.capability,
                action_id=action_id,
                invocation_id=invocation_id,
                invocation_sha256=invocation_sha256,
                admission_id=admission_id,
                admission_sha256=admission_sha256,
                execution_id=execution_id,
                execution_sha256=execution_sha256,
                downstream_result_sha256=downstream_result_sha256,
            )
        )
        _validate_sha256(
            self.bridge_sha256,
            label="bridge_sha256",
            expected=expected_sha256,
        )
        expected_id = f"{MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION}:bridge:{expected_sha256}"
        if self.bridge_id != expected_id:
            raise McpBoundaryValidationError(
                "bridge_id must match content-addressed MCP execution semantics"
            )
        _validate_identifier(
            self.bridge_id,
            label="bridge_id",
            pattern=_BRIDGE_ID_PATTERN,
        )

    @classmethod
    def create(
        cls,
        *,
        admission: McpToolCallAdmission,
        invocation: AgentCapabilityInvocation,
        execution: AgentCapabilityExecution,
    ) -> "McpCapabilityExecutionBridge":
        """Bind one exact MCP admission to one exact existing typed execution."""
        if type(admission) is not McpToolCallAdmission:
            raise McpBoundaryValidationError("MCP execution bridge requires one admission")
        if type(execution) is not AgentCapabilityExecution:
            raise McpBoundaryValidationError("MCP execution bridge requires one execution")

        capability = capability_for_invocation(invocation)
        action = action_for_invocation(invocation)
        if capability_for_mcp_tool(admission.tool_name) is not capability:
            raise McpBoundaryValidationError("MCP admission capability does not match invocation")
        if admission.capability is not capability:
            raise McpBoundaryValidationError("MCP admission capability identity drifted")
        if admission.action_id != action.action_id:
            raise McpBoundaryValidationError("MCP admission action identity drifted")
        if admission.invocation_id != invocation.invocation_id:
            raise McpBoundaryValidationError("MCP admission invocation identity drifted")
        if admission.invocation_sha256 != invocation.invocation_sha256:
            raise McpBoundaryValidationError("MCP admission invocation digest drifted")
        if execution.action_id != action.action_id:
            raise McpBoundaryValidationError("capability execution action identity drifted")
        if execution.capability is not capability:
            raise McpBoundaryValidationError("capability execution capability identity drifted")
        if execution.invocation_id != invocation.invocation_id:
            raise McpBoundaryValidationError("capability execution invocation identity drifted")

        digest = _canonical_sha256(
            _bridge_payload(
                tool_name=admission.tool_name,
                capability=capability,
                action_id=action.action_id,
                invocation_id=invocation.invocation_id,
                invocation_sha256=invocation.invocation_sha256,
                admission_id=admission.admission_id,
                admission_sha256=admission.admission_sha256,
                execution_id=execution.execution_id,
                execution_sha256=execution.execution_sha256,
                downstream_result_sha256=execution.downstream_result_sha256,
            )
        )
        return cls(
            tool_name=admission.tool_name,
            capability=capability,
            action_id=action.action_id,
            invocation_id=invocation.invocation_id,
            invocation_sha256=invocation.invocation_sha256,
            admission_id=admission.admission_id,
            admission_sha256=admission.admission_sha256,
            execution_id=execution.execution_id,
            execution_sha256=execution.execution_sha256,
            downstream_result_sha256=execution.downstream_result_sha256,
            bridge_sha256=digest,
            bridge_id=f"{MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION}:bridge:{digest}",
        )


__all__ = [
    "MCP_CAPABILITY_EXECUTION_CONTRACT_VERSION",
    "McpCapabilityExecutionBridge",
]
