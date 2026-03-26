from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from enterprise_rag_connector_kit.adapters.local_json import LocalJsonAdapter


def test_local_json_adapter_loads_documents(tmp_path) -> None:
    source_file = tmp_path / "source_docs.json"
    source_payload = [
        {
            "id": "doc-001",
            "title": "First Doc",
            "body": "First body",
            "updated_at": "2026-03-10T12:00:00Z",
            "view_url": "https://example.com/doc-001",
        },
        {
            "id": "doc-002",
            "title": "Second Doc",
            "body_text": "Second body",
            "updatedAt": "2026-03-10T13:00:00Z",
            "view_url": "https://example.com/doc-002",
        },
    ]
    source_file.write_text(json.dumps(source_payload), encoding="utf-8")

    adapter = LocalJsonAdapter(source_file)
    records = list(adapter.iter_documents())

    assert len(records) == 2
    assert records[0].is_success is True
    assert records[0].document is not None
    assert records[0].document.id == "doc-001"
    assert records[0].document.title == "First Doc"
    assert records[0].document.body_text == "First body"
    assert records[0].document.updated_at == datetime(
        2026, 3, 10, 12, 0, 0, tzinfo=UTC
    )

    assert records[1].is_success is True
    assert records[1].document is not None
    assert records[1].document.id == "doc-002"
    assert records[1].document.body_text == "Second body"


def test_local_json_adapter_marks_bad_record_without_failing_whole_run(
    tmp_path,
) -> None:
    source_file = tmp_path / "source_docs.json"
    source_payload = [
        {
            "id": "doc-001",
            "title": "Good Doc",
            "body": "Good body",
            "updated_at": "2026-03-10T12:00:00Z",
            "view_url": "https://example.com/doc-001",
        },
        {
            "id": "doc-002",
            "title": "Bad Doc",
        },
    ]
    source_file.write_text(json.dumps(source_payload), encoding="utf-8")

    adapter = LocalJsonAdapter(source_file)
    records = list(adapter.iter_documents())

    assert len(records) == 2
    assert records[0].is_success is True
    assert records[1].is_rejected is True
    assert records[1].error_message is not None
    assert "body field" in records[1].error_message.lower()


def test_local_json_adapter_raises_for_non_list_payload(tmp_path) -> None:
    source_file = tmp_path / "bad.json"
    source_file.write_text(json.dumps({"bad": "shape"}), encoding="utf-8")

    adapter = LocalJsonAdapter(source_file)

    with pytest.raises(ValueError, match="top-level JSON array"):
        list(adapter.iter_documents())