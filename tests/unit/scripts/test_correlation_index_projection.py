"""Tests for the parts of the projector that decide whether the index can mislead.

Most of this script is orchestration around modules already tested. Two things are its
own, and both can make the index lie:

**Freshness.** A response citing this index says "no known vulnerabilities as of
<instant>", and the instant has to come from the sources, not from the clock on the
machine that ran the build. A projector that ran at noon over a corpus last ingested
three days ago is three days stale.

```text
built at != current through
```

**Ordering.** Rows, then manifest, then pointer. Until the pointer is written the new
generation is unreachable and the previous one still answers; a run that dies earlier
leaves a key space nobody can address, which expires on its own.

```text
written != readable
```
"""

import importlib.util
import pathlib
import sys
from types import ModuleType
from typing import Final

import pytest

_REPOSITORY_ROOT: Final = pathlib.Path(__file__).resolve().parents[3]
_SCRIPTS_ROOT: Final = _REPOSITORY_ROOT / "scripts"


def _load() -> ModuleType:
    """Import the projector script as a module."""
    if str(_SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(
        "run_correlation_index_projection",
        _SCRIPTS_ROOT / "run_correlation_index_projection.py",
    )
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


_PROJECTOR: Final[ModuleType] = _load()


class TestSourceInstants:
    """Silver writes instants in more than one shape; the index renders exactly one."""

    @pytest.mark.parametrize(
        "value",
        [
            "2026-09-16T21:20:51Z",
            "2026-09-16T21:20:51+00:00",
            "2026-09-16 21:20:51",
            "2026-09-16T21:20:51.123456Z",
        ],
    )
    def test_every_shape_renders_to_one_form(self, value: str) -> None:
        """Two indexes are only comparable if their instants are written the same way."""
        assert _PROJECTOR._as_index_instant(value, source="ghsa") == (
            "2026-09-16T21:20:51Z"
        )

    @pytest.mark.parametrize("value", ["", "yesterday", "2026-09-16", "not an instant"])
    def test_an_unreadable_instant_stops_the_build(self, value: str) -> None:
        """Guessing a freshness is how a stale index gets presented as current."""
        with pytest.raises(_PROJECTOR.ProjectionRunError):
            _PROJECTOR._as_index_instant(value, source="ghsa")


class TestTheQueriesItRuns:
    """The statements are read by reviewers before they are run against real data."""

    def test_the_watermarks_ask_each_source_for_its_own_latest_instant(self) -> None:
        """A build cannot state freshness it did not read from the source."""
        from opslens.correlation_index.application.watermarks import (
            ghsa_watermark_sql,
            nvd_watermark_sql,
        )

        assert "max(updated_at)" in ghsa_watermark_sql("db", "ghsa")
        assert "max(last_modified_at)" in nvd_watermark_sql("db", "nvd")

    def test_the_default_workgroup_is_the_projection_one(self) -> None:
        """An anonymous caller must never be able to trigger a corpus scan (ADR 0086)."""
        namespace = _PROJECTOR._parser().parse_args([])
        assert namespace.workgroup == "opslens-dev-projection"

    def test_writing_requires_an_explicit_flag(self) -> None:
        """The default is a plan; this one writes a store the request path reads."""
        assert _PROJECTOR._parser().parse_args([]).apply is False
        assert _PROJECTOR._parser().parse_args(["--apply"]).apply is True
