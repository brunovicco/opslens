"""Tests for mapping Silver query results onto index rows.

The property under test is the one that decides whether the endpoint can lie. The index
key must equal the key a request arrives with, and the request path computes that key
with `canonicalize_pypi_package` — which validates against the PyPA grammar before
normalizing, and raises on anything that fails.

Athena's `lower(regexp_replace(...))` produces the same string for valid names and a
string for invalid ones too. An index keyed that way would hold rows no request can
match, and an advisory that never matches is an advisory that silently stops applying.

```text
normalized in SQL != canonical in Python
unmatched key != absent vulnerability
```

So the mapper canonicalizes in Python, and what it cannot key it counts.
"""

import re

import pytest

from opslens.correlation_index.application.projection import (
    GHSA_PROJECTION_COLUMNS,
    ProjectionMappingError,
    ghsa_projection_sql,
    nvd_projection_sql,
    project_ghsa_rows,
    project_nvd_rows,
)

_ADVISORY_DIGEST = "6872a46115d1775d1eac3f5ba734e73ec98a9f78487d178e38e13163c69d7dbf"
_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_CVE_DIGEST = "3e8f5bff0551f7533a34c40a9a944832e9a01d258049d908e179b24da872431c"
_GHSA_ID = "GHSA-fq2j-3j99-rx65"


def _result(**overrides: str) -> dict[str, str]:
    """Build one GHSA query result row."""
    row = {
        "ghsa_id": _GHSA_ID,
        "observed_advisory_version_id": f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
        "source_advisory_sha256": _ADVISORY_DIGEST,
        "cve_id": "CVE-2026-1234",
        "identifiers_json": f'[{{"type":"GHSA","value":"{_GHSA_ID}"}}]',
        "source_index": "0",
        "vulnerability_entry_id": "entry-0",
        "source_entry_sha256": _ENTRY_DIGEST,
        "ecosystem": "pip",
        "package_name": "TensorFlow",
        "vulnerable_version_range": ">= 2.0.0, < 2.11.1",
        "first_patched_version": "2.11.1",
    }
    row.update(overrides)
    return row


def _nvd_result(**overrides: str) -> dict[str, str]:
    """Build one NVD query result row, rendered the way Athena actually renders it.

    This fixture previously carried `2026-01-02T03:04:05Z`. Athena renders a Glue
    `timestamp` column as `2026-01-02 03:04:05.000` — space, milliseconds, no zone — and
    the fixture being tidier than the source is why the first live index stored a
    timestamp form nothing else in the system uses.

    ```text
    a fixture's rendering != the source's rendering
    ```
    """
    row = {
        "cve_id": "CVE-2026-1234",
        "observed_cve_version_id": f"CVE-2026-1234@sha256:{_CVE_DIGEST}",
        "source_cve_sha256": _CVE_DIGEST,
        "source_identifier": "cve@mitre.org",
        "published_at": "2026-01-02 03:04:05.000",
        "last_modified_at": "2026-02-03 04:05:06.527",
        "vuln_status": "Analyzed",
    }
    row.update(overrides)
    return row


class TestTheKeyMatchesTheRequestPath:
    """A key the request path cannot produce is a vulnerability that stops applying."""

    @pytest.mark.parametrize(
        ("source_name", "expected_key"),
        [
            ("TensorFlow", "tensorflow"),
            ("zope.interface", "zope-interface"),
            ("ruamel_yaml", "ruamel-yaml"),
            ("Flask--SQLAlchemy", "flask-sqlalchemy"),
        ],
    )
    def test_the_key_is_the_canonical_name(
        self, source_name: str, expected_key: str
    ) -> None:
        """Separator runs collapse and case folds, exactly as the request path does it."""
        outcome = project_ghsa_rows([_result(package_name=source_name)])
        assert outcome.rows[0].package_name_canonical == expected_key

    def test_the_source_name_survives_beside_the_key(self) -> None:
        """The authority re-canonicalizes the original, so the original has to be kept."""
        outcome = project_ghsa_rows([_result(package_name="TensorFlow")])
        assert outcome.rows[0].package_name_original == "TensorFlow"

    @pytest.mark.parametrize("source_name", ["-leading", "with space", "trailing-", ""])
    def test_a_name_python_refuses_is_rejected_rather_than_keyed(
        self, source_name: str
    ) -> None:
        """SQL would normalize these into keys no request can ever match."""
        outcome = project_ghsa_rows([_result(package_name=source_name)])
        assert outcome.rows == ()
        assert len(outcome.rejected) == 1
        assert outcome.rejected[0].reason.startswith("UNCANONICALIZABLE_PYPI_NAME")


class TestAccounting:
    """Everything in must be admitted or refused; a quiet drop under-reports."""

    def test_admitted_plus_rejected_covers_every_input(self) -> None:
        """The same accounting ADR 0085 established for Silver pages."""
        results = [
            _result(package_name="tensorflow"),
            _result(package_name="with space"),
            _result(package_name="django", source_index="1"),
        ]
        outcome = project_ghsa_rows(results)
        assert outcome.accounted_count == len(results)
        assert len(outcome.rows) == 2
        assert len(outcome.rejected) == 1

    def test_a_row_that_fails_the_contract_is_counted_not_dropped(self) -> None:
        """An identity contradicting its digest is refused, and the refusal is visible."""
        outcome = project_ghsa_rows(
            [_result(observed_advisory_version_id=f"{_GHSA_ID}@sha256:{_ENTRY_DIGEST}")]
        )
        assert outcome.rows == ()
        assert outcome.rejected[0].reason.startswith("UNSTORABLE_INDEX_ROW")


class TestSourceFidelity:
    """A projection that edits its source is not a projection."""

    def test_identifiers_are_read_in_source_order(self) -> None:
        """GitHub emits an order, and reordering it rewrites the source."""
        payload = (
            f'[{{"type":"GHSA","value":"{_GHSA_ID}"}},'
            '{"type":"CVE","value":"CVE-2026-1234"}]'
        )
        outcome = project_ghsa_rows([_result(identifiers_json=payload)])
        assert [
            (item.identifier_type, item.value)
            for item in outcome.rows[0].github_identifiers
        ] == [("GHSA", _GHSA_ID), ("CVE", "CVE-2026-1234")]

    @pytest.mark.parametrize("column", ["cve_id", "first_patched_version"])
    def test_an_empty_passthrough_field_reads_as_absent(self, column: str) -> None:
        """The reading ADR 0085 took: sparse is not malformed."""
        outcome = project_ghsa_rows([_result(**{column: ""})])
        assert outcome.rows != ()

    def test_advisories_with_no_identifiers_are_admitted(self) -> None:
        """An empty array is a sparse advisory, not a broken one."""
        outcome = project_ghsa_rows([_result(identifiers_json="[]")])
        assert outcome.rows[0].github_identifiers == ()

    def test_malformed_identifier_json_is_a_query_defect(self) -> None:
        """This cannot come from a source record, so it raises rather than counting."""
        with pytest.raises(ProjectionMappingError):
            project_ghsa_rows([_result(identifiers_json="{not json")])

    def test_a_missing_column_is_a_query_defect(self) -> None:
        """A projection reading a column the query never selected must not guess."""
        broken = _result()
        del broken["source_entry_sha256"]
        with pytest.raises(ProjectionMappingError):
            project_ghsa_rows([broken])


class TestSql:
    """The statements are read by reviewers, so their shape is asserted."""

    def test_the_ghsa_query_selects_every_column_the_mapper_reads(self) -> None:
        """A column the mapper needs and the query omits fails only at run time."""
        sql = ghsa_projection_sql("opslens_dev", "ghsa_advisory_versions")
        for column in GHSA_PROJECTION_COLUMNS:
            assert f"AS {column}" in sql

    def test_the_ghsa_query_excludes_withdrawn_advisories(self) -> None:
        """A withdrawn advisory no longer applies and must not reach the index."""
        sql = ghsa_projection_sql("opslens_dev", "ghsa_advisory_versions")
        assert "NOT r.is_withdrawn" in sql

    def test_the_ghsa_version_selection_orders_totally(self) -> None:
        """Without the tiebreak the same corpus produced two different indexes.

        Measured on 2026-09-17: 7 of 35,577 advisories carry two observed versions
        sharing an `updated_at`, so `ROW_NUMBER` picked between them arbitrarily and
        Presto resolved it differently between runs.

        ```text
        same query != same result
        ```
        """
        sql = ghsa_projection_sql("opslens_dev", "ghsa_advisory_versions")
        assert "ORDER BY updated_at DESC, observed_advisory_version_id DESC" in sql

    def test_the_nvd_version_selection_orders_totally(self) -> None:
        """The NVD corpus carries no ties today, which is a fact about the data.

        Zero ties is a property of what has been ingested, not of the query. The
        statement carries the tiebreak so tomorrow's corpus cannot introduce the defect
        silently.
        """
        sql = nvd_projection_sql("opslens_dev", "nvd_cve_versions", ["CVE-2026-1"])
        assert "ORDER BY last_modified_at DESC, observed_cve_version_id DESC" in sql

    def test_every_row_number_in_the_projection_breaks_ties(self) -> None:
        """A third statement added later must not reintroduce the defect.

        Asserted structurally rather than statement by statement: every window that
        selects one row per group has to name a second, unique ordering column.
        """
        statements = (
            ghsa_projection_sql("opslens_dev", "ghsa_advisory_versions"),
            nvd_projection_sql("opslens_dev", "nvd_cve_versions", ["CVE-2026-1"]),
        )
        for sql in statements:
            windows = re.findall(r"ROW_NUMBER\(\)\s*OVER\s*\((.*?)\)", sql, re.DOTALL)
            assert windows, "a projection statement stopped selecting one row per group"
            for window in windows:
                order_by = window.split("ORDER BY", 1)[1]
                assert order_by.count(",") >= 1, (
                    "ROW_NUMBER orders on one column; ties resolve arbitrarily"
                )

    def test_the_nvd_query_is_scoped_to_the_cves_ghsa_named(self) -> None:
        """The authority refuses NVD records unrelated to scoped GHSA evidence."""
        sql = nvd_projection_sql("opslens_dev", "nvd_cve_versions", ["CVE-2026-1"])
        assert "'CVE-2026-1'" in sql

    def test_an_empty_cve_scope_selects_nothing(self) -> None:
        """No scope must mean no rows, never every row."""
        sql = nvd_projection_sql("opslens_dev", "nvd_cve_versions", [])
        assert "IN ('')" in sql

    @pytest.mark.parametrize(
        "value", ["CVE-2026-1' OR '1'='1", "'; DROP TABLE x--", "not-a-cve", ""]
    )
    def test_a_non_cve_identifier_cannot_reach_the_statement(self, value: str) -> None:
        """These identifiers are interpolated, so the shape is enforced before they are."""
        with pytest.raises(ProjectionMappingError):
            nvd_projection_sql("opslens_dev", "nvd_cve_versions", [value])


class TestNvdMapping:
    """NVD has no unkeyable case, so a bad row is a defect rather than a rejection."""

    def test_a_valid_row_maps(self) -> None:
        """The happy case."""
        assert project_nvd_rows([_nvd_result()])[0].cve_id == "CVE-2026-1234"

    def test_a_row_failing_the_contract_raises(self) -> None:
        """Nothing about NVD makes a row legitimately unstorable."""
        with pytest.raises(ProjectionMappingError):
            project_nvd_rows([_nvd_result(source_cve_sha256="short")])

    def test_both_instants_are_rendered_in_the_index_form(self) -> None:
        """The stored row is what the response envelope will quote, so it is pinned.

        The first live index stored `2026-07-22 15:17:17.527` while its own manifest
        used `2026-09-17T03:40:55Z`. One build, two renderings of an instant.
        """
        row = project_nvd_rows([_nvd_result()])[0]
        assert row.published_at == "2026-01-02T03:04:05Z"
        assert row.last_modified_at == "2026-02-03T04:05:06Z"

    def test_an_unreadable_instant_raises_rather_than_storing_it(self) -> None:
        """A column Athena rendered as something else must not reach DynamoDB."""
        with pytest.raises(ProjectionMappingError):
            project_nvd_rows([_nvd_result(published_at="not a timestamp")])
