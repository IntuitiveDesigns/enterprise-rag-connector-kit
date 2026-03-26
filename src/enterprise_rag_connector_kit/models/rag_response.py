from __future__ import annotations

from dataclasses import dataclass, field

from enterprise_rag_connector_kit.models.search_result import SearchResult


@dataclass(slots=True)
class RagResponse:
    question: str
    answer: str
    sources: list[SearchResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "sources": [source.to_dict() for source in self.sources],
        }