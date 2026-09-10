#!/usr/bin/env python3
"""Verify bounded scheduled-ingestion recovery controls fail closed."""

from __future__ import annotations

import re
from pathlib import Path

DEV_INFRA = Path("infra/environments/dev")
CONTROL_PATH = DEV_INFRA / "operational_recovery.tf"
EXPECTED_SCHEDULES = {
    ("scheduler.tf", "epss_daily"),
    ("kev_scheduler.tf", "kev_daily"),
    ("nvd_incremental_scheduler.tf", "nvd_incremental_hourly"),
}
STATE_REFERENCE = "state = local.scheduled_ingestion_state"
EVENT_AGE_REFERENCE = (
    "maximum_event_age_in_seconds = "
    "local.scheduled_ingestion_maximum_event_age_in_seconds"
)
RETRY_REFERENCE = (
    "maximum_retry_attempts       = "
    "local.scheduled_ingestion_maximum_retry_attempts"
)


class RecoveryInvariantError(RuntimeError):
    """Raised when the retained operational-recovery contract drifts."""


def _extract_block(text: str, marker: str) -> str:
    """Return one balanced HCL block beginning at an exact marker."""
    marker_index = text.find(marker)
    if marker_index < 0:
        raise RecoveryInvariantError(f"missing HCL marker: {marker}")

    opening = text.find("{", marker_index + len(marker))
    if opening < 0:
        raise RecoveryInvariantError(f"missing opening brace after: {marker}")

    depth = 0
    for index in range(opening, len(text)):
        character = text[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[marker_index : index + 1]

    raise RecoveryInvariantError(f"unterminated HCL block: {marker}")


def _discover_schedules() -> set[tuple[str, str]]:
    """Discover every Terraform EventBridge Scheduler schedule in dev."""
    discovered: set[tuple[str, str]] = set()
    pattern = re.compile(r'resource\s+"aws_scheduler_schedule"\s+"([^"]+)"')

    for path in sorted(DEV_INFRA.glob("*.tf")):
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            discovered.add((path.name, match.group(1)))

    return discovered


def _verify_control_contract() -> None:
    """Verify the Terraform control remains explicit and non-disruptive by default."""
    text = CONTROL_PATH.read_text(encoding="utf-8")
    variable_block = _extract_block(
        text,
        'variable "scheduled_ingestion_enabled"',
    )

    if not re.search(r"\bdefault\s*=\s*true\b", variable_block):
        raise RecoveryInvariantError(
            "scheduled_ingestion_enabled must default to true"
        )

    normalized = " ".join(text.split())
    if 'var.scheduled_ingestion_enabled ? "ENABLED" : "DISABLED"' not in normalized:
        raise RecoveryInvariantError(
            "scheduled ingestion state must derive only from the bounded boolean control"
        )

    expected_constants = {
        "scheduled_ingestion_maximum_event_age_in_seconds": 3600,
        "scheduled_ingestion_maximum_retry_attempts": 2,
    }
    for name, value in expected_constants.items():
        if not re.search(rf"\b{re.escape(name)}\s*=\s*{value}\b", text):
            raise RecoveryInvariantError(
                f"scheduled ingestion budget drifted: {name} != {value}"
            )


def _verify_schedule(path_name: str, resource_name: str) -> None:
    """Verify one retained schedule uses the shared pause and retry contracts."""
    path = DEV_INFRA / path_name
    text = path.read_text(encoding="utf-8")
    block = _extract_block(
        text,
        f'resource "aws_scheduler_schedule" "{resource_name}"',
    )

    required = (
        STATE_REFERENCE,
        EVENT_AGE_REFERENCE,
        RETRY_REFERENCE,
    )
    for expression in required:
        if expression not in block:
            raise RecoveryInvariantError(
                f"{path_name}:{resource_name} is missing {expression!r}"
            )

    if re.search(r'\bstate\s*=\s*"(?:ENABLED|DISABLED)"', block):
        raise RecoveryInvariantError(
            f"{path_name}:{resource_name} hard-codes Scheduler state"
        )


def main() -> int:
    """Validate the exact retained Gate 17.6 recovery surface."""
    if not CONTROL_PATH.is_file():
        raise RecoveryInvariantError(f"missing recovery control: {CONTROL_PATH}")

    discovered = _discover_schedules()
    if discovered != EXPECTED_SCHEDULES:
        missing = sorted(EXPECTED_SCHEDULES - discovered)
        unexpected = sorted(discovered - EXPECTED_SCHEDULES)
        raise RecoveryInvariantError(
            "EventBridge Scheduler surface drifted; "
            f"missing={missing}, unexpected={unexpected}"
        )

    _verify_control_contract()
    for path_name, resource_name in sorted(EXPECTED_SCHEDULES):
        _verify_schedule(path_name, resource_name)

    print(
        "operational_recovery_invariants=PASS "
        "schedules=3 max_retries=2 max_event_age_seconds=3600"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
