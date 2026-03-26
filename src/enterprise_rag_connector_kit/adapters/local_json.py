from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from enterprise_rag_connector_kit.adapters.base import (
    AdapterRecord,
    DocumentSourceAdapter,
)
from enterprise_rag_connector_kit.models.document import Document


class LocalJsonAdapter(DocumentSourceAdapter):
    BODY_FIELD_CANDIDATES: tuple[str, ...] = ("body", "body_text", "text", "content")
    UPDATED_AT_FIELD_CANDIDATES: tuple[str, ...] = (
        "updated_at",
        "updatedAt",
        "last_updated",
    )

    def __init__(self, json_path: str | Path, datasource: str = "") -> None:
        self._json_path = Path(json_path)
        self._datasource = datasource.strip()

    def iter_documents(self) -> Iterable[AdapterRecord]:
        payload = self._load_json()

        if not isinstance(payload, list):
            raise ValueError(
                f"Expected top-level JSON array in '{self._json_path}', "
                f"but found {type(payload).__name__}."
            )

        for index, raw_record in enumerate(payload, start=1):
            if not isinstance(raw_record, dict):
                yield AdapterRecord(
                    record_number=index,
                    document=None,
                    raw_record={"raw_value": raw_record},
                    error_message=(
                        f"Expected object at index {index - 1} in '{self._json_path}', "
                        f"but found {type(raw_record).__name__}."
                    ),
                )
                continue

            try:
                document = self._to_document(raw_record=raw_record, record_number=index)
                yield AdapterRecord(
                    record_number=index,
                    document=document,
                    raw_record=raw_record,
                    error_message=None,
                )
            except ValueError as exc:
                yield AdapterRecord(
                    record_number=index,
                    document=None,
                    raw_record=raw_record,
                    error_message=str(exc),
                )

    def _load_json(self) -> Any:
        if not self._json_path.exists():
            raise FileNotFoundError(f"Source JSON file not found: {self._json_path}")

        if not self._json_path.is_file():
            raise ValueError(f"Source path is not a file: {self._json_path}")

        try:
            with self._json_path.open("r", encoding="utf-8") as infile:
                return json.load(infile)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in '{self._json_path}' at line {exc.lineno}, "
                f"column {exc.colno}: {exc.msg}"
            ) from exc

    def _to_document(self, raw_record: dict[str, Any], record_number: int) -> Document:
        doc_id = self._require_non_empty_string(raw_record, "id", record_number)
        title = self._require_non_empty_string(raw_record, "title", record_number)
        body_text = self._extract_body_text(raw_record, record_number)
        updated_at = self._extract_updated_at(raw_record, record_number)
        view_url = self._extract_optional_string(raw_record, "view_url")

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
        for field_name in self.BODY_FIELD_CANDIDATES:
            value = raw_record.get(field_name)
            if isinstance(value, str) and value.strip():
                return value.strip()

        supported = ", ".join(self.BODY_FIELD_CANDIDATES)
        raise ValueError(
            f"Record {record_number} is missing a non-empty body field. "
            f"Supported fields: {supported}."
        )

    def _extract_updated_at(
        self,
        raw_record: dict[str, Any],
        record_number: int,
    ) -> datetime:
        raw_timestamp: str | None = None

        for field_name in self.UPDATED_AT_FIELD_CANDIDATES:
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
                f"Record {record_number} has invalid timestamp '{raw_timestamp}'. "
                "Expected ISO-8601 format such as '2026-03-10T14:30:00Z'."
            ) from exc

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC)

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
        stripped = value.strip()
        return stripped or None