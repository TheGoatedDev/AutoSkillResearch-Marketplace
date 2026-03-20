"""Champion result caching to avoid redundant cloud execution calls."""

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class ExecutionResult:
    output: str
    token_count: int
    triggered: bool
    error: str | None


class ChampionCache:
    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    def _cache_key(self, champion_content: str, case_id: str) -> str:
        data = f"{champion_content}\n---\n{case_id}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def get(self, champion_content: str, case_id: str) -> ExecutionResult | None:
        path = self._cache_path(self._cache_key(champion_content, case_id))
        try:
            data = json.loads(path.read_text())
            return ExecutionResult(**data)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            return None

    def put(self, champion_content: str, case_id: str, result: ExecutionResult) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_path(self._cache_key(champion_content, case_id))
        path.write_text(json.dumps(asdict(result), indent=2))

    def invalidate(self) -> None:
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                f.unlink()
