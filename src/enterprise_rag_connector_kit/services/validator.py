from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from enterprise_rag_connector_kit.models.document import Document


@dataclass(slots=True)
class ValidationOutcome:
    is_valid: bool
    reasons: list[str]

    @property
    def error_message(self) -> str | None:
        if not self.reasons:
            return None
        return "; ".join(self.reasons)


class DocumentValidator:
    """
    Validates normalized Document instances before they are submitted to Glean.

    This validator is intentionally focused on connector-side sanity checks.
    It does not try to enforce every possible API-level rule, but it does catch
    the most likely bad inputs early and clearly.
    """

    def __init__(
        self,
        *,
        max_id_length: int = 512,
        max_title_length: int = 2048,
        max_body_length: int = 5_000_000,
        max_view_url_length: int = 4096,
        allowed_mime_types: set[str] | None = None,
    ) -> None:
        self._max_id_length = max_id_length
        self._max_title_length = max_title_length
        self._max_body_length = max_body_length
        self._max_view_url_length = max_view_url_length
        self._allowed_mime_types = allowed_mime_types or {"text/plain"}

    def validate(self, document: Document) -> ValidationOutcome:
        reasons: list[str] = []

        if not document.id.strip():
            reasons.append("Document id must be non-empty.")

        if len(document.id) > self._max_id_length:
            reasons.append(
                f"Document id exceeds maximum length of {self._max_id_length}."
            )

        if not document.title.strip():
            reasons.append("Document title must be non-empty.")

        if len(document.title) > self._max_title_length:
            reasons.append(
                f"Document title exceeds maximum length of {self._max_title_length}."
            )

        if not document.body_text.strip():
            reasons.append("Document body_text must be non-empty.")

        if len(document.body_text) > self._max_body_length:
            reasons.append(
                f"Document body_text exceeds maximum length of {self._max_body_length}."
            )

        if not document.mime_type.strip():
            reasons.append("Document mime_type must be non-empty.")

        if document.mime_type not in self._allowed_mime_types:
            reasons.append(
                f"Unsupported mime_type '{document.mime_type}'. "
                f"Allowed values: {sorted(self._allowed_mime_types)}."
            )

        if document.view_url is not None:
            if len(document.view_url) > self._max_view_url_length:
                reasons.append(
                    f"Document view_url exceeds maximum length of "
                    f"{self._max_view_url_length}."
                )
            elif not self._is_reasonable_url(document.view_url):
                reasons.append("Document view_url must be a valid http/https URL.")

        if document.updated_at.tzinfo is None:
            reasons.append("Document updated_at must be timezone-aware.")

        return ValidationOutcome(
            is_valid=not reasons,
            reasons=reasons,
        )

    def validate_or_raise(self, document: Document) -> None:
        outcome = self.validate(document)
        if not outcome.is_valid:
            raise ValueError(outcome.error_message or "Document validation failed.")

    @staticmethod
    def _is_reasonable_url(value: str) -> bool:
        try:
            parsed = urlparse(value)
        except ValueError:
            return False

        if parsed.scheme not in {"http", "https"}:
            return False

        if not parsed.netloc:
            return False

        return True
