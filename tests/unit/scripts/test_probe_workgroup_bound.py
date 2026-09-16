"""Tests for reading the scan ceiling a workgroup actually enforces.

The probe used to carry the cutoff as a constant and publish it as evidence. Pointed at
a different workgroup — which is the whole point of the projection workgroup in ADR
0086 — that constant would have reported a bound that was not the one in force.

```text
declared constant != configuration in force
```
"""

import importlib.util
import pathlib
import sys
from collections.abc import Mapping
from types import ModuleType
from typing import Final

import pytest

_REPOSITORY_ROOT: Final = pathlib.Path(__file__).resolve().parents[3]
_SCRIPTS_ROOT: Final = _REPOSITORY_ROOT / "scripts"


def _load() -> ModuleType:
    """Import the probe script as a module."""
    if str(_SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(
        "probe_correlation_index_size", _SCRIPTS_ROOT / "probe_correlation_index_size.py"
    )
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


_PROBE: Final[ModuleType] = _load()


class _StubAthena:
    """An Athena client that answers get_work_group with a scripted description."""

    def __init__(self, described: dict[str, object] | Exception) -> None:
        self._described = described

    def get_work_group(self, *, WorkGroup: str) -> Mapping[str, object]:
        """Return the scripted description."""
        del WorkGroup
        if isinstance(self._described, Exception):
            raise self._described
        return self._described


def _described(cutoff: object, enforced: object) -> dict[str, object]:
    """Build one workgroup description."""
    return {
        "WorkGroup": {
            "Configuration": {
                "BytesScannedCutoffPerQuery": cutoff,
                "EnforceWorkGroupConfiguration": enforced,
            }
        }
    }


def test_reads_the_enforced_ceiling() -> None:
    """The bound reported is the one the workgroup carries."""
    bound = _PROBE.read_workgroup_bound(_StubAthena(_described(2147483648, True)), "wg")
    assert bound.scan_cutoff_bytes == 2147483648
    assert bound.configuration_enforced


def test_an_overridable_workgroup_is_reported_as_such() -> None:
    """A ceiling a client may raise is not the same protection as one it may not."""
    bound = _PROBE.read_workgroup_bound(_StubAthena(_described(10485760, False)), "wg")
    assert bound.scan_cutoff_bytes == 10485760
    assert not bound.configuration_enforced


def test_a_workgroup_without_a_ceiling_reports_none_not_zero() -> None:
    """No declared ceiling is absence, never a bound of zero."""
    bound = _PROBE.read_workgroup_bound(_StubAthena(_described(None, True)), "wg")
    assert bound.scan_cutoff_bytes is None


def test_an_undescribable_workgroup_stops_the_probe() -> None:
    """A probe that cannot state its own bound must not publish evidence."""
    with pytest.raises(_PROBE.ProbeError):
        _PROBE.read_workgroup_bound(_StubAthena(RuntimeError("denied")), "wg")
