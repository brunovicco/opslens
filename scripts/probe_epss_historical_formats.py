#!/usr/bin/env python3
"""Probe exact historical EPSS archive formats without executing third-party code."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass

ARCHIVE_REPOSITORY = "empiricalsec/epss_scores"
DEFAULT_ARCHIVE_COMMIT = "7ba701f5599057c496489ceecd701cbd43911f5c"
MAX_COMPRESSED_BYTES = 16 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 128 * 1024 * 1024
DEFAULT_DATES = (
    "2021-04-14",
    "2022-02-03",
    "2022-02-04",
    "2023-03-06",
    "2023-03-07",
    "2025-03-16",
    "2025-03-17",
    "2026-06-14",
    "2026-06-15",
    "2026-08-30",
)


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Represent bounded evidence from one exact archive object."""

    snapshot_date: str
    archive_path: str
    archive_commit_sha: str
    source_url: str
    compressed_bytes: int
    decompressed_bytes: int
    source_sha256: str
    first_line: str
    second_line: str
    first_row: list[str]
    second_row: list[str]
    metadata_present: bool
    header: list[str]
    format_family: str


def _archive_path(snapshot_date: str) -> str:
    year = snapshot_date[:4]
    return f"{year}/epss_scores-{snapshot_date}.csv.gz"


def _source_url(commit: str, path: str) -> str:
    return (
        "https://raw.githubusercontent.com/"
        f"{ARCHIVE_REPOSITORY}/{commit}/{path}"
    )


def _fetch_bounded(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "OpsLens-EPSS-Historical-Probe/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) > MAX_COMPRESSED_BYTES:
                raise RuntimeError(f"source exceeds compressed limit: {content_length}")
            payload = response.read(MAX_COMPRESSED_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} for {url}") from exc

    if len(payload) > MAX_COMPRESSED_BYTES:
        raise RuntimeError(f"source exceeds compressed limit: {len(payload)}")
    if not payload:
        raise RuntimeError(f"empty source payload: {url}")
    return payload


def _decompress_bounded(payload: bytes) -> bytes:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as stream:
            decompressed = stream.read(MAX_DECOMPRESSED_BYTES + 1)
    except (gzip.BadGzipFile, EOFError, OSError) as exc:
        raise RuntimeError("invalid gzip payload") from exc

    if len(decompressed) > MAX_DECOMPRESSED_BYTES:
        raise RuntimeError(
            f"source exceeds decompressed limit: {len(decompressed)}"
        )
    return decompressed


def _decode_line(raw: bytes) -> str:
    return raw.decode("utf-8").rstrip("\r\n")


def _csv_row(line: str) -> list[str]:
    return next(csv.reader([line]))


def probe(snapshot_date: str, commit: str) -> ProbeResult:
    """Probe one exact historical EPSS source object."""
    path = _archive_path(snapshot_date)
    url = _source_url(commit, path)
    payload = _fetch_bounded(url)
    decompressed = _decompress_bounded(payload)

    line_stream = io.BytesIO(decompressed)
    first_line = _decode_line(line_stream.readline())
    second_line = _decode_line(line_stream.readline())
    first_row = _csv_row(first_line)
    second_row = _csv_row(second_line)
    metadata_present = first_line.startswith("#")

    if metadata_present:
        header = second_row
        format_family = "modern_metadata_v1"
    else:
        header = first_row
        format_family = "legacy_pre_v2"

    return ProbeResult(
        snapshot_date=snapshot_date,
        archive_path=path,
        archive_commit_sha=commit,
        source_url=url,
        compressed_bytes=len(payload),
        decompressed_bytes=len(decompressed),
        source_sha256=hashlib.sha256(payload).hexdigest(),
        first_line=first_line,
        second_line=second_line,
        first_row=first_row,
        second_row=second_row,
        metadata_present=metadata_present,
        header=header,
        format_family=format_family,
    )


def main() -> int:
    """Run the bounded representative historical-format probe."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-commit", default=DEFAULT_ARCHIVE_COMMIT)
    parser.add_argument("--dates", nargs="*", default=list(DEFAULT_DATES))
    args = parser.parse_args()

    results: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []

    for snapshot_date in args.dates:
        try:
            results.append(asdict(probe(snapshot_date, args.archive_commit)))
        except RuntimeError as exc:
            failures.append({"snapshot_date": snapshot_date, "error": str(exc)})

    output = {
        "schema_version": 1,
        "read_only": True,
        "third_party_code_executed": False,
        "archive_repository": ARCHIVE_REPOSITORY,
        "archive_commit_sha": args.archive_commit,
        "requested_dates": args.dates,
        "results": results,
        "failures": failures,
    }
    print(json.dumps(output, indent=2, sort_keys=True))

    if failures:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
