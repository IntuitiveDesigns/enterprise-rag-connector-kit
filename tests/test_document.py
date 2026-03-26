from __future__ import annotations

from datetime import UTC, datetime

from enterprise_rag_connector_kit.models.document import Document


def test_document_to_glean_payload() -> None:
    doc = Document(
        id="doc-123",
        title="Test Title",
        body_text="Test body",
        updated_at=datetime(2026, 3, 10, 15, 0, 0, tzinfo=UTC),
        view_url="https://example.com/doc-123",
    )

    payload = doc.to_glean_payload("interviewds")

    assert payload["datasource"] == "interviewds"
    assert payload["objectType"] == "Document"
    assert payload["id"] == "doc-123"
    assert payload["title"] == "Test Title"
    assert payload["body"]["mimeType"] == "text/plain"
    assert payload["body"]["textContent"] == "Test body"
    assert payload["permissions"]["allowAnonymousAccess"] is True
    assert payload["viewURL"] == "https://example.com/doc-123"


def test_document_strips_whitespace() -> None:
    doc = Document(
        id="  doc-1  ",
        title="  Title  ",
        body_text="  Body  ",
        updated_at=datetime(2026, 3, 10, 15, 0, 0, tzinfo=UTC),
        view_url="  https://example.com/doc-1  ",
    )

    assert doc.id == "doc-1"
    assert doc.title == "Title"
    assert doc.body_text == "Body"
    assert doc.view_url == "https://example.com/doc-1"