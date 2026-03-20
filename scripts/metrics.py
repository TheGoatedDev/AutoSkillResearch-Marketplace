"""Compute normalized metrics from raw eval data."""


def compute_eval_quality(matches: list[dict]) -> float:
    if not matches:
        return 0.0
    score = sum(1.0 if m["winner"] == "candidate" else 0.5 if m["winner"] == "draw" else 0.0 for m in matches)
    return score / len(matches)


def compute_trigger_accuracy(cases: list[dict]) -> float:
    if not cases:
        return 0.0
    correct = sum(1 for c in cases if c["expected_trigger"] == c["actual_trigger"])
    return correct / len(cases)


def compute_token_efficiency(champion_avg_tokens: int, candidate_avg_tokens: int) -> float:
    if candidate_avg_tokens == 0:
        return 0.5
    ratio = champion_avg_tokens / candidate_avg_tokens
    return min(ratio, 2.0) / 2.0


def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Compute metrics from raw eval data")
    parser.add_argument("--matches-file", help="Path to JSON file of match results")
    parser.add_argument("--triggers-file", help="Path to JSON file of trigger results")
    parser.add_argument("--champion-tokens", type=int, default=0)
    parser.add_argument("--candidate-tokens", type=int, default=0)
    args = parser.parse_args()

    result = {}
    if args.matches_file:
        matches = json.loads(Path(args.matches_file).read_text())
        result["eval_quality"] = compute_eval_quality(matches)
    if args.triggers_file:
        triggers = json.loads(Path(args.triggers_file).read_text())
        result["trigger_accuracy"] = compute_trigger_accuracy(triggers)
    if args.champion_tokens and args.candidate_tokens:
        result["token_efficiency"] = compute_token_efficiency(args.champion_tokens, args.candidate_tokens)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
