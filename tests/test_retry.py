import pytest
from scripts.retry import with_retry


class TestWithRetry:
    def test_succeeds_on_first_try(self):
        calls = []
        def fn():
            calls.append(1)
            return "ok"
        assert with_retry(fn, max_retries=3, base_delay=0.01) == "ok"
        assert len(calls) == 1

    def test_retries_on_failure_then_succeeds(self):
        attempts = []
        def fn():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("not yet")
            return "ok"
        assert with_retry(fn, max_retries=3, base_delay=0.01) == "ok"
        assert len(attempts) == 3

    def test_raises_after_max_retries(self):
        def fn():
            raise ValueError("always fail")
        with pytest.raises(ValueError, match="always fail"):
            with_retry(fn, max_retries=3, base_delay=0.01)

    def test_only_retries_specified_exceptions(self):
        def fn():
            raise TypeError("wrong type")
        with pytest.raises(TypeError):
            with_retry(fn, max_retries=3, base_delay=0.01, retry_on=(ValueError,))
