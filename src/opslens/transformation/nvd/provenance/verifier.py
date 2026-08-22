"""Fail-closed verification of exact persisted NVD Bronze evidence."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast

from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)
from opslens.transformation.nvd.provenance.errors import (
    InvalidNvdBronzeEvidenceError,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
    NvdBronzeObjectReferenceV1,
    NvdBronzeObjectRole,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverProvenanceV1,
    NvdSilverSourceKind,
)


class NvdBronzeEvidenceVerifierV1:
    """Verify COMPLETE manifests against exact persisted object bytes."""

    def verify_incremental(
        self,
        *,
        manifest_key: str,
        manifest_version_id: str,
        manifest_bytes: bytes,
        object_payloads: tuple[NvdBronzeObjectPayloadV1, ...],
    ) -> VerifiedNvdBronzeEvidenceV1:
        """Verify one complete incremental Bronze update batch."""
        document = self._parse_canonical_manifest(manifest_bytes)

        self._require_literal(
            document,
            "completion_status",
            "complete",
        )
        self._require_literal(
            document,
            "manifest_version",
            "1",
        )
        self._require_literal(
            document,
            "source",
            "nvd-cve",
        )
        self._require_literal(
            document,
            "source_interface",
            "cve-api-2.0",
        )
        self._require_literal(
            document,
            "source_format",
            "NVD_CVE",
        )
        self._require_literal(
            document,
            "source_version",
            "2.0",
        )

        update_id = self._required_string(
            document,
            "update_id",
        )

        if not self._is_sha256(update_id):
            raise InvalidNvdBronzeEvidenceError(
                "NVD incremental update_id must be a lowercase SHA-256 digest."
            )

        window_start_at = self._required_timestamp(
            document,
            "window_start_at",
            allow_naive_utc=False,
        )
        window_end_at = self._required_timestamp(
            document,
            "window_end_at",
            allow_naive_utc=False,
        )

        window = NvdIncrementalWindow(
            start_at=window_start_at,
            end_at=window_end_at,
        )

        if window.update_id != update_id:
            raise InvalidNvdBronzeEvidenceError(
                "NVD incremental manifest update_id does not match "
                "its deterministic window identity."
            )

        expected_manifest_suffix = f"/update_id={update_id}/manifest.json"

        if not manifest_key.endswith(expected_manifest_suffix):
            raise InvalidNvdBronzeEvidenceError(
                "NVD incremental manifest key does not match update_id."
            )

        total_results = self._required_int(
            document,
            "total_results",
            minimum=0,
        )
        page_count = self._required_int(
            document,
            "page_count",
            minimum=1,
        )
        page_values = self._required_array(
            document,
            "pages",
        )

        if len(page_values) != page_count:
            raise InvalidNvdBronzeEvidenceError(
                "NVD incremental manifest page_count does not match the page inventory."
            )

        manifest_base = manifest_key.removesuffix("/manifest.json")

        references: list[NvdBronzeObjectReferenceV1] = []
        expected_start = 0

        for index, page_value in enumerate(page_values):
            page = self._object(
                page_value,
                context=f"pages[{index}]",
            )

            page_start = self._required_int(
                page,
                "start_index",
                minimum=0,
            )
            results_per_page = self._required_int(
                page,
                "results_per_page",
                minimum=0,
            )
            page_total_results = self._required_int(
                page,
                "total_results",
                minimum=0,
            )

            if page_total_results != total_results:
                raise InvalidNvdBronzeEvidenceError(
                    "NVD incremental page total_results does not match manifest total_results."
                )

            if page_start != expected_start:
                raise InvalidNvdBronzeEvidenceError(
                    "NVD incremental page inventory is not contiguous."
                )

            if total_results > 0 and results_per_page == 0:
                raise InvalidNvdBronzeEvidenceError(
                    "NVD incremental non-empty result contains an empty page."
                )

            expected_key = f"{manifest_base}/page_start={page_start:06d}/response.json"
            page_key = self._required_string(
                page,
                "key",
            )

            if page_key != expected_key:
                raise InvalidNvdBronzeEvidenceError(
                    "NVD incremental page key does not match the deterministic page coordinate."
                )

            reference = NvdBronzeObjectReferenceV1(
                role=NvdBronzeObjectRole.PAGE,
                key=page_key,
                version_id=self._required_string(
                    page,
                    "version_id",
                ),
                size_bytes=self._required_int(
                    page,
                    "size_bytes",
                    minimum=1,
                ),
                sha256=self._required_sha256(
                    page,
                    "sha256",
                ),
                page_start=page_start,
                source_timestamp=self._required_string(
                    page,
                    "source_timestamp",
                ),
            )

            references.append(reference)
            expected_start += results_per_page

        if expected_start != total_results:
            raise InvalidNvdBronzeEvidenceError(
                "NVD incremental page inventory does not reach total_results."
            )

        if total_results == 0:
            if len(references) != 1:
                raise InvalidNvdBronzeEvidenceError(
                    "Empty NVD incremental result requires one page."
                )

            only_page = page_values[0]
            page = self._object(
                only_page,
                context="pages[0]",
            )

            if (
                self._required_int(
                    page,
                    "start_index",
                    minimum=0,
                )
                != 0
                or self._required_int(
                    page,
                    "results_per_page",
                    minimum=0,
                )
                != 0
            ):
                raise InvalidNvdBronzeEvidenceError("Empty NVD incremental page is invalid.")

        reference_tuple = tuple(references)

        self._verify_object_inventory(
            references=reference_tuple,
            payloads=object_payloads,
        )

        return VerifiedNvdBronzeEvidenceV1(
            source_kind=NvdSilverSourceKind.INCREMENTAL,
            source_batch_id=update_id,
            manifest_key=manifest_key,
            manifest_version_id=self._required_coordinate(
                manifest_version_id,
                "manifest VersionId",
            ),
            manifest_sha256=sha256(manifest_bytes).hexdigest(),
            manifest_size_bytes=len(manifest_bytes),
            objects=reference_tuple,
            bootstrap_feed_year=None,
            bootstrap_feed_revision=None,
            bootstrap_source_observed_at=None,
            incremental_update_id=update_id,
            incremental_window_start_at=window.start_at,
            incremental_window_end_at=window.end_at,
        )

    def verify_bootstrap(
        self,
        *,
        manifest_key: str,
        manifest_version_id: str,
        manifest_bytes: bytes,
        object_payloads: tuple[NvdBronzeObjectPayloadV1, ...],
    ) -> VerifiedNvdBronzeEvidenceV1:
        """Verify one complete yearly-feed bootstrap source revision."""
        document = self._parse_canonical_manifest(manifest_bytes)

        self._require_literal(
            document,
            "completion_status",
            "complete",
        )
        self._require_literal(
            document,
            "manifest_version",
            "1",
        )
        self._require_literal(
            document,
            "source",
            "nvd-cve",
        )
        self._require_literal(
            document,
            "source_interface",
            "json-2.0-yearly-feed",
        )

        feed_year = self._required_int(
            document,
            "feed_year",
            minimum=1000,
        )

        if feed_year > 9999:
            raise InvalidNvdBronzeEvidenceError("NVD bootstrap feed_year must contain four digits.")

        feed_revision = self._required_string(
            document,
            "feed_revision",
        )

        source_observed_at = self._required_timestamp(
            document,
            "source_last_modified_at",
            allow_naive_utc=False,
        )

        expected_suffix = f"/feed_year={feed_year}/feed_revision={feed_revision}/manifest.json"

        if not manifest_key.endswith(expected_suffix):
            raise InvalidNvdBronzeEvidenceError(
                "NVD bootstrap manifest key does not match feed identity."
            )

        manifest_base = manifest_key.removesuffix("/manifest.json")
        source_name = f"nvdcve-2.0-{feed_year}"

        feed_reference = self._stored_object(
            document,
            field_name="feed_object",
            role=NvdBronzeObjectRole.FEED,
        )
        meta_reference = self._stored_object(
            document,
            field_name="meta_object",
            role=NvdBronzeObjectRole.META,
        )

        if feed_reference.key != f"{manifest_base}/{source_name}.json.gz":
            raise InvalidNvdBronzeEvidenceError(
                "NVD bootstrap feed key does not match the deterministic feed identity."
            )

        if meta_reference.key != f"{manifest_base}/{source_name}.meta":
            raise InvalidNvdBronzeEvidenceError(
                "NVD bootstrap META key does not match the deterministic feed identity."
            )

        references = (
            feed_reference,
            meta_reference,
        )

        self._verify_object_inventory(
            references=references,
            payloads=object_payloads,
        )

        source_batch_id = f"feed_year={feed_year}/feed_revision={feed_revision}"

        return VerifiedNvdBronzeEvidenceV1(
            source_kind=NvdSilverSourceKind.BOOTSTRAP,
            source_batch_id=source_batch_id,
            manifest_key=manifest_key,
            manifest_version_id=self._required_coordinate(
                manifest_version_id,
                "manifest VersionId",
            ),
            manifest_sha256=sha256(manifest_bytes).hexdigest(),
            manifest_size_bytes=len(manifest_bytes),
            objects=references,
            bootstrap_feed_year=feed_year,
            bootstrap_feed_revision=feed_revision,
            bootstrap_source_observed_at=source_observed_at,
            incremental_update_id=None,
            incremental_window_start_at=None,
            incremental_window_end_at=None,
        )

    def _stored_object(
        self,
        document: dict[str, object],
        *,
        field_name: str,
        role: NvdBronzeObjectRole,
    ) -> NvdBronzeObjectReferenceV1:
        """Read one stored-object reference from a bootstrap manifest."""
        value = document.get(field_name)

        stored = self._object(
            value,
            context=field_name,
        )

        return NvdBronzeObjectReferenceV1(
            role=role,
            key=self._required_string(
                stored,
                "key",
            ),
            version_id=self._required_string(
                stored,
                "version_id",
            ),
            size_bytes=self._required_int(
                stored,
                "size_bytes",
                minimum=1,
            ),
            sha256=self._required_sha256(
                stored,
                "sha256",
            ),
            page_start=None,
            source_timestamp=None,
        )

    def _verify_object_inventory(
        self,
        *,
        references: tuple[NvdBronzeObjectReferenceV1, ...],
        payloads: tuple[NvdBronzeObjectPayloadV1, ...],
    ) -> None:
        """Require exact equality between manifest and supplied objects."""
        payload_by_key: dict[str, NvdBronzeObjectPayloadV1] = {}

        for payload in payloads:
            if payload.key in payload_by_key:
                raise InvalidNvdBronzeEvidenceError("Duplicate NVD Bronze payload key supplied.")

            payload_by_key[payload.key] = payload

        expected_keys = {reference.key for reference in references}

        supplied_keys = set(payload_by_key)

        missing = expected_keys - supplied_keys
        unexpected = supplied_keys - expected_keys

        if missing:
            raise InvalidNvdBronzeEvidenceError("NVD Bronze object inventory is incomplete.")

        if unexpected:
            raise InvalidNvdBronzeEvidenceError(
                "NVD Bronze object inventory contains unexpected objects."
            )

        for reference in references:
            payload = payload_by_key[reference.key]

            if payload.version_id != reference.version_id:
                raise InvalidNvdBronzeEvidenceError(
                    f"NVD Bronze VersionId mismatch for {reference.key!r}."
                )

            if len(payload.raw_bytes) != reference.size_bytes:
                raise InvalidNvdBronzeEvidenceError(
                    f"NVD Bronze size mismatch for {reference.key!r}."
                )

            actual_sha256 = sha256(payload.raw_bytes).hexdigest()

            if actual_sha256 != reference.sha256:
                raise InvalidNvdBronzeEvidenceError(
                    f"NVD Bronze SHA-256 mismatch for {reference.key!r}."
                )

    @staticmethod
    def _parse_canonical_manifest(
        raw_bytes: bytes,
    ) -> dict[str, object]:
        """Parse one manifest only if its exact bytes use canonical v1 JSON."""
        if not raw_bytes:
            raise InvalidNvdBronzeEvidenceError("NVD Bronze manifest bytes cannot be empty.")

        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidNvdBronzeEvidenceError("NVD Bronze manifest must be UTF-8.") from exc

        def reject_constant(value: str) -> object:
            raise ValueError(f"Non-finite JSON constant {value!r} is not allowed.")

        def unique_object(
            pairs: list[tuple[str, object]],
        ) -> dict[str, object]:
            result: dict[str, object] = {}

            for key, value in pairs:
                if key in result:
                    raise ValueError(f"Duplicate JSON key {key!r}.")

                result[key] = value

            return result

        try:
            parsed = cast(
                object,
                json.loads(
                    text,
                    parse_constant=reject_constant,
                    object_pairs_hook=unique_object,
                ),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise InvalidNvdBronzeEvidenceError(
                "NVD Bronze manifest contains invalid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise InvalidNvdBronzeEvidenceError("NVD Bronze manifest must contain a JSON object.")

        document = cast(
            dict[str, object],
            parsed,
        )

        canonical = (
            json.dumps(
                document,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8")

        if canonical != raw_bytes:
            raise InvalidNvdBronzeEvidenceError(
                "NVD Bronze manifest does not use its canonical manifest encoding."
            )

        return document

    @staticmethod
    def _object(
        value: object,
        *,
        context: str,
    ) -> dict[str, object]:
        """Require one JSON object."""
        if not isinstance(value, dict):
            raise InvalidNvdBronzeEvidenceError(f"NVD Bronze {context} must be an object.")

        return cast(
            dict[str, object],
            value,
        )

    @staticmethod
    def _required_array(
        document: dict[str, object],
        field_name: str,
    ) -> list[object]:
        """Read one required JSON array."""
        if field_name not in document:
            raise InvalidNvdBronzeEvidenceError(f"NVD Bronze manifest is missing {field_name!r}.")

        value = document[field_name]

        if not isinstance(value, list):
            raise InvalidNvdBronzeEvidenceError(f"NVD Bronze {field_name} must be an array.")

        return cast(
            list[object],
            value,
        )

    @staticmethod
    def _required_string(
        document: dict[str, object],
        field_name: str,
    ) -> str:
        """Read one required non-empty string."""
        value = document.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise InvalidNvdBronzeEvidenceError(
                f"NVD Bronze {field_name} must be a non-empty string."
            )

        return value

    @classmethod
    def _required_sha256(
        cls,
        document: dict[str, object],
        field_name: str,
    ) -> str:
        """Read one required lowercase SHA-256 digest."""
        value = cls._required_string(
            document,
            field_name,
        )

        if not cls._is_sha256(value):
            raise InvalidNvdBronzeEvidenceError(
                f"NVD Bronze {field_name} must be a lowercase SHA-256 digest."
            )

        return value

    @staticmethod
    def _is_sha256(value: str) -> bool:
        """Return whether text is a lowercase SHA-256 digest."""
        return len(value) == 64 and all(character in "0123456789abcdef" for character in value)

    @staticmethod
    def _required_int(
        document: dict[str, object],
        field_name: str,
        *,
        minimum: int,
    ) -> int:
        """Read one required bounded JSON integer."""
        value = document.get(field_name)

        if type(value) is not int:
            raise InvalidNvdBronzeEvidenceError(f"NVD Bronze {field_name} must be an integer.")

        if value < minimum:
            raise InvalidNvdBronzeEvidenceError(f"NVD Bronze {field_name} must be >= {minimum}.")

        return value

    @classmethod
    def _required_timestamp(
        cls,
        document: dict[str, object],
        field_name: str,
        *,
        allow_naive_utc: bool,
    ) -> datetime:
        """Parse one source timestamp into UTC."""
        value = cls._required_string(
            document,
            field_name,
        )

        return cls.parse_source_timestamp(
            value,
            field_name=field_name,
            allow_naive_utc=allow_naive_utc,
        )

    @staticmethod
    def parse_source_timestamp(
        value: str,
        *,
        field_name: str,
        allow_naive_utc: bool,
    ) -> datetime:
        """Parse ISO timestamp, optionally treating NVD naive time as UTC."""
        normalized = value

        if value.endswith("Z"):
            normalized = f"{value[:-1]}+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise InvalidNvdBronzeEvidenceError(
                f"NVD Bronze {field_name} is not a valid timestamp."
            ) from exc

        if parsed.tzinfo is None or parsed.utcoffset() is None:
            if not allow_naive_utc:
                raise InvalidNvdBronzeEvidenceError(
                    f"NVD Bronze {field_name} must be timezone-aware."
                )

            parsed = parsed.replace(
                tzinfo=UTC,
            )

        return parsed.astimezone(UTC)

    @classmethod
    def _require_literal(
        cls,
        document: dict[str, object],
        field_name: str,
        expected: str,
    ) -> None:
        """Require one exact internal manifest contract value."""
        actual = cls._required_string(
            document,
            field_name,
        )

        if actual != expected:
            raise InvalidNvdBronzeEvidenceError(f"NVD Bronze {field_name} must be {expected!r}.")

    @staticmethod
    def _required_coordinate(
        value: str,
        field_name: str,
    ) -> str:
        """Validate one externally supplied exact S3 coordinate."""
        if not value.strip():
            raise InvalidNvdBronzeEvidenceError(f"NVD Bronze {field_name} cannot be empty.")

        return value


class NvdSilverProvenanceFactoryV1:
    """Build Silver provenance only from fully verified Bronze evidence."""

    def build(
        self,
        *,
        evidence: VerifiedNvdBronzeEvidenceV1,
        bronze_object_key: str,
        record_index: int,
    ) -> NvdSilverProvenanceV1:
        """Bind one Silver observation to an exact verified Bronze object."""
        reference = evidence.object_by_key(bronze_object_key)

        if evidence.source_kind is NvdSilverSourceKind.BOOTSTRAP:
            if reference.role is not NvdBronzeObjectRole.FEED:
                raise InvalidNvdBronzeEvidenceError(
                    "Bootstrap CVE records must originate from the verified feed object."
                )

            source_observed_at = evidence.bootstrap_source_observed_at

            if source_observed_at is None:
                raise InvalidNvdBronzeEvidenceError(
                    "Verified bootstrap source timestamp is missing."
                )

            bootstrap_feed_year = evidence.bootstrap_feed_year
            bootstrap_feed_revision = evidence.bootstrap_feed_revision
            incremental_update_id = None
            incremental_page_start = None

        else:
            if reference.role is not NvdBronzeObjectRole.PAGE:
                raise InvalidNvdBronzeEvidenceError(
                    "Incremental CVE records must originate from a verified page object."
                )

            if reference.source_timestamp is None:
                raise InvalidNvdBronzeEvidenceError(
                    "Verified incremental page timestamp is missing."
                )

            source_observed_at = NvdBronzeEvidenceVerifierV1.parse_source_timestamp(
                reference.source_timestamp,
                field_name="source_timestamp",
                allow_naive_utc=True,
            )

            bootstrap_feed_year = None
            bootstrap_feed_revision = None
            incremental_update_id = evidence.incremental_update_id
            incremental_page_start = reference.page_start

        observation_id = self.build_observation_id(
            evidence=evidence,
            reference=reference,
            record_index=record_index,
        )

        return NvdSilverProvenanceV1(
            source_kind=evidence.source_kind,
            source_batch_id=evidence.source_batch_id,
            observation_id=observation_id,
            source_observed_at=source_observed_at,
            bronze_manifest_key=evidence.manifest_key,
            bronze_manifest_version_id=(evidence.manifest_version_id),
            bronze_manifest_sha256=evidence.manifest_sha256,
            bronze_object_key=reference.key,
            bronze_object_version_id=reference.version_id,
            bronze_object_sha256=reference.sha256,
            bronze_record_index=record_index,
            bootstrap_feed_year=bootstrap_feed_year,
            bootstrap_feed_revision=bootstrap_feed_revision,
            incremental_update_id=incremental_update_id,
            incremental_page_start=incremental_page_start,
        )

    @staticmethod
    def build_observation_id(
        *,
        evidence: VerifiedNvdBronzeEvidenceV1,
        reference: NvdBronzeObjectReferenceV1,
        record_index: int,
    ) -> str:
        """Derive occurrence identity from exact Bronze evidence."""
        if type(record_index) is not int or record_index < 0:
            raise InvalidNvdBronzeEvidenceError("NVD Bronze record_index must be non-negative.")

        verified_reference = evidence.object_by_key(reference.key)

        if verified_reference != reference:
            raise InvalidNvdBronzeEvidenceError(
                "Observation reference is not part of verified evidence."
            )

        payload = (
            "opslens-nvd-observation-v1\n"
            f"source_kind={evidence.source_kind.value}\n"
            f"source_batch_id={evidence.source_batch_id}\n"
            f"manifest_key={evidence.manifest_key}\n"
            f"manifest_version_id={evidence.manifest_version_id}\n"
            f"manifest_sha256={evidence.manifest_sha256}\n"
            f"object_key={reference.key}\n"
            f"object_version_id={reference.version_id}\n"
            f"object_sha256={reference.sha256}\n"
            f"record_index={record_index}\n"
        ).encode()

        return sha256(payload).hexdigest()
