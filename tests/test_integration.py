"""Integration test: exercises all Python scripts in sequence, simulating one loop iteration."""

import json
from pathlib import Path
from scripts.elo import create_initial_elo_state, update_elo_state
from scripts.metrics import compute_eval_quality, compute_trigger_accuracy, compute_token_efficiency
from scripts.promotion import decide_promotion
from scripts.experiment_log import create_empty_log, add_entry, prune_log, read_log
from scripts.changelog import generate_changelog
from scripts.lockfile import acquire_lock, release_lock, is_locked


def test_full_loop_simulation(tmp_path):
    """Simulate one complete iteration of the autoresearch loop using scripts."""
    skill_dir = tmp_path / "plugins" / "test-skill"
    skill_dir.mkdir(parents=True)
    experiments_dir = skill_dir / "experiments"
    experiments_dir.mkdir()
    evals_dir = skill_dir / "evals"
    evals_dir.mkdir()

    # 1. Setup: create initial state files
    lock_path = tmp_path / ".autoresearch.lock"
    elo_path = experiments_dir / "elo.json"
    log_path = experiments_dir / "log.json"

    assert acquire_lock(lock_path, skill="test-skill")
    assert is_locked(lock_path)

    elo_state = create_initial_elo_state("initial01")
    elo_path.write_text(json.dumps(elo_state, indent=2))
    create_empty_log(log_path)

    config = {
        "metrics": {
            "eval_quality": {"tolerance": 0.02, "minimum": 0.6},
            "trigger_accuracy": {"tolerance": 0.05, "minimum": 0.7},
        },
        "elo_confidence_threshold": 1520,
        "elo_minimum_matches": 5,
    }
    (evals_dir / "config.json").write_text(json.dumps(config))

    # 2. Simulate eval results (as if subagents ran)
    match_results = [
        {"winner": "candidate"},
        {"winner": "candidate"},
        {"winner": "candidate"},
        {"winner": "draw"},
        {"winner": "champion"},
        {"winner": "candidate"},
    ]
    trigger_results = [
        {"expected_trigger": True, "actual_trigger": True},
        {"expected_trigger": True, "actual_trigger": True},
        {"expected_trigger": True, "actual_trigger": True},
        {"expected_trigger": False, "actual_trigger": False},
        {"expected_trigger": False, "actual_trigger": False},
        {"expected_trigger": True, "actual_trigger": True},
    ]

    # 3. Compute metrics
    eval_quality = compute_eval_quality(match_results)
    trigger_accuracy = compute_trigger_accuracy(trigger_results)
    token_efficiency = compute_token_efficiency(150, 120)

    assert eval_quality > 0.6
    assert trigger_accuracy == 1.0
    assert token_efficiency > 0.5

    # 4. Update ELO for each match
    candidate_commit = "cand0001"
    for match in match_results:
        winner = "A" if match["winner"] == "candidate" else "B" if match["winner"] == "champion" else "draw"
        update_elo_state(elo_path, candidate_commit, winner)

    elo_state = json.loads(elo_path.read_text())
    assert elo_state["candidate"]["matches_played"] == 6
    candidate_elo = elo_state["candidate"]["elo"]

    # 5. Promotion decision
    metrics_old = {"eval_quality": 0.50, "trigger_accuracy": 0.85}
    metrics_new = {"eval_quality": eval_quality, "trigger_accuracy": trigger_accuracy}
    decision = decide_promotion(
        config=config,
        candidate_elo=candidate_elo,
        matches_played=6,
        metrics_old=metrics_old,
        metrics_new=metrics_new,
    )
    assert decision["decision"] == "keep"

    # 6. Log the result
    add_entry(log_path, {
        "iteration": 1,
        "commit": candidate_commit,
        "hypothesis": "Test hypothesis",
        "change_summary": "Test change",
        "metrics": {
            "eval_quality": {"old": 0.50, "new": eval_quality, "delta": eval_quality - 0.50},
            "trigger_accuracy": {"old": 0.85, "new": trigger_accuracy, "delta": trigger_accuracy - 0.85},
        },
        "elo": {"starting": 1500, "final": candidate_elo, "matches": 6, "wins": 4, "losses": 1, "draws": 1},
        "outcome": "kept",
        "lessons": "Test lesson",
    })
    log_data = read_log(log_path)
    assert len(log_data["entries"]) == 1

    # 7. Generate changelog
    changelog = generate_changelog("test-skill", log_data, version="v1.0.1")
    assert "v1.0.1" in changelog
    assert "Test change" in changelog

    # 8. Promote in ELO
    update_elo_state(elo_path, candidate_commit, "promote")
    final_elo = json.loads(elo_path.read_text())
    assert final_elo["current_champion"]["commit"] == candidate_commit
    assert final_elo["candidate"] is None

    # 9. Release lock
    release_lock(lock_path)
    assert not is_locked(lock_path)
