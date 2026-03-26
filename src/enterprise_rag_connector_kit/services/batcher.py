from __future__ import annotations

from collections.abc import Iterable, Iterator
from itertools import islice
from typing import TypeVar

T = TypeVar("T")


class Batcher:
    """
    Utility for splitting iterables into fixed-size batches.

    Designed to work with lists, generators, and adapter iterators without
    forcing all items into memory upfront.
    """

    def __init__(self, batch_size: int) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")
        self._batch_size = batch_size

    @property
    def batch_size(self) -> int:
        return self._batch_size

    def batch(self, items: Iterable[T]) -> Iterator[list[T]]:
        iterator = iter(items)

        while True:
            next_batch = list(islice(iterator, self._batch_size))
            if not next_batch:
                break
            yield next_batch
