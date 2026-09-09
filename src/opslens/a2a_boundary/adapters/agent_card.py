"""Minimal A2A 1.0 Agent Card projection and strict admission."""

from __future__ import annotations

from typing import cast

from opslens.a2a_boundary.adapters._contract import (
    A2A_PROTOCOL_BINDING,
    A2A_PROTOCOL_VERSION,
    AGENT_CARD_URL,
    AGENT_CARD_VERSION,
    canonical_json_bytes,
    expect_object,
    load_raw_json,
)
from opslens.a2a_boundary.domain.errors import A2ABoundaryValidationError


def _agent_card_object() -> dict[str, object]:
    """Build the exact minimal A2A 1.0 Agent Card object for the offline peer."""
    return {
        "name": "OpsLens Reference Peer",
        "description": "Offline reference-only A2A interoperability peer.",
        "supportedInterfaces": [
            {
                "url": AGENT_CARD_URL,
                "protocolBinding": A2A_PROTOCOL_BINDING,
                "protocolVersion": A2A_PROTOCOL_VERSION,
            }
        ],
        "version": AGENT_CARD_VERSION,
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "extendedAgentCard": False,
        },
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": "opslens.reference.resolve",
                "name": "Resolve OpsLens Reference",
                "description": "Resolve one pre-admitted specialist-task reference.",
                "tags": ["opslens", "reference"],
            }
        ],
    }


def build_agent_card() -> bytes:
    """Build the canonical raw Agent Card used by the offline reference peer."""
    return canonical_json_bytes(_agent_card_object())


def admit_agent_card(*, raw: bytes) -> dict[str, object]:
    """Admit only the exact Agent Card binding/version selected for Gate 15.2."""
    card = expect_object(
        load_raw_json(raw),
        label="Agent Card",
        exact_keys=frozenset(
            {
                "name",
                "description",
                "supportedInterfaces",
                "version",
                "capabilities",
                "defaultInputModes",
                "defaultOutputModes",
                "skills",
            }
        ),
    )
    if card["name"] != "OpsLens Reference Peer":
        raise A2ABoundaryValidationError("Agent Card name is not the bounded peer")
    if card["description"] != "Offline reference-only A2A interoperability peer.":
        raise A2ABoundaryValidationError("Agent Card description is not the bounded peer")
    if card["version"] != AGENT_CARD_VERSION:
        raise A2ABoundaryValidationError("unsupported OpsLens A2A peer version")

    interfaces_value = card["supportedInterfaces"]
    if type(interfaces_value) is not list:
        raise A2ABoundaryValidationError("supportedInterfaces must be a list")
    interfaces = cast(list[object], interfaces_value)
    if len(interfaces) != 1:
        raise A2ABoundaryValidationError(
            "Gate 15.2 requires exactly one supported AgentInterface"
        )
    interface = expect_object(
        interfaces[0],
        label="AgentInterface",
        exact_keys=frozenset({"url", "protocolBinding", "protocolVersion"}),
    )
    if interface["url"] != AGENT_CARD_URL:
        raise A2ABoundaryValidationError("AgentInterface URL is outside the offline profile")
    if interface["protocolBinding"] != A2A_PROTOCOL_BINDING:
        raise A2ABoundaryValidationError("unsupported A2A protocol binding")
    if interface["protocolVersion"] != A2A_PROTOCOL_VERSION:
        raise A2ABoundaryValidationError("unsupported A2A protocol version")

    capabilities = expect_object(
        card["capabilities"],
        label="AgentCapabilities",
        exact_keys=frozenset({"streaming", "pushNotifications", "extendedAgentCard"}),
    )
    if capabilities != {
        "streaming": False,
        "pushNotifications": False,
        "extendedAgentCard": False,
    }:
        raise A2ABoundaryValidationError("optional A2A capabilities are not allowed")

    for field in ("defaultInputModes", "defaultOutputModes"):
        value = card[field]
        if type(value) is not list or cast(list[object], value) != ["application/json"]:
            raise A2ABoundaryValidationError(f"{field} violates the bounded media profile")

    skills_value = card["skills"]
    if type(skills_value) is not list:
        raise A2ABoundaryValidationError("skills must be a list")
    skills = cast(list[object], skills_value)
    if len(skills) != 1:
        raise A2ABoundaryValidationError("Gate 15.2 requires exactly one reference skill")
    skill = expect_object(
        skills[0],
        label="AgentSkill",
        exact_keys=frozenset({"id", "name", "description", "tags"}),
    )
    if skill != {
        "id": "opslens.reference.resolve",
        "name": "Resolve OpsLens Reference",
        "description": "Resolve one pre-admitted specialist-task reference.",
        "tags": ["opslens", "reference"],
    }:
        raise A2ABoundaryValidationError("AgentSkill exceeds the reference-only profile")
    return card


__all__ = ["admit_agent_card", "build_agent_card"]
