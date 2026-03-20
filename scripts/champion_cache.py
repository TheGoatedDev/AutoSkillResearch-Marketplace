"""Champion result caching to avoid redundant cloud execution calls.

CLI usage:
    python3 scripts/champion_cache.py get --cache-dir <dir> --champion-content-file <path> --case-id <id>
    python3 scripts/champion_cache.py put --cache-dir <dir> --champion-content-file <path> --case-id <id> --result '<json>'
    python3 scripts/champion_cache.py invalidate --cache-dir <dir>
"""

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


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Champion result cache operations")
    sub = parser.add_subparsers(dest="command", required=True)

    get_cmd = sub.add_parser("get", help="Get cached champion result")
    get_cmd.add_argument("--cache-dir", required=True, help="Path to cache directory")
    get_cmd.add_argument("--champion-content-file", required=True, help="Path to file containing champion SKILL.md content")
    get_cmd.add_argument("--case-id", required=True, help="Eval case ID")

    put_cmd = sub.add_parser("put", help="Cache a champion result")
    put_cmd.add_argument("--cache-dir", required=True, help="Path to cache directory")
    put_cmd.add_argument("--champion-content-file", required=True, help="Path to file containing champion SKILL.md content")
    put_cmd.add_argument("--case-id", required=True, help="Eval case ID")
    put_cmd.add_argument("--result", required=True, help="JSON result from skill-executor")

    inv_cmd = sub.add_parser("invalidate", help="Clear all cached results")
    inv_cmd.add_argument("--cache-dir", required=True, help="Path to cache directory")

    args = parser.parse_args()
    cache = ChampionCache(Path(args.cache_dir))

    if args.command == "get":
        content = Path(args.champion_content_file).read_text()
        result = cache.get(content, args.case_id)
        if result is not None:
            print(json.dumps({"hit": True, **asdict(result)}))
        else:
            print(json.dumps({"hit": False}))

    elif args.command == "put":
        content = Path(args.champion_content_file).read_text()
        data = json.loads(args.result)
        result = ExecutionResult(
            output=data["output"],
            token_count=data["token_count"],
            triggered=data["triggered"],
            error=data.get("error"),
        )
        cache.put(content, args.case_id, result)
        print(json.dumps({"status": "cached"}))

    elif args.command == "invalidate":
        cache.invalidate()
        print(json.dumps({"status": "invalidated"}))


if __name__ == "__main__":
    main()
