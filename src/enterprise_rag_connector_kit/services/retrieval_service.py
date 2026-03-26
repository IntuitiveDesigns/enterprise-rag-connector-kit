from __future__ import annotations

from enterprise_rag_connector_kit.client.glean_search import GleanSearchClient
from enterprise_rag_connector_kit.models.search_result import SearchResult


class RetrievalService:
    def __init__(self, search_client: GleanSearchClient) -> None:
        self._search_client = search_client

    def retrieve(
        self,
        question: str,
        *,
        top_k: int = 5,
        datasource: str | None = None,
        corpus_hint: str | None = None,
    ) -> list[SearchResult]:
        query = question.strip()

        if corpus_hint:
            query = f"{corpus_hint} {query}".strip()

        results = self._search_client.search(query, top_k=max(top_k * 3, top_k))

        if datasource:
            filtered = [
                result for result in results if result.datasource == datasource
            ]
            return filtered[:top_k]

        return results[:top_k]