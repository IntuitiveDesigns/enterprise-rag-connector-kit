from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SearchResult:
    document_id: str | None
    title: str
    url: str | None
    snippet: str | None
    datasource: str | None = None

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "datasource": self.datasource,
        }