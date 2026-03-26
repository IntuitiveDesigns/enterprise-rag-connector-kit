from __future__ import annotations

from datetime import UTC, datetime

from enterprise_rag_connector_kit.client.glean_api import GleanApiClient
from enterprise_rag_connector_kit.models.document import Document


class FakeResponse:
    def __init__(self, status_code: int, body=None) -> None:
        self.status_code = status_code
        self._body = body
        self.ok = 200 <= status_code < 300
        self.text = "" if body is None else str(body)

    def json(self):
        if isinstance(self._body, dict):
            return self._body
        raise ValueError("No JSON body")


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.headers = {}

    def post(self, *args, **kwargs):
        return self._responses.pop(0)

    def close(self):
        return None


def _sample_document() -> Document:
    return Document(
        id="doc-001",
        title="Doc 1",
        body_text="Body 1",
        updated_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC),
        view_url="https://example.com/doc-001",
    )


def test_glean_api_index_documents_success() -> None:
    session = FakeSession([FakeResponse(200, {"status": "ok"})])

    client = GleanApiClient(
        base_url="https://example.glean.com",
        datasource="interviewds",
        api_token="secret-token",
        session=session,
    )

    result = client.index_documents([_sample_document()])

    assert result.success is True
    assert result.status_code == 200
    assert result.document_count == 1
    assert result.response_body == {"status": "ok"}


def test_glean_api_retries_and_then_succeeds() -> None:
    session = FakeSession(
        [
            FakeResponse(503, {"error": "temporarily unavailable"}),
            FakeResponse(200, {"status": "ok"}),
        ]
    )

    client = GleanApiClient(
        base_url="https://example.glean.com",
        datasource="interviewds",
        api_token="secret-token",
        session=session,
        max_attempts=2,
        backoff_base_seconds=0.0,
        backoff_jitter_seconds=0.0,
    )

    result = client.index_documents([_sample_document()])

    assert result.success is True
    assert result.attempt_count == 2
    assert result.status_code == 200
