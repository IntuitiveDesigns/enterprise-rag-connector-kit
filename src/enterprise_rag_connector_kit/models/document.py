from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class Document:
    """
    Normalized internal document model.

    Keep this model friendly for tests and adapters. The concrete datasource used
    for indexing can be injected by the API client at send time.
    """

    id: str
    title: str
    body_text: str
    updated_at: datetime
    view_url: str | None = None
    datasource: str = ""
    mime_type: str = "text/plain"
    object_type: str = "Document"
    allow_anonymous_access: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.id = self.id.strip()
        self.title = self.title.strip()
        self.body_text = self.body_text.strip()
        self.datasource = self.datasource.strip()
        self.mime_type = self.mime_type.strip()
        self.object_type = self.object_type.strip()

        if self.view_url is not None:
            self.view_url = self.view_url.strip() or None

        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=UTC)
        else:
            self.updated_at = self.updated_at.astimezone(UTC)

    def to_glean_payload(
        self,
        datasource_override: str | None = None,
    ) -> dict[str, Any]:
        """
        Convert the normalized document into the Glean payload shape.

        Datasource can be provided either on the document itself or overridden
        by the API client.
        """
        datasource = (datasource_override or self.datasource).strip()
        if not datasource:
            raise ValueError(
                "Document datasource is required before converting to a Glean payload."
            )

        payload: dict[str, Any] = {
            "datasource": datasource,
            "objectType": self.object_type,
            "id": self.id,
            "title": self.title,
            "body": {
                "mimeType": self.mime_type,
                "textContent": self.body_text,
            },
            "permissions": {
                "allowAnonymousAccess": self.allow_anonymous_access,
            },
        }

        if self.view_url:
            payload["viewURL"] = self.view_url

        return payload

    def updated_at_iso(self) -> str:
        return self.updated_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "datasource": self.datasource,
            "object_type": self.object_type,
            "updated_at": self.updated_at_iso(),
            "view_url": self.view_url,
            "mime_type": self.mime_type,
            "allow_anonymous_access": self.allow_anonymous_access,
            "body_length": len(self.body_text),
            "metadata": self.metadata,
        }