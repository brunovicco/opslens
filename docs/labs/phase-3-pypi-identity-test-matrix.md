# Phase 3 — PyPI Identity Test Matrix

The identity gate is intentionally smaller than the future vulnerable-range evaluator.

| Concern | Deterministic behavior |
|---|---|
| GHSA ecosystem alias | `pip -> pypi` |
| Unknown ecosystem | fail closed |
| PyPI name | validate before normalization |
| Name equality | lowercase + collapse `[-_.]+` to `-` |
| Concrete version | PEP 440 parser/comparator |
| Invalid concrete version | fail closed with `invalid_version` |
| PURL namespace | prohibited for PyPI v1 |
| PURL missing version | invalid for OpsLens correlation identity v1 |
| PURL qualifiers/subpath | unsupported, never silently discarded |
| PURL package/version disagreement | invalid evidence |
| Epoch/local PEP 440 separators | canonical percent-encoding in PURL |

This matrix is covered by the unit tests under `tests/unit/correlation/` and the frozen corpus in `tests/fixtures/correlation/pypi_v1_cases.json`.
