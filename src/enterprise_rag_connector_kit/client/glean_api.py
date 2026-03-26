from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import requests
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from enterprise_rag_connector_kit.models.document import Document

LOGGER = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {
    HTTPStatus.TOO_MANY_REQUESTS,
    HTTPStatus.INTERNAL_SERVER_ERROR,
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
    HTTPStatus.GATEWAY_TIMEOUT,
}


@dataclass(slots=True)
class BatchIndexResult:
    success: bool
    datasource: str
    document_count: int
    status_code: int | None
    attempt_count: int
    elapsed_ms: int
    response_body: dict[str, Any] | str | None
    error_message: str | None = None


@dataclass(slots=True)
class DebugDocumentResult:
    success: bool
    datasource: str
    document_id: str
    status_code: int | None
    response_body: dict[str, Any] | str | None
    error_message: str | None = None


class GleanApiError(Exception):
    pass


class RetryableGleanApiError(GleanApiError):
    pass


class PermanentGleanApiError(GleanApiError):
    pass


class GleanApiClient:
    def __init__(
        self,
        base_url: str,
        datasource: str,
        api_token: str,
        *,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 30.0,
        max_attempts: int = 4,
        backoff_base_seconds: float = 0.75,
        backoff_jitter_seconds: float = 0.35,
        session: Session | None = None,
        user_agent: str = "glean-indexing-connector/1.0",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._datasource = datasource
        self._api_token = api_token
        self._connect_timeout_seconds = connect_timeout_seconds
        self._read_timeout_seconds = read_timeout_seconds
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds
        self._backoff_jitter_seconds = backoff_jitter_seconds
        self._user_agent = user_agent
        self._session = session or self._build_session()

    @property
    def datasource(self) -> str:
        return self._datasource

    def index_documents(self, documents: list[Document]) -> BatchIndexResult:
        if not documents:
            raise ValueError("index_documents() received an empty document list.")

        payload = {
            "datasource": self._datasource,
            "documents": [
                document.to_glean_payload(self._datasource) for document in documents
            ],
        }





        endpoint = f"{self._base_url}/api/index/v1/indexdocuments"
        return self._post_with_retry(
            endpoint=endpoint,
            payload=payload,
            document_count=len(documents),
        )

    def debug_document(self, document_id: str) -> DebugDocumentResult:
        if not document_id or not document_id.strip():
            raise ValueError("document_id must be a non-empty string.")

        endpoint = f"{self._base_url}/api/index/v1/debug/{self._datasource}/document"
        payload = {
            "objectType": "Document",
            "docId": document_id.strip(),
        }

        try:
            response = self._session.post(
                endpoint,
                json=payload,
                timeout=(self._connect_timeout_seconds, self._read_timeout_seconds),
            )
            parsed_body = self._safe_parse_response_body(response)

            if response.ok:
                return DebugDocumentResult(
                    success=True,
                    datasource=self._datasource,
                    document_id=document_id,
                    status_code=response.status_code,
                    response_body=parsed_body,
                )

            return DebugDocumentResult(
                success=False,
                datasource=self._datasource,
                document_id=document_id,
                status_code=response.status_code,
                response_body=parsed_body,
                error_message=self._build_error_message(response),
            )

        except requests.RequestException as exc:
            LOGGER.exception(
                "Debug document call failed for document_id=%s",
                document_id,
            )
            return DebugDocumentResult(
                success=False,
                datasource=self._datasource,
                document_id=document_id,
                status_code=None,
                response_body=None,
                error_message=str(exc),
            )

    def close(self) -> None:
        self._session.close()

    def _post_with_retry(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
        document_count: int,
    ) -> BatchIndexResult:
        last_error_message: str | None = None
        last_status_code: int | None = None
        last_response_body: dict[str, Any] | str | None = None

        start_time = time.perf_counter()

        for attempt in range(1, self._max_attempts + 1):
            try:
                LOGGER.info(
                    "Submitting Glean batch: datasource=%s "
                    "document_count=%s attempt=%s/%s",
                    self._datasource,
                    document_count,
                    attempt,
                    self._max_attempts,
                )

                response = self._session.post(
                    endpoint,
                    json=payload,
                    timeout=(self._connect_timeout_seconds, self._read_timeout_seconds),
                )

                parsed_body = self._safe_parse_response_body(response)
                last_status_code = response.status_code
                last_response_body = parsed_body

                if response.ok:
                    elapsed_ms = self._elapsed_ms(start_time)
                    LOGGER.info(
                        "Glean batch succeeded: datasource=%s "
                        "document_count=%s status_code=%s elapsed_ms=%s",
                        self._datasource,
                        document_count,
                        response.status_code,
                        elapsed_ms,
                    )
                    return BatchIndexResult(
                        success=True,
                        datasource=self._datasource,
                        document_count=document_count,
                        status_code=response.status_code,
                        attempt_count=attempt,
                        elapsed_ms=elapsed_ms,
                        response_body=parsed_body,
                        error_message=None,
                    )

                if response.status_code in {
                    status.value for status in RETRYABLE_STATUS_CODES
                }:
                    last_error_message = self._build_error_message(response)
                    LOGGER.warning(
                        "Retryable Glean response received: datasource=%s "
                        "status_code=%s attempt=%s/%s message=%s",
                        self._datasource,
                        response.status_code,
                        attempt,
                        self._max_attempts,
                        last_error_message,
                    )
                    if attempt < self._max_attempts:
                        self._sleep_before_retry(attempt)
                        continue

                    break

                last_error_message = self._build_error_message(response)
                elapsed_ms = self._elapsed_ms(start_time)
                LOGGER.error(
                    "Permanent Glean response failure: datasource=%s "
                    "document_count=%s status_code=%s elapsed_ms=%s message=%s",
                    self._datasource,
                    document_count,
                    response.status_code,
                    elapsed_ms,
                    last_error_message,
                )
                return BatchIndexResult(
                    success=False,
                    datasource=self._datasource,
                    document_count=document_count,
                    status_code=response.status_code,
                    attempt_count=attempt,
                    elapsed_ms=elapsed_ms,
                    response_body=parsed_body,
                    error_message=last_error_message,
                )

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error_message = str(exc)
                LOGGER.warning(
                    "Transient network failure calling Glean: datasource=%s "
                    "document_count=%s attempt=%s/%s error=%s",
                    self._datasource,
                    document_count,
                    attempt,
                    self._max_attempts,
                    exc,
                )
                if attempt < self._max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                break

            except requests.RequestException as exc:
                last_error_message = str(exc)
                elapsed_ms = self._elapsed_ms(start_time)
                LOGGER.exception(
                    "Non-retryable requests failure calling Glean: "
                    "datasource=%s document_count=%s elapsed_ms=%s",
                    self._datasource,
                    document_count,
                    elapsed_ms,
                )
                return BatchIndexResult(
                    success=False,
                    datasource=self._datasource,
                    document_count=document_count,
                    status_code=None,
                    attempt_count=attempt,
                    elapsed_ms=elapsed_ms,
                    response_body=None,
                    error_message=last_error_message,
                )

        elapsed_ms = self._elapsed_ms(start_time)
        LOGGER.error(
            "Glean batch failed after retries exhausted: datasource=%s "
            "document_count=%s attempts=%s elapsed_ms=%s "
            "status_code=%s message=%s",
            self._datasource,
            document_count,
            self._max_attempts,
            elapsed_ms,
            last_status_code,
            last_error_message,
        )
        return BatchIndexResult(
            success=False,
            datasource=self._datasource,
            document_count=document_count,
            status_code=last_status_code,
            attempt_count=self._max_attempts,
            elapsed_ms=elapsed_ms,
            response_body=last_response_body,
            error_message=last_error_message,
        )

    def _build_session(self) -> Session:
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": self._user_agent,
            }
        )

        retry = Retry(
            total=0,
            connect=0,
            read=0,
            redirect=0,
            status=0,
            backoff_factor=0,
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _sleep_before_retry(self, attempt: int) -> None:
        exponential_delay = self._backoff_base_seconds * (2 ** (attempt - 1))
        jitter = random.uniform(0.0, self._backoff_jitter_seconds)
        sleep_seconds = exponential_delay + jitter

        LOGGER.info(
            "Sleeping before retry: datasource=%s attempt=%s sleep_seconds=%.3f",
            self._datasource,
            attempt,
            sleep_seconds,
        )
        time.sleep(sleep_seconds)

    @staticmethod
    def _safe_parse_response_body(response: Response) -> dict[str, Any] | str | None:
        if not response.text:
            return None

        try:
            return response.json()
        except ValueError:
            return response.text.strip() or None

    @staticmethod
    def _build_error_message(response: Response) -> str:
        body = GleanApiClient._safe_parse_response_body(response)

        if isinstance(body, dict):
            try:
                compact_body = json.dumps(body, ensure_ascii=False)
            except TypeError:
                compact_body = str(body)
            return f"HTTP {response.status_code}: {compact_body}"

        if isinstance(body, str) and body:
            return f"HTTP {response.status_code}: {body}"

        return f"HTTP {response.status_code}: empty response body"

    @staticmethod
    def _elapsed_ms(start_time: float) -> int:
        return int((time.perf_counter() - start_time) * 1000)
