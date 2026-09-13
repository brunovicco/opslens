"""Run the bounded offline A2A 1.0 reference-only interoperability experiment."""

import json
from dataclasses import asdict

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.a2a_boundary.adapters import (  # noqa: E402
    A2A_PROTOCOL_BINDING,
    A2A_PROTOCOL_RELEASE,
    A2A_PROTOCOL_VERSION,
    A2AResponseKind,
    OfflineA2AReferencePeer,
    build_agent_card,
    run_offline_exchange,
)
from opslens.a2a_boundary.application.registry import A2AReferenceRegistry  # noqa: E402
from opslens.agent_baseline.domain.models import (  # noqa: E402
    AgentCapability,
    create_single_agent_task,
)
from opslens.multi_agent.application.handoff import admit_multi_agent_handoff  # noqa: E402
from opslens.multi_agent.domain.handoff import (  # noqa: E402
    AgentSpecialization,
    MultiAgentHandoffDecision,
    SpecialistAgentTask,
    create_multi_agent_handoff_proposal,
    create_triage_agent_task,
)


def _specialist_task() -> SpecialistAgentTask:
    """Create one already-admitted specialist task without invoking a model."""
    source_task = create_single_agent_task(
        text="Which admitted security capability should analyze this evidence?",
        allowed_capabilities=(
            AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
            AgentCapability.STRUCTURED_SECURITY_QUERY,
        ),
    )
    proposal = create_multi_agent_handoff_proposal(
        source_task_id=source_task.task_id,
        decision=MultiAgentHandoffDecision.HANDOFF,
        target_specialization=AgentSpecialization.EVIDENCE_ANALYSIS,
    )
    admitted = admit_multi_agent_handoff(
        source=create_triage_agent_task(task=source_task),
        proposal=proposal,
    )
    if not isinstance(admitted, SpecialistAgentTask):
        raise RuntimeError("offline A2A experiment requires one admitted specialist task")
    return admitted


def _run(response_kind: A2AResponseKind) -> dict[str, object]:
    """Run one response form with a fresh replay guard."""
    specialist = _specialist_task()
    registry = A2AReferenceRegistry()
    reference = registry.register(specialist_task=specialist)
    peer = OfflineA2AReferencePeer(registry=registry)
    exchange = run_offline_exchange(
        peer=peer,
        reference=reference,
        response_kind=response_kind,
    )
    return {
        "response_kind": response_kind.value,
        "reference_id": reference.reference_id,
        "reference_sha256": reference.reference_sha256,
        "handoff_id": reference.handoff_id,
        "specialist_task_id": reference.specialist_task_id,
        "result": asdict(exchange.result),
        "evidence": asdict(exchange.evidence),
    }


def main() -> None:
    """Emit machine-readable local interoperability evidence."""
    runs = [_run(A2AResponseKind.MESSAGE), _run(A2AResponseKind.TASK)]
    payload = {
        "contract": "a2a-reference-interoperability:v1",
        "a2a_release": A2A_PROTOCOL_RELEASE,
        "protocol_version": A2A_PROTOCOL_VERSION,
        "protocol_binding": A2A_PROTOCOL_BINDING,
        "agent_card_bytes": len(build_agent_card()),
        "runs": runs,
        "aggregate": {
            "protocol_request_count": 2,
            "peer_handler_count": 2,
            "retry_count": 0,
            "model_invocations": 0,
            "capability_executions": 0,
            "new_aws_resources": 0,
            "new_iam_roles_or_policies": 0,
            "incremental_aws_cost_usd": 0.0,
        },
    }
    print(
        json.dumps(
            payload,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
