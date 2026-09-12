"""Offline demonstration composition for the OpsLens V1 reviewer path."""

from opslens.demo.controlled_benign import (
    CONTROLLED_BENIGN_FIXTURE_VERSION,
    CONTROLLED_BENIGN_RESULT_CONTRACT_VERSION,
    CONTROLLED_BENIGN_SCENARIO_ID,
    ControlledBenignDemoResult,
    build_controlled_benign_demo,
)
from opslens.demo.evaluation import (
    DEMO_SUITE_EVALUATION_CONTRACT_VERSION,
    DemoSuiteEvaluation,
    build_demo_suite_evaluation,
)
from opslens.demo.fail_closed import (
    FAIL_CLOSED_FIXTURE_VERSION,
    FAIL_CLOSED_RESULT_CONTRACT_VERSION,
    FAIL_CLOSED_SCENARIO_ID,
    FailClosedDemoResult,
    build_fail_closed_incomplete_evidence_demo,
)
from opslens.demo.material_vulnerability import (
    DEMO_RESULT_CONTRACT_VERSION,
    MATERIAL_VULNERABILITY_FIXTURE_VERSION,
    MATERIAL_VULNERABILITY_SCENARIO_ID,
    DemoContractError,
    DemoRunResult,
    build_material_vulnerability_demo,
)

__all__ = [
    "CONTROLLED_BENIGN_FIXTURE_VERSION",
    "CONTROLLED_BENIGN_RESULT_CONTRACT_VERSION",
    "CONTROLLED_BENIGN_SCENARIO_ID",
    "DEMO_RESULT_CONTRACT_VERSION",
    "DEMO_SUITE_EVALUATION_CONTRACT_VERSION",
    "FAIL_CLOSED_FIXTURE_VERSION",
    "FAIL_CLOSED_RESULT_CONTRACT_VERSION",
    "FAIL_CLOSED_SCENARIO_ID",
    "MATERIAL_VULNERABILITY_FIXTURE_VERSION",
    "MATERIAL_VULNERABILITY_SCENARIO_ID",
    "ControlledBenignDemoResult",
    "DemoContractError",
    "DemoRunResult",
    "DemoSuiteEvaluation",
    "FailClosedDemoResult",
    "build_controlled_benign_demo",
    "build_demo_suite_evaluation",
    "build_fail_closed_incomplete_evidence_demo",
    "build_material_vulnerability_demo",
]
