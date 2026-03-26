from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from enterprise_rag_connector_kit.models.batch_result import BatchResult


@dataclass(slots=True)
class RejectedDocument:
    """
    Captures a document that was rejected before indexing, typically during
    source normalization or validation.
    """

    record_number: int | None
    document_id: str | None
    title: str | None
    reason: str
    raw_record: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_number": self.record_number,
            "document_id": self.document_id,
            "title": self.title,
            "reason": self.reason,
            "raw_record": self.raw_record,
        }


@dataclass(slots=True)
class RunReport:
    """
    Aggregated report for a complete indexing run.
    """

    run_id: str
    datasource: str
    adapter_name: str
    started_at: datetime
    completed_at: datetime | None = None

    total_source_records: int = 0
    valid_documents: int = 0
    rejected_documents: int = 0
    indexed_documents: int = 0
    failed_documents: int = 0

    batch_results: list[BatchResult] = field(default_factory=list)
    rejected_document_details: list[RejectedDocument] = field(default_factory=list)

    output_summary_path: str | None = None
    output_rejected_path: str | None = None
    output_batch_results_path: str | None = None

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None:
            self.started_at = self.started_at.replace(tzinfo=UTC)
        else:
            self.started_at = self.started_at.astimezone(UTC)

        if self.completed_at is not None:
            if self.completed_at.tzinfo is None:
                self.completed_at = self.completed_at.replace(tzinfo=UTC)
            else:
                self.completed_at = self.completed_at.astimezone(UTC)

    def mark_completed(self) -> None:
        self.completed_at = datetime.now(UTC)

    @property
    def successful_batches(self) -> int:
        return sum(1 for batch in self.batch_results if batch.success)

    @property
    def failed_batches(self) -> int:
        return sum(1 for batch in self.batch_results if not batch.success)

    @property
    def total_batches(self) -> int:
        return len(self.batch_results)

    @property
    def duration_ms(self) -> int | None:
        if self.completed_at is None:
            return None
        return int((self.completed_at - self.started_at).total_seconds() * 1000)

    @property
    def success(self) -> bool:
        return self.failed_batches == 0 and self.failed_documents == 0

    def add_batch_result(self, batch_result: BatchResult) -> None:
        self.batch_results.append(batch_result)

        if batch_result.success:
            self.indexed_documents += batch_result.document_count
        else:
            self.failed_documents += batch_result.document_count

    def add_rejected_document(self, rejected_document: RejectedDocument) -> None:
        self.rejected_document_details.append(rejected_document)
        self.rejected_documents += 1

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "datasource": self.datasource,
            "adapter_name": self.adapter_name,
            "started_at": self._to_iso(self.started_at),
            "completed_at": self._to_iso(self.completed_at),
            "duration_ms": self.duration_ms,
            "success": self.success,
            "total_source_records": self.total_source_records,
            "valid_documents": self.valid_documents,
            "rejected_documents": self.rejected_documents,
            "indexed_documents": self.indexed_documents,
            "failed_documents": self.failed_documents,
            "total_batches": self.total_batches,
            "successful_batches": self.successful_batches,
            "failed_batches": self.failed_batches,
            "output_summary_path": self.output_summary_path,
            "output_rejected_path": self.output_rejected_path,
            "output_batch_results_path": self.output_batch_results_path,
        }

    def to_detailed_dict(self) -> dict[str, Any]:
        return {
            **self.to_summary_dict(),
            "batch_results": [batch.to_dict() for batch in self.batch_results],
            "rejected_document_details": [
                item.to_dict() for item in self.rejected_document_details
            ],
        }

    @staticmethod
    def _to_iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
