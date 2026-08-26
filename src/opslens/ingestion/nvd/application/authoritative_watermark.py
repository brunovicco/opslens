"""Authoritative committed-watermark contract for NVD incremental ingestion."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar, cast

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _canonical_utc(value: datetime) -> str:
    """Serialize one timezone-aware timestamp deterministically."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("NVD watermark timestamp must be timezone-aware.")

    normalized = value.astimezone(UTC)
    timespec = "microseconds" if normalized.microsecond else "seconds"

    return normalized.isoformat(timespec=timespec).replace("+00:00", "Z")


def _normalize_utc(
    value: datetime,
    *,
    label: str,
) -> datetime:
    """Require timezone evidence and normalize one instant to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"NVD {label} must be timezone-aware.")

    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class NvdWatermarkEvidenceObjectV1:
    """Identify one exact persisted object supporting a watermark commit."""

    key: str
    version_id: str
    sha256: str

    def __post_init__(self) -> None:
        """Validate exact persisted-object identity."""
        if not self.key.strip():
            raise ValueError("NVD watermark evidence object key cannot be empty.")

        if not self.version_id.strip():
            raise ValueError(
                "NVD watermark evidence object VersionId cannot be empty."
            )

        if _SHA256_PATTERN.fullmatch(self.sha256) is None:
            raise ValueError(
                "NVD watermark evidence object SHA-256 must contain "
                "exactly 64 lowercase hexadecimal characters."
            )


@dataclass(frozen=True, slots=True)
class NvdWatermarkBootstrapRecoverySeedV1:
    """Explain the initial committed boundary recovered from Bootstrap evidence.

    The originally intended pre-bootstrap T0 was not persisted by the first
    runtime implementation. The recovery seed therefore uses the exact source
    revision represented by the successfully persisted Bootstrap COMPLETE
    evidence.

    This intentionally prefers overlap over a temporal gap.
    """

    KIND: ClassVar[str] = "bootstrap_source_revision_recovery_seed"
    RECOVERY_REASON: ClassVar[str] = (
        "original_bootstrap_boundary_not_persisted"
    )

    source_revision_at: datetime
    bootstrap_manifest: NvdWatermarkEvidenceObjectV1

    def __post_init__(self) -> None:
        """Normalize the source revision used as the recovery boundary."""
        object.__setattr__(
            self,
            "source_revision_at",
            _normalize_utc(
                self.source_revision_at,
                label="Bootstrap recovery source revision",
            ),
        )

    @property
    def canonical_source_revision_at(self) -> str:
        """Return the canonical source revision boundary."""
        return _canonical_utc(self.source_revision_at)


@dataclass(frozen=True, slots=True)
class NvdWatermarkSilverPromotionCommitV1:
    """Explain one authoritative advancement authorized by Silver evidence."""

    KIND: ClassVar[str] = "silver_complete_promotion"

    previous_committed_through_at: datetime
    update_id: str

    bronze_manifest: NvdWatermarkEvidenceObjectV1
    silver_manifest: NvdWatermarkEvidenceObjectV1
    silver_parquet: NvdWatermarkEvidenceObjectV1

    logical_record_set_sha256: str

    def __post_init__(self) -> None:
        """Validate immutable promotion evidence."""
        object.__setattr__(
            self,
            "previous_committed_through_at",
            _normalize_utc(
                self.previous_committed_through_at,
                label="previous committed watermark",
            ),
        )

        if _SHA256_PATTERN.fullmatch(self.update_id) is None:
            raise ValueError(
                "NVD watermark promotion update id must contain "
                "exactly 64 lowercase hexadecimal characters."
            )

        if _SHA256_PATTERN.fullmatch(
            self.logical_record_set_sha256
        ) is None:
            raise ValueError(
                "NVD watermark logical record-set SHA-256 must contain "
                "exactly 64 lowercase hexadecimal characters."
            )

    @property
    def canonical_previous_committed_through_at(self) -> str:
        """Return the canonical previous committed boundary."""
        return _canonical_utc(self.previous_committed_through_at)


NvdWatermarkCommitBasisV1 = (
    NvdWatermarkBootstrapRecoverySeedV1
    | NvdWatermarkSilverPromotionCommitV1
)


@dataclass(frozen=True, slots=True)
class NvdAuthoritativeWatermarkV1:
    """Represent the single authoritative NVD incremental boundary."""

    WATERMARK_VERSION: ClassVar[str] = "1"
    STATE: ClassVar[str] = "committed"
    SOURCE: ClassVar[str] = "nvd-cve"
    SOURCE_INTERFACE: ClassVar[str] = "cve-api-2.0"

    committed_through_at: datetime
    commit_basis: NvdWatermarkCommitBasisV1

    def __post_init__(self) -> None:
        """Validate committed-state invariants."""
        committed = _normalize_utc(
            self.committed_through_at,
            label="authoritative committed watermark",
        )

        object.__setattr__(
            self,
            "committed_through_at",
            committed,
        )

        if isinstance(
            self.commit_basis,
            NvdWatermarkBootstrapRecoverySeedV1,
        ):
            if committed != self.commit_basis.source_revision_at:
                raise ValueError(
                    "NVD Bootstrap recovery seed must commit exactly "
                    "the source revision boundary."
                )

            return

        if committed <= (
            self.commit_basis.previous_committed_through_at
        ):
            raise ValueError(
                "NVD promoted watermark must advance beyond "
                "the previous committed boundary."
            )

    @property
    def canonical_committed_through_at(self) -> str:
        """Return canonical authoritative boundary."""
        return _canonical_utc(self.committed_through_at)


class NvdAuthoritativeWatermarkSerializerV1:
    """Serialize authoritative watermark state deterministically."""

    def serialize(
        self,
        watermark: NvdAuthoritativeWatermarkV1,
    ) -> bytes:
        """Return canonical UTF-8 JSON bytes."""
        document: dict[str, object] = {
            "commit_basis": self._serialize_commit_basis(
                watermark.commit_basis
            ),
            "committed_through_at": (
                watermark.canonical_committed_through_at
            ),
            "source": watermark.SOURCE,
            "source_interface": watermark.SOURCE_INTERFACE,
            "state": watermark.STATE,
            "watermark_version": watermark.WATERMARK_VERSION,
        }

        text = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )

        return f"{text}\n".encode()

    @staticmethod
    def _serialize_object(
        value: NvdWatermarkEvidenceObjectV1,
    ) -> dict[str, object]:
        """Serialize one exact persisted-object reference."""
        return {
            "key": value.key,
            "sha256": value.sha256,
            "version_id": value.version_id,
        }

    def _serialize_commit_basis(
        self,
        basis: NvdWatermarkCommitBasisV1,
    ) -> dict[str, object]:
        """Serialize the discriminated commit basis."""
        if isinstance(
            basis,
            NvdWatermarkBootstrapRecoverySeedV1,
        ):
            return {
                "bootstrap_manifest": self._serialize_object(
                    basis.bootstrap_manifest
                ),
                "kind": basis.KIND,
                "recovery_reason": basis.RECOVERY_REASON,
                "source_revision_at": (
                    basis.canonical_source_revision_at
                ),
            }

        return {
            "bronze_manifest": self._serialize_object(
                basis.bronze_manifest
            ),
            "kind": basis.KIND,
            "logical_record_set_sha256": (
                basis.logical_record_set_sha256
            ),
            "previous_committed_through_at": (
                basis.canonical_previous_committed_through_at
            ),
            "silver_manifest": self._serialize_object(
                basis.silver_manifest
            ),
            "silver_parquet": self._serialize_object(
                basis.silver_parquet
            ),
            "update_id": basis.update_id,
        }


class NvdAuthoritativeWatermarkParserV1:
    """Parse only canonical persisted authoritative-watermark bytes."""

    _TOP_LEVEL_KEYS = frozenset(
        {
            "commit_basis",
            "committed_through_at",
            "source",
            "source_interface",
            "state",
            "watermark_version",
        }
    )

    _EVIDENCE_OBJECT_KEYS = frozenset(
        {
            "key",
            "sha256",
            "version_id",
        }
    )

    _BOOTSTRAP_BASIS_KEYS = frozenset(
        {
            "bootstrap_manifest",
            "kind",
            "recovery_reason",
            "source_revision_at",
        }
    )

    _PROMOTION_BASIS_KEYS = frozenset(
        {
            "bronze_manifest",
            "kind",
            "logical_record_set_sha256",
            "previous_committed_through_at",
            "silver_manifest",
            "silver_parquet",
            "update_id",
        }
    )

    def __init__(
        self,
        *,
        serializer: NvdAuthoritativeWatermarkSerializerV1 | None = None,
    ) -> None:
        """Initialize deterministic canonicalization dependency."""
        self._serializer = (
            serializer
            if serializer is not None
            else NvdAuthoritativeWatermarkSerializerV1()
        )

    def parse(
        self,
        payload: bytes,
    ) -> NvdAuthoritativeWatermarkV1:
        """Parse and verify one exact canonical watermark document."""
        if not payload:
            raise ValueError(
                "Authoritative NVD watermark payload cannot be empty."
            )

        try:
            text = payload.decode("utf-8")
            decoded = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "Authoritative NVD watermark is not valid UTF-8 JSON."
            ) from exc

        if not isinstance(decoded, dict):
            raise ValueError(
                "Authoritative NVD watermark must be a JSON object."
            )

        document = cast(dict[str, object], decoded)

        self._require_exact_keys(
            document,
            self._TOP_LEVEL_KEYS,
            "authoritative NVD watermark",
        )

        if (
            self._require_str(
                document,
                "watermark_version",
            )
            != NvdAuthoritativeWatermarkV1.WATERMARK_VERSION
        ):
            raise ValueError(
                "Unsupported authoritative NVD watermark version."
            )

        if (
            self._require_str(document, "state")
            != NvdAuthoritativeWatermarkV1.STATE
        ):
            raise ValueError(
                "Authoritative NVD watermark state is invalid."
            )

        if (
            self._require_str(document, "source")
            != NvdAuthoritativeWatermarkV1.SOURCE
        ):
            raise ValueError(
                "Authoritative NVD watermark source is invalid."
            )

        if (
            self._require_str(
                document,
                "source_interface",
            )
            != NvdAuthoritativeWatermarkV1.SOURCE_INTERFACE
        ):
            raise ValueError(
                "Authoritative NVD watermark source interface is invalid."
            )

        committed = self._parse_timestamp(
            self._require_str(
                document,
                "committed_through_at",
            ),
            label="committed_through_at",
        )

        basis_document = self._require_object(
            document,
            "commit_basis",
        )

        kind = self._require_str(
            basis_document,
            "kind",
        )

        if (
            kind
            == NvdWatermarkBootstrapRecoverySeedV1.KIND
        ):
            basis = self._parse_bootstrap_basis(
                basis_document
            )
        elif (
            kind
            == NvdWatermarkSilverPromotionCommitV1.KIND
        ):
            basis = self._parse_promotion_basis(
                basis_document
            )
        else:
            raise ValueError(
                "Authoritative NVD watermark commit basis kind is invalid."
            )

        watermark = NvdAuthoritativeWatermarkV1(
            committed_through_at=committed,
            commit_basis=basis,
        )

        if self._serializer.serialize(watermark) != payload:
            raise ValueError(
                "Authoritative NVD watermark payload is not canonical."
            )

        return watermark

    def _parse_bootstrap_basis(
        self,
        document: dict[str, object],
    ) -> NvdWatermarkBootstrapRecoverySeedV1:
        """Parse the one allowed recovery-seed basis."""
        self._require_exact_keys(
            document,
            self._BOOTSTRAP_BASIS_KEYS,
            "Bootstrap recovery commit basis",
        )

        if (
            self._require_str(
                document,
                "recovery_reason",
            )
            != NvdWatermarkBootstrapRecoverySeedV1.RECOVERY_REASON
        ):
            raise ValueError(
                "NVD Bootstrap recovery reason is invalid."
            )

        return NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=self._parse_timestamp(
                self._require_str(
                    document,
                    "source_revision_at",
                ),
                label="Bootstrap source revision",
            ),
            bootstrap_manifest=self._parse_evidence_object(
                self._require_object(
                    document,
                    "bootstrap_manifest",
                )
            ),
        )

    def _parse_promotion_basis(
        self,
        document: dict[str, object],
    ) -> NvdWatermarkSilverPromotionCommitV1:
        """Parse one Silver-authorized promotion basis."""
        self._require_exact_keys(
            document,
            self._PROMOTION_BASIS_KEYS,
            "Silver promotion commit basis",
        )

        return NvdWatermarkSilverPromotionCommitV1(
            previous_committed_through_at=self._parse_timestamp(
                self._require_str(
                    document,
                    "previous_committed_through_at",
                ),
                label="previous committed watermark",
            ),
            update_id=self._require_str(
                document,
                "update_id",
            ),
            bronze_manifest=self._parse_evidence_object(
                self._require_object(
                    document,
                    "bronze_manifest",
                )
            ),
            silver_manifest=self._parse_evidence_object(
                self._require_object(
                    document,
                    "silver_manifest",
                )
            ),
            silver_parquet=self._parse_evidence_object(
                self._require_object(
                    document,
                    "silver_parquet",
                )
            ),
            logical_record_set_sha256=self._require_str(
                document,
                "logical_record_set_sha256",
            ),
        )

    def _parse_evidence_object(
        self,
        document: dict[str, object],
    ) -> NvdWatermarkEvidenceObjectV1:
        """Parse one exact immutable evidence-object coordinate."""
        self._require_exact_keys(
            document,
            self._EVIDENCE_OBJECT_KEYS,
            "watermark evidence object",
        )

        return NvdWatermarkEvidenceObjectV1(
            key=self._require_str(document, "key"),
            version_id=self._require_str(
                document,
                "version_id",
            ),
            sha256=self._require_str(
                document,
                "sha256",
            ),
        )

    @staticmethod
    def _parse_timestamp(
        value: str,
        *,
        label: str,
    ) -> datetime:
        """Parse one ISO-8601 timestamp with explicit timezone."""
        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError(
                f"NVD {label} is not a valid ISO-8601 timestamp."
            ) from exc

        return _normalize_utc(
            parsed,
            label=label,
        )

    @staticmethod
    def _require_exact_keys(
        document: dict[str, object],
        expected: frozenset[str],
        label: str,
    ) -> None:
        """Reject missing or additive persisted-state fields."""
        actual = frozenset(document)

        if actual != expected:
            raise ValueError(
                f"{label} fields do not match the supported contract."
            )

    @staticmethod
    def _require_str(
        document: dict[str, object],
        key: str,
    ) -> str:
        """Read one required non-empty string."""
        value = document.get(key)

        if type(value) is not str or not value.strip():
            raise ValueError(
                f"Authoritative NVD watermark field {key!r} "
                "must be a non-empty string."
            )

        return value

    @staticmethod
    def _require_object(
        document: dict[str, object],
        key: str,
    ) -> dict[str, object]:
        """Read one required nested JSON object."""
        value = document.get(key)

        if not isinstance(value, dict):
            raise ValueError(
                f"Authoritative NVD watermark field {key!r} "
                "must be an object."
            )

        return cast(dict[str, object], value)
