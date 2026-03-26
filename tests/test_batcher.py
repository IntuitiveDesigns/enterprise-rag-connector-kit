from __future__ import annotations

import pytest

from enterprise_rag_connector_kit.services.batcher import Batcher


def test_batcher_splits_items_into_expected_batch_sizes() -> None:
    batcher = Batcher(batch_size=3)
    batches = list(batcher.batch([1, 2, 3, 4, 5, 6, 7]))
    assert batches == [[1, 2, 3], [4, 5, 6], [7]]


def test_batcher_rejects_invalid_batch_size() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        Batcher(batch_size=0)