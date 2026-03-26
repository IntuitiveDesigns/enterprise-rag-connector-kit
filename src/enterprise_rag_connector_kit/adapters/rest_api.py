from __future__ import annotations

import logging
import random
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import requests

from enterprise_rag_connector_kit.adapters.base import (
    AdapterRecord,
    DocumentSourceAdapter,
)
from enterprise_rag_connector_kit.models.document import Document

LOGGER = logging.getLogger(__name__)


class RestApiAdapter(DocumentSourceAdapter):
    """
    Production-style REST API adapter.

    Responsibilities:
    - fetch paginated records from an external REST API
    - normalize each record into a Document
    - isolate bad records without killing the full run
    - retry transient HTTP/network failures
    - support both page-number and cursor-based pagination

    Assumptions:
    - the API returns JSON
    - records are found in a configurable top-level field
    - pagination metadata can be described via config
    """

    BODY_FIELD_CANDIDATES: tuple[str, ...] = ("body", "body_text", "text", "content")
    UPDATED_AT_FIELD_CANDIDATES: tuple[str, ...] = (
        "updated_at",
        "updatedAt",
        "last_updated",
        "modified_at",
        "modifiedAt",
    )

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        base_url: str,
        endpoint_path: str,
        datasource: str,
        api_token: str | None = None,
        auth_header_name: str = "Authorization",
        auth_header_prefix: str = "Bearer",
        records_field: str = "items",
        pagination_mode: str = "cursor",
        page_size: int = 100,
        page_size_param: str = "page_size",
        page_number_param: str = "page",
        cursor_param: str = "cursor",
        next_cursor_field: str = "next_cursor",
        has_more_field: str = "has_more",
        additional_query_params: dict[str, Any] | None = None,
        id_field: str = "id",
        title_field: str = "title",
        body_field: str | None = None,
        updated_at_field: str | None = None,
        view_url_field: str | None = None,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 30.0,
        max_attempts: int = 4,
        backoff_base_seconds: float = 0.75,
        backoff_jitter_seconds: float = 0.35,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._endpoint_path = (
            endpoint_path
            if endpoint_path.startswith("/")
            else f"/{endpoint_path}"
        )
        self._datasource = datasource.strip()

        self._api_token = api_token
        self._auth_header_name = auth_header_name
        self._auth_header_prefix = auth_header_prefix.strip()

        self._records_field = records_field
        self._pagination_mode = pagination_mode.strip().lower()
        self._page_size = page_size
        self._page_size_param = page_size_param
        self._page_number_param = page_number_param
        self._cursor_param = cursor_param
        self._next_cursor_field = next_cursor_field
        self._has_more_field = has_more_field
        self._additional_query_params = additional_query_params or {}

        self._id_field = id_field
        self._title_field = title_field
        self._body_field = body_field
        self._updated_at_field = updated_at_field
        self._view_url_field = view_url_field

        self._connect_timeout_seconds = connect_timeout_seconds
        self._read_timeout_seconds = read_timeout_seconds
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds
        self._backoff_jitter_seconds = backoff_jitter_seconds

        self._session = session or requests.Session()
        self._session.headers.update({"Accept": "application/json"})

        if self._api_token:
            token_value = self._api_token
            if self._auth_header_prefix:
                token_value = f"{self._auth_header_prefix} {token_value}"
            self._session.headers[self._auth_header_name] = token_value

        if self._pagination_mode not in {"cursor", "page"}:
            raise ValueError("pagination_mode must be either 'cursor' or 'page'.")

    def iter_documents(self) -> Iterable[AdapterRecord]:
        record_number = 0

        for raw_record in self._iter_raw_records():
            record_number += 1

            if not isinstance(raw_record, dict):
                yield AdapterRecord(
                    record_number=record_number,
                    document=None,
                    raw_record={"raw_value": raw_record},
                    error_message=(
                        f"Expected each API record to be an object, but found "
                        f"{type(raw_record).__name__}."
                    ),
                )
                continue

            try:
                document = self._to_document(raw_record, record_number)
                yield AdapterRecord(
                    record_number=record_number,
                    document=document,
                    raw_record=raw_record,
                    error_message=None,
                )
            except ValueError as exc:
                yield AdapterRecord(
                    record_number=record_number,
                    document=None,
                    raw_record=raw_record,
                    error_message=str(exc),
                )

    def close(self) -> None:
        self._session.close()

    def _iter_raw_records(self) -> Iterable[Any]:
        if self._pagination_mode == "cursor":
            yield from self._iter_cursor_pages()
            return

        yield from self._iter_page_number_pages()

    def _iter_cursor_pages(self) -> Iterable[Any]:
        next_cursor: str | None = None
        page_index = 0

        while True:
            page_index += 1
            payload = self._get_page(cursor=next_cursor)

            records = self._extract_records(payload, page_index)
            yield from records

            has_more = bool(payload.get(self._has_more_field))
            next_cursor = self._extract_optional_string(
                payload,
                self._next_cursor_field,
            )

            LOGGER.info(
                "REST adapter page fetched: mode=cursor "
                "page_index=%s record_count=%s has_more=%s "
                "next_cursor_present=%s",
                page_index,
                len(records),
                has_more,
                bool(next_cursor),
            )

            if not has_more and not next_cursor:
                break

            if has_more and not next_cursor:
                raise ValueError(
                    f"API indicated more pages via '{self._has_more_field}' "
                    f"but did not provide '{self._next_cursor_field}'."
                )

    def _iter_page_number_pages(self) -> Iterable[Any]:
        page_number = 1

        while True:
            payload = self._get_page(page_number=page_number)

            records = self._extract_records(payload, page_number)
            yield from records

            LOGGER.info(
                "REST adapter page fetched: mode=page "
                "page_number=%s record_count=%s",
                page_number,
                len(records),
            )

            if not records:
                break

            has_more = payload.get(self._has_more_field)
            if isinstance(has_more, bool):
                if not has_more:
                    break
            elif len(records) < self._page_size:
                break

            page_number += 1

    def _get_page(
        self,
        *,
        cursor: str | None = None,
        page_number: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = dict(self._additional_query_params)
        params[self._page_size_param] = self._page_size

        if self._pagination_mode == "cursor":
            if cursor:
                params[self._cursor_param] = cursor
        else:
            params[self._page_number_param] = page_number or 1

        url = f"{self._base_url}{self._endpoint_path}"

        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._session.get(
                    url,
                    params=params,
                    timeout=(
                        self._connect_timeout_seconds,
                        self._read_timeout_seconds,
                    ),
                )

                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    if attempt >= self._max_attempts:
                        response.raise_for_status()

                    self._sleep_before_retry(attempt)
                    continue

                response.raise_for_status()

                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError(
                        "Expected top-level API response object but found "
                        f"{type(payload).__name__}."
                    )

                return payload

            except (requests.Timeout, requests.ConnectionError) as exc:
                LOGGER.warning(
                    "Transient REST adapter failure: attempt=%s/%s error=%s",
                    attempt,
                    self._max_attempts,
                    exc,
                )
                if attempt >= self._max_attempts:
                    raise
                self._sleep_before_retry(attempt)

            except requests.HTTPError as exc:
                LOGGER.warning(
                    "HTTP error from REST adapter: attempt=%s/%s status_code=%s",
                    attempt,
                    self._max_attempts,
                    exc.response.status_code if exc.response else None,
                )
                raise

            except ValueError as exc:
                LOGGER.error("REST adapter received invalid JSON payload: %s", exc)
                raise

        raise ValueError(
            f"API indicated more pages via '{self._has_more_field}' "
            f"but did not provide '{self._next_cursor_field}'."
        )

    def _extract_records(
        self,
        payload: dict[str, Any],
        page_identifier: int,
    ) -> list[Any]:
        records = payload.get(self._records_field)
        if records is None:
            raise ValueError(
                f"API response page {page_identifier} is missing records field "
                f"'{self._records_field}'."
            )
        if not isinstance(records, list):
            raise ValueError(
                f"API response field '{self._records_field}' must be a list, found "
                f"{type(records).__name__}."
            )
        return records

    def _to_document(
        self,
        raw_record: dict[str, Any],
        record_number: int,
    ) -> Document:
        doc_id = self._require_non_empty_string(
            raw_record,
            self._id_field,
            record_number,
        )
        title = self._require_non_empty_string(
            raw_record,
            self._title_field,
            record_number,
        )
        body_text = self._extract_body_text(raw_record, record_number)
        updated_at = self._extract_updated_at(raw_record, record_number)
        view_url = self._extract_view_url(raw_record)

        return Document(
            id=doc_id,
            title=title,
            body_text=body_text,
            updated_at=updated_at,
            datasource=self._datasource,
            view_url=view_url,
        )

    def _extract_body_text(
        self,
        raw_record: dict[str, Any],
        record_number: int,
    ) -> str:
        if self._body_field:
            return self._require_non_empty_string(
                raw_record,
                self._body_field,
                record_number,
            )

        for field_name in self.BODY_FIELD_CANDIDATES:
            value = raw_record.get(field_name)
            if isinstance(value, str) and value.strip():
                return value.strip()

        raise ValueError(f"Record {record_number} is missing a non-empty body field.")

    def _extract_updated_at(
        self,
        raw_record: dict[str, Any],
        record_number: int,
    ) -> datetime:
        if self._updated_at_field:
            candidate_fields = (self._updated_at_field,)
        else:
            candidate_fields = self.UPDATED_AT_FIELD_CANDIDATES

        raw_timestamp: str | None = None
        for field_name in candidate_fields:
            value = raw_record.get(field_name)
            if isinstance(value, str) and value.strip():
                raw_timestamp = value.strip()
                break

        if raw_timestamp is None:
            return datetime.now(UTC)

        try:
            normalized = raw_timestamp.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(
                f"Record {record_number} has invalid timestamp '{raw_timestamp}'."
            ) from exc

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC)

    def _extract_view_url(self, raw_record: dict[str, Any]) -> str | None:
        if self._view_url_field:
            return self._extract_optional_string(raw_record, self._view_url_field)

        for candidate in ("view_url", "viewURL", "url", "link"):
            value = raw_record.get(candidate)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    def _sleep_before_retry(self, attempt: int) -> None:
        delay = self._backoff_base_seconds * (2 ** (attempt - 1))
        jitter = random.uniform(0.0, self._backoff_jitter_seconds)
        time.sleep(delay + jitter)

    @staticmethod
    def _require_non_empty_string(
        raw_record: dict[str, Any],
        field_name: str,
        record_number: int,
    ) -> str:
        value = raw_record.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Record {record_number} is missing required non-empty field "
                f"'{field_name}'."
            )
        return value.strip()

    @staticmethod
    def _extract_optional_string(
        raw_record: dict[str, Any],
        field_name: str,
    ) -> str | None:
        value = raw_record.get(field_name)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(
                f"Optional field '{field_name}' must be a string when provided."
            )
        value = value.strip()
        return value or None