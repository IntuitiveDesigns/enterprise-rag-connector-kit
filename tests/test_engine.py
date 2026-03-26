from __future__ import annotations

from datetime import UTC, datetime

from enterprise_rag_connector_kit.adapters.base import (
    AdapterRecord,
    DocumentSourceAdapter,
)
from enterprise_rag_connector_kit.core.engine import IndexingEngine
from enterprise_rag_connector_kit.models.document import Document
from enterprise_rag_connector_kit.services.batcher import Batcher
from enterprise_rag_connector_kit.services.report_writer import ReportWriter
from enterprise_rag_connector_kit.services.validator import DocumentValidator


class FakeAdapter(DocumentSourceAdapter):
    def __init__(self, records):
        self._records = records

    def iter_documents(self):
        yield from self._records


class FakeClientResult:
    def __init__(self, *, success=True, document_count=1):
        self.success = success
        self.datasource = "interviewds"
        self.document_count = document_count
        self.status_code = 200 if success else 500
        self.attempt_count = 1
        self.elapsed_ms = 5
        self.response_body = {"status": "ok"} if success else {"error": "failure"}
        self.error_message = None if success else "failure"


class FakeClient:
    datasource = "interviewds"

    def index_documents(self, documents):
        return FakeClientResult(success=True, document_count=len(documents))


def test_engine_processes_valid_documents(tmp_path) -> None:
    docs = [
        AdapterRecord(
            record_number=1,
            document=Document(
                id="doc-001",
                title="Doc 1",
                body_text="Body 1",
                updated_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC),
                view_url="https://example.com/doc-001",
            ),
            raw_record={"id": "doc-001"},
        ),
        AdapterRecord(
            record_number=2,
            document=Document(
                id="doc-002",
                title="Doc 2",
                body_text="Body 2",
                updated_at=datetime(2026, 3, 10, 12, 5, 0, tzinfo=UTC),
                view_url="https://example.com/doc-002",
            ),
            raw_record={"id": "doc-002"},
        ),
    ]

    engine = IndexingEngine(
        adapter=FakeAdapter(docs),
        client=FakeClient(),
        validator=DocumentValidator(),
        batcher=Batcher(1),
        report_writer=ReportWriter(tmp_path),
        run_prefix="TEST",
    )

    report = engine.run()

    assert report.success is True
    assert report.total_source_records == 2
    assert report.valid_documents == 2
    assert report.rejected_documents == 0
    assert report.indexed_documents == 2
    assert report.total_batches == 2


def test_engine_tracks_adapter_rejections(tmp_path) -> None:
    records = [
        AdapterRecord(
            record_number=1,
            document=Document(
                id="doc-001",
                title="Doc 1",
                body_text="Body 1",
                updated_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC),
                view_url="https://example.com/doc-001",
            ),
            raw_record={"id": "doc-001"},
        ),
        AdapterRecord(
            record_number=2,
            document=None,
            raw_record={"id": "doc-002"},
            error_message="Missing body field.",
        ),
    ]

    engine = IndexingEngine(
        adapter=FakeAdapter(records),
        client=FakeClient(),
        validator=DocumentValidator(),
        batcher=Batcher(10),
        report_writer=ReportWriter(tmp_path),
        run_prefix="TEST",
    )

    report = engine.run()

    assert report.total_source_records == 2
    assert report.valid_documents == 1
    assert report.rejected_documents == 1
    assert report.indexed_documents == 1
    assert report.total_batches == 1
