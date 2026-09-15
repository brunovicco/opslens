#!/usr/bin/env python3
"""Load the GHSA advisory corpus by orchestrating the two lambdas that already exist.

The correlation index probe found the GHSA half of the threat authority holds two
PyPI advisories. Nothing is broken: `ghsa_lambda.tf` says so in its own comments —
"Phase 2.4C proves synchronous manual invocation first" — and the GHSA milestone
closed on a single-CVE cross-source attribution proof. The pipeline was built and
proven; the corpus was never loaded, because loading it was never a V1 requirement.

```text
pipeline built != corpus loaded
contract proof != source coverage
```

Both lambdas take an explicit versioned envelope, and that is a design choice rather
than a missing trigger. EPSS, KEV and NVD promote Bronze to Silver through S3
notifications; GHSA Silver instead requires an exact manifest coordinate, so an
object cannot be promoted by accident. The two contracts compose directly — Bronze
returns, per leaf window, the precise pair Silver demands:

    Bronze  {schema_version, mode, start_at, end_at}
         -> leaves[] each carrying {manifest_key, manifest_version_id}
    Silver  {schema_version, manifest_key, manifest_version_id}

So orchestration from an operator script is the intended path, not a workaround, and
this script adds no infrastructure and changes no contract.

`GhsaSyncWindow.MAX_SPAN` is 31 days, so a historical load is many bounded windows
rather than one long scrape. Its `filter_expression` is a closed range, so the windows
are cut one second apart rather than abutting: otherwise both sides of a boundary
would claim an advisory published exactly on it.

Any window can fail on a GitHub rate limit, so the run
keeps a ledger: every window that completed is recorded by its own `sync_id`, and a
re-run skips it. Resuming is the normal case, not the exception.

The default is `--dry-run`: the window plan prints and nothing is invoked. Real
invocation requires `--apply`, because this one writes to S3 through a live Lambda
and spends GitHub rate limit.

```text
READ AND WRITE through the existing lambdas only.
Creates no table, no trigger, no infrastructure.
```
"""

import argparse
import json
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final, Protocol, cast

from _bootstrap import ensure_repository_src_on_path
from boto3.session import Session

ensure_repository_src_on_path()

from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow  # noqa: E402
from opslens.shared.evidence import canonical_json, canonical_sha256  # noqa: E402

GHSA_CORPUS_BACKFILL_CONTRACT_VERSION: Final = "opslens-ghsa-corpus-backfill:v1"

_DEFAULT_REGION: Final = "us-east-1"
_DEFAULT_BRONZE_FUNCTION: Final = "opslens-dev-ghsa-bronze"
_DEFAULT_SILVER_FUNCTION: Final = "opslens-dev-ghsa-silver"
_DEFAULT_LEDGER: Final = ".tmp/ghsa-backfill-ledger.json"
# One day under the domain's own 31-day ceiling, so a window can never be rejected
# by rounding at a month boundary.
_WINDOW_DAYS: Final = 30
_DEFAULT_PAUSE_SECONDS: Final = 2.0
_INVOCATION_SCHEMA_VERSION: Final = 1


class BackfillError(RuntimeError):
    """Raised when the backfill cannot proceed without inventing a result."""


class _PayloadStream(Protocol):
    """The streaming body a Lambda response carries."""

    def read(self) -> bytes:
        """Read the whole payload."""
        ...


class _LambdaClient(Protocol):
    """Only the Lambda operation this orchestrator needs."""

    def invoke(
        self,
        *,
        FunctionName: str,
        InvocationType: str,
        Payload: bytes,
    ) -> Mapping[str, object]:
        """Invoke one function synchronously."""
        ...


@dataclass(frozen=True, slots=True)
class WindowPlan:
    """One bounded synchronization window to request.

    Attributes:
        window: The typed domain window, validated by the same rules the lambda uses.
        sync_id: The window's own content-addressed identity, used as the ledger key.
    """

    window: GhsaSyncWindow
    sync_id: str


@dataclass(frozen=True, slots=True)
class WindowOutcome:
    """What one window produced, Bronze and Silver together.

    Attributes:
        sync_id: The requested window's identity.
        start_at: Canonical window start.
        end_at: Canonical window end.
        leaf_count: Leaf windows the Bronze runtime split this window into.
        total_items: Advisories retrieved across those leaves.
        promoted: Leaf manifests successfully promoted to Silver.
        silver_keys: The Silver completion keys, in leaf order.
    """

    sync_id: str
    start_at: str
    end_at: str
    leaf_count: int
    total_items: int
    promoted: int
    silver_keys: tuple[str, ...]


def _plan_windows(start: datetime, end: datetime, mode: GhsaSyncMode) -> tuple[WindowPlan, ...]:
    """Split a date range into windows the domain will accept.

    Args:
        start: Inclusive UTC start.
        end: Exclusive UTC end.
        mode: Synchronization mode the lambda will filter by.

    Returns:
        Windows covering the range, oldest first.

    Raises:
        BackfillError: If the range is empty or inverted.
    """
    if end <= start:
        raise BackfillError("the backfill range must end after it starts")

    plans: list[WindowPlan] = []
    cursor = start
    while cursor < end:
        boundary = min(cursor + timedelta(days=_WINDOW_DAYS), end)
        window = GhsaSyncWindow(mode=mode, start_at=cursor, end_at=boundary)
        plans.append(WindowPlan(window=window, sync_id=window.sync_id))
        # GhsaSyncWindow.filter_expression is a CLOSED GitHub search range, so
        # abutting windows would both claim an advisory published exactly on the
        # boundary second. The domain works at second precision, so one second is
        # the smallest gap that makes the cover disjoint.
        cursor = boundary + timedelta(seconds=1)
    return tuple(plans)


def _invoke(
    client: _LambdaClient,
    function: str,
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    """Invoke one lambda synchronously and refuse to read a failed response as success.

    Args:
        client: The Lambda client.
        function: Function name to invoke.
        payload: The explicit invocation envelope.

    Returns:
        The decoded response payload.

    Raises:
        BackfillError: If the invocation fails, the function errors, or the response
            is not a JSON object.
    """
    try:
        response = client.invoke(
            FunctionName=function,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
    except Exception as exc:
        raise BackfillError(f"could not invoke {function}: {exc}") from exc

    raw = _read_payload(response, function)
    if response.get("FunctionError") is not None:
        detail = raw.decode("utf-8", "replace")
        raise BackfillError(f"{function} returned an error: {detail[:600]}")

    try:
        decoded = cast(object, json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackfillError(f"{function} returned a non-JSON payload") from exc
    if not isinstance(decoded, dict):
        raise BackfillError(f"{function} returned {type(decoded).__name__}, expected an object")
    return cast(Mapping[str, object], decoded)


def _read_payload(response: Mapping[str, object], function: str) -> bytes:
    """Read one Lambda response body.

    Args:
        response: The raw invoke response.
        function: Function name, for the error message.

    Returns:
        The payload bytes.

    Raises:
        BackfillError: If the response carries no readable payload.
    """
    body = response.get("Payload")
    if body is None:
        raise BackfillError(f"{function} returned no payload")
    return cast(_PayloadStream, body).read()


def _run_window(
    client: _LambdaClient,
    plan: WindowPlan,
    *,
    bronze_function: str,
    silver_function: str,
    pause_seconds: float,
) -> WindowOutcome:
    """Ingest one window to Bronze, then promote every leaf manifest to Silver.

    Args:
        client: The Lambda client.
        plan: The window to request.
        bronze_function: Bronze function name.
        silver_function: Silver function name.
        pause_seconds: Delay between invocations, to respect GitHub rate limits.

    Returns:
        What the window produced.

    Raises:
        BackfillError: If Bronze or any Silver promotion fails, or Bronze returns a
            leaf without the exact coordinate Silver requires.
    """
    bronze = _invoke(
        client,
        bronze_function,
        {
            "schema_version": _INVOCATION_SCHEMA_VERSION,
            "mode": plan.window.mode.value,
            "start_at": plan.window.canonical_start_at,
            "end_at": plan.window.canonical_end_at,
        },
    )

    leaves = bronze.get("leaves")
    if not isinstance(leaves, list):
        raise BackfillError(f"Bronze returned no leaf list for {plan.sync_id}")

    silver_keys: list[str] = []
    for index, leaf in enumerate(cast(list[object], leaves)):
        if not isinstance(leaf, dict):
            raise BackfillError(f"Bronze leaf {index} of {plan.sync_id} is not an object")
        leaf_map = cast(Mapping[str, object], leaf)
        manifest_key = leaf_map.get("manifest_key")
        manifest_version_id = leaf_map.get("manifest_version_id")
        if not isinstance(manifest_key, str) or not isinstance(manifest_version_id, str):
            raise BackfillError(
                f"Bronze leaf {index} of {plan.sync_id} carries no exact manifest coordinate"
            )

        time.sleep(pause_seconds)
        silver = _invoke(
            client,
            silver_function,
            {
                "schema_version": _INVOCATION_SCHEMA_VERSION,
                "manifest_key": manifest_key,
                "manifest_version_id": manifest_version_id,
            },
        )
        complete_key = silver.get("silver_complete_key")
        if not isinstance(complete_key, str):
            raise BackfillError(
                f"Silver did not report a completion key for {manifest_key}"
            )
        silver_keys.append(complete_key)

    return WindowOutcome(
        sync_id=plan.sync_id,
        start_at=plan.window.canonical_start_at,
        end_at=plan.window.canonical_end_at,
        leaf_count=_as_int(bronze.get("leaf_count")),
        total_items=_as_int(bronze.get("total_items")),
        promoted=len(silver_keys),
        silver_keys=tuple(silver_keys),
    )


def _as_int(value: object) -> int:
    """Read one non-negative integer from a lambda response, defaulting to zero."""
    return value if type(value) is int and value >= 0 else 0


def _load_ledger(path: Path) -> dict[str, object]:
    """Read the resume ledger, treating an absent or unreadable one as empty."""
    if not path.is_file():
        return {}
    try:
        decoded = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return cast(dict[str, object], decoded) if isinstance(decoded, dict) else {}


def _save_ledger(path: Path, ledger: Mapping[str, object]) -> None:
    """Persist the resume ledger after every window, so an interrupt loses one window."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(ledger) + b"\n")


def _parser() -> argparse.ArgumentParser:
    """Build the orchestrator's command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Load the GHSA advisory corpus through the existing Bronze and Silver "
            "lambdas. Prints the window plan and invokes nothing unless --apply."
        ),
    )
    parser.add_argument("--from", dest="start", required=True, help="UTC start date, YYYY-MM-DD")
    parser.add_argument("--to", dest="end", default=None, help="UTC end date (default: today)")
    parser.add_argument(
        "--mode", choices=("published", "modified"), default="published",
        help="published for a historical load, modified for a refresh",
    )
    parser.add_argument("--apply", action="store_true", help="actually invoke; default is a plan")
    parser.add_argument(
        "--max-windows", type=int, default=None,
        help="stop after this many windows, so a first run can be small",
    )
    parser.add_argument(
        "--pause-seconds", type=float, default=_DEFAULT_PAUSE_SECONDS,
        help=f"delay between invocations (default: {_DEFAULT_PAUSE_SECONDS})",
    )
    parser.add_argument("--ledger", default=_DEFAULT_LEDGER, help="resume ledger path")
    parser.add_argument("--region", default=_DEFAULT_REGION, help="AWS Region")
    parser.add_argument("--profile", default=None, help="Optional local AWS profile")
    parser.add_argument("--bronze-function", default=_DEFAULT_BRONZE_FUNCTION)
    parser.add_argument("--silver-function", default=_DEFAULT_SILVER_FUNCTION)
    parser.add_argument("--output", default=None, help="write canonical JSON evidence here")
    return parser


def _parse_date(value: str, *, field: str) -> datetime:
    """Parse one UTC calendar date.

    Args:
        value: The `YYYY-MM-DD` text.
        field: Field name for the error message.

    Returns:
        Midnight UTC on that date.

    Raises:
        BackfillError: If the value is not a calendar date.
    """
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise BackfillError(f"{field} must be a YYYY-MM-DD date") from exc


def main(argv: Sequence[str] | None = None) -> int:
    """Plan, and on --apply run, the GHSA corpus backfill.

    Args:
        argv: Command-line arguments, or None to read `sys.argv`.

    Returns:
        0 on success or a completed plan, 2 when the backfill was refused.
    """
    namespace = _parser().parse_args(list(argv) if argv is not None else None)
    ledger_path = Path(cast(str, namespace.ledger))

    try:
        start = _parse_date(cast(str, namespace.start), field="--from")
        raw_end = cast(str | None, namespace.end)
        end = (
            _parse_date(raw_end, field="--to")
            if raw_end is not None
            else datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        )
        mode = GhsaSyncMode(cast(str, namespace.mode))
        plans = _plan_windows(start, end, mode)
    except (BackfillError, ValueError) as exc:
        print(f"ghsa corpus backfill rejected: {exc}", file=sys.stderr)
        return 2

    ledger = _load_ledger(ledger_path)
    completed = cast(dict[str, object], ledger.get("completed", {}))
    pending = [plan for plan in plans if plan.sync_id not in completed]
    limit = cast(int | None, namespace.max_windows)
    if limit is not None:
        pending = pending[:limit]

    print(f"mode: {mode.value}   range: {start.date()} .. {end.date()}")
    print(f"windows: {len(plans)} planned, {len(completed)} already in the ledger, "
          f"{len(pending)} to run")

    if not cast(bool, namespace.apply):
        for plan in pending[:12]:
            print(f"  would run  {plan.window.canonical_start_at} .. "
                  f"{plan.window.canonical_end_at}")
        if len(pending) > 12:
            print(f"  ... and {len(pending) - 12} more")
        print("\nplan only. Re-run with --apply to invoke.")
        return 0

    session = Session(profile_name=cast(str | None, namespace.profile))
    client = cast(
        _LambdaClient,
        session.client(  # pyright: ignore[reportUnknownMemberType]
            "lambda",
            region_name=cast(str, namespace.region),
        ),
    )

    outcomes: list[WindowOutcome] = []
    pause = cast(float, namespace.pause_seconds)
    try:
        for index, plan in enumerate(pending, start=1):
            print(f"[{index}/{len(pending)}] {plan.window.canonical_start_at} "
                  f".. {plan.window.canonical_end_at}", flush=True)
            outcome = _run_window(
                client,
                plan,
                bronze_function=cast(str, namespace.bronze_function),
                silver_function=cast(str, namespace.silver_function),
                pause_seconds=pause,
            )
            outcomes.append(outcome)
            completed[plan.sync_id] = {
                "start_at": outcome.start_at,
                "end_at": outcome.end_at,
                "leaf_count": outcome.leaf_count,
                "total_items": outcome.total_items,
                "promoted": outcome.promoted,
            }
            ledger["completed"] = completed
            _save_ledger(ledger_path, ledger)
            print(f"    leaves={outcome.leaf_count} advisories={outcome.total_items} "
                  f"promoted={outcome.promoted}", flush=True)
            time.sleep(pause)
    except BackfillError as exc:
        # The ledger already holds every window that finished, so the fix is to
        # re-run rather than to work out where it stopped.
        print(f"ghsa corpus backfill stopped: {exc}", file=sys.stderr)
        print(f"{len(outcomes)} window(s) completed and recorded in {ledger_path};"
              " re-run to resume", file=sys.stderr)
        return 2

    payload: dict[str, object] = {
        "contract_version": GHSA_CORPUS_BACKFILL_CONTRACT_VERSION,
        "authority": {
            "creates_infrastructure": False,
            "changes_contracts": False,
            "invokes": ["ghsa-bronze", "ghsa-silver"],
        },
        "request": {
            "mode": mode.value,
            "range_start": start.isoformat(),
            "range_end": end.isoformat(),
            "windows_planned": len(plans),
            "windows_run": len(outcomes),
        },
        "windows": [
            {
                "sync_id": item.sync_id,
                "start_at": item.start_at,
                "end_at": item.end_at,
                "leaf_count": item.leaf_count,
                "total_items": item.total_items,
                "promoted": item.promoted,
                "silver_complete_keys": list(item.silver_keys),
            }
            for item in outcomes
        ],
        "totals": {
            "advisories": sum(item.total_items for item in outcomes),
            "leaves": sum(item.leaf_count for item in outcomes),
            "promoted": sum(item.promoted for item in outcomes),
        },
    }
    payload["backfill_id"] = (
        f"{GHSA_CORPUS_BACKFILL_CONTRACT_VERSION}@sha256:{canonical_sha256(payload)}"
    )

    output = cast(str | None, namespace.output)
    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json(payload) + b"\n")

    totals = cast(Mapping[str, object], payload["totals"])
    print()
    print(f"advisories retrieved: {totals['advisories']}")
    print(f"leaf manifests promoted to Silver: {totals['promoted']}")
    print(f"backfill: {payload['backfill_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
