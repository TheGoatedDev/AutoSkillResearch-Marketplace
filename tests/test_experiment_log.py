import json
from pathlib import Path
from scripts.experiment_log import create_empty_log, add_entry, prune_log, read_log


class TestCreateEmptyLog:
    def test_creates_valid_structure(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        data = json.loads(log_path.read_text())
        assert data["entries"] == []
        assert "lessons_summary" not in data


class TestAddEntry:
    def test_adds_entry(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        entry = {"iteration": 1, "commit": "abc1234", "hypothesis": "test",
                 "change_summary": "test change", "metrics": {}, "elo": {},
                 "outcome": "kept", "lessons": "it worked"}
        add_entry(log_path, entry)
        data = read_log(log_path)
        assert len(data["entries"]) == 1
        assert "timestamp" in data["entries"][0]


class TestPruneLog:
    def test_prunes_discarded_entries_fifo(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        for i in range(55):
            add_entry(log_path, {"iteration": i, "commit": f"d{i:04d}", "hypothesis": f"hyp {i}",
                "change_summary": f"change {i}", "metrics": {}, "elo": {},
                "outcome": "discarded", "lessons": ""})
        prune_log(log_path, max_discarded=50)
        data = read_log(log_path)
        discarded = [e for e in data["entries"] if e["outcome"] == "discarded"]
        assert len(discarded) == 50
        iterations = [e["iteration"] for e in discarded]
        assert min(iterations) == 5

    def test_keeps_kept_entries_during_prune(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        for i in range(10):
            add_entry(log_path, {"iteration": i, "commit": f"k{i:04d}", "hypothesis": "",
                "change_summary": "", "metrics": {}, "elo": {}, "outcome": "kept", "lessons": f"lesson {i}"})
        for i in range(10, 65):
            add_entry(log_path, {"iteration": i, "commit": f"d{i:04d}", "hypothesis": "",
                "change_summary": "", "metrics": {}, "elo": {}, "outcome": "discarded", "lessons": ""})
        prune_log(log_path, max_discarded=50)
        data = read_log(log_path)
        kept = [e for e in data["entries"] if e["outcome"] == "kept"]
        assert len(kept) == 10

    def test_keeps_keep_alias_entries_during_prune(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        for i in range(10):
            add_entry(log_path, {"iteration": i, "commit": f"k{i:04d}", "hypothesis": "",
                "change_summary": "", "metrics": {}, "elo": {}, "outcome": "keep", "lessons": f"lesson {i}"})
        for i in range(10, 65):
            add_entry(log_path, {"iteration": i, "commit": f"d{i:04d}", "hypothesis": "",
                "change_summary": "", "metrics": {}, "elo": {}, "outcome": "discarded", "lessons": ""})
        prune_log(log_path, max_discarded=50)
        data = read_log(log_path)
        kept = [e for e in data["entries"] if e["outcome"] == "keep"]
        assert len(kept) == 10

    def test_summarizes_old_kept_entries(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        for i in range(35):
            add_entry(log_path, {"iteration": i, "commit": f"k{i:04d}", "hypothesis": f"hyp {i}",
                "change_summary": f"change {i}", "metrics": {}, "elo": {},
                "outcome": "kept", "lessons": f"lesson {i}"})
        prune_log(log_path, max_discarded=50, max_kept_detailed=30)
        data = read_log(log_path)
        kept = [e for e in data["entries"] if e["outcome"] == "kept"]
        assert len(kept) == 30
        assert "lessons_summary" in data
        assert len(data["lessons_summary"]) == 5

    def test_summarizes_repo_schema_entries_without_blank_lessons(self, tmp_path):
        log_path = tmp_path / "log.json"
        create_empty_log(log_path)
        for i in range(35):
            add_entry(log_path, {
                "iteration": i,
                "commit": f"k{i:04d}",
                "hypothesis": f"hypothesis {i}",
                "metrics": {"eval_quality": 0.8},
                "elo": 1530 + i,
                "outcome": "keep",
                "reason": f"reason {i}",
            })
        prune_log(log_path, max_discarded=50, max_kept_detailed=30)
        data = read_log(log_path)
        assert "lessons_summary" in data
        assert len(data["lessons_summary"]) == 5
        assert all(not summary.endswith(": ") for summary in data["lessons_summary"])
        assert data["lessons_summary"][0] == "iter 0: reason 0"
