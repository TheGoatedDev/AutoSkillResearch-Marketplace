from scripts.changelog import generate_changelog


class TestGenerateChangelog:
    def test_empty_log(self):
        result = generate_changelog("my-skill", {"entries": []})
        assert "# Changelog" in result
        assert "my-skill" in result

    def test_kept_entries_appear(self):
        log = {"entries": [
            {"iteration": 1, "timestamp": "2026-03-20T22:15:00Z", "commit": "abc1234",
             "change_summary": "Added step numbering",
             "metrics": {"eval_quality": {"old": 0.72, "new": 0.78, "delta": 0.06}},
             "outcome": "kept"}
        ]}
        result = generate_changelog("my-skill", log, version="1.0.1")
        assert "1.0.1" in result
        assert "Added step numbering" in result
        assert "0.72" in result
        assert "0.78" in result

    def test_discarded_entries_excluded(self):
        log = {"entries": [
            {"iteration": 1, "outcome": "discarded", "change_summary": "Bad change"},
            {"iteration": 2, "outcome": "kept", "change_summary": "Good change",
             "timestamp": "2026-03-20T22:15:00Z", "commit": "abc1234",
             "metrics": {"eval_quality": {"old": 0.70, "new": 0.75, "delta": 0.05}}}
        ]}
        result = generate_changelog("my-skill", log)
        assert "Bad change" not in result
        assert "Good change" in result

    def test_multiple_kept_entries_ordered_newest_first(self):
        log = {"entries": [
            {"iteration": 1, "outcome": "kept", "change_summary": "First",
             "timestamp": "2026-03-20T20:00:00Z", "commit": "aaa",
             "metrics": {"eval_quality": {"old": 0.70, "new": 0.75, "delta": 0.05}}},
            {"iteration": 2, "outcome": "kept", "change_summary": "Second",
             "timestamp": "2026-03-20T21:00:00Z", "commit": "bbb",
             "metrics": {"eval_quality": {"old": 0.75, "new": 0.80, "delta": 0.05}}}
        ]}
        result = generate_changelog("my-skill", log)
        second_pos = result.index("Second")
        first_pos = result.index("First")
        assert second_pos < first_pos
