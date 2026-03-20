import json
import pytest
from pathlib import Path
from scripts.elo import compute_elo_update, update_elo_state, create_initial_elo_state


class TestComputeEloUpdate:
    def test_win_increases_rating(self):
        new_a, new_b = compute_elo_update(1500, 1500, "A", k=32)
        assert new_a > 1500
        assert new_b < 1500

    def test_loss_decreases_rating(self):
        new_a, new_b = compute_elo_update(1500, 1500, "B", k=32)
        assert new_a < 1500
        assert new_b > 1500

    def test_draw_stays_near_equal(self):
        new_a, new_b = compute_elo_update(1500, 1500, "draw", k=32)
        assert abs(new_a - 1500) < 1
        assert abs(new_b - 1500) < 1

    def test_underdog_win_larger_gain(self):
        gain_underdog, _ = compute_elo_update(1400, 1600, "A", k=32)
        gain_favorite, _ = compute_elo_update(1600, 1400, "A", k=32)
        assert (gain_underdog - 1400) > (gain_favorite - 1600)

    def test_symmetric(self):
        new_a, new_b = compute_elo_update(1500, 1500, "A", k=32)
        assert abs((new_a - 1500) + (new_b - 1500)) < 0.01


class TestCreateInitialEloState:
    def test_creates_initial_state(self):
        state = create_initial_elo_state("abc1234")
        assert state["current_champion"]["commit"] == "abc1234"
        assert state["current_champion"]["elo"] == 1500
        assert state["current_champion"]["matches_played"] == 0
        assert state["history"] == []
        assert state["candidate"] is None


class TestUpdateEloState:
    def test_updates_candidate_after_match(self, tmp_path):
        elo_path = tmp_path / "elo.json"
        initial = create_initial_elo_state("champ01")
        elo_path.write_text(json.dumps(initial))
        result = update_elo_state(elo_path=elo_path, candidate_commit="cand001", match_result="A")
        assert result["candidate"]["elo"] > 1500
        assert result["candidate"]["matches_played"] == 1

    def test_promotion_updates_champion(self, tmp_path):
        elo_path = tmp_path / "elo.json"
        state = create_initial_elo_state("champ01")
        state["candidate"] = {"commit": "cand001", "elo": 1530, "matches_played": 6}
        elo_path.write_text(json.dumps(state))
        result = update_elo_state(elo_path=elo_path, candidate_commit="cand001", match_result="promote")
        assert result["current_champion"]["commit"] == "cand001"
        assert result["candidate"] is None
        assert len(result["history"]) == 1

    def test_discard_clears_candidate(self, tmp_path):
        elo_path = tmp_path / "elo.json"
        state = create_initial_elo_state("champ01")
        state["candidate"] = {"commit": "cand001", "elo": 1490, "matches_played": 6}
        elo_path.write_text(json.dumps(state))
        result = update_elo_state(elo_path=elo_path, candidate_commit="cand001", match_result="discard")
        assert result["current_champion"]["commit"] == "champ01"
        assert result["candidate"] is None
        assert result["history"][-1]["outcome"] == "discarded"
