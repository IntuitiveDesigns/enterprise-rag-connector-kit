from __future__ import annotations

import logging

import requests

from enterprise_rag_connector_kit.models.search_result import SearchResult

LOGGER = logging.getLogger(__name__)


class GleanSearchClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._connect_timeout_seconds = connect_timeout_seconds
        self._read_timeout_seconds = read_timeout_seconds
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def search(self, query: str, *, top_k: int = 5) -> list[SearchResult]:
        payload = {
            "query": query,
            "pageSize": top_k,
        }

        response = self._session.post(
            f"{self._base_url}/rest/api/v1/search",
            json=payload,
            timeout=(self._connect_timeout_seconds, self._read_timeout_seconds),
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        normalized: list[SearchResult] = []
        for item in results:
            normalized.append(
                SearchResult(
                    document_id=(
                        item.get("document", {}).get("id")
                        if isinstance(item.get("document"), dict)
                        else item.get("documentId")
                    ),
                    title=item.get("title") or "<untitled>",
                    url=item.get("url") or item.get("viewURL"),
                    snippet=(
                        item.get("snippets", [{}])[0].get("text")
                        if isinstance(item.get("snippets"), list)
                        and item.get("snippets")
                        and isinstance(item.get("snippets")[0], dict)
                        else item.get("snippet")
                    ),
                    datasource=(
                        item.get("document", {}).get("datasource")
                        if isinstance(item.get("document"), dict)
                        else item.get("datasource")
                    ),
                )
            )

        LOGGER.info("Search returned %s results for query=%r", len(normalized), query)
        return normalized

    def close(self) -> None:
        self._session.close()