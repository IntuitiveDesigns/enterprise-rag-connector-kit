from .base import AdapterRecord, DocumentSourceAdapter
from .local_json import LocalJsonAdapter
from .rest_api import RestApiAdapter

__all__ = [
    "AdapterRecord",
    "DocumentSourceAdapter",
    "LocalJsonAdapter",
    "RestApiAdapter",
]