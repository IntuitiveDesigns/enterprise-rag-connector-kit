

from __future__ import annotations

import logging
from datetime import UTC, datetime

from enterprise_rag_connector_kit.adapters.base import (
    AdapterRecord,
    DocumentSourceAdapter,
)
from enterprise_rag_connector_kit.client.glean_api import GleanApiClient
from enterprise_rag_connector_kit.models.batch_result import BatchResult
from enterprise_rag_connector_kit.models.document import Document
from enterprise_rag_connector_kit.models.run_report import RejectedDocument, RunReport
from enterprise_rag_connector_kit.services.batcher import Batcher
from enterprise_rag_connector_kit.services.report_writer import ReportWriter
from enterprise_rag_connector_kit.services.validator import DocumentValidator

LOGGER = logging.getLogger(__name__)


class IndexingEngine:
    """
    Orchestrates the end-to-end indexing workflow.
    """

    def __init__(
        self,
        *,
        adapter: DocumentSourceAdapter,
        client: GleanApiClient,
        validator: DocumentValidator,
        batcher: Batcher,
        report_writer: ReportWriter,
        run_prefix: str,
    ) -> None:
        self._adapter = adapter
        self._client = client
        self._validator = validator
        self._batcher = batcher
        self._report_writer = report_writer
        self._run_prefix = run_prefix.strip() or "GLEAN-RUN"

    def run(self) -> RunReport:
        run_report = RunReport(
            run_id=self._build_run_id(),
            datasource=self._client.datasource,
            adapter_name=self._adapter.source_name,
            started_at=datetime.now(UTC),
        )

        LOGGER.info(
            "Starting indexing run: run_id=%s datasource=%s adapter=%s",
            run_report.run_id,
            run_report.datasource,
            run_report.adapter_name,
        )

        valid_documents = self._load_and_validate_documents(run_report)

        LOGGER.info(
            "Validation complete: total_source_records=%s "
            "valid_documents=%s rejected_documents=%s",
            run_report.total_source_records,
            run_report.valid_documents,
            run_report.rejected_documents,
        )

        for batch_number, batch_documents in enumerate(
            self._batcher.batch(valid_documents),
            start=1,
        ):
            LOGGER.info(
                "Submitting batch %s with %s documents",
                batch_number,
                len(batch_documents),
            )
            batch_result = self._index_batch(batch_number, batch_documents)
            run_report.add_batch_result(batch_result)

        run_report.mark_completed()
        self._report_writer.write_all(run_report)

        LOGGER.info(
            "Run complete: run_id=%s success=%s indexed_documents=%s "
            "failed_documents=%s total_batches=%s",
            run_report.run_id,
            run_report.success,
            run_report.indexed_documents,
            run_report.failed_documents,
            run_report.total_batches,
        )

        return run_report

    def _load_and_validate_documents(self, run_report: RunReport) -> list[Document]:
        valid_documents: list[Document] = []

        for item in self._adapter.iter_documents():
            run_report.total_source_records += 1

            if not isinstance(item, AdapterRecord):
                self._add_rejected(
                    run_report=run_report,
                    record_number=None,
                    document_id=None,
                    title=None,
                    reason=(
                        "Adapter returned unexpected object type: "
                        f"{type(item).__name__}"
                    ),
                    raw_record=None,
                )
                continue

            if item.is_rejected or item.document is None:
                self._add_rejected(
                    run_report=run_report,
                    record_number=item.record_number,
                    document_id=None,
                    title=None,
                    reason=item.error_message or "Adapter rejected source record.",
                    raw_record=item.raw_record,
                )
                continue

            document = item.document
            validation = self._validator.validate(document)

            if not validation.is_valid:
                self._add_rejected(
                    run_report=run_report,
                    record_number=item.record_number,
                    document_id=document.id,
                    title=document.title,
                    reason=validation.error_message or "Document validation failed.",
                    raw_record=item.raw_record or document.to_summary_dict(),
                )
                continue

            valid_documents.append(document)

        run_report.valid_documents = len(valid_documents)
        return valid_documents

    def _index_batch(self, batch_number: int, documents: list[Document]) -> BatchResult:
        client_result = self._client.index_documents(documents)

        return BatchResult(
            batch_number=batch_number,
            document_count=client_result.document_count,
            success=client_result.success,
            attempt_count=client_result.attempt_count,
            elapsed_ms=client_result.elapsed_ms,
            datasource=client_result.datasource,
            status_code=client_result.status_code,
            error_message=client_result.error_message,
            response_body=client_result.response_body,
            document_ids=[document.id for document in documents],
        )

    @staticmethod
    def _add_rejected(
        *,
        run_report: RunReport,
        record_number: int | None,
        document_id: str | None,
        title: str | None,
        reason: str,
        raw_record: dict | None,
    ) -> None:
        run_report.add_rejected_document(
            RejectedDocument(
                record_number=record_number,
                document_id=document_id,
                title=title,
                reason=reason,
                raw_record=raw_record,
            )
        )

    def _build_run_id(self) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        safe_prefix = self._run_prefix.replace(" ", "-")
        return f"{safe_prefix}-{timestamp}"
