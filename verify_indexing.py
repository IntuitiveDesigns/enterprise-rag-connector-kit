from __future__ import annotations

import json
import os
import sys

import requests
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()

    base_url = os.environ["GLEAN_BASE_URL"]
    client_token = os.environ["GLEAN_CLIENT_API_TOKEN"]
    query = os.getenv("GLEAN_VERIFY_QUERY") or os.getenv(
        "GLEAN_CORPUS_HINT", "enterprise-rag-demo"
    )

    url = f"{base_url}/rest/api/v1/search"
    payload = {
        "query": query,
        "pageSize": 10,
    }
    headers = {
        "Authorization": f"Bearer {client_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    print("Status:", response.status_code)
    print("URL:", url)
    print("Query:", query)

    try:
        data = response.json()
    except ValueError:
        print("Non-JSON response body:")
        print(response.text[:2000] if response.text else "<empty>")
        return 1

    if response.status_code != 200:
        print("JSON error response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 1

    print("\nTop Results:")
    results = data.get("results", [])
    if not results:
        print("No results returned.")
        return 2

    for idx, result in enumerate(results, start=1):
        title = result.get("title", "<no title>")
        url_value = result.get("url") or result.get("viewURL") or "<no url>"
        print(f"{idx}. {title}")
        print(f"   {url_value}")

    return 0


if __name__ == "__main__":
    sys.exit(main())