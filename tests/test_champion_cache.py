import json
import subprocess
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


class TestChampionCacheCLI:
    """Test the CLI interface used by the SKILL.md orchestrator."""

    def _run(self, *args: str) -> dict:
        result = subprocess.run(
            ["python3", "-m", "scripts.champion_cache", *args],
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    def _write_content(self, tmp_path: Path, content: str = "skill content") -> Path:
        p = tmp_path / "champion.md"
        p.write_text(content)
        return p

    def test_get_miss(self, tmp_path):
        content_file = self._write_content(tmp_path)
        cache_dir = tmp_path / ".cache"
        out = self._run("get", "--cache-dir", str(cache_dir), "--champion-content-file", str(content_file), "--case-id", "c1")
        assert out["hit"] is False

    def test_put_then_get_hit(self, tmp_path):
        content_file = self._write_content(tmp_path)
        cache_dir = tmp_path / ".cache"
        result_json = json.dumps({"output": "hello", "token_count": 100, "triggered": True, "error": None})
        self._run("put", "--cache-dir", str(cache_dir), "--champion-content-file", str(content_file), "--case-id", "c1", "--result", result_json)
        out = self._run("get", "--cache-dir", str(cache_dir), "--champion-content-file", str(content_file), "--case-id", "c1")
        assert out["hit"] is True
        assert out["output"] == "hello"
        assert out["token_count"] == 100
        assert out["triggered"] is True

    def test_invalidate_clears_cache(self, tmp_path):
        content_file = self._write_content(tmp_path)
        cache_dir = tmp_path / ".cache"
        result_json = json.dumps({"output": "hi", "token_count": 50, "triggered": False, "error": None})
        self._run("put", "--cache-dir", str(cache_dir), "--champion-content-file", str(content_file), "--case-id", "c1", "--result", result_json)
        self._run("invalidate", "--cache-dir", str(cache_dir))
        out = self._run("get", "--cache-dir", str(cache_dir), "--champion-content-file", str(content_file), "--case-id", "c1")
        assert out["hit"] is False
