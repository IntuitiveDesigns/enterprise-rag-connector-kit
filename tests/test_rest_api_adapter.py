from __future__ import annotations

from datetime import UTC, datetime

import pytest
import requests

from enterprise_rag_connector_kit.adapters.rest_api import RestApiAdapter


class FakeResponse:
    def __init__(self, *, status_code: int, json_body=None) -> None:
        self.status_code = status_code
        self._json_body = json_body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error

    def json(self):
        return self._json_body


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "params": dict(params or {}),
                "timeout": timeout,
            }
        )
        if not self._responses:
            raise AssertionError("No more fake responses available.")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self) -> None:
        return None


def test_rest_api_adapter_cursor_pagination_loads_documents() -> None:
    session = FakeSession(
        [
            FakeResponse(
                status_code=200,
                json_body={
                    "items": [
                        {
                            "id": "doc-001",
                            "title": "Doc 1",
                            "content": "Body 1",
                            "updated_at": "2026-03-10T12:00:00Z",
                            "url": "https://example.com/doc-001",
                        },
                        {
                            "id": "doc-002",
                            "title": "Doc 2",
                            "content": "Body 2",
                            "updated_at": "2026-03-10T12:05:00Z",
                            "url": "https://example.com/doc-002",
                        },
                    ],
                    "has_more": True,
                    "next_cursor": "cursor-2",
                },
            ),
            FakeResponse(
                status_code=200,
                json_body={
                    "items": [
                        {
                            "id": "doc-003",
                            "title": "Doc 3",
                            "content": "Body 3",
                            "updated_at": "2026-03-10T12:10:00Z",
                            "url": "https://example.com/doc-003",
                        }
                    ],
                    "has_more": False,
                    "next_cursor": None,
                },
            ),
        ]
    )

    adapter = RestApiAdapter(
        base_url="https://api.example.com",
        endpoint_path="/v1/documents",
        datasource="interviewds",
        api_token="secret-token",
        records_field="items",
        pagination_mode="cursor",
        page_size=2,
        body_field="content",
        updated_at_field="updated_at",
        view_url_field="url",
        session=session,
        backoff_base_seconds=0.0,
        backoff_jitter_seconds=0.0,
    )

    records = list(adapter.iter_documents())

    assert len(records) == 3
    assert all(record.is_success for record in records)

    assert records[0].document is not None
    assert records[0].document.id == "doc-001"
    assert records[0].document.title == "Doc 1"
    assert records[0].document.body_text == "Body 1"
    assert records[0].document.updated_at == datetime(
        2026, 3, 10, 12, 0, 0, tzinfo=UTC
    )
    assert records[0].document.datasource == "interviewds"

    assert len(session.calls) == 2
    assert session.calls[0]["params"]["page_size"] == 2
    assert "cursor" not in session.calls[0]["params"]
    assert session.calls[1]["params"]["cursor"] == "cursor-2"


def test_rest_api_adapter_page_pagination_stops_when_has_more_false() -> None:
    session = FakeSession(
        [
            FakeResponse(
                status_code=200,
                json_body={
                    "items": [
                        {
                            "id": "doc-001",
                            "title": "Doc 1",
                            "content": "Body 1",
                        }
                    ],
                    "has_more": True,
                },
            ),
            FakeResponse(
                status_code=200,
                json_body={
                    "items": [
                        {
                            "id": "doc-002",
                            "title": "Doc 2",
                            "content": "Body 2",
                        }
                    ],
                    "has_more": False,
                },
            ),
        ]
    )

    adapter = RestApiAdapter(
        base_url="https://api.example.com",
        endpoint_path="/v1/documents",
        datasource="interviewds",
        records_field="items",
        pagination_mode="page",
        page_size=100,
        body_field="content",
        session=session,
        backoff_base_seconds=0.0,
        backoff_jitter_seconds=0.0,
    )

    records = list(adapter.iter_documents())

    assert len(records) == 2
    assert all(record.is_success for record in records)
    assert session.calls[0]["params"]["page"] == 1
    assert session.calls[1]["params"]["page"] == 2


def test_rest_api_adapter_retries_transient_500_then_succeeds(monkeypatch) -> None:
    sleep_calls = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "enterprise_rag_connector_kit.adapters.rest_api.time.sleep",
        fake_sleep,
    )
    monkeypatch.setattr(
        "enterprise_rag_connector_kit.adapters.rest_api.random.uniform",
        lambda a, b: 0.0,
    )

    session = FakeSession(
        [
            FakeResponse(status_code=500, json_body={"error": "temporary"}),
            FakeResponse(
                status_code=200,
                json_body={
                    "items": [
                        {
                            "id": "doc-001",
                            "title": "Doc 1",
                            "content": "Body 1",
                        }
                    ],
                    "has_more": False,
                },
            ),
        ]
    )

    adapter = RestApiAdapter(
        base_url="https://api.example.com",
        endpoint_path="/v1/documents",
        datasource="interviewds",
        records_field="items",
        pagination_mode="cursor",
        body_field="content",
        session=session,
        max_attempts=3,
        backoff_base_seconds=0.1,
        backoff_jitter_seconds=0.0,
    )

    records = list(adapter.iter_documents())

    assert len(records) == 1
    assert records[0].is_success is True
    assert len(session.calls) == 2
    assert sleep_calls == [0.1]


def test_rest_api_adapter_retries_connection_error_then_succeeds(monkeypatch) -> None:
    sleep_calls = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "enterprise_rag_connector_kit.adapters.rest_api.time.sleep",
        fake_sleep,
    )
    monkeypatch.setattr(
        "enterprise_rag_connector_kit.adapters.rest_api.random.uniform",
        lambda a, b: 0.0,
    )

    session = FakeSession(
        [
            requests.ConnectionError("temporary network issue"),
            FakeResponse(
                status_code=200,
                json_body={
                    "items": [
                        {
                            "id": "doc-001",
                            "title": "Doc 1",
                            "content": "Body 1",
                        }
                    ],
                    "has_more": False,
                },
            ),
        ]
    )

    adapter = RestApiAdapter(
        base_url="https://api.example.com",
        endpoint_path="/v1/documents",
        datasource="interviewds",
        records_field="items",
        pagination_mode="cursor",
        body_field="content",
        session=session,
        max_attempts=3,
        backoff_base_seconds=0.2,
        backoff_jitter_seconds=0.0,
    )

    records = list(adapter.iter_documents())

    assert len(records) == 1
    assert records[0].is_success is True
    assert len(session.calls) == 2
    assert sleep_calls == [0.2]





def test_rest_api_adapter_marks_bad_record_as_rejected() -> None:
    session = FakeSession(
        [
            FakeResponse(
                status_code=200,
                json_body={
                    "items": [
                        {
                            "id": "doc-001",
                            "title": "Good Doc",
                            "content": "Good Body",
                        },
                        {
                            "id": "doc-002",
                            "title": "Bad Doc",
                        },
                    ],
                    "has_more": False,
                },
            )
        ]
    )

    adapter = RestApiAdapter(
        base_url="https://api.example.com",
        endpoint_path="/v1/documents",
        datasource="interviewds",
        records_field="items",
        pagination_mode="cursor",
        body_field="content",
        session=session,
        backoff_base_seconds=0.0,
        backoff_jitter_seconds=0.0,
    )

    records = list(adapter.iter_documents())

    assert len(records) == 2
    assert records[0].is_success is True
    assert records[1].is_rejected is True
    assert records[1].error_message is not None
    assert "content" in records[1].error_message.lower()


def test_rest_api_adapter_raises_when_records_field_missing() -> None:
    session = FakeSession(
        [
            FakeResponse(
                status_code=200,
                json_body={
                    "unexpected": [],
                    "has_more": False,
                },
            )
        ]
    )

    adapter = RestApiAdapter(
        base_url="https://api.example.com",
        endpoint_path="/v1/documents",
        datasource="interviewds",
        records_field="items",
        pagination_mode="cursor",
        session=session,
    )

    with pytest.raises(ValueError, match="missing records field"):
        list(adapter.iter_documents())


def test_rest_api_adapter_raises_when_cursor_has_more_without_next_cursor() -> None:
    session = FakeSession(
        [
            FakeResponse(
                status_code=200,
                json_body={
                    "items": [],
                    "has_more": True,
                    "next_cursor": None,
                },
            )
        ]
    )

    adapter = RestApiAdapter(
        base_url="https://api.example.com",
        endpoint_path="/v1/documents",
        datasource="interviewds",
        records_field="items",
        pagination_mode="cursor",
        session=session,
    )

    with pytest.raises(ValueError, match="did not provide"):
        list(adapter.iter_documents())
