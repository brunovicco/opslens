"""Tests that freeze the Gate 15.2 protocol fixture independently from implementation code."""

import json
from pathlib import Path
from typing import cast

from opslens.a2a_boundary.adapters import (
    A2A_JSONRPC_VERSION,
    A2A_PROTOCOL_BINDING,
    A2A_PROTOCOL_RELEASE,
    A2A_PROTOCOL_VERSION,
    A2A_SEND_MESSAGE_METHOD,
)
from opslens.a2a_boundary.domain.reference import (
    A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION,
)

_FIXTURE = Path("tests/fixtures/a2a/protocol-contract-v1.json")


def test_protocol_fixture_matches_frozen_gate_15_2_contract() -> None:
    """Exercise the frozen A2A boundary behavior."""
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    if type(raw) is not dict:
        raise AssertionError("A2A protocol fixture must be an object")
    fixture = cast(dict[str, object], raw)

    assert fixture["contract_version"] == A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION
    assert fixture["a2a_release"] == A2A_PROTOCOL_RELEASE
    assert fixture["a2a_protocol_version"] == A2A_PROTOCOL_VERSION
    assert fixture["protocol_binding"] == A2A_PROTOCOL_BINDING
    assert fixture["jsonrpc_version"] == A2A_JSONRPC_VERSION
    assert fixture["send_message_method"] == A2A_SEND_MESSAGE_METHOD
    assert fixture["terminal_success_state"] == "TASK_STATE_COMPLETED"
    assert fixture["model_invocations"] == 0
    assert fixture["capability_executions"] == 0
    assert fixture["aws_resources"] == 0
    assert fixture["new_iam_roles_or_policies"] == 0
