"""Protocol adapters for bounded A2A interoperability."""

from opslens.a2a_boundary.adapters._contract import (
    A2A_JSONRPC_VERSION,
    A2A_PROTOCOL_BINDING,
    A2A_PROTOCOL_RELEASE,
    A2A_PROTOCOL_VERSION,
    A2A_SEND_MESSAGE_METHOD,
    A2AOfflineExchange,
    A2AOfflineExchangeEvidence,
    A2AReferenceResult,
    A2AResponseKind,
)
from opslens.a2a_boundary.adapters.agent_card import admit_agent_card, build_agent_card
from opslens.a2a_boundary.adapters.jsonrpc import (
    admit_send_message_response,
    build_send_message_request,
    parse_send_message_request,
)
from opslens.a2a_boundary.adapters.offline import (
    OfflineA2AReferencePeer,
    evidence_as_dict,
    run_offline_exchange,
)

__all__ = [
    "A2A_JSONRPC_VERSION",
    "A2A_PROTOCOL_BINDING",
    "A2A_PROTOCOL_RELEASE",
    "A2A_PROTOCOL_VERSION",
    "A2A_SEND_MESSAGE_METHOD",
    "A2AOfflineExchange",
    "A2AOfflineExchangeEvidence",
    "A2AReferenceResult",
    "A2AResponseKind",
    "OfflineA2AReferencePeer",
    "admit_agent_card",
    "admit_send_message_response",
    "build_agent_card",
    "build_send_message_request",
    "evidence_as_dict",
    "parse_send_message_request",
    "run_offline_exchange",
]
