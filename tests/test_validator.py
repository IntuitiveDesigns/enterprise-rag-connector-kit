from __future__ import annotations

from datetime import datetime

from enterprise_rag_connector_kit.models.document import Document
from enterprise_rag_connector_kit.services.validator import DocumentValidator


def test_validator_accepts_valid_document(sample_document: Document) -> None:
    validator = DocumentValidator()

    outcome = validator.validate(sample_document)

    assert outcome.is_valid is True
    assert outcome.reasons == []


def test_validator_rejects_empty_title(sample_document: Document) -> None:
    validator = DocumentValidator()
    sample_document.title = ""

    outcome = validator.validate(sample_document)

    assert outcome.is_valid is False
    assert "title" in outcome.error_message.lower()


def test_validator_rejects_invalid_url(sample_document: Document) -> None:
    validator = DocumentValidator()
    sample_document.view_url = "ftp://example.com/file"

    outcome = validator.validate(sample_document)

    assert outcome.is_valid is False
    assert "http/https" in outcome.error_message


def test_validator_rejects_naive_datetime() -> None:
    validator = DocumentValidator()
    document = Document(
        id="doc-1",
        title="Title",
        body_text="Body",
        updated_at=datetime(2026, 3, 10, 12, 0, 0),
        view_url="https://example.com/doc-1",
    )


    outcome = validator.validate(document)

    assert outcome.is_valid is True

