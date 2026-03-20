"""ELO rating system for head-to-head skill comparisons."""

import json
from datetime import datetime, timezone
from pathlib import Path

INITIAL_ELO = 1500
DEFAULT_K_FACTOR = 32


def compute_elo_update(rating_a: float, rating_b: float, winner: str, k: int = DEFAULT_K_FACTOR) -> tuple[float, float]:
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 - expected_a
    if winner == "A":
        score_a, score_b = 1.0, 0.0
    elif winner == "B":
        score_a, score_b = 0.0, 1.0
    else:
        score_a, score_b = 0.5, 0.5
    new_a = rating_a + k * (score_a - expected_a)
    new_b = rating_b + k * (score_b - expected_b)
    return new_a, new_b


def create_initial_elo_state(champion_commit: str) -> dict:
    return {
        "current_champion": {
            "commit": champion_commit,
            "elo": INITIAL_ELO,
            "matches_played": 0,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        },
        "candidate": None,
        "history": [],
    }


def update_elo_state(elo_path: Path, candidate_commit: str, match_result: str) -> dict:
    state = json.loads(elo_path.read_text())
    if match_result == "promote":
        candidate = state["candidate"]
        state["history"].append({"commit": candidate["commit"], "final_elo": candidate["elo"], "outcome": "promoted"})
        state["current_champion"] = {"commit": candidate["commit"], "elo": candidate["elo"], "matches_played": candidate["matches_played"], "promoted_at": datetime.now(timezone.utc).isoformat()}
        state["candidate"] = None
    elif match_result == "discard":
        candidate = state["candidate"]
        if candidate:
            state["history"].append({"commit": candidate["commit"], "final_elo": candidate["elo"], "outcome": "discarded"})
        state["candidate"] = None
    else:
        if state["candidate"] is None or state["candidate"]["commit"] != candidate_commit:
            state["candidate"] = {"commit": candidate_commit, "elo": 1500, "matches_played": 0}
        champion_elo = state["current_champion"]["elo"]
        candidate_elo = state["candidate"]["elo"]
        new_candidate, new_champion = compute_elo_update(candidate_elo, champion_elo, match_result)
        state["candidate"]["elo"] = new_candidate
        state["candidate"]["matches_played"] += 1
        state["current_champion"]["elo"] = new_champion
        state["current_champion"]["matches_played"] += 1
    elo_path.write_text(json.dumps(state, indent=2))
    return state


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ELO rating operations")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create initial ELO state")
    init.add_argument("--elo-path", required=True)
    init.add_argument("--champion-commit", required=True)

    update = sub.add_parser("update", help="Update ELO after match/decision")
    update.add_argument("--elo-path", required=True)
    update.add_argument("--candidate-commit", required=True)
    update.add_argument("--result", required=True, choices=["A", "B", "draw", "promote", "discard"])

    args = parser.parse_args()

    if args.command == "init":
        state = create_initial_elo_state(args.champion_commit)
        Path(args.elo_path).write_text(json.dumps(state, indent=2))
        print(json.dumps(state, indent=2))
    elif args.command == "update":
        state = update_elo_state(Path(args.elo_path), args.candidate_commit, args.result)
        print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
