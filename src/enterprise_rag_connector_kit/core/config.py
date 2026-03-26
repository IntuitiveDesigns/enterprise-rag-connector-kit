from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    """
    Centralized application configuration.

    Values are sourced from environment variables so credentials and
    environment-specific settings stay out of source control.
    """

    base_url: str
    datasource: str
    api_token: str



    source_type: str

    input_json_path: Path
    output_dir: Path

    batch_size: int
    connect_timeout_seconds: float
    read_timeout_seconds: float
    max_attempts: int
    backoff_base_seconds: float
    backoff_jitter_seconds: float

    log_level: str
    run_prefix: str
    user_agent: str

    client_api_token: str
    chat_agent_id: str | None

    rest_base_url: str | None
    rest_endpoint_path: str | None
    rest_api_token: str | None
    rest_auth_header_name: str
    rest_auth_header_prefix: str

    rest_records_field: str
    rest_pagination_mode: str
    rest_page_size: int
    rest_page_size_param: str
    rest_page_number_param: str
    rest_cursor_param: str
    rest_next_cursor_field: str
    rest_has_more_field: str

    rest_id_field: str
    rest_title_field: str
    rest_body_field: str | None
    rest_updated_at_field: str | None
    rest_view_url_field: str | None

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            base_url=_required_env("GLEAN_BASE_URL"),
            datasource=_required_env("GLEAN_DATASOURCE"),
            api_token=_required_env("GLEAN_INDEXING_TOKEN"),
            client_api_token=_required_env("GLEAN_CLIENT_API_TOKEN"),
            chat_agent_id=os.getenv("GLEAN_CHAT_AGENT_ID"),
            source_type=os.getenv("GLEAN_SOURCE_TYPE", "local_json").strip().lower(),
            input_json_path=Path(
                os.getenv("GLEAN_INPUT_JSON_PATH", "data/source_docs.json")
            ),
            output_dir=Path(os.getenv("GLEAN_OUTPUT_DIR", "output")),
            batch_size=_int_env("GLEAN_BATCH_SIZE", default=10, minimum=1),
            connect_timeout_seconds=_float_env(
                "GLEAN_CONNECT_TIMEOUT",
                default=5.0,
                minimum=0.1,
            ),
            read_timeout_seconds=_float_env(
                "GLEAN_READ_TIMEOUT",
                default=30.0,
                minimum=0.1,
            ),
            max_attempts=_int_env("GLEAN_MAX_ATTEMPTS", default=4, minimum=1),
            backoff_base_seconds=_float_env(
                "GLEAN_BACKOFF_BASE_SECONDS",
                default=0.75,
                minimum=0.0,
            ),
            backoff_jitter_seconds=_float_env(
                "GLEAN_BACKOFF_JITTER_SECONDS",
                default=0.35,
                minimum=0.0,
            ),
            log_level=os.getenv("GLEAN_LOG_LEVEL", "INFO").strip().upper(),
            run_prefix=os.getenv("GLEAN_RUN_PREFIX", "STEVEN-GLEAN-DEMO").strip(),
            user_agent=os.getenv(
                "GLEAN_USER_AGENT",
                "glean-indexing-connector/1.0",
            ).strip(),
            rest_base_url=os.getenv("GLEAN_REST_BASE_URL"),
            rest_endpoint_path=os.getenv("GLEAN_REST_ENDPOINT_PATH"),
            rest_api_token=os.getenv("GLEAN_REST_API_TOKEN"),
            rest_auth_header_name=os.getenv(
                "GLEAN_REST_AUTH_HEADER_NAME",
                "Authorization",
            ).strip(),
            rest_auth_header_prefix=os.getenv(
                "GLEAN_REST_AUTH_HEADER_PREFIX",
                "Bearer",
            ).strip(),
            rest_records_field=os.getenv(
                "GLEAN_REST_RECORDS_FIELD",
                "items",
            ).strip(),
            rest_pagination_mode=os.getenv(
                "GLEAN_REST_PAGINATION_MODE",
                "cursor",
            ).strip().lower(),
            rest_page_size=_int_env("GLEAN_REST_PAGE_SIZE", default=100, minimum=1),
            rest_page_size_param=os.getenv(
                "GLEAN_REST_PAGE_SIZE_PARAM",
                "page_size",
            ).strip(),
            rest_page_number_param=os.getenv(
                "GLEAN_REST_PAGE_NUMBER_PARAM",
                "page",
            ).strip(),
            rest_cursor_param=os.getenv("GLEAN_REST_CURSOR_PARAM", "cursor").strip(),
            rest_next_cursor_field=os.getenv(
                "GLEAN_REST_NEXT_CURSOR_FIELD",
                "next_cursor",
            ).strip(),
            rest_has_more_field=os.getenv(
                "GLEAN_REST_HAS_MORE_FIELD",
                "has_more",
            ).strip(),
            rest_id_field=os.getenv("GLEAN_REST_ID_FIELD", "id").strip(),
            rest_title_field=os.getenv("GLEAN_REST_TITLE_FIELD", "title").strip(),
            rest_body_field=os.getenv("GLEAN_REST_BODY_FIELD"),
            rest_updated_at_field=os.getenv("GLEAN_REST_UPDATED_AT_FIELD"),
            rest_view_url_field=os.getenv("GLEAN_REST_VIEW_URL_FIELD"),
        )

    def masked_token(self) -> str:
        """
        Safe token representation for logs.
        """
        if len(self.api_token) <= 8:
            return "****"
        return f"{self.api_token[:4]}...{self.api_token[-4:]}"

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Required environment variable '{name}' is missing or empty.")
    return value.strip()


def _int_env(name: str, *, default: int, minimum: int | None = None) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        value = default
    else:
        try:
            value = int(raw_value.strip())
        except ValueError as exc:
            raise ValueError(
                f"Environment variable '{name}' must be an integer. "
                f"Received: {raw_value!r}"
            ) from exc

    if minimum is not None and value < minimum:
        raise ValueError(
            f"Environment variable '{name}' must be >= {minimum}. Received: {value}"
        )
    return value


def _float_env(name: str, *, default: float, minimum: float | None = None) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        value = default
    else:
        try:
            value = float(raw_value.strip())
        except ValueError as exc:
            raise ValueError(
                f"Environment variable '{name}' must be a float. "
                f"Received: {raw_value!r}"
            ) from exc

    if minimum is not None and value < minimum:
        raise ValueError(
            f"Environment variable '{name}' must be >= {minimum}. Received: {value}"
        )
    return value

def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None
