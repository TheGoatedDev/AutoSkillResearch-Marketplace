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
