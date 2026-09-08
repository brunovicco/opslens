"""Application services for bounded OpsLens multi-agent coordination."""

from opslens.multi_agent.application.comparison import (
    evaluate_multi_agent_comparison_dataset,
    load_multi_agent_comparison_dataset,
)
from opslens.multi_agent.application.handoff import admit_multi_agent_handoff
from opslens.multi_agent.application.real_comparison import (
    evaluate_multi_agent_real_comparison_dataset,
    load_multi_agent_real_comparison_dataset,
)
from opslens.multi_agent.application.triage_reasoning import (
    parse_triage_model_output,
    reason_about_triage_task,
)
from opslens.multi_agent.application.two_model_reasoning import run_two_model_reasoning

__all__ = [
    "admit_multi_agent_handoff",
    "evaluate_multi_agent_comparison_dataset",
    "evaluate_multi_agent_real_comparison_dataset",
    "load_multi_agent_comparison_dataset",
    "load_multi_agent_real_comparison_dataset",
    "parse_triage_model_output",
    "reason_about_triage_task",
    "run_two_model_reasoning",
]
