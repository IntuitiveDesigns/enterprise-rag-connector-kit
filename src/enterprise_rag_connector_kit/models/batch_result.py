from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BatchResult:
    """
    Result of attempting to index a single batch to Glean.

    This is intended to be the durable, pipeline-facing result object used by
    the engine and report writer, regardless of the lower-level client details.
    """

    batch_number: int
    document_count: int
    success: bool
    attempt_count: int
    elapsed_ms: int
    datasource: str
    status_code: int | None = None
    error_message: str | None = None
    response_body: dict[str, Any] | str | None = None
    document_ids: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return not self.success

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_number": self.batch_number,
            "document_count": self.document_count,
            "success": self.success,
            "attempt_count": self.attempt_count,
            "elapsed_ms": self.elapsed_ms,
            "datasource": self.datasource,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "response_body": self.response_body,
            "document_ids": self.document_ids,
        }
