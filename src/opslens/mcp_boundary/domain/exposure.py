"""Provider-neutral MCP capability exposure and admission evidence."""

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

from opslens.agent_baseline.domain.models import AgentCapability
from opslens.mcp_boundary.domain.errors import McpBoundaryValidationError
from opslens.shared.evidence import canonical_json

MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION = "mcp-capability-exposure:v1"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_ACTION_ID_PATTERN = re.compile(r"^single-agent-authority:v1:action:[0-9a-f]{64}$", re.ASCII)
_INVOCATION_ID_PATTERN = re.compile(
    r"^single-agent-execution:v1:invocation:[0-9a-f]{64}$",
    re.ASCII,
)
_EXPOSURE_ID_PATTERN = re.compile(
    rf"^{re.escape(MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION)}:exposure:[0-9a-f]{{64}}$",
    re.ASCII,
)
_ADMISSION_ID_PATTERN = re.compile(
    rf"^{re.escape(MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION)}:admission:[0-9a-f]{{64}}$",
    re.ASCII,
)


class McpToolName(StrEnum):
    """Closed MCP tool identities for already-bounded OpsLens capabilities."""

    STRUCTURED_SECURITY_QUERY = "opslens.structured_security_query"
    KNOWLEDGE_GUIDANCE = "opslens.knowledge_guidance"
    HYBRID_SECURITY_ANSWER = "opslens.hybrid_security_answer"
    PUBLIC_REPOSITORY_ANALYSIS = "opslens.public_repository_analysis"


_TOOL_TO_CAPABILITY: dict[McpToolName, AgentCapability] = {
    McpToolName.STRUCTURED_SECURITY_QUERY: AgentCapability.STRUCTURED_SECURITY_QUERY,
    McpToolName.KNOWLEDGE_GUIDANCE: AgentCapability.KNOWLEDGE_GUIDANCE,
    McpToolName.HYBRID_SECURITY_ANSWER: AgentCapability.HYBRID_SECURITY_ANSWER,
    McpToolName.PUBLIC_REPOSITORY_ANALYSIS: AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
}
_CAPABILITY_TO_TOOL: dict[AgentCapability, McpToolName] = {
    capability: tool_name for tool_name, capability in _TOOL_TO_CAPABILITY.items()
}


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic MCP identity payload."""
    return canonical_json(value)


def _canonical_sha256(value: object) -> str:
    """Hash one canonical MCP identity payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _validate_sha256(value: object, *, label: str, expected: str | None = None) -> str:
    """Validate one lowercase SHA-256 field and optional canonical expectation."""
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        raise McpBoundaryValidationError(f"{label} must be lowercase SHA-256")
    if expected is not None and value != expected:
        raise McpBoundaryValidationError(f"{label} must match canonical MCP semantics")
    return value


def _validate_identifier(
    value: object,
    *,
    label: str,
    pattern: re.Pattern[str],
) -> str:
    """Validate one exact upstream or MCP content-addressed identifier."""
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise McpBoundaryValidationError(f"{label} violates the MCP identity contract")
    return value


def parse_mcp_tool_name(value: object) -> McpToolName:
    """Parse one transport-visible tool name through the closed v1 enum."""
    if type(value) is not str:
        raise McpBoundaryValidationError("MCP tool name must be a string")
    try:
        return McpToolName(value)
    except ValueError as exc:
        raise McpBoundaryValidationError("unknown MCP tool name") from exc


def capability_for_mcp_tool(tool_name: McpToolName) -> AgentCapability:
    """Resolve one closed MCP tool to its existing deterministic capability identity."""
    if type(tool_name) is not McpToolName:
        raise McpBoundaryValidationError("tool_name must be McpToolName")
    try:
        return _TOOL_TO_CAPABILITY[tool_name]
    except KeyError as exc:
        raise McpBoundaryValidationError("MCP tool has no capability binding") from exc


def mcp_tool_for_capability(capability: AgentCapability) -> McpToolName:
    """Resolve one existing capability to its exact closed MCP tool identity."""
    if type(capability) is not AgentCapability:
        raise McpBoundaryValidationError("capability must be AgentCapability")
    try:
        return _CAPABILITY_TO_TOOL[capability]
    except KeyError as exc:
        raise McpBoundaryValidationError("capability has no MCP tool binding") from exc


def _exposure_payload(
    *,
    tool_name: McpToolName,
    capability: AgentCapability,
) -> dict[str, object]:
    """Return canonical semantics for one MCP capability exposure."""
    return {
        "capability": capability.value,
        "contract_version": MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION,
        "tool_name": tool_name.value,
    }


@dataclass(frozen=True, slots=True)
class McpCapabilityExposure:
    """Content-addressed one-to-one MCP tool to capability exposure evidence."""

    tool_name: McpToolName
    capability: AgentCapability
    exposure_sha256: str
    exposure_id: str

    def __post_init__(self) -> None:
        """Reject dynamic, mismatched, or forged exposure identities."""
        if type(self.tool_name) is not McpToolName:
            raise McpBoundaryValidationError("tool_name must be McpToolName")
        if type(self.capability) is not AgentCapability:
            raise McpBoundaryValidationError("capability must be AgentCapability")
        expected_capability = capability_for_mcp_tool(self.tool_name)
        if self.capability is not expected_capability:
            raise McpBoundaryValidationError("MCP tool capability binding is not code-owned")

        expected_sha256 = _canonical_sha256(
            _exposure_payload(tool_name=self.tool_name, capability=self.capability)
        )
        _validate_sha256(
            self.exposure_sha256,
            label="exposure_sha256",
            expected=expected_sha256,
        )
        expected_id = (
            f"{MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION}:exposure:{expected_sha256}"
        )
        if self.exposure_id != expected_id:
            raise McpBoundaryValidationError(
                "exposure_id must match content-addressed MCP exposure semantics"
            )
        _validate_identifier(
            self.exposure_id,
            label="exposure_id",
            pattern=_EXPOSURE_ID_PATTERN,
        )

    @classmethod
    def create(
        cls,
        *,
        tool_name: McpToolName,
        capability: AgentCapability,
    ) -> "McpCapabilityExposure":
        """Create one deterministic code-owned MCP exposure."""
        if type(tool_name) is not McpToolName:
            raise McpBoundaryValidationError("tool_name must be McpToolName")
        if type(capability) is not AgentCapability:
            raise McpBoundaryValidationError("capability must be AgentCapability")
        if capability_for_mcp_tool(tool_name) is not capability:
            raise McpBoundaryValidationError("MCP tool capability binding is not code-owned")
        digest = _canonical_sha256(
            _exposure_payload(tool_name=tool_name, capability=capability)
        )
        return cls(
            tool_name=tool_name,
            capability=capability,
            exposure_sha256=digest,
            exposure_id=(
                f"{MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION}:exposure:{digest}"
            ),
        )


def list_mcp_capability_exposures() -> tuple[McpCapabilityExposure, ...]:
    """Return the complete deterministic v1 exposure catalog in canonical tool order."""
    return tuple(
        McpCapabilityExposure.create(
            tool_name=tool_name,
            capability=capability_for_mcp_tool(tool_name),
        )
        for tool_name in sorted(McpToolName, key=lambda item: item.value)
    )


def _admission_payload(
    *,
    tool_name: McpToolName,
    capability: AgentCapability,
    action_id: str,
    invocation_id: str,
    invocation_sha256: str,
) -> dict[str, object]:
    """Return canonical semantics for one MCP invocation-reference admission."""
    return {
        "action_id": action_id,
        "capability": capability.value,
        "contract_version": MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION,
        "invocation_id": invocation_id,
        "invocation_sha256": invocation_sha256,
        "tool_name": tool_name.value,
    }


@dataclass(frozen=True, slots=True)
class McpToolCallAdmission:
    """Evidence that one MCP tool references one already-authorized typed invocation."""

    tool_name: McpToolName
    capability: AgentCapability
    action_id: str
    invocation_id: str
    invocation_sha256: str
    admission_sha256: str
    admission_id: str

    def __post_init__(self) -> None:
        """Reject capability broadening, forged upstream identity, or forged admission."""
        if type(self.tool_name) is not McpToolName:
            raise McpBoundaryValidationError("tool_name must be McpToolName")
        if type(self.capability) is not AgentCapability:
            raise McpBoundaryValidationError("capability must be AgentCapability")
        if capability_for_mcp_tool(self.tool_name) is not self.capability:
            raise McpBoundaryValidationError("MCP tool capability does not match exposure policy")
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
        expected_sha256 = _canonical_sha256(
            _admission_payload(
                tool_name=self.tool_name,
                capability=self.capability,
                action_id=action_id,
                invocation_id=invocation_id,
                invocation_sha256=invocation_sha256,
            )
        )
        _validate_sha256(
            self.admission_sha256,
            label="admission_sha256",
            expected=expected_sha256,
        )
        expected_id = (
            f"{MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION}:admission:{expected_sha256}"
        )
        if self.admission_id != expected_id:
            raise McpBoundaryValidationError(
                "admission_id must match content-addressed MCP admission semantics"
            )
        _validate_identifier(
            self.admission_id,
            label="admission_id",
            pattern=_ADMISSION_ID_PATTERN,
        )

    @classmethod
    def create(
        cls,
        *,
        tool_name: McpToolName,
        capability: AgentCapability,
        action_id: str,
        invocation_id: str,
        invocation_sha256: str,
    ) -> "McpToolCallAdmission":
        """Create deterministic admission for an already-authorized typed invocation."""
        if type(tool_name) is not McpToolName:
            raise McpBoundaryValidationError("tool_name must be McpToolName")
        if type(capability) is not AgentCapability:
            raise McpBoundaryValidationError("capability must be AgentCapability")
        if capability_for_mcp_tool(tool_name) is not capability:
            raise McpBoundaryValidationError("MCP tool capability does not match exposure policy")
        normalized_action_id = _validate_identifier(
            action_id,
            label="action_id",
            pattern=_ACTION_ID_PATTERN,
        )
        normalized_invocation_id = _validate_identifier(
            invocation_id,
            label="invocation_id",
            pattern=_INVOCATION_ID_PATTERN,
        )
        normalized_invocation_sha256 = _validate_sha256(
            invocation_sha256,
            label="invocation_sha256",
        )
        digest = _canonical_sha256(
            _admission_payload(
                tool_name=tool_name,
                capability=capability,
                action_id=normalized_action_id,
                invocation_id=normalized_invocation_id,
                invocation_sha256=normalized_invocation_sha256,
            )
        )
        return cls(
            tool_name=tool_name,
            capability=capability,
            action_id=normalized_action_id,
            invocation_id=normalized_invocation_id,
            invocation_sha256=normalized_invocation_sha256,
            admission_sha256=digest,
            admission_id=f"{MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION}:admission:{digest}",
        )


__all__ = [
    "MCP_CAPABILITY_EXPOSURE_CONTRACT_VERSION",
    "McpCapabilityExposure",
    "McpToolCallAdmission",
    "McpToolName",
    "capability_for_mcp_tool",
    "list_mcp_capability_exposures",
    "mcp_tool_for_capability",
    "parse_mcp_tool_name",
]
