"""Retry with exponential backoff."""

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except retry_on as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
    raise last_error  # type: ignore[misc]
