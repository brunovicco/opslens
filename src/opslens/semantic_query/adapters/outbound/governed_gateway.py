"""Governed LLM Gateway transport for the bounded semantic-query planner."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from governed_llm_gateway_client import (
    GatewayClient,
    GatewayClientConfig,
    GatewayClientError,
    GatewayHTTPError,
)
from governed_llm_gateway_contracts import (
    DataClassification,
    ExecutionStatus,
    Message,
    MessageRole,
    RiskLevel,
    StructuredOutputSchema,
    WorkloadRequirements,
)

from opslens.semantic_query.planner.models import PlannerOutcome, SemanticPlannerRequest
from opslens.semantic_query.planner.parser import parse_planner_json
from opslens.semantic_query.planner.prompt import PLANNER_MAX_TOKENS, PLANNER_SYSTEM_PROMPT
from opslens.semantic_query.planner.schema import PLANNER_OUTPUT_SCHEMA, PLANNER_SCHEMA_NAME


class SemanticPlannerUnavailableError(RuntimeError):
    """Raised when governed model execution cannot produce a planner proposal."""


@dataclass(frozen=True, slots=True)
class GovernedGatewayPlannerConfig:
    """Explicit gateway configuration for the bounded OpsLens planner."""

    base_url: str
    api_key: str
    workload: str = "opslens.semantic-query.plan"
    risk_level: RiskLevel = RiskLevel.LOW
    data_classification: DataClassification = DataClassification.PUBLIC
    timeout_seconds: float = 10.0


class GovernedGatewaySemanticPlanner:
    """Request a typed proposal while leaving query authority deterministic."""

    def __init__(self, config: GovernedGatewayPlannerConfig) -> None:
        """Store provider-neutral gateway configuration only."""
        self._config = config

    def plan(self, request: SemanticPlannerRequest) -> PlannerOutcome:
        """Return only a proposal that survives the existing deterministic parser."""
        if type(request) is not SemanticPlannerRequest:
            raise TypeError("request must be SemanticPlannerRequest.")
        return asyncio.run(self._plan(request))

    async def _plan(self, request: SemanticPlannerRequest) -> PlannerOutcome:
        client_config = GatewayClientConfig(
            base_url=self._config.base_url,
            api_key=self._config.api_key,
            request_timeout_seconds=self._config.timeout_seconds,
        )
        try:
            async with GatewayClient(client_config) as client:
                response = await client.generate(
                    workload=self._config.workload,
                    messages=(
                        Message(role=MessageRole.SYSTEM, content=PLANNER_SYSTEM_PROMPT),
                        Message(role=MessageRole.USER, content=request.question),
                    ),
                    risk_level=self._config.risk_level,
                    data_classification=self._config.data_classification,
                    requirements=WorkloadRequirements(structured_output=True),
                    structured_output=StructuredOutputSchema(
                        name=PLANNER_SCHEMA_NAME,
                        schema=PLANNER_OUTPUT_SCHEMA,
                    ),
                    max_output_tokens=PLANNER_MAX_TOKENS,
                    provider_timeout_seconds=self._config.timeout_seconds,
                )
        except GatewayHTTPError as exc:
            raise SemanticPlannerUnavailableError(
                f"Governed gateway rejected planner request: {exc.code}"
            ) from None
        except GatewayClientError as exc:
            raise SemanticPlannerUnavailableError(
                f"Governed gateway planner request failed: {type(exc).__name__}"
            ) from None

        if response.status is not ExecutionStatus.SUCCEEDED:
            raise SemanticPlannerUnavailableError(
                "Governed gateway planner execution did not succeed"
            )
        if response.content is None or not response.content.strip():
            raise SemanticPlannerUnavailableError("Governed gateway planner returned no content")

        return parse_planner_json(response.content)
