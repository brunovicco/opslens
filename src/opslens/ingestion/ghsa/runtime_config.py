"""Environment-backed settings for GHSA Bronze Lambda runtime composition."""

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GhsaBronzeRuntimeSettingsV1:
    """Hold non-secret GHSA Bronze runtime configuration."""

    bucket_name: str
    github_token_secret_id: str
    bronze_prefix: str = "bronze/ghsa/advisories"
    http_timeout_seconds: float = 15.0
    http_max_attempts: int = 3
    secret_cache_ttl_seconds: float = 300.0
    max_leaf_windows: int = 64

    def __post_init__(self) -> None:
        """Validate bounded runtime settings without reading credential material."""
        if not self.bucket_name.strip():
            raise ValueError("GHSA data bucket name cannot be empty.")

        if not self.github_token_secret_id.strip():
            raise ValueError("GHSA GitHub token secret id cannot be empty.")

        if not self.bronze_prefix.strip("/"):
            raise ValueError("GHSA Bronze prefix cannot be empty.")

        if self.http_timeout_seconds <= 0:
            raise ValueError("GHSA HTTP timeout must be positive.")

        if type(self.http_max_attempts) is not int or self.http_max_attempts < 1:
            raise ValueError("GHSA HTTP max attempts must be a positive integer.")

        if self.secret_cache_ttl_seconds <= 0:
            raise ValueError("GHSA secret cache TTL must be positive.")

        if type(self.max_leaf_windows) is not int or self.max_leaf_windows < 1:
            raise ValueError("GHSA max leaf windows must be a positive integer.")

        object.__setattr__(self, "bucket_name", self.bucket_name.strip())
        object.__setattr__(
            self,
            "github_token_secret_id",
            self.github_token_secret_id.strip(),
        )
        object.__setattr__(self, "bronze_prefix", self.bronze_prefix.strip("/"))

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "GhsaBronzeRuntimeSettingsV1":
        """Load explicit GHSA settings from Lambda environment variables."""
        values = os.environ if environment is None else environment

        return cls(
            bucket_name=cls._required(values, "GHSA_DATA_BUCKET"),
            github_token_secret_id=cls._required(
                values,
                "GHSA_GITHUB_TOKEN_SECRET_ID",
            ),
            bronze_prefix=values.get(
                "GHSA_BRONZE_PREFIX",
                "bronze/ghsa/advisories",
            ),
            http_timeout_seconds=cls._float_value(
                values,
                "GHSA_HTTP_TIMEOUT_SECONDS",
                15.0,
            ),
            http_max_attempts=cls._int_value(
                values,
                "GHSA_HTTP_MAX_ATTEMPTS",
                3,
            ),
            secret_cache_ttl_seconds=cls._float_value(
                values,
                "GHSA_SECRET_CACHE_TTL_SECONDS",
                300.0,
            ),
            max_leaf_windows=cls._int_value(
                values,
                "GHSA_MAX_LEAF_WINDOWS",
                64,
            ),
        )

    @staticmethod
    def _required(values: Mapping[str, str], name: str) -> str:
        """Read one required non-empty environment setting."""
        value = values.get(name)

        if value is None or not value.strip():
            raise ValueError(f"Required GHSA environment variable {name} is missing.")

        return value

    @staticmethod
    def _float_value(
        values: Mapping[str, str],
        name: str,
        default: float,
    ) -> float:
        """Read one finite positive float-like setting."""
        raw = values.get(name)

        if raw is None:
            return default

        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(f"GHSA environment variable {name} must be numeric.") from exc

        if value <= 0 or value == float("inf") or value == float("-inf") or value != value:
            raise ValueError(f"GHSA environment variable {name} must be finite and positive.")

        return value

    @staticmethod
    def _int_value(
        values: Mapping[str, str],
        name: str,
        default: int,
    ) -> int:
        """Read one positive integer setting."""
        raw = values.get(name)

        if raw is None:
            return default

        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"GHSA environment variable {name} must be an integer.") from exc

        if value < 1:
            raise ValueError(f"GHSA environment variable {name} must be positive.")

        return value
