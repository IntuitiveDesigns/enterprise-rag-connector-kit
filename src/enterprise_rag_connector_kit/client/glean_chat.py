from __future__ import annotations

import logging

import requests

from enterprise_rag_connector_kit.models.chat_result import ChatResult

LOGGER = logging.getLogger(__name__)


class GleanChatClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 60.0,
        session: requests.Session | None = None,
        agent_id: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._connect_timeout_seconds = connect_timeout_seconds
        self._read_timeout_seconds = read_timeout_seconds
        self._agent_id = agent_id
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def chat(
        self,
        question: str,
        *,
        context_chunks: list[str] | None = None,
    ) -> ChatResult:
        prompt_text = self._build_grounded_prompt(
            question=question,
            context_chunks=context_chunks or [],
        )

        payload: dict = {
            "messages": [
                {
                    "author": "USER",
                    "fragments": [{"text": prompt_text}],
                }
            ]
        }

        if self._agent_id:
            payload["agentId"] = self._agent_id

        response = self._session.post(
            f"{self._base_url}/rest/api/v1/chat",
            json=payload,
            timeout=(self._connect_timeout_seconds, self._read_timeout_seconds),
        )
        response.raise_for_status()

        data = response.json()
        answer = self._extract_answer_text(data)

        return ChatResult(
            answer=answer,
            chat_id=data.get("chatId"),
            raw_response=data,
            citations=data.get("citations", []),
        )

    def _build_grounded_prompt(
        self,
        *,
        question: str,
        context_chunks: list[str],
    ) -> str:
        if not context_chunks:
            return question

        joined_context = "\n\n".join(context_chunks)

        return (
            "Answer the user's question using only the provided retrieved context. "
            "If the answer cannot be determined from the context, say so clearly.\n\n"
            "Retrieved context:\n"
            f"{joined_context}\n\n"
            "User question:\n"
            f"{question}"
        )

    def _extract_answer_text(self, data: dict) -> str:
        if isinstance(data.get("answer"), str) and data["answer"].strip():
            return data["answer"].strip()

        message = data.get("message")
        if isinstance(message, dict):
            fragments = message.get("fragments", [])
            texts = [
                fragment.get("text", "")
                for fragment in fragments
                if isinstance(fragment, dict) and fragment.get("text")
            ]
            if texts:
                return "\n".join(texts).strip()

        messages = data.get("messages", [])
        if isinstance(messages, list):
            for message_item in reversed(messages):
                if not isinstance(message_item, dict):
                    continue
                if message_item.get("author") in {"GLEAN_AI", "ASSISTANT"}:
                    fragments = message_item.get("fragments", [])
                    texts = [
                        fragment.get("text", "")
                        for fragment in fragments
                        if isinstance(fragment, dict) and fragment.get("text")
                    ]
                    if texts:
                        return "\n".join(texts).strip()

        return "No answer text was returned by the Chat API."

    def close(self) -> None:
        self._session.close()