"""Parser and validator for FIRST EPSS gzip snapshots."""

import gzip
import hashlib
import io
from datetime import datetime

from opslens.ingestion.epss.domain.errors import InvalidEpssSnapshotError
from opslens.ingestion.epss.domain.models import EpssSnapshot


class EpssSnapshotParser:
    """Parse and validate raw FIRST EPSS snapshot artifacts."""

    EXPECTED_HEADER = "cve,epss,percentile"
    REQUIRED_METADATA_FIELDS = frozenset({"model_version", "score_date"})

    def parse(self, payload: bytes) -> EpssSnapshot:
        """Parse raw gzip bytes into a validated EPSS snapshot.

        Args:
            payload: Original gzip-compressed EPSS artifact.

        Returns:
            A validated immutable EPSS snapshot.

        Raises:
            InvalidEpssSnapshotError: If the artifact is empty, invalid,
                malformed, or does not satisfy the expected EPSS contract.
        """
        if not payload:
            raise InvalidEpssSnapshotError("EPSS snapshot payload is empty.")

        decompressed = self._decompress(payload)

        stream = io.BytesIO(decompressed)

        metadata_line = self._decode_line(
            stream.readline(),
            description="metadata",
        )
        header_line = self._decode_line(
            stream.readline(),
            description="CSV header",
        )

        if header_line != self.EXPECTED_HEADER:
            raise InvalidEpssSnapshotError(
                "Unexpected EPSS CSV header. "
                f"Expected '{self.EXPECTED_HEADER}', received '{header_line}'."
            )

        metadata = self._parse_metadata(metadata_line)

        model_version = metadata["model_version"]
        score_timestamp = self._parse_score_timestamp(metadata["score_date"])
        row_count = self._count_data_rows(decompressed)

        if row_count <= 0:
            raise InvalidEpssSnapshotError("EPSS snapshot does not contain data rows.")

        return EpssSnapshot(
            raw_bytes=payload,
            model_version=model_version,
            score_timestamp=score_timestamp,
            sha256=hashlib.sha256(payload).hexdigest(),
            row_count=row_count,
        )

    @staticmethod
    def _decompress(payload: bytes) -> bytes:
        """Decompress and validate the complete gzip artifact."""
        try:
            return gzip.decompress(payload)
        except (gzip.BadGzipFile, EOFError, OSError) as exc:
            raise InvalidEpssSnapshotError("EPSS snapshot is not a valid gzip artifact.") from exc

    @staticmethod
    def _decode_line(raw_line: bytes, description: str) -> str:
        """Decode and normalize one UTF-8 line from the source artifact."""
        if not raw_line:
            raise InvalidEpssSnapshotError(f"EPSS snapshot is missing the {description} line.")

        try:
            return raw_line.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise InvalidEpssSnapshotError(f"EPSS {description} line is not valid UTF-8.") from exc

    def _parse_metadata(self, metadata_line: str) -> dict[str, str]:
        """Parse metadata fields from the FIRST EPSS comment line."""
        if not metadata_line.startswith("#"):
            raise InvalidEpssSnapshotError("EPSS metadata line must start with '#'.")

        raw_fields = metadata_line.removeprefix("#").split(",")
        metadata: dict[str, str] = {}

        for raw_field in raw_fields:
            if ":" not in raw_field:
                raise InvalidEpssSnapshotError(f"Malformed EPSS metadata field: '{raw_field}'.")

            key, value = raw_field.split(":", maxsplit=1)

            key = key.strip()
            value = value.strip()

            if not key or not value:
                raise InvalidEpssSnapshotError(f"Malformed EPSS metadata field: '{raw_field}'.")

            metadata[key] = value

        missing_fields = self.REQUIRED_METADATA_FIELDS - metadata.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise InvalidEpssSnapshotError(f"EPSS metadata is missing required fields: {missing}.")

        return metadata

    @staticmethod
    def _parse_score_timestamp(value: str) -> datetime:
        """Parse the EPSS source timestamp as a timezone-aware datetime."""
        normalized_value = f"{value[:-1]}+00:00" if value.endswith("Z") else value

        try:
            score_timestamp = datetime.fromisoformat(normalized_value)
        except ValueError as exc:
            raise InvalidEpssSnapshotError(f"Invalid EPSS score_date value: '{value}'.") from exc

        if score_timestamp.tzinfo is None:
            raise InvalidEpssSnapshotError("EPSS score_date must include timezone information.")

        return score_timestamp

    @staticmethod
    def _count_data_rows(decompressed: bytes) -> int:
        """Count EPSS rows without allocating a list for every line."""
        total_lines = decompressed.count(b"\n")

        if decompressed and not decompressed.endswith(b"\n"):
            total_lines += 1

        metadata_and_header_lines = 2

        return max(total_lines - metadata_and_header_lines, 0)
