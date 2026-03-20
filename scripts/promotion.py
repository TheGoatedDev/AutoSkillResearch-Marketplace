"""Promotion decision tree: should a candidate skill version be kept or discarded?"""


def decide_promotion(config: dict, candidate_elo: float, matches_played: int,
                     metrics_old: dict[str, float], metrics_new: dict[str, float]) -> dict:
    min_matches = config.get("elo_minimum_matches", 5)
    if matches_played < min_matches:
        return {"decision": "defer", "reason": f"Only {matches_played}/{min_matches} matches played"}

    metric_configs = config.get("metrics", {})
    for metric_name, new_value in metrics_new.items():
        mc = metric_configs.get(metric_name, {})
        minimum = mc.get("minimum")
        if minimum is not None and new_value < minimum:
            return {"decision": "discard", "reason": f"Hard floor violation: {metric_name}={new_value:.3f} < minimum={minimum}"}

    elo_threshold = config.get("elo_confidence_threshold", 1520)
    if candidate_elo < elo_threshold:
        return {"decision": "discard", "reason": f"ELO {candidate_elo:.0f} < threshold {elo_threshold}"}

    any_improved = False
    for metric_name in metrics_new:
        old_val = metrics_old.get(metric_name, 0.0)
        new_val = metrics_new[metric_name]
        delta = new_val - old_val
        if delta > 0:
            any_improved = True
        elif delta < 0:
            mc = metric_configs.get(metric_name, {})
            tolerance = mc.get("tolerance", 0.0)
            if abs(delta) > tolerance:
                return {"decision": "discard", "reason": f"Tolerance exceeded: {metric_name} regressed by {abs(delta):.3f} > tolerance={tolerance}"}

    if not any_improved:
        return {"decision": "discard", "reason": "No metric improved"}

    return {"decision": "keep", "reason": "All checks passed"}


def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Promotion decision tree")
    parser.add_argument("--config", required=True, help="Path to eval config JSON")
    parser.add_argument("--elo", type=float, required=True)
    parser.add_argument("--matches", type=int, required=True)
    parser.add_argument("--metrics-old-file", required=True, help="Path to JSON file of old metrics")
    parser.add_argument("--metrics-new-file", required=True, help="Path to JSON file of new metrics")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text())
    result = decide_promotion(
        config=config,
        candidate_elo=args.elo,
        matches_played=args.matches,
        metrics_old=json.loads(Path(args.metrics_old_file).read_text()),
        metrics_new=json.loads(Path(args.metrics_new_file).read_text()),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
