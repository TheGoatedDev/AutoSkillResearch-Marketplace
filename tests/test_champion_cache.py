from pathlib import Path
from scripts.champion_cache import ChampionCache, ExecutionResult


class TestChampionCache:
    def _make_cache(self, tmp_path: Path) -> ChampionCache:
        cache_dir = tmp_path / ".cache"
        return ChampionCache(cache_dir)

    def _make_result(self, output: str = "hello", token_count: int = 100, triggered: bool = True) -> ExecutionResult:
        return ExecutionResult(output=output, token_count=token_count, triggered=triggered, error=None)

    def test_get_returns_none_on_miss(self, tmp_path):
        cache = self._make_cache(tmp_path)
        assert cache.get("skill content", "case-1") is None

    def test_put_then_get_returns_result(self, tmp_path):
        cache = self._make_cache(tmp_path)
        result = self._make_result()
        cache.put("skill content", "case-1", result)
        cached = cache.get("skill content", "case-1")
        assert cached is not None
        assert cached.output == "hello"
        assert cached.token_count == 100
        assert cached.triggered is True

    def test_different_content_is_cache_miss(self, tmp_path):
        cache = self._make_cache(tmp_path)
        cache.put("skill v1", "case-1", self._make_result())
        assert cache.get("skill v2", "case-1") is None

    def test_different_case_id_is_cache_miss(self, tmp_path):
        cache = self._make_cache(tmp_path)
        cache.put("skill content", "case-1", self._make_result())
        assert cache.get("skill content", "case-2") is None

    def test_invalidate_clears_all(self, tmp_path):
        cache = self._make_cache(tmp_path)
        cache.put("skill content", "case-1", self._make_result())
        cache.put("skill content", "case-2", self._make_result())
        cache.invalidate()
        assert cache.get("skill content", "case-1") is None
        assert cache.get("skill content", "case-2") is None

    def test_get_on_nonexistent_dir_returns_none(self, tmp_path):
        cache = ChampionCache(tmp_path / "nonexistent" / ".cache")
        assert cache.get("content", "case-1") is None

    def test_put_creates_cache_dir(self, tmp_path):
        cache_dir = tmp_path / "new" / ".cache"
        cache = ChampionCache(cache_dir)
        cache.put("content", "case-1", self._make_result())
        assert cache_dir.exists()
