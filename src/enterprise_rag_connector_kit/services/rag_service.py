

from __future__ import annotations

from enterprise_rag_connector_kit.client.glean_chat import GleanChatClient
from enterprise_rag_connector_kit.models.rag_response import RagResponse
from enterprise_rag_connector_kit.services.retrieval_service import RetrievalService


class RagService:
    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        chat_client: GleanChatClient,
        datasource: str | None = None,
        corpus_hint: str | None = None,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._chat_client = chat_client
        self._datasource = datasource
        self._corpus_hint = corpus_hint

    def ask(self, question: str, *, top_k: int = 5) -> RagResponse:
        search_results = self._retrieval_service.retrieve(
            question,
            top_k=top_k,
            datasource=self._datasource,
            corpus_hint=self._corpus_hint,
        )

        if not search_results:
            return RagResponse(
                question=question,
                answer=(
                    "I could not find relevant indexed content in the target Glean "
                    "datasource for that question."
                ),
                sources=[],
            )

        context_chunks = []
        for result in search_results:
            context_chunks.append(
                "\n".join(
                    [
                        f"Title: {result.title}",
                        f"URL: {result.url or 'N/A'}",
                        f"Snippet: {result.snippet or 'N/A'}",
                    ]
                )
            )

        chat_result = self._chat_client.chat(
            question,
            context_chunks=context_chunks,
        )

        return RagResponse(
            question=question,
            answer=chat_result.answer,
            sources=search_results,
        )
