"""Read the live index back, refusing every way a read can be quietly incomplete.

Writing the index was the easy direction. Reading it has three ways to answer wrongly
without raising anything, and all three were observed on the first live generation
rather than imagined here.

**A page is not an answer.** A DynamoDB query stops at 1 MB and hands back a cursor.
The first index stores 1,078 bytes per item, so 973 fill a page and `tensorflow` alone
carries 1,323 rows: a caller that issues one query and ignores `LastEvaluatedKey` gets
973 advisories, no error, and no indication that 350 are missing.

```text
truncated page != complete answer
```

**A generation is not a table.** The partition key carries the generation prefix
(ADR 0088), so a build writes where nothing is reading and the pointer makes it live.
A request that resolves the pointer, then reads while a new pointer lands, would mix two
generations into one answer. Every item is therefore checked against the generation the
request resolved, not against whatever is live when the item arrives.

```text
the live generation at read != the live generation at request
```

**An empty key space is not an absence.** A pointer naming a generation whose rows were
never written, or expired, reads as "no known vulnerabilities" — the most dangerous
wrong answer this system can give. Two checks stand against it. A pointer is usable only
if its own generation agrees with the digest it names. And the manifest is re-derived
rather than trusted: rebuilding it from its stored payload reproduces a content-addressed
identity, which must equal the one the pointer named, so a manifest that was truncated,
edited or left over from another build cannot certify a key space.

```text
empty key space != no advisories
a manifest that parses != the manifest the pointer names
```

This module decodes and refuses. It issues no query and knows no table.

One bound is deliberately absent: nothing here caps how many rows a request may read.
Gate 21.1 sets that from a measured figure and must reject rather than trim. Until then
a read is complete or it fails, and never silently small.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from opslens.correlation_index.domain.index_contract import (
    CorrelationIndexContractError,
    CorrelationIndexManifest,
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
    ProjectedSourceIdentifier,
    SourceWatermark,
    ghsa_partition_key,
    index_generation,
    nvd_partition_key,
)

_POINTER_FIELDS: Final = ("built_at", "generation", "index_id")


class IndexReadError(ValueError):
    """Raised when a read cannot be trusted to be complete and of one generation."""


@dataclass(frozen=True, slots=True)
class LiveIndexGeneration:
    """The generation one request reads, resolved once and held for that request.

    Attributes:
        index_id: The manifest identity the pointer names.
        generation: The key-space prefix derived from that identity.
        built_at: When the build behind it ran.
    """

    index_id: str
    generation: str
    built_at: str

    def ghsa_key(self, package_name_canonical: str) -> str:
        """Return the GHSA partition key for one package in this generation.

        Args:
            package_name_canonical: The canonical name the request asks about.

        Returns:
            The partition key.

        Raises:
            CorrelationIndexContractError: If the name cannot be keyed.
        """
        return ghsa_partition_key(self.generation, package_name_canonical)

    def nvd_key(self, cve_id: str) -> str:
        """Return the NVD partition key for one CVE in this generation.

        Args:
            cve_id: The CVE identifier.

        Returns:
            The partition key.

        Raises:
            CorrelationIndexContractError: If the identifier cannot be keyed.
        """
        return nvd_partition_key(self.generation, cve_id)


@dataclass(frozen=True, slots=True)
class IndexQueryPage:
    """One page of a paginated index query, exactly as the store returned it.

    Attributes:
        items: The items on this page.
        last_evaluated_key: The store's cursor, or `None` when the page is the last.
    """

    items: tuple[Mapping[str, object], ...]
    last_evaluated_key: Mapping[str, object] | None


def read_pointer(document: Mapping[str, object]) -> LiveIndexGeneration:
    """Resolve the live generation from the pointer object.

    The pointer states the generation and the identity separately, so the two can
    disagree. They must not: a pointer naming one identity and a different generation
    sends every read into a key space that build never wrote, which returns nothing and
    reads as an absence of vulnerabilities.

    Args:
        document: The parsed pointer object.

    Returns:
        The generation this request reads.

    Raises:
        IndexReadError: If the pointer is malformed or internally inconsistent.
    """
    values: dict[str, str] = {}
    for field in _POINTER_FIELDS:
        value = document.get(field)
        if not isinstance(value, str) or not value.strip():
            raise IndexReadError(f"index pointer is missing {field}")
        values[field] = value

    try:
        expected = index_generation(values["index_id"])
    except CorrelationIndexContractError as exc:
        raise IndexReadError(f"index pointer names no content-addressed identity: {exc}") from exc

    if values["generation"] != expected:
        raise IndexReadError(
            "index pointer generation does not match the identity it names; "
            "reading it would address a key space this build never wrote"
        )

    return LiveIndexGeneration(
        index_id=values["index_id"],
        generation=values["generation"],
        built_at=values["built_at"],
    )


def manifest_from_document(
    document: Mapping[str, object], *, live: LiveIndexGeneration
) -> CorrelationIndexManifest:
    """Rebuild the manifest for one generation and prove it is that generation's.

    The manifest is content-addressed, so it can certify itself: rebuilding the typed
    manifest from the stored payload and re-deriving its identity must reproduce exactly
    the identity the pointer named. A manifest that merely parses proves nothing — it
    could be truncated, hand-edited, or left over from another build, and a response
    citing it would name counts and watermarks belonging to an index nobody read.

    Args:
        document: The parsed manifest object.
        live: The generation this request resolved.

    Returns:
        The typed manifest for that generation.

    Raises:
        IndexReadError: If the manifest is malformed, or describes another build.
    """
    counts = document.get("counts")
    if not isinstance(counts, Mapping):
        raise IndexReadError("index manifest carries no counts")
    counts_map = cast(Mapping[str, object], counts)

    raw_watermarks = document.get("watermarks")
    if not isinstance(raw_watermarks, (list, tuple)):
        raise IndexReadError("index manifest carries no watermarks")

    watermarks: list[SourceWatermark] = []
    for entry in cast(Sequence[object], raw_watermarks):
        if not isinstance(entry, Mapping):
            raise IndexReadError("index manifest watermark is not a mapping")
        entry_map = cast(Mapping[str, object], entry)
        try:
            watermarks.append(
                SourceWatermark(
                    source=_text(entry_map, "source"),
                    observed_through=_text(entry_map, "observed_through"),
                    record_count=_integer(entry_map, "record_count"),
                )
            )
        except CorrelationIndexContractError as exc:
            raise IndexReadError(f"index manifest watermark is not valid: {exc}") from exc

    try:
        manifest = CorrelationIndexManifest(
            built_at=_text(document, "built_at"),
            content_digest=_text(document, "content_digest"),
            ghsa_row_count=_integer(counts_map, "ghsa_rows"),
            nvd_row_count=_integer(counts_map, "nvd_rows"),
            distinct_package_count=_integer(counts_map, "distinct_packages"),
            watermarks=tuple(watermarks),
        )
    except CorrelationIndexContractError as exc:
        raise IndexReadError(f"index manifest is not valid: {exc}") from exc

    if manifest.index_id != live.index_id:
        raise IndexReadError(
            "index manifest re-derives a different identity than the pointer names; "
            "it does not describe the generation this request is reading"
        )
    return manifest


def collect_pages(pages: Iterable[IndexQueryPage]) -> tuple[Mapping[str, object], ...]:
    """Flatten a paginated query, refusing a sequence that stopped early.

    The completeness rule is structural rather than trusting: every page but the last
    carries a cursor, and the last carries none. A sequence whose final page still has a
    cursor is a read that stopped, and a read that stopped is not an answer.

    Args:
        pages: The pages in the order the store returned them.

    Returns:
        Every item, in page order.

    Raises:
        IndexReadError: If a page after the final one exists, or the sequence ends with
            an unfollowed cursor, or the sequence is empty.
    """
    collected: list[Mapping[str, object]] = []
    ended = False
    seen = 0
    for page in pages:
        if ended:
            raise IndexReadError(
                "index query returned a page after the store said there were none left"
            )
        seen += 1
        collected.extend(page.items)
        ended = page.last_evaluated_key is None

    if seen == 0:
        raise IndexReadError(
            "index query produced no pages at all; an empty result is one empty page"
        )
    if not ended:
        raise IndexReadError(
            "index query stopped with an unfollowed cursor; "
            "a truncated page is not a complete answer"
        )
    return tuple(collected)


def ghsa_rows(
    items: Sequence[Mapping[str, object]], *, live: LiveIndexGeneration
) -> tuple[ProjectedGhsaIndexRow, ...]:
    """Decode stored GHSA items back into rows, of one generation only.

    Args:
        items: The items a complete query returned.
        live: The generation this request resolved.

    Returns:
        The rows, in the order the store returned them.

    Raises:
        IndexReadError: If an item belongs to another generation or cannot be decoded.
    """
    rows: list[ProjectedGhsaIndexRow] = []
    for item in items:
        _require_generation(item, live=live)
        try:
            rows.append(
                ProjectedGhsaIndexRow(
                    package_name_canonical=_text(item, "package_name_canonical"),
                    observed_advisory_version_id=_text(item, "observed_advisory_version_id"),
                    source_advisory_sha256=_text(item, "source_advisory_sha256"),
                    source_entry_sha256=_text(item, "source_entry_sha256"),
                    ghsa_id=_text(item, "ghsa_id"),
                    github_cve_id=_optional_text(item, "github_cve_id"),
                    github_identifiers=_identifiers(item),
                    vulnerability_entry_id=_text(item, "vulnerability_entry_id"),
                    source_index=_integer(item, "source_index"),
                    ecosystem_original=_text(item, "ecosystem_original"),
                    package_name_original=_text(item, "package_name_original"),
                    vulnerable_range_original=_text(item, "vulnerable_range_original"),
                    first_patched_version_original=_optional_text(
                        item, "first_patched_version_original"
                    ),
                )
            )
        except CorrelationIndexContractError as exc:
            raise IndexReadError(f"stored GHSA item is not a valid row: {exc}") from exc
    return tuple(rows)


def nvd_rows(
    items: Sequence[Mapping[str, object]], *, live: LiveIndexGeneration
) -> tuple[ProjectedNvdIndexRow, ...]:
    """Decode stored NVD items back into rows, of one generation only.

    These rows cannot become `NvdCveCoreRecord`; ADR 0089 says why, and the rebuild
    tests enforce it. They are decoded because the CVE spine is real information — which
    CVEs NVD knows, and their status and instants — and Gate 20.4 may surface it as a
    field weaker than a typed record.

    Args:
        items: The items a complete query returned.
        live: The generation this request resolved.

    Returns:
        The rows, in the order the store returned them.

    Raises:
        IndexReadError: If an item belongs to another generation or cannot be decoded.
    """
    rows: list[ProjectedNvdIndexRow] = []
    for item in items:
        _require_generation(item, live=live)
        try:
            rows.append(
                ProjectedNvdIndexRow(
                    cve_id=_text(item, "cve_id"),
                    observed_cve_version_id=_text(item, "observed_cve_version_id"),
                    source_cve_sha256=_text(item, "source_cve_sha256"),
                    source_identifier=_text(item, "source_identifier"),
                    published_at=_text(item, "published_at"),
                    last_modified_at=_text(item, "last_modified_at"),
                    vuln_status=_text(item, "vuln_status"),
                )
            )
        except CorrelationIndexContractError as exc:
            raise IndexReadError(f"stored NVD item is not a valid row: {exc}") from exc
    return tuple(rows)


def _require_generation(item: Mapping[str, object], *, live: LiveIndexGeneration) -> None:
    """Refuse an item that belongs to a generation this request did not resolve.

    Args:
        item: One stored item.
        live: The generation this request resolved.

    Raises:
        IndexReadError: If the item names another identity or none.
    """
    stored = item.get("index_id")
    if stored != live.index_id:
        raise IndexReadError(
            "stored item belongs to a different index generation than the pointer "
            "this request resolved; one answer cannot mix two builds"
        )


def _text(item: Mapping[str, object], field: str) -> str:
    """Read one required text attribute.

    Args:
        item: One stored item.
        field: The attribute name.

    Returns:
        The value.

    Raises:
        IndexReadError: If the attribute is absent or not text.
    """
    value = item.get(field)
    if not isinstance(value, str):
        raise IndexReadError(f"stored item is missing text attribute {field}")
    return value


def _optional_text(item: Mapping[str, object], field: str) -> str | None:
    """Read one nullable text attribute.

    A stored `None` is a source that carried nothing, which ADR 0085 reads as sparse
    rather than invalid. A missing attribute is a different thing and is refused.

    Args:
        item: One stored item.
        field: The attribute name.

    Returns:
        The value, or `None`.

    Raises:
        IndexReadError: If the attribute is absent or is neither text nor null.
    """
    if field not in item:
        raise IndexReadError(f"stored item is missing attribute {field}")
    value = item[field]
    if value is None:
        return None
    if not isinstance(value, str):
        raise IndexReadError(f"stored attribute {field} is neither text nor null")
    return value


def _integer(item: Mapping[str, object], field: str) -> int:
    """Read one required integer attribute.

    DynamoDB returns numbers as `Decimal` through the resource API, and `bool` is an
    `int` in Python, so both are handled explicitly rather than by duck typing.

    Args:
        item: One stored item.
        field: The attribute name.

    Returns:
        The value.

    Raises:
        IndexReadError: If the attribute is absent or is not a whole number.
    """
    value = item.get(field)
    if isinstance(value, bool) or value is None:
        raise IndexReadError(f"stored item is missing integer attribute {field}")
    try:
        number = int(value)  # pyright: ignore[reportArgumentType]
    except (TypeError, ValueError) as exc:
        raise IndexReadError(f"stored attribute {field} is not an integer") from exc
    if number != value:
        raise IndexReadError(f"stored attribute {field} is not a whole number")
    return number


def _identifiers(item: Mapping[str, object]) -> tuple[ProjectedSourceIdentifier, ...]:
    """Read the stored identifier list back into typed identifiers.

    Order is preserved: GitHub emits identifiers in an order, and reordering them
    rewrites the source.

    Args:
        item: One stored item.

    Returns:
        The identifiers, in stored order.

    Raises:
        IndexReadError: If the attribute is absent or malformed.
    """
    value = item.get("github_identifiers")
    if not isinstance(value, (list, tuple)):
        raise IndexReadError("stored item is missing the github_identifiers list")
    entries = cast(Sequence[object], value)
    identifiers: list[ProjectedSourceIdentifier] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise IndexReadError("stored github_identifiers entry is not a mapping")
        entry_map = cast(Mapping[str, object], entry)
        try:
            identifiers.append(
                ProjectedSourceIdentifier(
                    identifier_type=_text(entry_map, "identifier_type"),
                    value=_text(entry_map, "value"),
                )
            )
        except CorrelationIndexContractError as exc:
            raise IndexReadError(f"stored identifier is not valid: {exc}") from exc
    return tuple(identifiers)
