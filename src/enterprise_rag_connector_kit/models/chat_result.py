from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ChatResult:
    answer: str
    chat_id: str | None = None
    raw_response: dict | None = None
    citations: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "chat_id": self.chat_id,
            "citations": self.citations,
            "raw_response": self.raw_response,
        }