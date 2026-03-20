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
