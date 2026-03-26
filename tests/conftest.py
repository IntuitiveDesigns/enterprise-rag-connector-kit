from __future__ import annotations

from datetime import UTC, datetime

import pytest

from enterprise_rag_connector_kit.models.document import Document


@pytest.fixture
def sample_document() -> Document:
    return Document(
        id="doc-001",
        title="Sample Title",
        body_text="Sample body text for testing.",
        updated_at=datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC),
        view_url="https://example.com/doc-001",
    )
