from __future__ import annotations

import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from enterprise_rag_connector_kit.client.glean_chat import GleanChatClient
from enterprise_rag_connector_kit.client.glean_search import GleanSearchClient
from enterprise_rag_connector_kit.services.rag_service import RagService
from enterprise_rag_connector_kit.services.retrieval_service import RetrievalService

load_dotenv()

mcp = FastMCP("glean-enterprise-chatbot")


def _build_rag_service() -> RagService:
    base_url = os.environ["GLEAN_BASE_URL"]
    client_token = os.environ["GLEAN_CLIENT_API_TOKEN"]
    datasource = os.getenv("GLEAN_DATASOURCE", "interviewds")
    corpus_hint = os.getenv("GLEAN_CORPUS_HINT", "STEVEN-GLEAN-DEMO-20260310")
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

    return RagService(
        retrieval_service=retrieval_service,
        chat_client=chat_client,
        datasource=datasource,
        corpus_hint=corpus_hint,
    )


@mcp.tool()
def ask_enterprise_chatbot(question: str, top_k: int = 5) -> dict:
    rag_service = _build_rag_service()
    response = rag_service.ask(question, top_k=top_k)
    return response.to_dict()


if __name__ == "__main__":
    mcp.run()