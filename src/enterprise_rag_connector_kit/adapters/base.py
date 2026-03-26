from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from enterprise_rag_connector_kit.models.document import Document


@dataclass(slots=True)
class AdapterRecord:
    """
    Represents the result of processing one source record.

    Exactly one of these should be true:
      - document is populated and error_message is None
      - document is None and error_message is populated
    """

    record_number: int
    document: Document | None
    raw_record: dict[str, Any] | None = None
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.document is not None and self.error_message is None

    @property
    def is_rejected(self) -> bool:
        return not self.is_success


class DocumentSourceAdapter(ABC):
    """
    Abstract contract for any document source adapter.

    Adapters normalize source data into AdapterRecord objects so the pipeline
    can continue processing even when individual source records are malformed.
    """

    @abstractmethod
    def iter_documents(self) -> Iterable[AdapterRecord]:
        """
        Yield AdapterRecord objects from the source.
        """
        raise NotImplementedError

    def get_documents(self) -> list[AdapterRecord]:
        return list(self.iter_documents())

    @property
    def source_name(self) -> str:
        return self.__class__.__name__