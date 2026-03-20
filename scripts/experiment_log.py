"""Experiment log management with pruning and cap enforcement."""

import json
from datetime import datetime, timezone
from pathlib import Path


def create_empty_log(log_path: Path) -> None:
    log_path.write_text(json.dumps({"entries": []}, indent=2))


def read_log(log_path: Path) -> dict:
    return json.loads(log_path.read_text())


def add_entry(log_path: Path, entry: dict) -> None:
    data = read_log(log_path)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    data["entries"].append(entry)
    log_path.write_text(json.dumps(data, indent=2))


def prune_log(log_path: Path, max_discarded: int = 50, max_kept_detailed: int = 30) -> None:
    data = read_log(log_path)
    entries = data["entries"]
    kept = [e for e in entries if e["outcome"] == "kept"]
    discarded = [e for e in entries if e["outcome"] != "kept"]

    if len(discarded) > max_discarded:
        discarded = discarded[-max_discarded:]

    if len(kept) > max_kept_detailed:
        to_summarize = kept[: len(kept) - max_kept_detailed]
        kept = kept[len(kept) - max_kept_detailed:]
        summaries = data.get("lessons_summary", [])
        for entry in to_summarize:
            summaries.append(f"iter {entry['iteration']}: {entry.get('lessons', entry.get('change_summary', ''))}")
        data["lessons_summary"] = summaries

    data["entries"] = kept + discarded
    log_path.write_text(json.dumps(data, indent=2))
