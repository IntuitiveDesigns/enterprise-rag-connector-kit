from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv

from enterprise_rag_connector_kit.client.glean_chat import GleanChatClient
from enterprise_rag_connector_kit.client.glean_search import GleanSearchClient
from enterprise_rag_connector_kit.core.logging_config import configure_logging
from enterprise_rag_connector_kit.services.rag_service import RagService
from enterprise_rag_connector_kit.services.retrieval_service import RetrievalService


def main() -> int:
    load_dotenv()

    if len(sys.argv) < 2:
        print('Usage: python ask_chatbot.py "your question" [top_k]')
        return 1

    question = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    configure_logging(os.getenv("GLEAN_LOG_LEVEL", "INFO"))

    base_url = os.environ["GLEAN_BASE_URL"]
    client_token = os.environ["GLEAN_CLIENT_API_TOKEN"]
    datasource = os.getenv("GLEAN_DATASOURCE", "sample-datasource")
    corpus_hint = os.getenv("GLEAN_CORPUS_HINT", "")
    agent_id = os.getenv("GLEAN_CHAT_AGENT_ID")

    search_client = GleanSearchClient(
        base_url=base_url,
        api_token=client_token,
    )
    chat_client = GleanChatClient(
        base_url=base_url,
        api_token=client_token,
        agent_id=agent_id,
    )
    retrieval_service = RetrievalService(search_client)
    rag_service = RagService(
        retrieval_service=retrieval_service,
        chat_client=chat_client,
        datasource=datasource,
        corpus_hint=corpus_hint,
    )

    try:
        response = rag_service.ask(question, top_k=top_k)
        print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))
        return 0
    finally:
        search_client.close()
        chat_client.close()


if __name__ == "__main__":
    raise SystemExit(main())