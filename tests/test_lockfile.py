import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scripts.lockfile import acquire_lock, release_lock, refresh_lock, is_locked


class TestAcquireLock:
    def test_creates_lock_file(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        result = acquire_lock(lock_path, skill="test-skill")
        assert result is True
        assert lock_path.exists()
        data = json.loads(lock_path.read_text())
        assert data["skill"] == "test-skill"
        assert "pid" in data
        assert "started_at" in data

    def test_refuses_if_lock_exists_and_fresh(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        acquire_lock(lock_path, skill="first")
        result = acquire_lock(lock_path, skill="second")
        assert result is False

    def test_overwrites_stale_lock(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        lock_path.write_text(json.dumps({"pid": 99999, "started_at": stale_time, "skill": "old"}))
        result = acquire_lock(lock_path, skill="new", stale_hours=4)
        assert result is True
        data = json.loads(lock_path.read_text())
        assert data["skill"] == "new"


class TestReleaseLock:
    def test_deletes_lock_file(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        acquire_lock(lock_path, skill="test")
        release_lock(lock_path)
        assert not lock_path.exists()

    def test_noop_if_no_lock(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        release_lock(lock_path)


class TestRefreshLock:
    def test_updates_timestamp(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        acquire_lock(lock_path, skill="test")
        old_data = json.loads(lock_path.read_text())
        refresh_lock(lock_path)
        new_data = json.loads(lock_path.read_text())
        assert new_data["started_at"] >= old_data["started_at"]


class TestIsLocked:
    def test_returns_false_when_no_lock(self, tmp_path):
        assert is_locked(tmp_path / ".autoresearch.lock") is False

    def test_returns_true_when_locked(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        acquire_lock(lock_path, skill="test")
        assert is_locked(lock_path) is True

    def test_returns_false_when_stale(self, tmp_path):
        lock_path = tmp_path / ".autoresearch.lock"
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        lock_path.write_text(json.dumps({"pid": 99999, "started_at": stale_time, "skill": "old"}))
        assert is_locked(lock_path, stale_hours=4) is False
