"""Concurrency guard for the autoresearch loop."""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path


def acquire_lock(lock_path: Path, skill: str, stale_hours: int = 4) -> bool:
    if lock_path.exists():
        if not _is_stale(lock_path, stale_hours):
            return False
    lock_data = {"pid": os.getpid(), "started_at": datetime.now(timezone.utc).isoformat(), "skill": skill}
    lock_path.write_text(json.dumps(lock_data, indent=2))
    return True


def release_lock(lock_path: Path) -> None:
    if lock_path.exists():
        lock_path.unlink()


def refresh_lock(lock_path: Path) -> None:
    if lock_path.exists():
        data = json.loads(lock_path.read_text())
        data["started_at"] = datetime.now(timezone.utc).isoformat()
        lock_path.write_text(json.dumps(data, indent=2))


def is_locked(lock_path: Path, stale_hours: int = 4) -> bool:
    if not lock_path.exists():
        return False
    return not _is_stale(lock_path, stale_hours)


def _is_stale(lock_path: Path, stale_hours: int) -> bool:
    data = json.loads(lock_path.read_text())
    started = datetime.fromisoformat(data["started_at"])
    return datetime.now(timezone.utc) - started > timedelta(hours=stale_hours)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Autoresearch lockfile management")
    sub = parser.add_subparsers(dest="command", required=True)

    acquire_cmd = sub.add_parser("acquire", help="Acquire lock")
    acquire_cmd.add_argument("--skill", required=True)
    acquire_cmd.add_argument("--lock-path", default=".autoresearch.lock")
    acquire_cmd.add_argument("--stale-hours", type=int, default=4)

    release_cmd = sub.add_parser("release", help="Release lock")
    release_cmd.add_argument("--lock-path", default=".autoresearch.lock")

    refresh_cmd = sub.add_parser("refresh", help="Refresh lock timestamp")
    refresh_cmd.add_argument("--lock-path", default=".autoresearch.lock")

    check_cmd = sub.add_parser("check", help="Check if locked")
    check_cmd.add_argument("--lock-path", default=".autoresearch.lock")
    check_cmd.add_argument("--stale-hours", type=int, default=4)

    args = parser.parse_args()

    if args.command == "acquire":
        result = acquire_lock(Path(args.lock_path), args.skill, args.stale_hours)
        status = "acquired" if result else "blocked"
        print(json.dumps({"status": status}))
    elif args.command == "release":
        release_lock(Path(args.lock_path))
        print('{"status": "released"}')
    elif args.command == "refresh":
        refresh_lock(Path(args.lock_path))
        print('{"status": "refreshed"}')
    elif args.command == "check":
        locked = is_locked(Path(args.lock_path), args.stale_hours)
        info = {}
        if locked:
            info = json.loads(Path(args.lock_path).read_text())
        print(json.dumps({"locked": locked, **info}))


if __name__ == "__main__":
    main()
