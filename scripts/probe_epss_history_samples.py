#!/usr/bin/env python3
"""Probe representative immutable EPSS history files without mutating AWS state."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import time
import tracemalloc
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any

from opslens.ingestion.epss.domain.errors import InvalidEpssSnapshotError
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.transformation.epss.adapters.outbound.parquet import (
    PyArrowSilverEpssRecordWriter,
)
from opslens.transformation.epss.domain.transformer import EpssSilverTransformer

REPOSITORY = "empiricalsec/epss_scores"
GITHUB_API = "https://api.github.com"
RAW_GITHUB = "https://raw.githubusercontent.com"
DEFAULT_COMMIT = "7ba701f5599057c496489ceecd701cbd43911f5c"
USER_AGENT = "opslens-epss-history-sample-probe/1"


@dataclass(frozen=True, slots=True)
class Sample:
    """One model-era representative source file."""

    era: str
    snapshot_date: date

    @property
    def path(self) -> str:
        """Return the canonical archive path for this sample."""
        rendered = self.snapshot_date.isoformat()
        return f"{self.snapshot_date.year}/epss_scores-{rendered}.csv.gz"


SAMPLES = (
    Sample("v1", date(2021, 4, 14)),
    Sample("v2", date(2022, 2, 4)),
    Sample("v3", date(2023, 3, 7)),
    Sample("v4", date(2025, 3, 17)),
    Sample("v5", date(2026, 6, 15)),
)


class SourceProbeError(RuntimeError):
    """Raised when immutable source evidence violates the probe contract."""


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Download five representative EPSS score files from an immutable "
            "empiricalsec/epss_scores commit and measure format compatibility."
        )
    )
    parser.add_argument(
        "--commit",
        default=DEFAULT_COMMIT,
        help="Immutable empiricalsec/epss_scores commit SHA.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="Per-request HTTP timeout (default: 30 seconds).",
    )
    return parser.parse_args()


def _request_bytes(url: str, *, timeout_seconds: float) -> tuple[bytes, int]:
    """Fetch one public URL and return bytes plus elapsed milliseconds."""
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2026-03-10",
        },
        method="GET",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise SourceProbeError(f"HTTP read failed for {url!r}: {exc}") from exc
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return payload, elapsed_ms


def _content_metadata(
    *,
    commit: str,
    sample: Sample,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Read GitHub content metadata for one pinned sample path."""
    encoded_path = urllib.parse.quote(sample.path, safe="/")
    encoded_ref = urllib.parse.quote(commit, safe="")
    raw, _ = _request_bytes(
        f"{GITHUB_API}/repos/{REPOSITORY}/contents/{encoded_path}?ref={encoded_ref}",
        timeout_seconds=timeout_seconds,
    )
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise SourceProbeError(f"metadata for {sample.path} must be an object")
    blob_sha = value.get("sha")
    size = value.get("size")
    if not isinstance(blob_sha, str) or len(blob_sha) != 40:
        raise SourceProbeError(f"metadata for {sample.path} has invalid blob SHA")
    if not isinstance(size, int) or size <= 0:
        raise SourceProbeError(f"metadata for {sample.path} has invalid size")
    return {"blob_sha": blob_sha, "size": size}


def _git_blob_sha1(payload: bytes) -> str:
    """Compute the Git blob identity for exact source bytes."""
    prefix = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(prefix + payload, usedforsecurity=False).hexdigest()


def _decode_lines(decompressed: bytes) -> list[str]:
    """Decode source bytes into normalized UTF-8 lines."""
    try:
        return decompressed.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise SourceProbeError("sample is not valid UTF-8 after gzip decompression") from exc


def _parse_comment_metadata(line: str | None) -> dict[str, str] | None:
    """Parse a FIRST-style metadata comment when physically present."""
    if line is None or not line.startswith("#"):
        return None
    result: dict[str, str] = {}
    for item in line.removeprefix("#").split(","):
        if ":" not in item:
            continue
        key, value = item.split(":", maxsplit=1)
        key = key.strip()
        value = value.strip()
        if key and value:
            result[key] = value
    return result


def _measure_current_pipeline(payload: bytes) -> dict[str, Any]:
    """Measure current parser and, when accepted, current Silver serialization."""
    parser = EpssSnapshotParser()
    transformer = EpssSilverTransformer()
    writer = PyArrowSilverEpssRecordWriter()

    tracemalloc.start()
    parse_started = time.perf_counter()
    try:
        snapshot = parser.parse(payload)
    except InvalidEpssSnapshotError as exc:
        parse_elapsed_ms = round((time.perf_counter() - parse_started) * 1000, 3)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return {
            "current_parser_accepts": False,
            "current_parser_error": str(exc),
            "current_parser_elapsed_ms": parse_elapsed_ms,
            "python_tracemalloc_peak_bytes": peak,
            "current_silver_serialization_attempted": False,
        }

    parse_elapsed_ms = round((time.perf_counter() - parse_started) * 1000, 3)
    destination = io.BytesIO()
    write_started = time.perf_counter()
    write_result = writer.write(
        records=transformer.iter_records(snapshot),
        destination=destination,
    )
    write_elapsed_ms = round((time.perf_counter() - write_started) * 1000, 3)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "current_parser_accepts": True,
        "current_parser_error": None,
        "current_parser_elapsed_ms": parse_elapsed_ms,
        "current_parser_model_version": snapshot.model_version,
        "current_parser_score_timestamp": snapshot.score_timestamp.isoformat(),
        "current_parser_row_count": snapshot.row_count,
        "current_silver_serialization_attempted": True,
        "current_silver_row_count": write_result.row_count,
        "current_silver_size_bytes": write_result.size_bytes,
        "current_silver_write_elapsed_ms": write_elapsed_ms,
        "current_parse_plus_silver_elapsed_ms": round(parse_elapsed_ms + write_elapsed_ms, 3),
        "python_tracemalloc_peak_bytes": peak,
    }


def _probe_sample(
    *,
    commit: str,
    sample: Sample,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Download and inspect one immutable model-era sample."""
    metadata = _content_metadata(
        commit=commit,
        sample=sample,
        timeout_seconds=timeout_seconds,
    )
    raw_url = f"{RAW_GITHUB}/{REPOSITORY}/{commit}/{sample.path}"
    payload, download_elapsed_ms = _request_bytes(
        raw_url,
        timeout_seconds=timeout_seconds,
    )

    if len(payload) != metadata["size"]:
        raise SourceProbeError(
            f"{sample.path}: downloaded size {len(payload)} != GitHub metadata {metadata['size']}"
        )
    git_blob_sha = _git_blob_sha1(payload)
    if git_blob_sha != metadata["blob_sha"]:
        raise SourceProbeError(
            f"{sample.path}: exact bytes do not match pinned Git blob identity"
        )

    decompress_started = time.perf_counter()
    try:
        decompressed = gzip.decompress(payload)
    except (gzip.BadGzipFile, EOFError, OSError) as exc:
        raise SourceProbeError(f"{sample.path}: invalid gzip payload") from exc
    decompress_elapsed_ms = round((time.perf_counter() - decompress_started) * 1000, 3)
    lines = _decode_lines(decompressed)
    if not lines:
        raise SourceProbeError(f"{sample.path}: decompressed file is empty")

    first_line = lines[0].strip()
    has_metadata_comment = first_line.startswith("#")
    metadata_line = first_line if has_metadata_comment else None
    header_index = 1 if has_metadata_comment else 0
    if len(lines) <= header_index:
        raise SourceProbeError(f"{sample.path}: missing CSV header")
    header_line = lines[header_index].strip()
    data_row_count = len(lines) - header_index - 1
    source_metadata = _parse_comment_metadata(metadata_line)
    source_score_date = None if source_metadata is None else source_metadata.get("score_date")
    source_model_version = (
        None if source_metadata is None else source_metadata.get("model_version")
    )

    score_date_matches_archive_date: bool | None = None
    if source_score_date is not None:
        score_date_matches_archive_date = source_score_date[:10] == sample.snapshot_date.isoformat()

    result = {
        "era": sample.era,
        "archive_date": sample.snapshot_date.isoformat(),
        "archive_path": sample.path,
        "pinned_blob_sha1": metadata["blob_sha"],
        "exact_blob_identity_verified": True,
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "compressed_bytes": len(payload),
        "uncompressed_bytes": len(decompressed),
        "compression_ratio_uncompressed_over_compressed": round(
            len(decompressed) / len(payload),
            3,
        ),
        "download_elapsed_ms": download_elapsed_ms,
        "decompress_elapsed_ms": decompress_elapsed_ms,
        "line_count": len(lines),
        "data_row_count_by_physical_layout": data_row_count,
        "has_metadata_comment": has_metadata_comment,
        "source_metadata": source_metadata,
        "source_declared_model_version": source_model_version,
        "source_declared_score_date": source_score_date,
        "source_score_date_matches_archive_date": score_date_matches_archive_date,
        "csv_header": header_line,
    }
    result.update(_measure_current_pipeline(payload))
    return result


def main() -> None:
    """Run the bounded five-file immutable source compatibility probe."""
    args = parse_args()
    commit = args.commit.strip()
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ValueError("commit must be a lowercase 40-character Git SHA")
    if args.timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be positive")

    samples = [
        _probe_sample(
            commit=commit,
            sample=sample,
            timeout_seconds=args.timeout_seconds,
        )
        for sample in SAMPLES
    ]

    accepted = [item["era"] for item in samples if item["current_parser_accepts"]]
    rejected = [item["era"] for item in samples if not item["current_parser_accepts"]]
    output = {
        "schema_version": 1,
        "read_only": True,
        "repository": REPOSITORY,
        "commit": commit,
        "sample_strategy": "first published archive snapshot for each documented EPSS model era",
        "sample_count": len(samples),
        "third_party_code_executed": False,
        "source_data_files_downloaded": len(samples),
        "current_parser_accepted_eras": accepted,
        "current_parser_rejected_eras": rejected,
        "samples": samples,
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
