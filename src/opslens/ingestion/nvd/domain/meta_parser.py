"""Parser for NVD yearly-feed META artifacts."""

from datetime import datetime

from opslens.ingestion.nvd.domain.errors import InvalidNvdFeedMetaError
from opslens.ingestion.nvd.domain.models import NvdFeedMeta


class NvdFeedMetaParser:
    """Parse and validate the minimum NVD yearly-feed META contract."""

    REQUIRED_FIELDS = frozenset(
        {
            "lastModifiedDate",
            "size",
            "zipSize",
            "gzSize",
            "sha256",
        }
    )

    def parse(self, payload: bytes) -> NvdFeedMeta:
        """Parse original META bytes into validated NVD source metadata.

        Unknown additive fields are preserved in the raw Bronze artifact but
        intentionally ignored by this minimum contract.

        Args:
            payload: Original META bytes received from NVD.

        Returns:
            Validated immutable NVD feed metadata.

        Raises:
            InvalidNvdFeedMetaError: If the required source contract is
                missing, malformed, duplicated, or internally invalid.
        """
        if not payload:
            raise InvalidNvdFeedMetaError("NVD feed META payload is empty.")

        values = self._parse_fields(payload)

        missing_fields = self.REQUIRED_FIELDS - values.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise InvalidNvdFeedMetaError(f"NVD feed META is missing required fields: {missing}.")

        last_modified_at = self._parse_datetime(values["lastModifiedDate"])

        uncompressed_size = self._parse_positive_integer(
            name="size",
            value=values["size"],
        )
        zip_size = self._parse_positive_integer(
            name="zipSize",
            value=values["zipSize"],
        )
        gzip_size = self._parse_positive_integer(
            name="gzSize",
            value=values["gzSize"],
        )

        source_sha256 = self._parse_sha256(values["sha256"])

        try:
            return NvdFeedMeta(
                raw_bytes=payload,
                last_modified_at=last_modified_at,
                uncompressed_size_bytes=uncompressed_size,
                zip_size_bytes=zip_size,
                gzip_size_bytes=gzip_size,
                source_sha256=source_sha256,
            )
        except ValueError as exc:
            raise InvalidNvdFeedMetaError(str(exc)) from exc

    @staticmethod
    def _parse_fields(payload: bytes) -> dict[str, str]:
        """Decode META bytes and return unique key-value fields."""
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidNvdFeedMetaError("NVD feed META payload is not valid UTF-8.") from exc

        values: dict[str, str] = {}

        for line_number, raw_line in enumerate(
            text.splitlines(),
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                continue

            if ":" not in line:
                raise InvalidNvdFeedMetaError(
                    f"NVD feed META line {line_number} does not contain a key-value separator."
                )

            key, value = line.split(":", 1)
            normalized_key = key.strip()
            normalized_value = value.strip()

            if not normalized_key or not normalized_value:
                raise InvalidNvdFeedMetaError(f"NVD feed META line {line_number} is malformed.")

            if normalized_key in values:
                raise InvalidNvdFeedMetaError(
                    f"NVD feed META contains duplicate field: {normalized_key}."
                )

            values[normalized_key] = normalized_value

        return values

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        """Parse NVD source timestamp and require timezone information."""
        normalized_value = f"{value[:-1]}+00:00" if value.endswith("Z") else value

        try:
            parsed = datetime.fromisoformat(normalized_value)
        except ValueError as exc:
            raise InvalidNvdFeedMetaError(
                f"Invalid NVD lastModifiedDate value: '{value}'."
            ) from exc

        if parsed.tzinfo is None:
            raise InvalidNvdFeedMetaError("NVD lastModifiedDate must include timezone information.")

        return parsed

    @staticmethod
    def _parse_positive_integer(
        *,
        name: str,
        value: str,
    ) -> int:
        """Parse one META size field as a strictly positive integer."""
        try:
            parsed = int(value)
        except ValueError as exc:
            raise InvalidNvdFeedMetaError(f"NVD feed META {name} must be an integer.") from exc

        if parsed <= 0:
            raise InvalidNvdFeedMetaError(f"NVD feed META {name} must be positive.")

        return parsed

    @staticmethod
    def _parse_sha256(value: str) -> str:
        """Normalize and validate the NVD source SHA-256 digest."""
        normalized = value.strip().lower()

        if len(normalized) != 64 or any(
            character not in "0123456789abcdef" for character in normalized
        ):
            raise InvalidNvdFeedMetaError(
                "NVD feed META sha256 must contain exactly 64 hexadecimal characters."
            )

        return normalized
