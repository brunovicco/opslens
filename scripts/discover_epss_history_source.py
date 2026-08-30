#!/usr/bin/env python3
"""Inventory the public EPSS historical archive without downloading score files."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

GITHUB_API = "https://api.github.com"
REPOSITORY = "empiricalsec/epss_scores"
DEFAULT_REF = "main"
USER_AGENT = "opslens-epss-history-discovery/1"
FIRST_AVAILABLE_DATE = date(2021, 4, 14)
FILE_PATTERN = re.compile(r"^epss_scores-(\d{4}-\d{2}-\d{2})\.csv\.gz$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class ModelEra:
    """One documented EPSS model-publishing interval."""

    label: str
    source_model_version: str | None
    start: date
    end_exclusive: date | None
    source_metadata_expected: bool


MODEL_ERAS = (
    ModelEra("v1", None, date(2021, 4, 14), date(2022, 2, 4), False),
    ModelEra("v2", "v2022.01.01", date(2022, 2, 4), date(2023, 3, 7), True),
    ModelEra("v3", "v2023.03.01", date(2023, 3, 7), date(2025, 3, 17), True),
    ModelEra("v4", "v2025.03.14", date(2025, 3, 17), date(2026, 6, 15), True),
    ModelEra("v5", "v2026.06.15", date(2026, 6, 15), None, True),
)


class GitHubApiError(RuntimeError):
    """Raised when the public GitHub metadata API violates expectations."""


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory empiricalsec/epss_scores at an immutable Git commit using "
            "Git tree metadata only; score files are never downloaded."
        )
    )
    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help="Git ref or 40-character commit SHA to inventory (default: main).",
    )
    parser.add_argument(
        "--github-token-env",
        default=None,
        help=(
            "Optional environment variable containing a GitHub token. Public "
            "discovery works without authentication and never requires a token."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=20.0,
        help="Per-request HTTP timeout (default: 20 seconds).",
    )
    return parser.parse_args()


class GitHubReader:
    """Minimal serial GitHub REST reader with explicit request accounting."""

    def __init__(self, *, token: str | None, timeout_seconds: float) -> None:
        """Initialize the reader with optional authentication and a timeout."""
        if timeout_seconds <= 0:
            raise ValueError("timeout-seconds must be positive")
        self._token = token
        self._timeout_seconds = timeout_seconds
        self.request_count = 0

    def get_json(self, path: str) -> dict[str, Any]:
        """GET one GitHub REST resource and decode its JSON object."""
        request = urllib.request.Request(
            f"{GITHUB_API}{path}",
            headers=self._headers(),
            method="GET",
        )
        self.request_count += 1
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            retry_after = exc.headers.get("Retry-After")
            remaining = exc.headers.get("X-RateLimit-Remaining")
            reset = exc.headers.get("X-RateLimit-Reset")
            raise GitHubApiError(
                "GitHub API request failed: "
                f"status={exc.code} path={path!r} retry_after={retry_after!r} "
                f"rate_limit_remaining={remaining!r} rate_limit_reset={reset!r}"
            ) from exc
        except urllib.error.URLError as exc:
            raise GitHubApiError(f"GitHub API request failed for {path!r}: {exc}") from exc

        value = json.loads(raw)
        if not isinstance(value, dict):
            raise GitHubApiError(f"GitHub API response for {path!r} must be an object")
        return value

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2026-03-10",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers


def resolve_commit(reader: GitHubReader, ref: str) -> tuple[str, str]:
    """Resolve a branch/ref or exact commit and return commit SHA plus tree SHA."""
    normalized = ref.strip()
    if not normalized:
        raise ValueError("ref cannot be empty")

    if SHA_PATTERN.fullmatch(normalized):
        commit_sha = normalized
    else:
        branch = reader.get_json(f"/repos/{REPOSITORY}/branches/{normalized}")
        commit_value = branch.get("commit")
        if not isinstance(commit_value, dict):
            raise GitHubApiError("branch response is missing commit metadata")
        commit_sha_value = commit_value.get("sha")
        if not isinstance(commit_sha_value, str) or not SHA_PATTERN.fullmatch(commit_sha_value):
            raise GitHubApiError("branch response contains an invalid commit SHA")
        commit_sha = commit_sha_value

    commit = reader.get_json(f"/repos/{REPOSITORY}/git/commits/{commit_sha}")
    tree_value = commit.get("tree")
    if not isinstance(tree_value, dict):
        raise GitHubApiError("commit response is missing tree metadata")
    tree_sha = tree_value.get("sha")
    if not isinstance(tree_sha, str) or not SHA_PATTERN.fullmatch(tree_sha):
        raise GitHubApiError("commit response contains an invalid tree SHA")
    return commit_sha, tree_sha


def get_tree_entries(reader: GitHubReader, tree_sha: str) -> list[dict[str, Any]]:
    """Read one non-recursive Git tree and fail closed on truncation."""
    result = reader.get_json(f"/repos/{REPOSITORY}/git/trees/{tree_sha}")
    if result.get("truncated") is True:
        raise GitHubApiError(f"Git tree {tree_sha} was truncated")
    tree = result.get("tree")
    if not isinstance(tree, list):
        raise GitHubApiError(f"Git tree {tree_sha} has no tree array")
    entries: list[dict[str, Any]] = []
    for item in tree:
        if not isinstance(item, dict):
            raise GitHubApiError(f"Git tree {tree_sha} contains a non-object entry")
        entries.append(item)
    return entries


def model_era_for(snapshot_date: date) -> ModelEra:
    """Return the documented model era for one archive date."""
    for era in MODEL_ERAS:
        if snapshot_date < era.start:
            continue
        if era.end_exclusive is None or snapshot_date < era.end_exclusive:
            return era
    raise ValueError(f"No EPSS model era defined for {snapshot_date.isoformat()}")


def expected_dates(start: date, end: date) -> set[date]:
    """Return every calendar date in the inclusive range."""
    result: set[date] = set()
    current = start
    while current <= end:
        result.add(current)
        current += timedelta(days=1)
    return result


def main() -> None:
    """Inventory the pinned archive and print a deterministic JSON summary."""
    args = parse_args()
    token: str | None = None
    if args.github_token_env:
        token_value = os.environ.get(args.github_token_env, "").strip()
        if not token_value:
            raise ValueError(
                f"Environment variable {args.github_token_env!r} is empty or unavailable"
            )
        token = token_value

    reader = GitHubReader(token=token, timeout_seconds=args.timeout_seconds)
    commit_sha, root_tree_sha = resolve_commit(reader, args.ref)
    root_entries = get_tree_entries(reader, root_tree_sha)

    year_trees: dict[int, str] = {}
    ignored_root_entries: list[str] = []
    for entry in root_entries:
        path = entry.get("path")
        entry_type = entry.get("type")
        entry_sha = entry.get("sha")
        if not isinstance(path, str):
            raise GitHubApiError("root tree entry is missing path")
        if path.isdigit() and len(path) == 4 and entry_type == "tree":
            if not isinstance(entry_sha, str) or not SHA_PATTERN.fullmatch(entry_sha):
                raise GitHubApiError(f"year tree {path} contains an invalid SHA")
            year_trees[int(path)] = entry_sha
        else:
            ignored_root_entries.append(path)

    if not year_trees:
        raise GitHubApiError("archive root does not contain year trees")

    snapshots: dict[date, dict[str, Any]] = {}
    unexpected_year_entries: list[str] = []
    per_year_count: Counter[int] = Counter()
    per_year_bytes: Counter[int] = Counter()
    per_model_count: Counter[str] = Counter()
    per_model_bytes: Counter[str] = Counter()

    for year in sorted(year_trees):
        for entry in get_tree_entries(reader, year_trees[year]):
            path = entry.get("path")
            if not isinstance(path, str):
                raise GitHubApiError(f"year {year} contains an entry without path")
            match = FILE_PATTERN.fullmatch(path)
            if match is None:
                unexpected_year_entries.append(f"{year}/{path}")
                continue
            if entry.get("type") != "blob":
                raise GitHubApiError(f"{year}/{path} must be a blob")
            size = entry.get("size")
            sha = entry.get("sha")
            if not isinstance(size, int) or size <= 0:
                raise GitHubApiError(f"{year}/{path} has invalid size metadata")
            if not isinstance(sha, str) or not SHA_PATTERN.fullmatch(sha):
                raise GitHubApiError(f"{year}/{path} has invalid blob SHA")

            snapshot_date = date.fromisoformat(match.group(1))
            if snapshot_date.year != year:
                raise GitHubApiError(
                    f"archive year/path mismatch: {year}/{path} -> {snapshot_date}"
                )
            if snapshot_date in snapshots:
                raise GitHubApiError(f"duplicate archive date {snapshot_date}")

            era = model_era_for(snapshot_date)
            snapshots[snapshot_date] = {
                "path": f"{year}/{path}",
                "blob_sha": sha,
                "size_bytes": size,
                "model_era": era.label,
            }
            per_year_count[year] += 1
            per_year_bytes[year] += size
            per_model_count[era.label] += 1
            per_model_bytes[era.label] += size

    if not snapshots:
        raise GitHubApiError("archive contains no EPSS snapshot files")

    min_date = min(snapshots)
    max_date = max(snapshots)
    if min_date != FIRST_AVAILABLE_DATE:
        raise GitHubApiError(
            f"archive start date changed: expected {FIRST_AVAILABLE_DATE}, found {min_date}"
        )

    missing = sorted(expected_dates(min_date, max_date) - set(snapshots))
    total_bytes = sum(item["size_bytes"] for item in snapshots.values())

    model_eras = []
    for era in MODEL_ERAS:
        model_eras.append(
            {
                "label": era.label,
                "source_model_version": era.source_model_version,
                "start_date": era.start.isoformat(),
                "end_date_inclusive": (
                    (era.end_exclusive - timedelta(days=1)).isoformat()
                    if era.end_exclusive is not None
                    else None
                ),
                "source_metadata_expected": era.source_metadata_expected,
                "snapshot_count_at_pin": per_model_count[era.label],
                "compressed_bytes_at_pin": per_model_bytes[era.label],
            }
        )

    output = {
        "schema_version": 1,
        "read_only": True,
        "repository": REPOSITORY,
        "requested_ref": args.ref,
        "resolved_commit_sha": commit_sha,
        "root_tree_sha": root_tree_sha,
        "archive_start_date": min_date.isoformat(),
        "archive_end_date": max_date.isoformat(),
        "snapshot_count": len(snapshots),
        "compressed_bytes": total_bytes,
        "compressed_mib": round(total_bytes / (1024 * 1024), 2),
        "calendar_dates_expected": len(expected_dates(min_date, max_date)),
        "missing_date_count": len(missing),
        "missing_dates": [value.isoformat() for value in missing],
        "per_year": [
            {
                "year": year,
                "snapshot_count": per_year_count[year],
                "compressed_bytes": per_year_bytes[year],
            }
            for year in sorted(year_trees)
        ],
        "model_eras": model_eras,
        "legacy_v1_snapshot_count": per_model_count["v1"],
        "ignored_root_entries": sorted(ignored_root_entries),
        "unexpected_year_entries": sorted(unexpected_year_entries),
        "github_api_request_count": reader.request_count,
        "enumeration_strategy": "non-recursive root tree plus one non-recursive tree per year",
        "score_files_downloaded": 0,
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
