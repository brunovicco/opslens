"""Offline A2A peer/replay guard and local exchange evidence."""

from dataclasses import asdict
from time import perf_counter_ns
from typing import cast

from opslens.a2a_boundary.adapters._contract import (
    A2A_PROTOCOL_BINDING,
    A2A_PROTOCOL_VERSION,
    A2AOfflineExchange,
    A2AOfflineExchangeEvidence,
    A2AResponseKind,
)
from opslens.a2a_boundary.adapters.agent_card import admit_agent_card, build_agent_card
from opslens.a2a_boundary.adapters.jsonrpc import (
    admit_send_message_response,
    build_message_response,
    build_send_message_request,
    build_task_response,
    parse_send_message_request,
)
from opslens.a2a_boundary.application.registry import A2AReferenceRegistry
from opslens.a2a_boundary.domain.errors import (
    A2ABoundaryValidationError,
    A2AReplayError,
)
from opslens.a2a_boundary.domain.reference import A2AReference


class OfflineA2AReferencePeer:
    """Local peer that resolves only registered references and rejects replay."""

    def __init__(self, *, registry: A2AReferenceRegistry) -> None:
        """Initialize one peer around code-owned admitted specialist state."""
        if type(registry) is not A2AReferenceRegistry:
            raise A2ABoundaryValidationError("registry must be A2AReferenceRegistry")
        self._registry = registry
        self._request_ids: set[str] = set()
        self._message_ids: set[str] = set()

    def handle(
        self,
        *,
        raw: bytes,
        response_kind: A2AResponseKind,
    ) -> tuple[bytes, float]:
        """Handle one local request with zero model or capability execution."""
        if type(response_kind) is not A2AResponseKind:
            raise A2ABoundaryValidationError("response_kind must be A2AResponseKind")
        started_ns = perf_counter_ns()
        request = parse_send_message_request(raw=raw)
        if request.request_id in self._request_ids:
            raise A2AReplayError("duplicate JSON-RPC request id is not allowed")
        if request.message_id in self._message_ids:
            raise A2AReplayError("duplicate A2A messageId is not allowed")

        self._registry.resolve(reference=request.reference)
        self._request_ids.add(request.request_id)
        self._message_ids.add(request.message_id)
        response = (
            build_message_response(request=request)
            if response_kind is A2AResponseKind.MESSAGE
            else build_task_response(request=request)
        )
        elapsed_ms = (perf_counter_ns() - started_ns) / 1_000_000
        return response, elapsed_ms


def run_offline_exchange(
    *,
    peer: OfflineA2AReferencePeer,
    reference: A2AReference,
    response_kind: A2AResponseKind,
) -> A2AOfflineExchange:
    """Run one local request/response exchange and record independent evidence."""
    if type(peer) is not OfflineA2AReferencePeer:
        raise A2ABoundaryValidationError("peer must be OfflineA2AReferencePeer")
    admit_agent_card(raw=build_agent_card())
    request = build_send_message_request(reference=reference)
    started_ns = perf_counter_ns()
    response, handler_elapsed_ms = peer.handle(raw=request, response_kind=response_kind)
    result = admit_send_message_response(raw=response, reference=reference)
    client_elapsed_ms = (perf_counter_ns() - started_ns) / 1_000_000
    evidence = A2AOfflineExchangeEvidence(
        protocol_request_count=1,
        peer_handler_count=1,
        request_bytes=len(request),
        response_bytes=len(response),
        client_elapsed_ms=client_elapsed_ms,
        handler_elapsed_ms=handler_elapsed_ms,
        retry_count=0,
        failure_class=None,
        reference_admission_outcome="ADMITTED",
        protocol_outcome=result.outcome.value,
        protocol_binding=A2A_PROTOCOL_BINDING,
        protocol_version=A2A_PROTOCOL_VERSION,
        model_invocations=0,
        capability_executions=0,
        incremental_aws_cost_usd=0.0,
    )
    return A2AOfflineExchange(result=result, evidence=evidence)


def evidence_as_dict(evidence: A2AOfflineExchangeEvidence) -> dict[str, object]:
    """Project offline evidence into a JSON-ready dictionary."""
    if type(evidence) is not A2AOfflineExchangeEvidence:
        raise A2ABoundaryValidationError("evidence must be A2AOfflineExchangeEvidence")
    return cast(dict[str, object], asdict(evidence))


__all__ = [
    "OfflineA2AReferencePeer",
    "evidence_as_dict",
    "run_offline_exchange",
]
